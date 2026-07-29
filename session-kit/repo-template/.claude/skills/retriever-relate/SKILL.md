---
name: retriever-relate
description: "Record a typed relationship between two entities (people, places, or objects) in a Stonetop campaign — \"Brann is in love with Eirlys\", \"Hask is next of kin to Wren\", \"the Muster-Horn is hidden in the Drowned Mill\". Normalizes the phrasing to the canonical vocabulary, creates the entity notes if they don't exist yet, and writes the relationship (plus its natural reciprocal) as an inline field on the notes so it shows up in Obsidian and in the generated map. Use at the table or while prepping. This skill does NOT draw the map (that's retriever-graph) or edit playbook sheets (that's retriever-track)."
user-invocable: true
---

# Record a Relationship

You capture how two entities are connected and write it onto their notes in a form that is
both Obsidian/Dataview-native and readable by the map generator. You do not draw the map —
`/retriever-graph` does that from what you write here.

`$ARGUMENTS` = the relationship in plain language, e.g.:

- `Brann is in love with Eirlys`
- `Hask is next of kin to Wren (brother)`
- `the Greenmother claims Eirlys`
- `the Muster-Horn is hidden in the Drowned Mill`
- `Wren serves the Steward`

If `$ARGUMENTS` is empty, ask who/what relates to who/what, and how.

Your job is to parse the sentence and infer each entity's **type**; `_tools/relate.py`
does the rest deterministically — it normalizes the phrasing, finds or creates both notes,
and writes the inline field plus the reciprocal without duplicating anything.

## Steps

1. **Resolve the group** (from `config.json` `default_group`, or ask if ambiguous).

2. **Parse** subject, relationship phrase, object, and any parenthetical/after-dash note.
   Infer each entity's type so a missing note is created in the right folder: a person →
   `npc`, a location → `place`, an object/artifact → `thing` (an existing PC sheet is found
   automatically). You do **not** need to normalize the relationship yourself — pass the
   natural phrasing through; the script maps it (e.g. "in love with"→`loves`, "next of
   kin"→`kin-of`, "hidden in"→`located-in`). The canonical vocabulary, synonyms, and
   reciprocals live in `_tools/stonetop_lib.py` (the single source of truth).

3. **Call the script:**
   ```powershell
   python _tools/relate.py --group <g> --subject "<S>" --relation "<phrase>" --object "<O>" \
                           --subject-type <npc|place|thing|player> --object-type <npc|place|thing|player> \
                           [--note "<note>"] [--session session-NN]
   ```
   It prints the normalized relation, what it wrote on each note, and whether either note
   was created. If it warns that the relation isn't canonical, tell the GM (it still works,
   just renders in the neutral color).

4. **Confirm** — echo the result and nudge: run `/retriever-graph <group>` to refresh the
   map. (Batch several `/retriever-relate` calls, then graph once.)

## Rules

- **Let `relate.py` write the notes.** It guarantees the exact inline-field syntax, the
  reciprocal on the other note, and no duplicates. Don't hand-edit relationship lines.
- **Infer types carefully.** The one judgment the script can't make is person vs place vs
  thing for a note it has to create — get `--subject-type`/`--object-type` right.
- **Don't redraw the map here.** Hand that to `/retriever-graph`.
- **Entities, not rules.** This tracks who-relates-to-whom. Playbook moves/stats/gear go
  through `/retriever-track`.
