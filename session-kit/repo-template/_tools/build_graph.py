#!/usr/bin/env python
r"""
build_graph.py — render the relationship map for a Stonetop play group.

Crawls a group's entity notes (groups/<group>/world/{people,places,things}/*.md and
groups/<group>/players/*.md), parses the typed relationships written as inline fields
in each note's `## Relationships` block, and writes a Mermaid `flowchart` into
groups/<group>/world/relationships.md. GitHub renders that diagram natively, and the
same links power Obsidian's graph view.

The inline-field syntax is the contract (one relationship per line):

    - loves :: [[Eirlys]] — since the Greenmother's bargain
      \_____/    \_____/   \__________________________________/
       relation   target    optional note (after — or -)

This is also a valid Dataview inline field, so Obsidian sees it too. Maintained by
the /retriever-relate skill; this script only reads it.

Usage:
  python build_graph.py --group seal
  python build_graph.py --group seal --focus "The Greenmother"
  python build_graph.py --all
  python build_graph.py --group seal --print     # write nothing, print to stdout

Pure stdlib; no dependencies. The relationship vocabulary below is the shared source
of truth referenced by the retriever-relate / retriever-graph skills.
"""
import argparse, os, re, sys

try:  # Windows consoles default to cp1252; the legend uses emoji.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stonetop_lib import (REPO, RELATION_CATEGORY, RECIPROCAL,  # shared vocabulary
                          frontmatter_field, display_title)

EDGE_COLOR = {
    "affinity": "#d81b60", "kin": "#1565c0", "allegiance": "#2e7d32",
    "antagonism": "#c62828", "spatial": "#757575", "other": "#9e9e9e",
}
# node fill / stroke by entity type (npc folded into "person")
NODE_STYLE = {
    "person": ("#e8f5e9", "#2e7d32"),
    "place":  ("#e3f2fd", "#1565c0"),
    "thing":  ("#fff3e0", "#e65100"),
    "player": ("#f3e5f5", "#6a1b9a"),
    "unknown": ("#f5f5f5", "#9e9e9e"),
}
TYPE_TO_CLASS = {"npc": "person", "person": "person", "place": "place",
                 "thing": "thing", "object": "thing", "player": "player"}

REL_LINE = re.compile(
    r"^\s*-\s*([A-Za-z][\w-]*)\s*::\s*\[\[([^\]]+)\]\]\s*(?:[—–-]\s*(.*))?$")


def parse_note(path):
    """Return (name, type, aliases, [(relation, target, note), ...]) for a note file."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    ntype, aliases = "unknown", []
    m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if m:
        fm = m.group(1)
        tm = re.search(r"^type:\s*(.+)$", fm, re.MULTILINE)
        if tm:
            ntype = tm.group(1).strip().strip('"').strip("'").lower()
        am = re.search(r"^aliases:\s*\[(.*?)\]\s*$", fm, re.MULTILINE)
        if am:
            aliases = [a.strip().strip('"').strip("'") for a in am.group(1).split(",") if a.strip()]
    hm = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    name = hm.group(1).strip() if hm else os.path.splitext(os.path.basename(path))[0]

    rels = []
    sec = re.search(r"^##\s+Relationships\s*\n(.*?)(?=^##\s|\Z)", text,
                    re.MULTILINE | re.DOTALL)
    if sec:
        for line in sec.group(1).splitlines():
            lm = REL_LINE.match(line)
            if not lm:
                continue
            rel = lm.group(1).strip().lower()
            target = lm.group(2).split("|")[0].split("#")[0].strip()
            note = (lm.group(3) or "").strip()
            rels.append((rel, target, note))
    return name, ntype, aliases, rels


def collect(group):
    """Walk a group's notes -> (nodes: name->type, edges: [(src,rel,dst,note)])."""
    base = os.path.join(REPO, "groups", group)
    if not os.path.isdir(base):
        sys.exit(f"No such group: {base}")
    dirs = [os.path.join(base, "world", "people"),
            os.path.join(base, "world", "places"),
            os.path.join(base, "world", "things"),
            os.path.join(base, "players")]
    nodes, alias_to_name, edges = {}, {}, []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"):
                continue
            name, ntype, aliases, rels = parse_note(os.path.join(d, fn))
            nodes[name] = TYPE_TO_CLASS.get(ntype, "unknown")
            for a in aliases:
                alias_to_name[a.lower()] = name
            for rel, target, note in rels:
                edges.append((name, rel, target, note))
    # resolve edge targets through aliases; add unknown targets as nodes
    resolved = []
    lower = {n.lower(): n for n in nodes}
    for src, rel, dst, note in edges:
        canon = lower.get(dst.lower()) or alias_to_name.get(dst.lower())
        if not canon:
            canon = dst
            nodes.setdefault(canon, "unknown")
        resolved.append((src, rel, canon, note))
    return nodes, resolved


def neighborhood(nodes, edges, focus):
    """Restrict to the focus entity and its direct neighbors."""
    match = next((n for n in nodes if n.lower() == focus.lower()), None)
    if not match:
        sys.exit(f"Focus entity not found: {focus}")
    keep, kept_edges = {match}, []
    for src, rel, dst, note in edges:
        if src == match or dst == match:
            keep.add(src); keep.add(dst); kept_edges.append((src, rel, dst, note))
    return {n: t for n, t in nodes.items() if n in keep}, kept_edges, match


def mermaid(nodes, edges):
    """Render nodes/edges as a Mermaid flowchart with type + category styling."""
    ids, out = {}, ["```mermaid", "flowchart LR"]
    for i, name in enumerate(sorted(nodes)):
        nid = f"N{i}"
        ids[name] = nid
        label = name.replace('"', "'")
        out.append(f'  {nid}["{label}"]')
    link_styles, seen = [], set()
    for src, rel, dst, note in edges:
        if src not in ids or dst not in ids:
            continue
        # collapse a reciprocal pair (A parent-of B / B child-of A) into one edge
        key = frozenset([(src, rel), (dst, RECIPROCAL.get(rel, rel))])
        if key in seen:
            continue
        seen.add(key)
        idx = len(link_styles)
        out.append(f'  {ids[src]} -->|{rel}| {ids[dst]}')
        cat = RELATION_CATEGORY.get(rel, "other")
        link_styles.append((idx, EDGE_COLOR[cat]))
    # node classes
    for cls, (fill, stroke) in NODE_STYLE.items():
        out.append(f"  classDef {cls} fill:{fill},stroke:{stroke},color:#1a1a1a;")
    by_class = {}
    for name, cls in nodes.items():
        by_class.setdefault(cls, []).append(ids[name])
    for cls, nid_list in by_class.items():
        out.append(f"  class {','.join(sorted(nid_list))} {cls};")
    for idx, color in link_styles:
        out.append(f"  linkStyle {idx} stroke:{color},stroke-width:2px;")
    out.append("```")
    return "\n".join(out)


LEGEND = (
    "**Nodes:** "
    "🟩 people · 🟦 places · 🟧 things · 🟪 players. "
    "**Edges:** "
    "affinity (pink) · kin (blue) · allegiance (green) · antagonism (red) · spatial (grey)."
)


def render_doc(group, title, body, focus=None):
    head = f"# Relationship Map — {title}"
    if focus:
        head += f"  ·  focus: {focus}"
    return (f"{head}\n\n"
            "<!-- GENERATED by /retriever-graph (_tools/build_graph.py). Do not edit by "
            "hand;\n     edit the `## Relationships` blocks on the entity notes instead, "
            "then regenerate. -->\n\n"
            f"{LEGEND}\n\n{body}\n")


def table_players(group, table):
    """Return the node names of the PCs whose `table:` field matches (the BFS seeds)."""
    pdir = os.path.join(REPO, "groups", group, "players")
    seeds = []
    if os.path.isdir(pdir):
        for fn in sorted(os.listdir(pdir)):
            if not fn.endswith(".md"):
                continue
            t = (frontmatter_field(os.path.join(pdir, fn), "table") or "").lower()
            if t == table.lower():
                seeds.append(os.path.splitext(fn)[0])
    return seeds


def table_subgraph(nodes, edges, seeds):
    """Keep a table's PCs and their direct (1-hop) neighbors, plus edges among them.

    Neighbors are computed from the seed set only (not a growing set), so the view stays
    a true 1-hop neighborhood and doesn't cascade across cross-table links into the
    other table's web.
    """
    seedset = {s for s in seeds if s in nodes}
    keep = set(seedset)
    for src, _rel, dst, _note in edges:
        if src in seedset:
            keep.add(dst)
        if dst in seedset:
            keep.add(src)
    nn = {k: v for k, v in nodes.items() if k in keep}
    ee = [e for e in edges if e[0] in keep and e[2] in keep]
    return nn, ee


def run(group, focus, do_print, table=None):
    nodes, edges = collect(group)
    if table:
        seeds = table_players(group, table)
        if not seeds:
            sys.exit(f"No PCs with table '{table}' in group '{group}'.")
        nodes, edges = table_subgraph(nodes, edges, seeds)
    if focus:
        nodes, edges, match = neighborhood(nodes, edges, focus)
        focus = match
    body = mermaid(nodes, edges) if nodes else "_No entities with relationships yet._"
    label = focus or (f"{table} table" if table else None)
    doc = render_doc(group, display_title(group, table), body, label)
    if do_print:
        print(doc)
        return
    fname = f"relationships-{table}.md" if table else "relationships.md"
    out = os.path.join(REPO, "groups", group, "world", fname)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    n_edges = sum(1 for e in edges if e[0] in nodes and e[2] in nodes)
    print(f"Wrote {out}  ({len(nodes)} entities, {n_edges} relationships"
          + (f", focused on {focus}" if focus else "")
          + (f", {table} table" if table else "") + ")")


def main():
    ap = argparse.ArgumentParser(description="Build the Stonetop relationship map.")
    ap.add_argument("--group", help="group folder name, e.g. your-campaign")
    ap.add_argument("--focus", help="restrict to one entity and its direct neighbors")
    ap.add_argument("--table", help="restrict to one table's PCs and their direct links")
    ap.add_argument("--all", action="store_true", help="build every group under groups/")
    ap.add_argument("--print", dest="do_print", action="store_true",
                    help="print to stdout instead of writing the file")
    args = ap.parse_args()

    if args.all:
        groups_dir = os.path.join(REPO, "groups")
        for g in sorted(os.listdir(groups_dir)):
            if os.path.isdir(os.path.join(groups_dir, g)):
                run(g, None, args.do_print)
        return
    if not args.group:
        ap.error("provide --group <name> or --all")
    run(args.group, args.focus, args.do_print, args.table)


if __name__ == "__main__":
    main()
