# `.claude/` — the Stonetop table skills

This folder holds the Claude Code skills that run and maintain a Stonetop campaign in this
repo. Open the repository in **Claude Code** and each skill is available as a `/slash`
command; type the command and describe what you want in plain language.

The skills do two things and nothing else: they **parse your natural language** and they
**write recap prose**. Every actual file change (sheets, notes, the map, commits, the Discord
post) is performed by a deterministic Python script in [`_tools/`](../_tools/README.md), so
the same instruction always produces the same file. If a skill ever proposes hand-editing a
sheet instead of calling its script, that's a bug.

## The skills

| Command | When | What it does |
|---|---|---|
| `/retriever-table-init` | setup | Scaffold the repo or a new play group (folders, world stubs, player sheets). |
| `/retriever-track` | during play | Apply one playbook change — a move, stat, item, harm, bond, or note. |
| `/retriever-relate` | during play / prep | Record a typed relationship ("Brann is in love with Eirlys"). |
| `/retriever-recap` | after a session | Turn a session transcript into the player-facing recap. |
| `/retriever-graph` | after relationships change | Regenerate the Mermaid relationship map. |
| `/retriever-map` | after places/locations change | Regenerate the map gazetteer that ties a drawn map to location text. |
| `/retriever-distance` | at the table / prep | Answer "how far / how long from X to Y" over a keyed map (geometry + explicit routes). |
| `/retriever-table-publish` | end of session | Commit & push the repo, then post the recap to Discord. |

## The lifecycle of a campaign

```
            ┌─────────────────────────  one-time / per new group  ──────────────────────────┐
            │  /retriever-table-init  →  scaffold the group, add player sheets, wire config   │
            └──────────────────────────────────────────────────────────────────────────────┘

            ┌───────────────────────────────  at the table  ──────────────────────────────┐
            │  /retriever-track   "Brann gained move Hack and Slash"   (sheet + change log) │
            │  /retriever-relate  "Wren serves the Steward"            (entity notes + map) │
            └─────────────────────────────────────────────────────────────────────────────┘

            ┌────────────────────────────  after the session  ────────────────────────────┐
            │  (record audio →  python _tools/transcribe.py …  →  _work/transcript.md)     │
            │  /retriever-recap          read transcript → write session-NN.md + world log  │
            │  /retriever-graph          redraw the relationship map if relations changed   │
            │  /retriever-map            redraw the map gazetteer if places/locations moved │
            │  /retriever-table-publish  commit, push, post the recap to Discord            │
            └─────────────────────────────────────────────────────────────────────────────┘
```

Transcription itself is the one manual step (you run `_tools/transcribe.py` between the
session and the recap). See [`_tools/README.md`](../_tools/README.md) for how.

## Each skill, with example arguments

Arguments are plain language — these are typical shapes, not a rigid syntax. If you leave out
something the skill needs (like which group), it asks. The default group comes from
`config.json` `default_group` when you don't name one.

### `/retriever-table-init` — stand up a group
```
/retriever-table-init winterfell
```
Builds `groups/winterfell/` (players, world/people|places|things, sessions) and the
events/threads/relationships stubs. With no argument it just verifies the shared repo files
exist. Add player sheets as the roster firms up; it never overwrites an existing sheet.
Afterwards, copy `config.example.json` to `config.json` and fill in the group's title,
Discord webhook, and character→player roster.

### `/retriever-track` — one mid-session sheet change
```
/retriever-track Brann: gained move Hack and Slash
/retriever-track Wren +1 STR
/retriever-track add a silver ring to Aldra's gear
/retriever-track note: the party freed the Hewn at the breach
```
Edits the right player's sheet **and** logs the change to the active session's working log,
so the recap has a record to draw on. Keep these fast; they run during play.

### `/retriever-relate` — record a relationship
```
/retriever-relate Brann is in love with Eirlys
/retriever-relate Hask is next of kin to Wren (brother)
/retriever-relate the Muster-Horn is hidden in the Drowned Mill
```
Normalizes the phrasing to the canonical vocabulary, creates either entity's note if it
doesn't exist yet, and writes the relationship plus its reciprocal as an inline field. It
does **not** draw the map — run `/retriever-graph` for that.

### `/retriever-recap` — write the session recap
```
/retriever-recap your-campaign weekend-01
```
Reads `groups/<group>/sessions/<session-id>/_work/transcript.md` (from `transcribe.py`) plus
the mid-session change log, then writes the committed `<session-id>.md` recap (e.g.
`weekend-01.md`), updates the world events and open threads, and proposes any relationship
edits to hand to `/retriever-relate`.
Run `transcribe.py` first so the transcript exists.

### `/retriever-graph` — redraw the relationship map
```
/retriever-graph your-campaign
/retriever-graph your-campaign "Wren"             # focused neighborhood map
/retriever-graph your-campaign --table weeknight     # one table's view (multi-table campaign)
/retriever-graph --all                        # every group
```
Crawls the `## Relationships` blocks across the group's notes and writes
`groups/<group>/world/relationships.md` as a Mermaid diagram (GitHub renders it natively;
Obsidian's graph view mirrors the same links). Run it after relationships change.

### `/retriever-table-publish` — share with the players
```
/retriever-table-publish your-campaign weekend weekend-02
```
**Outward-facing** — it confirms first, previews with a dry run, then commits and pushes the
repo and posts the recap to that table's Discord channel (frontmatter stripped, `[[wikilinks]]`
flattened, chunked under Discord's limit). Needs the webhook in `config.json` (per-table under
`tables` for a multi-table campaign, else `discord_webhook`); if Discord isn't set up it can
still push and skip the post. If relationships
changed this session, run `/retriever-graph` first so the map ships current.

## Configuration

`config.json` (git-ignored; copy from `config.example.json`) holds each group's `title`,
`discord_webhook`, and character→player `roster`. The skills and the `--group` check in
`transcribe.py` read it. Keep real webhook URLs out of version control — that's why the file
is ignored.
