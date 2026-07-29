---
name: retriever-map
description: "Regenerate the map gazetteer for a Stonetop group — the text index that ties a drawn map image to the locations Claude reasons over when prepping a session. Crawls the group's place notes for their map frontmatter (map/key/zone/region) and `## Map / Location` blocks and writes groups/<group>/world/maps/<map-slug>.md (a keyed table + per-location briefing, rendered natively by GitHub and Obsidian). Use after pinning places to a map or editing their location details, or any time the gazetteer is stale. This skill does NOT draw the map image (you do that) or record relationships (that's /retriever-relate)."
user-invocable: true
---

# Build the Map Gazetteer

Where `/retriever-graph` draws the *social* graph, you build the *spatial* one: a gazetteer
that ties a drawn map (the image you keep in `attachments/`) to the structured location text
the table actually reasons over. You do not draw the map image — you regenerate the index
from what the place notes say.

`$ARGUMENTS` = the group (and optionally a single map slug), e.g.:

- `your-campaign`
- `your-campaign stonetop-steading`
- `--all`

If `$ARGUMENTS` is empty, resolve the group from `config.json` `default_group`, or ask.

## How the spatial layer works

A **place note** is pinned to a map by four frontmatter fields and described by one section:

```yaml
map:    stonetop-steading   # the map image slug — matches attachments/<slug>.*
key:    3                    # the number/label drawn on that map (steading style)
zone:   C2                   # OR a grid cell on a regional map
region: The Steading         # human region name
```

```markdown
## Map / Location
- **What's here:** forge, anvil, a locked chest under the workbench
- **Hidden:** a strongbox key, buried in the slack tub
- **Visible from outside:** smoke when lit; otherwise looks shut
- **Exits / approaches:** main door (square), back door (to the wall walk)
- **Usually present:** the smith by day
```

Spatial **relationships** (`adjacent-to`, `north-of`/`south-of`, `above`/`below`,
`overlooks`, `travel-to` with the time/route in the note) are recorded with
`/retriever-relate` like any other relationship and get pulled into each entry as
**Connections**. New place notes already carry this scaffolding (`templates/place.md`).

`_tools/build_gazetteer.py` reads all of that and writes one gazetteer per map. You never
hand-format the gazetteer — like the relationship map, it is generated.

## Steps

1. **Resolve the group** (and optional map slug) from `$ARGUMENTS` or `config.json`.

2. **Call the script:**
   ```powershell
   python _tools/build_gazetteer.py --group <g> [--map <slug>] [--print]
   python _tools/build_gazetteer.py --all
   ```
   It writes `groups/<group>/world/maps/<slug>.md` for each map and reports any **unmapped**
   places (a place with no `map:` set) so you know what still needs pinning.

3. **Confirm** — echo what was written and the unmapped list. If a map has no image yet, the
   gazetteer embeds a placeholder pointing at `attachments/<slug>.png`; remind the GM to drop
   the keyed image there and number its locations to match the `key:` column.

4. **Reconcile the drawing (SVG maps).** If the map is an SVG with a `keys` layer, check that
   its numbered markers and the notes agree:
   ```powershell
   python _tools/check_map.py --group <g> [--map <slug>]
   ```
   It reports keyed notes with no marker, orphan markers, duplicates, and name mismatches,
   and exits non-zero on any hard drift. Each marker is a `<g>` in the `keys` layer carrying
   `data-key` (matching the note's `key:`/`zone:`) and `data-place`/`<title>` (its name).
   PNG/JPG maps have no readable key layer and are skipped.

## Rules

- **Let `build_gazetteer.py` write the gazetteer.** Edit the place notes' frontmatter and
  `## Map / Location` blocks, then regenerate — never hand-edit `world/maps/*.md`.
- **Drawing is the manual step.** Like transcription, the one thing this system can't do for
  you is draw the map; it keys text to whatever you draw. Keep the `key:`/`zone:` values in
  sync with the labels on the image.
- **Relationships go through `/retriever-relate`.** Adjacency, direction, and travel times are
  relationships; record them there so they land on both notes and color the relationship map.
- **Prep, not rules.** This indexes *where things are*. Playbook moves/stats/gear go through
  `/retriever-track`.
