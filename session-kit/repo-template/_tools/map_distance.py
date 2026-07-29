#!/usr/bin/env python
"""
map_distance.py — answer "how far / how long from X to Y" on a keyed SVG map.

The model is a hybrid (see the retriever-distance skill):

  1. Geometry + scale (automatic).  Every location marker on the map carries a
     transparent <ellipse>/<circle> whose center is the location's anchor point.
     The `keys` layer carries a `data-map-scale` (userspace units per hour of
     direct overland travel). Straight-line distance between two anchors / scale
     gives an estimated direct travel time for ANY pair — including new pins the
     GM adds later, with no extra data entry.

  2. Explicit edges (exact, optional).  Known/road/multi-day journeys that the
     straight line gets wrong are recorded as `travel-to` relationships on the
     place notes (the same vocabulary /retriever-relate already uses), with the
     time/route in the note. When a --group is given, those are loaded and a
     shortest path over them is preferred whenever one exists.

So: explicit edge if we have one, otherwise a clearly-labelled geometric estimate.

Markers flagged `data-offmap="true"` (off-map directional labels, roads, regions
with no single point) are excluded from geometry — ask about them via edges only.

Usage:
  python map_distance.py --svg attachments/the-vicinity.svg --from Stonetop --to "The Maw"
  python map_distance.py --map the-vicinity --group your-campaign --from Stonetop --to "Red Grove"
  python map_distance.py --svg attachments/the-vicinity.svg --list
  python map_distance.py --svg attachments/the-vicinity.svg --calibrate   # QA vs data-distance

Pure stdlib.
"""
import argparse, math, os, re, sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import stonetop_lib as lib
except Exception:
    lib = None

SVG = "{http://www.w3.org/2000/svg}"
INK = "{http://www.inkscape.org/namespaces/inkscape}"


# --------------------------------------------------------------- SVG geometry
def _translate(g):
    tr = g.get("transform") or ""
    m = re.search(r"translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)", tr)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"matrix\(([^)]+)\)", tr)
    if m:
        v = [float(x) for x in re.split(r"[ ,]+", m.group(1).strip())]
        return v[4], v[5]
    return 0.0, 0.0


def _anchor(g):
    """Absolute (x, y) of a marker's anchor: an inner element labelled 'anchor'
    if present, else the first ellipse/circle center, else the first text origin."""
    tx, ty = _translate(g)
    # explicit anchor child (lets an AREA pin its measuring point precisely)
    for el in g.iter():
        if (el.get(INK + "label") or "").lower() == "anchor":
            cx = el.get("cx")
            if cx is not None:
                return tx + float(cx), ty + float(el.get("cy"))
    for el in g.iter():
        tag = el.tag.split("}")[-1]
        if tag in ("ellipse", "circle") and el.get("cx") is not None:
            return tx + float(el.get("cx")), ty + float(el.get("cy"))
    for el in g.iter():
        if el.tag.split("}")[-1] == "text" and el.get("x") is not None:
            return tx + float(el.get("x")), ty + float(el.get("y"))
    return None


def load_map(svg_path):
    """Return (locations, scale, origin). locations: name -> dict(xy, offmap, distance)."""
    root = ET.parse(svg_path).getroot()
    scale, origin = None, None
    locs = {}
    for g in root.iter(SVG + "g"):
        if g.get(INK + "label") == "keys":
            if g.get("data-map-scale"):
                scale = float(g.get("data-map-scale"))
            origin = g.get("data-map-origin")
        place = g.get("data-place")
        if not place:
            continue
        locs[place] = {
            "xy": _anchor(g),
            "offmap": g.get("data-offmap") == "true",
            "distance": g.get("data-distance"),       # optional ground-truth time
            "distance_from": g.get("data-distance-from"),  # origin for it (else map origin)
            "key": g.get("data-key"),
        }
    return locs, scale, origin


def resolve(names, name):
    """Case-insensitive / 'the'-insensitive lookup of a name in any iterable of names.
    Exact (normalized) match wins; a loose contains match is the fallback."""
    def norm(s):
        return re.sub(r"^the\s+", "", s.strip().lower())
    want = norm(name)
    names = list(names)
    for k in names:
        if norm(k) == want:
            return k
    for k in names:              # loose contains match
        if want in norm(k):
            return k
    return None


# ------------------------------------------------------------ explicit edges
HOURS = {"hour": 1, "hr": 1, "day": 24}


def parse_time(text):
    """'4-6 hours' -> 5.0 ; '2 days' -> 48.0 ; returns midpoint hours or None."""
    if not text:
        return None
    m = re.search(r"([\d.]+)\s*(?:[-–]\s*([\d.]+))?\s*(hour|hr|day)", text.lower())
    if not m:
        return None
    lo = float(m.group(1))
    hi = float(m.group(2)) if m.group(2) else lo
    return (lo + hi) / 2 * HOURS[m.group(3).rstrip("s") if m.group(3) in HOURS
                                 else m.group(3)]


def load_edges(group):
    """Explicit travel-to edges from the group's place notes: {(a,b): hours}."""
    edges = {}
    if not (lib and group):
        return edges
    try:
        places_dir = os.path.join(lib.group_dir(group), "world", "places")
        files = [os.path.join(places_dir, f) for f in os.listdir(places_dir)
                 if f.endswith(".md")]
    except FileNotFoundError:
        return edges
    rel_re = re.compile(r"^\s*-\s*travel-to\s*::\s*\[\[([^\]]+)\]\]\s*(?:[—–-]\s*(.*))?$",
                        re.IGNORECASE)
    for fp in files:
        text = open(fp, encoding="utf-8").read()
        src = lib.h1_of(text) or os.path.splitext(os.path.basename(fp))[0]
        for line in text.splitlines():
            m = rel_re.match(line)
            if not m:
                continue
            dst = m.group(1).split("|")[0].split("#")[0].strip()
            hrs = parse_time(m.group(2) or "")
            if hrs is not None:
                edges[(src, dst)] = hrs
                edges.setdefault((dst, src), hrs)
    return edges


def shortest_path(edges, a, b):
    """Dijkstra over explicit edges. Returns (hours, [path]) or (None, None)."""
    import heapq
    nodes = {x for e in edges for x in e}
    if a not in nodes or b not in nodes:
        return None, None
    dist = {a: 0.0}
    prev = {}
    pq = [(0.0, a)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == b:
            path = [b]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return d, list(reversed(path))
        if d > dist.get(u, math.inf):
            continue
        for (x, y), w in edges.items():
            if x == u and d + w < dist.get(y, math.inf):
                dist[y] = d + w
                prev[y] = u
                heapq.heappush(pq, (d + w, y))
    return None, None


# --------------------------------------------------------------------- modes
def fmt_hours(h):
    if h is None:
        return "?"
    if h >= 24:
        return f"{h/24:.1f} days ({h:.0f}h)"
    return f"{h:.1f}h"


def cmd_distance(locs, scale, edges, a_in, b_in):
    # 1) explicit edge / path — resolve names against the edge graph first, so a
    #    note/edge name ("Barrier Pass") isn't shadowed by a map label ("To Barrier Pass").
    edge_nodes = {x for e in edges for x in e}
    ea, eb = resolve(edge_nodes, a_in), resolve(edge_nodes, b_in)
    if ea and eb:
        hrs, path = shortest_path(edges, ea, eb)
        if hrs is not None:
            print(f"{ea} to {eb}: {fmt_hours(hrs)}  [explicit route: {' -> '.join(path)}]")
            return
    # 2) geometric estimate — resolve against the map markers
    a, b = resolve(locs, a_in), resolve(locs, b_in)
    if not a:
        sys.exit(f"Unknown location: {a_in!r}. Try --list.")
    if not b:
        sys.exit(f"Unknown location: {b_in!r}. Try --list.")
    pa, pb = locs[a]["xy"], locs[b]["xy"]
    if locs[a]["offmap"] or locs[b]["offmap"] or not pa or not pb:
        why = "off-map / no point anchor" if (locs[a]["offmap"] or locs[b]["offmap"]) \
              else "missing anchor"
        sys.exit(f"No geometric estimate for {a} -> {b} ({why}); "
                 f"record a `travel-to` time in the notes instead.")
    units = math.dist(pa, pb)
    if not scale:
        sys.exit("Map has no data-map-scale; cannot estimate. Set it on the keys layer.")
    print(f"{a} to {b}: ~{fmt_hours(units/scale)}  "
          f"(straight-line estimate, {units:.0f} units; direct overland)")


def cmd_list(locs):
    print("On-map point locations (geometric):")
    for k in sorted(locs):
        if not locs[k]["offmap"] and locs[k]["xy"]:
            print(f"  {k}")
    off = sorted(k for k in locs if locs[k]["offmap"])
    if off:
        print("Off-map / edges-only (ask via travel-to notes):")
        for k in off:
            print(f"  {k}")


def cmd_calibrate(locs, scale, origin):
    """Compare the geometric estimate to each marker's data-distance ground truth.

    Each marker's distance is measured from its own data-distance-from origin when set,
    else from the map's data-map-origin, so a leg quoted from a different start (e.g. the
    Ruined Tower from the Crossroads) calibrates correctly instead of skewing the pace."""
    if not origin or origin not in locs:
        sys.exit("No data-map-origin set on the keys layer; cannot calibrate.")
    print(f"Calibration against data-distance (map origin = {origin}, scale = {scale} u/h):\n")
    print(f"  {'location':18s} {'from':14s} {'truth':>10s} {'est':>9s} {'units/h':>8s}")
    paces = []
    for k in sorted(locs):
        d = locs[k]
        if d["offmap"] or not d["xy"] or not d["distance"]:
            continue
        frm = resolve(locs, d["distance_from"]) if d["distance_from"] else origin
        if k == frm or not frm or not locs[frm]["xy"]:
            continue
        truth = parse_time(d["distance"])
        units = math.dist(locs[frm]["xy"], d["xy"])
        est = units / scale if scale else None
        pace = units / truth if truth else None
        if pace:
            paces.append(pace)
        print(f"  {k:18s} {frm:14s} {d['distance']:>10s} {fmt_hours(est):>9s} "
              f"{pace:>8.1f}" if pace else
              f"  {k:18s} {frm:14s} {d['distance']:>10s} {fmt_hours(est):>9s} {'?':>8s}")
    if paces:
        mean = sum(paces) / len(paces)
        var = sum((p - mean) ** 2 for p in paces) / len(paces)
        print(f"\n  mean pace {mean:.1f} u/h  (current scale {scale}); "
              f"spread +/-{var**0.5:.1f}  -> straight-line is a ~{var**0.5/mean*100:.0f}% estimator.")
        print(f"  Tip: set data-map-scale to ~{mean:.0f} to center the estimates.")


def main():
    ap = argparse.ArgumentParser(description="Distance/time on a keyed SVG map.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--svg", help="path to the map SVG")
    src.add_argument("--map", help="map slug -> attachments/<slug>.svg")
    ap.add_argument("--group", help="load explicit travel-to edges from this group's notes")
    ap.add_argument("--from", dest="a", help="origin location")
    ap.add_argument("--to", dest="b", help="destination location")
    ap.add_argument("--list", action="store_true", help="list locations and exit")
    ap.add_argument("--calibrate", action="store_true", help="QA geometry vs data-distance")
    args = ap.parse_args()

    svg = args.svg or os.path.join("attachments", f"{args.map}.svg")
    if not os.path.exists(svg):
        sys.exit(f"No such map SVG: {svg}")
    locs, scale, origin = load_map(svg)
    edges = load_edges(args.group)

    if args.list:
        cmd_list(locs)
    elif args.calibrate:
        cmd_calibrate(locs, scale, origin)
    elif args.a and args.b:
        cmd_distance(locs, scale, edges, args.a, args.b)
    else:
        ap.error("give --from and --to, or --list, or --calibrate")


if __name__ == "__main__":
    main()
