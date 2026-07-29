---
name: retriever-graph
description: "Regenerate the relationship map for a Stonetop group from the entity notes — crawls the people/places/things/players notes, parses their typed relationships, and writes a committed Mermaid diagram to groups/<group>/world/relationships.md (which GitHub renders natively and Obsidian mirrors in its graph view). Optionally renders a focused neighborhood map for one entity. Use after recording relationships with retriever-relate, or any time the map is stale. This skill does NOT record new relationships (that's retriever-relate)."
user-invocable: true
---

# Regenerate the Relationship Map

You run the generator that turns the `## Relationships` blocks across a group's notes into a
Mermaid map. You don't author relationships here (`/retriever-relate` does) — you render
what's already written.

`$ARGUMENTS` = `[group] [focus-entity]`. Examples: `your-campaign`, `your-campaign "The Greenmother"`,
`--all`. If no group is given, use `config.json` `default_group` (or ask).

## Steps

1. **Run the generator** with `_tools/build_graph.py`:
   ```powershell
   python _tools/build_graph.py --group <group>
   ```
   - For a focused neighborhood (one entity and its direct connections):
     `python _tools/build_graph.py --group <group> --focus "<Entity Name>"`
   - For one table's view in a multi-table campaign (that table's PCs + their direct links):
     `python _tools/build_graph.py --group <group> --table <table>` → writes
     `relationships-<table>.md`.
   - For every group at once: `python _tools/build_graph.py --all`
   - To preview without writing: add `--print`.

   The full run writes `groups/<group>/world/relationships.md` — nodes colored by type
   (people / places / things / players), edges colored by category (affinity / kin /
   allegiance / antagonism / spatial), with reciprocal pairs collapsed into one edge. For a
   shared-world campaign like `your-campaign`, regenerate the full map **and** each
   `--table` view so both stay current.

2. **Sanity-check the output.** If the generator reports unknown targets (entities named in
   a relationship but with no note), that usually means a typo in a `[[wikilink]]` or a
   missing entity note — point the GM at it, or offer to create the stub via
   `/retriever-relate`.

3. **Report** the file path and the entity/relationship counts the script printed. Note
   that the committed Markdown renders as a diagram on GitHub and that Obsidian's graph view
   shows the same links live.

## Rules

- **Generated file — don't hand-edit `relationships.md`.** It is overwritten every run.
  Fix the source `## Relationships` blocks on the entity notes (via `/retriever-relate`),
  then regenerate.
- **The vocabulary lives in `_tools/stonetop_lib.py`; the edge/node styling in
  `build_graph.py`.** If a relation renders in the neutral "other" color, it isn't in the
  canonical list — either a deliberate one-off, or it should be normalized at capture time
  in `/retriever-relate`.
- **Regenerate after relating.** A map is only as fresh as its last run; re-run after a
  batch of `/retriever-relate` edits (or at session's end before publishing).
