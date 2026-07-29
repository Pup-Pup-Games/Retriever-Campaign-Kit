#!/usr/bin/env python
r"""
check_map.py — reconcile a drawn map's key layer against the place notes.

The gazetteer (build_gazetteer.py) ties text to a drawn map by a shared key: each place
note carries `key:` (or `zone:`) in its frontmatter, and the map image carries a matching
numbered/labelled marker. This script keeps the two honest. It parses the `keys` layer of
each map's SVG (attachments/<map-slug>.svg) and cross-checks it against the notes that set
`map: <slug>`, reporting drift in either direction:

  - a keyed note with no marker on the map        (you forgot to draw it)
  - a marker on the map with no keyed note         (orphan number)
  - duplicate keys among the notes, or the markers
  - a marker whose name disagrees with its note    (warning)

It only checks SVG maps — a PNG/JPG map has no readable key layer, so those are skipped
with a note. Same mechanical-sync spirit as build_graph / build_gazetteer.

Marker convention (in the SVG's `keys` layer, one <g> per location):
    <g inkscape:label="The Smithy" data-key="3" data-place="The Smithy">
      <title>The Smithy</title>
      <circle .../><text ...>3</text>
    </g>
Identity is read in this order — key: data-key → inkscape:label (if key-shaped) →
the marker's visible number; place: data-place → <title> → inkscape:label.

Usage:
  python check_map.py --group your-campaign
  python check_map.py --group your-campaign --map stonetop-steading
  python check_map.py --all
Exit code is 1 if any hard discrepancy is found (clean / warnings-only exit 0), so a skill
or hook can gate on it. Pure stdlib.
"""
import argparse, os, re, sys
import xml.etree.ElementTree as ET

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_gazetteer import collect          # places grouped by map slug
from stonetop_lib import REPO

SVG = "{http://www.w3.org/2000/svg}"
INK = "{http://www.inkscape.org/namespaces/inkscape}"
IDENT_RE = re.compile(r"^[A-Za-z]{0,2}\d{1,3}$")   # 3, 12, C2, B14 — a key or a zone
LAYER_IDS = {"keys", "key", "markers"}


def _norm(s):
    return " ".join((s or "").split())


def _visible_number(el):
    """The text shown on the marker (from <text> descendants only, never <title>)."""
    parts = ["".join(t.itertext()) for t in el.iter(SVG + "text")]
    return _norm(" ".join(parts))


def _title(el):
    t = el.find(SVG + "title")
    return _norm("".join(t.itertext())) if t is not None else ""


def marker_identity(el):
    """Return (ident, place) for one marker group, using the documented fallbacks."""
    label = _norm(el.get(INK + "label") or "")
    dkey = _norm(el.get("data-key") or "")
    dplace = _norm(el.get("data-place") or "")
    title = _title(el)
    number = _visible_number(el)

    ident = ""
    for cand in (dkey, label, number):
        if cand and IDENT_RE.match(cand):
            ident = cand
            break
    if not ident:
        ident = dkey or number or label  # last resort: take whatever's there

    place = ""
    for cand in (dplace, title, label):
        if cand and not IDENT_RE.match(cand):
            place = cand
            break
    return ident, place


def find_keys_layer(root):
    for el in root.iter():
        if not el.tag.endswith("}g") and el.tag != "g":
            continue
        if (el.get("id") or "").lower() in LAYER_IDS:
            return el
        if _norm(el.get(INK + "label") or "").lower() in LAYER_IDS:
            return el
    return None


def parse_markers(svg_path):
    """Return (markers, problem). markers is [(ident, place)]; problem is a string or None."""
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError as e:
        return [], f"could not parse SVG ({e})"
    layer = find_keys_layer(root)
    if layer is None:
        return [], "no 'keys' layer found (name a layer/group 'keys')"
    groups = [c for c in layer if c.tag.endswith("}g") or c.tag == "g"]
    if not groups:                                   # markers as bare <text>, no grouping
        groups = [t for t in layer if t.tag.endswith("}text") or t.tag == "text"]
    markers = []
    for g in groups:
        ident, place = marker_identity(g)
        if ident:
            markers.append((ident, place))
    return markers, None


def _dups(values):
    seen, dups = set(), set()
    for v in values:
        k = v.lower()
        (dups if k in seen else seen).add(k)
    return dups


def note_ident(p):
    """A note's map identifier: key if set, else zone, else '' (overview / unpinned)."""
    return p["fields"]["key"] or p["fields"]["zone"]


def reconcile_map(slug, places):
    """Return (lines, n_errors, n_warnings) for one map slug."""
    lines, errors, warns = [], 0, 0
    svg = os.path.join(REPO, "attachments", f"{slug}.svg")
    pinned = [p for p in places if note_ident(p)]
    overview = [p for p in places if not note_ident(p)]

    if not os.path.exists(svg):
        other = next((e for e in (".png", ".jpg", ".jpeg", ".webp")
                      if os.path.exists(os.path.join(REPO, "attachments", slug + e))), None)
        why = (f"only a {other} map (no readable key layer)" if other else "no map image yet")
        lines.append(f"  – skipped: {why}; {len(pinned)} keyed note(s) unchecked")
        return lines, errors, warns

    markers, problem = parse_markers(svg)
    if problem:
        lines.append(f"  ✗ {problem}")
        return lines, errors + 1, warns

    note_by_id = {note_ident(p).lower(): p for p in pinned}
    marker_by_id = {ident.lower(): place for ident, place in markers}

    for d in _dups([note_ident(p) for p in pinned]):
        lines.append(f"  ✗ duplicate key '{d}' on more than one note"); errors += 1
    for d in _dups([i for i, _ in markers]):
        lines.append(f"  ✗ duplicate marker '{d}' on the map"); errors += 1

    for nid, p in sorted(note_by_id.items()):
        if nid not in marker_by_id:
            lines.append(f"  ✗ note '{p['name']}' is keyed {nid.upper()} but has no marker")
            errors += 1
    for mid, mplace in sorted(marker_by_id.items()):
        if mid not in note_by_id:
            tag = f" (\"{mplace}\")" if mplace else ""
            lines.append(f"  ✗ marker {mid.upper()}{tag} has no keyed note"); errors += 1
        elif mplace:
            p = note_by_id[mid]
            if mplace.lower() not in (p["name"].lower(), p["fname"].lower()):
                lines.append(f"  ⚠ marker {mid.upper()} names \"{mplace}\" but key "
                             f"{mid.upper()} is note '{p['name']}'"); warns += 1

    if not errors and not warns:
        extra = f" (+{len(overview)} overview)" if overview else ""
        lines.append(f"  ✓ {len(markers)} markers ↔ {len(pinned)} keyed notes{extra}")
    return lines, errors, warns


def run(group, only_map=None):
    by_map, unmapped = collect(group)
    if only_map:
        by_map = {s: p for s, p in by_map.items() if s == only_map}
    print(f"[{group}]")
    total_err = total_warn = 0
    if not by_map:
        print("  (no mapped places yet)")
    for slug, places in sorted(by_map.items()):
        print(f" map: {slug}")
        lines, err, warn = reconcile_map(slug, places)
        for ln in lines:
            print(ln)
        total_err += err
        total_warn += warn
    if unmapped:
        print(f"  note: unmapped places (no `map:`): {', '.join(unmapped)}")
    return total_err, total_warn


def main():
    ap = argparse.ArgumentParser(description="Reconcile drawn maps against place notes.")
    ap.add_argument("--group", help="group folder name, e.g. your-campaign")
    ap.add_argument("--map", dest="only_map", help="check only this map slug")
    ap.add_argument("--all", action="store_true", help="check every group under groups/")
    args = ap.parse_args()

    groups = []
    if args.all:
        gdir = os.path.join(REPO, "groups")
        groups = [g for g in sorted(os.listdir(gdir))
                  if os.path.isdir(os.path.join(gdir, g))]
    elif args.group:
        groups = [args.group]
    else:
        ap.error("provide --group <name> or --all")

    err = warn = 0
    for g in groups:
        e, w = run(g, args.only_map)
        err += e
        warn += w
    print(f"\n{'✓ all maps reconcile' if not err else f'✗ {err} discrepancy(ies)'}"
          + (f", {warn} warning(s)" if warn else ""))
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
