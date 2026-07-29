# `attachments/` — map images

This is where your **map images** live. The `/retriever-map` skill keys your place notes to a
map by its slug: a place note with `map: stonetop-steading` in its frontmatter pairs with
`attachments/stonetop-steading.*`.

The kit ships two **placeholder map templates** here:

- `stonetop-steading.svg` — the home steading, with numbered location markers.
- `the-vicinity.svg` — the wider vicinity.

These are the same editable templates documented in the
[map templates README](https://github.com/Pup-Pup-Games/Stonetop/tree/main/maps). Each has the
map artwork replaced by a placeholder; **drop in the map image from your own copy of
Stonetop** (open in Inkscape, put your image on the `base` layer, keep the numbered `keys`
layer on top), then export.

If you'd rather use a raster map, save it here as `stonetop-steading.png` (or `.jpg`) and
point your place notes at that slug. PNG/JPG maps have no readable key layer, so
`check_map.py` skips them — only the SVG templates get reconciled against your notes.

Anything large or private (scans, exports you don't want committed) can be left out via
`.gitignore`; the kit only commits what you choose to add here.
