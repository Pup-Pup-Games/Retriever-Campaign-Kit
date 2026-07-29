---
name: retriever-distance
description: "Answer 'how far / how long from X to Y' on a Stonetop group's keyed map. Uses a hybrid model: a straight-line geometric estimate from each location's map anchor and the map's scale (works for any pair, including new pins), preferring an exact `travel-to` time recorded in the notes when one exists (for roads and multi-day journeys geometry can't capture). Use when the GM or players ask about travel distance or time between two places. This skill does NOT draw the map (you do that) or record relationships (that's /retriever-relate); it reads them."
user-invocable: true
---

# Assess Map Distance

You answer travel questions — "how long from Stonetop to the Maw?", "how far is the Red
Grove from the cave bears' den?" — over a group's keyed SVG map. You don't compute anything by
hand: `_tools/map_distance.py` resolves marker anchors, applies the map scale, and prefers any
explicit route, deterministically.

`$ARGUMENTS` = a travel question in plain language, e.g.:

- `how long from Stonetop to the Maw?`
- `distance from the Red Grove to the cave bears`
- `how far is it to Gordin's Delve?`

## How the model works

Two layers, exact-route-first:

1. **Explicit `travel-to` edges (exact).** Known and road journeys are recorded with
   `/retriever-relate` as `travel-to` relationships, with the time/route in the note (e.g.
   *"via the Roads, 2 days"*). The tool reads these and takes a shortest path over them. Use
   this for anything geometry gets wrong: road travel that doesn't go in a straight line,
   multi-day legs, and **off-map** destinations (markers flagged `data-offmap="true"`: the
   roads, the region labels, the "To …" pointers — they have no single point to measure).
2. **Geometric estimate (any pair).** Otherwise the tool measures the straight line between
   the two markers' anchor points and divides by the map's `data-map-scale` (userspace units
   per hour of direct overland travel, on the `keys` layer). This works for *any* two on-map
   points, including pins added after the map was made — but it's a **~±25% estimate** and
   ignores roads and terrain. Always present it as approximate ("about half a day on foot").

Each location's anchor is the center of its transparent `<ellipse>`/`<circle>` (the marker the
label hangs off). An **area** can carry its own measuring point: add a small element labelled
`anchor` inside the marker group and the tool uses that instead.

## Steps

1. **Resolve the group and map.** Default group from `config.json` `default_group`; the map is
   usually `the-vicinity` (`attachments/the-vicinity.svg`). Ask only if ambiguous.

2. **Call the script:**
   ```powershell
   python _tools/map_distance.py --map the-vicinity --group <g> --from "<X>" --to "<Y>"
   ```
   - `--group` loads the explicit `travel-to` edges; drop it for geometry-only.
   - `--list` shows which locations are on-map points vs off-map/edges-only.
   - `--calibrate` checks the geometric estimate against each marker's `data-distance`
     ground-truth and reports the pace and spread — run it after re-scaling a map.

3. **Report** the answer in plain language. If the tool gave a **straight-line estimate**, say
   so and that real travel (roads, terrain) takes longer. If it found an **explicit route**,
   give the route. If it refused (an off-map endpoint with no edge), tell the GM to record the
   time with `/retriever-relate <X> travel-to <Y> (… time/route …)`.

## Rules

- **Exact beats estimate.** If a `travel-to` time exists, use it; only fall back to geometry.
- **Label estimates as estimates.** Never present a straight-line number as a known travel
  time. Stonetop journeys follow roads and terrain; the geometry is a sanity-check figure.
- **Don't edit the map or the notes here.** New travel times are recorded with
  `/retriever-relate` (they become `travel-to` edges); new pins are drawn on the map by hand.
  This skill only reads.
- **Calibrate after re-scaling.** If you change a map's `data-map-scale`, run `--calibrate`
  and confirm the spread is sane before trusting estimates.
