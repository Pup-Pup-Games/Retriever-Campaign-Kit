#!/usr/bin/env python
r"""
build_gazetteer.py — render the map gazetteer(s) for a Stonetop play group.

Where build_graph.py models the *social* graph, this models *space*. It crawls a
group's place notes (groups/<group>/world/places/*.md), reads the map frontmatter
(map / key / zone / region) and the `## Map / Location` block on each, and writes one
gazetteer per map into groups/<group>/world/maps/<map-slug>.md — a keyed index that
ties a drawn map image (attachments/<map-slug>.*) to the text Claude reasons over when
prepping a session.

The contract is the place-note frontmatter plus two prose sections:

    ---
    map: stonetop-steading     # which drawn map this location sits on
    key: 3                     # the number/label on that map (steading style)
    zone: C2                   # OR a grid cell on a regional map
    region: The Steading       # human region name
    ---
    *one-line description*     # the italic line under the H1
    ## Map / Location          # what's here / hidden / visible / exits / who's present
    ## Relationships           # spatial relations (adjacent-to, travel-to, …) are pulled in

Place notes with an empty `map:` are reported as unmapped, not written. A place's
spatial relationships (adjacency, direction, travel time) are surfaced under each entry
so the gazetteer reads as a self-contained briefing.

Usage:
  python build_gazetteer.py --group your-campaign
  python build_gazetteer.py --group your-campaign --map stonetop-steading
  python build_gazetteer.py --all
  python build_gazetteer.py --group your-campaign --print     # write nothing, print to stdout

Pure stdlib; no dependencies. Mirrors build_graph.py so the two generators feel the same.
"""
import argparse, os, re, sys

try:  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stonetop_lib import REPO, display_title

# Relations worth showing in a *map* briefing (everything else is the social graph's job).
MAP_RELATIONS = {
    "adjacent-to", "near", "north-of", "south-of", "east-of", "west-of",
    "above", "below", "overlooks", "overlooked-by", "travel-to",
    "part-of", "has-part", "located-in", "location-of",
}
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".svg")

REL_LINE = re.compile(
    r"^\s*-\s*([A-Za-z][\w-]*)\s*::\s*\[\[([^\]]+)\]\]\s*(?:[—–-]\s*(.*))?$")


def fm_fields(fm):
    """Pull the flat frontmatter fields we care about into a dict."""
    out = {}
    for key in ("type", "status", "map", "key", "zone", "region"):
        # [ \t]* not \s* — \s would cross the newline and swallow the next line on empty fields
        m = re.search(rf"^{key}:[ \t]*(.*)$", fm, re.MULTILINE)
        out[key] = (m.group(1).strip().strip('"').strip("'") if m else "")
    return out


def section(text, heading):
    """Return the raw body lines of a `## heading` section (minus comments/placeholders)."""
    sec = re.search(rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)", text,
                    re.MULTILINE | re.DOTALL)
    if not sec:
        return []
    body, keep, in_comment = sec.group(1).splitlines(), [], False
    for ln in body:
        s = ln.strip()
        if "<!--" in s:
            in_comment = "-->" not in s
            continue
        if in_comment:
            in_comment = "-->" not in s
            continue
        if s in ("", "-", "- "):
            continue
        keep.append(ln.rstrip())
    return keep


def parse_place(path):
    """Return a dict describing one place note, or None if it isn't a place."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm = ""
    m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if m:
        fm = m.group(1)
    fields = fm_fields(fm)
    if fields["type"].lower() != "place":
        return None
    hm = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    name = hm.group(1).strip() if hm else os.path.splitext(os.path.basename(path))[0]
    dm = re.search(r"^\*(.+?)\*\s*$", text, re.MULTILINE)
    desc = dm.group(1).strip() if dm else ""
    rels = []
    for ln in section(text, "Relationships"):
        lm = REL_LINE.match(ln)
        if lm:
            rel = lm.group(1).strip().lower()
            if rel in MAP_RELATIONS:
                rels.append((rel, lm.group(2).split("|")[0].split("#")[0].strip(),
                             (lm.group(3) or "").strip()))
    return {
        "name": name, "desc": desc, "fields": fields,
        "loc": section(text, "Map / Location"), "rels": rels,
        "fname": os.path.splitext(os.path.basename(path))[0],
    }


def collect(group):
    """Walk a group's place notes -> (places_by_map, unmapped_names)."""
    pdir = os.path.join(REPO, "groups", group, "world", "places")
    if not os.path.isdir(pdir):
        sys.exit(f"No places dir: {pdir}")
    by_map, unmapped = {}, []
    for fn in sorted(os.listdir(pdir)):
        if not fn.endswith(".md"):
            continue
        p = parse_place(os.path.join(pdir, fn))
        if not p:
            continue
        mp = p["fields"]["map"]
        if mp:
            by_map.setdefault(mp, []).append(p)
        else:
            unmapped.append(p["name"])
    return by_map, unmapped


def key_sort(p):
    """Numeric keys first (ascending), then alpha keys, then unkeyed — stable by name."""
    k = p["fields"]["key"]
    if k.isdigit():
        return (0, int(k), "")
    if k:
        return (1, 0, k.lower())
    return (2, 0, p["name"].lower())


def image_link(group, slug, out_path):
    """Markdown for the drawn map image if present in attachments/, else a TODO line."""
    adir = os.path.join(REPO, "attachments")
    for ext in IMAGE_EXTS:
        cand = os.path.join(adir, slug + ext)
        if os.path.exists(cand):
            rel = os.path.relpath(cand, os.path.dirname(out_path)).replace("\\", "/")
            return f"![{slug}]({rel})"
    return (f"> _Drop the keyed map image at_ `attachments/{slug}.png` _(or .jpg/.svg) "
            "and it embeds here. Number the locations on it to match the `key:` column._")


def render_map(group, slug, places, out_path):
    places = sorted(places, key=key_sort)
    L = [f"# Gazetteer — {display_title(group)} · {slug}", ""]
    L.append("<!-- GENERATED by /retriever-map (_tools/build_gazetteer.py). Do not edit by "
             "hand;\n     edit the place notes' frontmatter + `## Map / Location` blocks, "
             "then regenerate. -->")
    L.append("")
    L.append(image_link(group, slug, out_path))
    L.append("")

    # ---- key table ----
    L.append("| Key | Location | Region / Zone | Status | What it is |")
    L.append("|---|---|---|---|---|")
    for p in places:
        f = p["fields"]
        key = f["key"] or "—"
        rz = " · ".join(x for x in (f["region"], f["zone"]) if x) or "—"
        link = f"[[{p['fname']}|{p['name']}]]"
        L.append(f"| {key} | {link} | {rz} | {f['status'] or '—'} | {p['desc'] or '—'} |")
    L.append("")

    # ---- per-location detail ----
    L.append("## Locations in detail")
    L.append("")
    for p in places:
        f = p["fields"]
        head = f"### {f['key'] + '. ' if f['key'] else ''}{p['name']}"
        tags = " · ".join(x for x in (f["region"], f["zone"], f["status"]) if x)
        L.append(head + (f"  \n*{tags}*" if tags else ""))
        if p["desc"]:
            L.append(f"\n{p['desc']}")
        if p["loc"]:
            L.append("")
            L.extend(p["loc"])
        if p["rels"]:
            L.append("")
            L.append("**Connections:**")
            for rel, tgt, note in p["rels"]:
                L.append(f"- {rel} → [[{tgt}]]" + (f" — {note}" if note else ""))
        L.append("")
    return "\n".join(L).rstrip() + "\n"


def run(group, only_map, do_print):
    by_map, unmapped = collect(group)
    if not by_map:
        print(f"[{group}] no mapped places yet "
              "(set `map:` in a place note's frontmatter).")
    maps_dir = os.path.join(REPO, "groups", group, "world", "maps")
    for slug, places in sorted(by_map.items()):
        if only_map and slug != only_map:
            continue
        out = os.path.join(maps_dir, f"{slug}.md")
        doc = render_map(group, slug, places, out)
        if do_print:
            print(doc)
            continue
        os.makedirs(maps_dir, exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(doc)
        print(f"Wrote {os.path.relpath(out, REPO)}  ({len(places)} locations)")
    if unmapped and not do_print:
        print(f"[{group}] unmapped places (no `map:` set): " + ", ".join(unmapped))


def main():
    ap = argparse.ArgumentParser(description="Build the Stonetop map gazetteer(s).")
    ap.add_argument("--group", help="group folder name, e.g. your-campaign")
    ap.add_argument("--map", dest="only_map", help="build only this map slug")
    ap.add_argument("--all", action="store_true", help="build every group under groups/")
    ap.add_argument("--print", dest="do_print", action="store_true",
                    help="print to stdout instead of writing files")
    args = ap.parse_args()

    if args.all:
        groups_dir = os.path.join(REPO, "groups")
        for g in sorted(os.listdir(groups_dir)):
            if os.path.isdir(os.path.join(groups_dir, g)):
                run(g, args.only_map, args.do_print)
        return
    if not args.group:
        ap.error("provide --group <name> or --all")
    run(args.group, args.only_map, args.do_print)


if __name__ == "__main__":
    main()
