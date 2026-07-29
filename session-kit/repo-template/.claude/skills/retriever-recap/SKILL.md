---
name: retriever-recap
description: "Turn a session transcript (and the mid-session change log) into a player-facing recap for a Stonetop group — narrative of what happened, world events, bond/relationship shifts, open threads, and rewards. Writes the committed sessions/session-NN.md, updates the group's world events and threads, and proposes relationship edits to hand to retriever-relate. Use after a session, once you have a transcript from _tools/transcribe.py (or your own notes). This skill does NOT post to Discord or push (that's retriever-table-publish) and does NOT edit playbook sheets (that's retriever-track)."
user-invocable: true
---

# Write a Session Recap

You read what happened at the table and produce a clean, player-facing recap plus the
world-log updates. The recap is the artifact players read on GitHub/Obsidian and the one
that later goes to Discord.

`$ARGUMENTS` = `<group> <session-id> [transcript-path]`, e.g. `your-campaign weeknight-02`. The
session id is `<table>-NN` in a multi-table campaign (e.g. `weeknight-02`, `weekend-01`) or
`session-NN` in a single-table one. If the transcript path is omitted, use
`groups/<group>/sessions/<session-id>/_work/transcript.md`. If group or session is missing, ask.

## Read first

- `groups/<group>/sessions/<session-id>/_work/transcript.md` — the raw transcript (from
  `_tools/transcribe.py`). May be long; read it fully.
- `groups/<group>/sessions/<session-id>/_work/changes.md` — the mid-session change log from
  `/retriever-track`, if present. It anchors the concrete events (moves used, items gained).
- `groups/<group>/world/threads.md` — the open threads going in, so the recap can resolve
  or advance them.
- `templates/session.md` — the recap shape to follow.

## Steps

1. **Draft the recap** into `groups/<group>/sessions/<session-id>.md` following the
   `templates/session.md` structure exactly: frontmatter (`group`, `session`, `date`,
   `present`, and a `table:` line in a multi-table campaign), a short teaser, a `## Recap`
   narrative in play order, `## World events`, `## Bonds & relationships`, `## Open threads`,
   and `## Loot & rewards`. The prose is yours to write; keep the headings as-is so every
   recap has the same shape (and `post_discord.py` strips the frontmatter cleanly on
   publish). Reference people and places as `[[wikilinks]]`. If you mention a brand-new
   NPC/place/thing that has no note yet, create its stub deterministically with
   `python _tools/new_note.py --kind <npc|place|thing> --group <g> --name "<Name>" --session <session-id>`.

2. **Update the world log.** Add the session's changes to `groups/<group>/world/events.md`
   (newest at top) and update `groups/<group>/world/threads.md` — check off resolved
   threads, add new ones. Keep these terse; the narrative lives in the recap.

3. **Propose relationship edits.** From the transcript, list the new or changed connections
   you noticed ("Brann is clearly falling for Eirlys", "the party now owes the Steward").
   Present them as ready-to-run `/retriever-relate ...` lines for the GM to confirm — do
   **not** write them to entity notes yourself (that's `retriever-relate`'s job, and the GM
   should approve relationship changes).

4. **Report** the recap path and a one-line summary, and remind the GM to run
   `/retriever-table-publish <group> <table> <session-id>` when ready to share (the `<table>`
   is only needed for a multi-table campaign).

## Rules

- **Player-safe only.** This repo is visible to players. Write what the characters know and
  experienced. Keep GM secrets (twists not yet revealed, future prep, the doom clock) out —
  they stay in the GM's private campaign docs, not here.
- **Faithful, not embellished.** Recap what actually happened at the table. If the
  transcript is unclear on a point, say so or leave it out rather than inventing.
- **Match the house prose style.** Clear and warm, second-person or past-tense narrative.
  Do not use em dashes as sentence separators — use commas, semicolons, or colons.
- **Don't publish or push.** Hand sharing to `/retriever-table-publish`. Don't edit sheets
  or write relationships directly.
