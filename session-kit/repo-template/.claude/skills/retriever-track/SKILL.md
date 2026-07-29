---
name: retriever-track
description: "Apply a single mid-session change to a Stonetop player's playbook sheet — a new move, a stat or level/XP change, gear gained or lost, harm, a bond, or a quick note. Parses a short natural-language instruction (\"Brann: gained move Hack and Slash\", \"Wren +1 STR\", \"add silver ring to Aldra's gear\", \"note: party freed the Hewn\"), edits the right player's Markdown sheet, and logs the change to the active session's working log. Use at the table while running a session. This skill does NOT write recaps (that's retriever-recap) or map relationships (that's retriever-relate)."
user-invocable: true
---

# Track a Playbook Change

You apply one quick change to a player's sheet during play and log it, so the sheet stays
current and the recap has a record to draw on. Keep it fast: this runs mid-session.

`$ARGUMENTS` = the change in plain language. Common shapes:

- `Brann: gained move Hack and Slash` — add a move
- `Wren +1 STR` / `Aldra: CON now +2` — adjust a stat
- `Brann level 3` / `Wren xp +1` — advancement
- `add a silver ring to Aldra's gear` / `Brann loses his shield` — gear
- `Brann takes 2 harm` / `Wren: clear harm` — harm/conditions
- `bond: Brann -> Wren "owes me for the bridge"` — a bond line
- `note: the party freed the Hewn at the breach` — a freeform sheet note

If `$ARGUMENTS` is empty, ask what changed and for whom.

Your job is to turn the sentence into the right **structured op**, then let
`_tools/track.py` make the edit and log it. The script owns the file mutation (which
section, exact format, the timestamped change-log line) so it comes out identical every
time; you only decide the op and its values.

## Steps

1. **Resolve the group and character.** Default to `config.json` `default_group`; if the
   character exists in more than one group, ask. If it's actually a relationship between
   entities ("X loves Y", "X is kin to Y"), stop and route to `/retriever-relate`.

2. **Classify into one op** and call the script (it edits the sheet *and* appends the
   change-log line — never hand-edit the sheet yourself):

   | Change | Command |
   |---|---|
   | new move | `python _tools/track.py --group <g> --character <C> --op add-move --name "<Move>" --ref "Book I p.XX" --text "<full move text>"` |
   | stat | `... --op set-stat --stat STR --value +2` |
   | level | `... --op set-level --value 3` |
   | XP (set / delta) | `... --op set-xp --value 5`  /  `... --op adj-xp --value +1` |
   | gear gained / lost | `... --op add-gear --value "<item>"`  /  `... --op remove-gear --value "<item>"` |
   | harm | `... --op add-harm --value "<harm>"`  /  `... --op clear-harm` |
   | bond | `... --op add-bond --value "[[Wren]] — owes me"` |
   | sheet note | `... --op add-note --value "<note>"` |
   | table note (no PC) | `python _tools/track.py --group <g> --table <table> --op session-note --value "<note>"` |

   For **add-move**, supply the move's real rules text and page from *Stonetop* in
   `--text`/`--ref` so the player has it at the table. If you're not certain of the exact
   wording or page, omit `--text` (the script inserts a `confirm move text` marker) and ask
   the GM, rather than inventing text.

3. **Confirm briefly** — echo the script's one-line result. The script auto-targets the
   latest session for the character's table; pass `--session <table>-NN` (e.g. `weeknight-02`)
   to override. Do not commit or push (that's `retriever-table-publish`).

## Tables

`your-campaign` is a multi-table campaign (tables: `weeknight`, `weekend`). The script reads a
PC's table from the `table:` field on their sheet, so for a character op you don't pass
`--table` — it's inferred, and the change logs to `sessions/<table>-NN/`. The one case that
needs `--table` is a `session-note` (no character to infer from). Single-table campaigns
have no tables and use `session-NN`.

## Rules

- **Let `track.py` make the edit.** Don't hand-edit the sheet — the script keeps the format
  and the change log deterministic. Your value-add is parsing the sentence into the op.
- **One change per invocation, fast.** This is a table tool; don't reorganize the sheet.
- **Never invent rules text.** If you don't know a move's exact wording/page, omit `--text`
  (the script flags it) and ask the GM. Wrong rules are worse than a placeholder.
- **Stay player-safe.** Sheets are visible to players. Don't add GM secrets here; those
  belong in the GM's private campaign docs, not this repo.
- **Relationships go to `/retriever-relate`**, recaps to `/retriever-recap`. Route the user
  there instead of half-doing their job.
