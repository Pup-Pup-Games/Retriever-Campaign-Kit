# Stonetop map templates

Three editable **SVG map templates** for running Stonetop, built in [Inkscape](https://inkscape.org/), at three zoom levels:

| File | What it is |
|---|---|
| [`stonetop-steading-template.svg`](stonetop-steading-template.svg) | The home steading, with numbered markers for the canonical locations (the Stone, the Chronicle, the Granary, the Public House & Stables, the Cistern, the Pavilion of the Gods, the Watchtowers). |
| [`the-vicinity-template.svg`](the-vicinity-template.svg) | The wider vicinity — the Wood, the river, the roads, and the lands around the steading — for regional play. |
| [`the-worlds-end-template.svg`](the-worlds-end-template.svg) | The whole of the known world — Stonetop out to Tor's Fist, Marshedge, the Steplands, Barrier Pass, and the lakes — for long overland journeys. |

> **Why these are templates, not finished maps.** The published *Stonetop* maps are the
> copyrighted work of Jeremy Strandberg / Lampblack & Brimstone, so they are **not** included
> here. In each file the map artwork has been replaced with a plain placeholder rectangle and
> the note *"Add your Stonetop map in this layer."* You drop in the map image from **your own
> copy of Stonetop**, and keep the numbered key layer on top. The result is yours, for your
> table — please don't redistribute a version with the official map baked in.

## How the layers are organised

Each template has two Inkscape layers:

- **`base`** — the placeholder rectangle and the *"Add your Stonetop map in this layer"* text.
  This is where your own map image goes.
- **`keys`** — the numbered location markers (locked, so you don't nudge them while editing the
  base). Each marker is a small group carrying `data-key` (the number) and `data-place` (the
  location name), which is what the session kit's `check_map.py` reads to reconcile the drawing
  against your notes. The markers and this layer also carry the optional travel-distance data
  described in [Travel distances](#travel-distances) below.

## Add your own map

1. Open the template in **Inkscape**.
2. Open the **Layers** panel (`Layer → Layers…`) and select the **`base`** layer.
3. Delete the placeholder rectangle and the "Add your Stonetop map…" text.
4. **Import your Stonetop map image** (`File → Import`) from your own copy of the book, and
   place it on the `base` layer. Scale it to fill the page; the `keys` layer stays on top.
5. Nudge the numbered markers in the **`keys`** layer so each sits on its location. (Unlock the
   layer first if needed — the markers ship locked.)
6. Export a flat image for the table: `File → Export`, PNG at 96 dpi or higher.

## Travel distances

The vicinity template carries data that the session kit's **`/retriever-distance`** skill (and
[`_tools/map_distance.py`](../session-kit/repo-template/_tools/map_distance.py)) uses to answer
*"how far / how long from X to Y."* The model is a **hybrid**, exact-route-first:

- **Explicit routes (exact).** Road and multi-day journeys a straight line gets wrong are
  recorded in the notes as `travel-to` relationships with the time/route in the note. The tool
  prefers these and chains them across hops (Stonetop → the Foothills → Barrier Pass = 3 days).
  This is also how you ask about **off-map** destinations.
- **Geometry + scale (any pair, approximate).** Otherwise the tool measures the straight line
  between two markers' anchor points and divides by the map's `data-map-scale`. This works for
  *any* pair, including pins you add later, but it's a **~±20–25% estimate** — it ignores roads
  and terrain, so present it as "about half a day on foot," never as a fact. Each map carries
  its own scale, calibrated from that map's own known legs (the close-in maps from direct
  overland hops, the world map from long road journeys), so the estimate reflects how people
  actually travel at that zoom.

### The attributes

Everything lives on the `keys` layer and its marker groups (custom `data-*` attributes that
Inkscape preserves):

| Where | Attribute | Meaning |
|---|---|---|
| `keys` layer `<g>` | `data-map-scale` | userspace units per hour of travel — **per map**, see the table below |
| `keys` layer `<g>` | `data-map-origin` | the location single `data-distance` values are measured from (usually **Stonetop**) |
| marker `<g>` | `data-key`, `data-place` | the drawn number and the location name (also read by `check_map.py`) |
| marker `<g>` | *(its transparent `<ellipse>`)* | the **anchor**: its center is the point distances measure from |
| marker `<g>` | `data-offmap="true"` | no single point on this map (roads, region labels, "To …" pointers) — excluded from geometry |
| marker `<g>` | `data-distance` | *(optional)* a known travel time, e.g. `4-6 hours`, `2 days` — calibration ground-truth |
| marker `<g>` | `data-distance-from` | *(optional)* the origin for that `data-distance`, when it isn't the map origin (e.g. the Ruined Tower is timed from **The Crossroads**) |

### Adding a new pin

1. Draw the marker in the `keys` layer (copy an existing group) and set `data-key` /
   `data-place`. Its transparent `<ellipse>` center is the anchor — place it on the spot.
2. For an **area** with no obvious single point, add a small element labelled `anchor` inside
   the group; the tool measures from that instead of the ellipse.
3. If it's reachable only by road or is off this map, flag it `data-offmap="true"` and record
   the time in the notes as a `travel-to` relationship (via `/retriever-relate`) — geometry
   won't apply.
4. *(Optional)* If you know the canonical time, add `data-distance` (and `data-distance-from`
   if it isn't from the map origin) so calibration can check the scale against it.

### Calibrating the scale

After dropping in your own map image (which changes the pixel scale) or adding ground-truth
distances, recalibrate:

```powershell
python _tools/map_distance.py --map the-worlds-end --calibrate
```

It measures each `data-distance` marker from its origin (honouring `data-distance-from`),
reports the implied pace and the spread, and suggests a `data-map-scale` that centers the
estimates. The two regional templates calibrate cleanly:

| Map | Calibration legs | Pace | Spread | `data-map-scale` |
|---|---|---|---|---|
| `the-vicinity` | 4 direct hops from Stonetop (Cave Bears, Red Grove, the Crossroads, the Maw) | ~62 units/hour | ±22% | **62** |
| `the-worlds-end` | 10 regional journeys (Stonetop→Marshedge 10 days, the Foothills→Tor's Fist 5 days, Marshedge→the lakes, …) | ~91 units/day (3.8 units/hour) | ±23% | **3.8** |

The world map's legs are mostly multi-day **road** journeys measured from several origins
(Stonetop, Marshedge, the Foothills), yet straight-line distance still tracks them to ±23% —
so the same hybrid model holds at world scale. Because those journeys are road-paced rather
than direct overland, read its estimates as "a bit under the real road time" and lean on
explicit `travel-to` routes for anything that has to be exact.

## Using these with the session kit

These templates are designed to pair with the **[Stonetop session kit](../session-kit/)** in
this repo. Bootstrap a session repo and the same templates are copied into its `attachments/`
folder, where the `/retriever-map` skill keys your location notes to the markers, the
`check_map.py` tool flags any drift between the map and the notes, and `/retriever-distance`
answers travel questions from the data above. You can also just print them and use them at the
table — the kit is optional.

---

*Unofficial, fan-made templates. Not affiliated with, endorsed by, or sponsored by Lampblack &
Brimstone or Jeremy Strandberg. You'll need a copy of *Stonetop* to use them.*
