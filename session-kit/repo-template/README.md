# Stonetop Session Notes

A table companion for running **Stonetop** campaigns: player playbooks, session recaps, world
events, and a typed relationship map of everyone (and everything) the party has met. It is
both a browsable home for your players and a small set of Claude Code skills that maintain it
during and after play.

This repo was generated from the [Pup Pup **Stonetop session kit**](https://github.com/Pup-Pup-Games/Stonetop/tree/main/session-kit).
Everything here is yours to edit; the kit is just the starting structure.

> **Keep your filled-in repo private.** Once you start recording moves and rules text on the
> player sheets, this repository quotes rules from *Stonetop*. Complete sheets are a normal
> private-use copy for the people at your table — fine to keep in a **private** GitHub repo
> shared with your players, but don't publish it. *Stonetop* is the creation of **Jeremy
> Strandberg** (Lampblack & Brimstone) and is licensed CC BY-SA 4.0. (The empty templates that
> ship in this kit contain no rules text and are safe to share; your filled sheets are what
> stays private.)

## What's here

```
groups/<group>/                 one folder per campaign (e.g. your-campaign)
  players/<character>.md         a player's complete playbook sheet (with a `table:` field)
  world/
    people/  places/  things/    entity notes (NPCs, locations, objects)
    events.md  threads.md        world log + open plot threads
    relationships.md             the generated relationship map (Mermaid)
    maps/<slug>.md               the generated map gazetteer(s)
  sessions/
    <table>-NN.md                the published recap (e.g. weeknight-01.md; or session-NN.md)
    <table>-NN/_work/            raw transcript + change log + audio (not committed)
attachments/                     map images (the kit ships placeholder SVG map templates)
templates/                       note templates (no rules text)
_tools/                          the deterministic Python scripts the skills call
.claude/skills/                  the Claude Code skills (the /slash commands)
```

## The skills

Open this folder in **Claude Code** and these are available as `/slash` commands:

| Skill | What it does |
|---|---|
| `/retriever-table-init` | Scaffold the repo and a new play group. |
| `/retriever-track` | Apply a playbook change mid-session — a move, stat, item, harm, bond, or note. |
| `/retriever-relate` | Record a typed relationship ("Brann is in love with Eirlys"). |
| `/retriever-recap` | Turn a session transcript into a player-facing recap. |
| `/retriever-graph` | Regenerate the Mermaid relationship map (and per-entity views). |
| `/retriever-map` | Regenerate the map gazetteer that ties a drawn map to location text. |
| `/retriever-table-publish` | Commit & push, then post the recap to Discord. |

The skills only parse your natural language and write recap prose. Every file mutation and
publish step is done by a deterministic Python script in `_tools/` (see
[`_tools/README.md`](_tools/README.md)), so templating and publishing come out identical every
run. The full lifecycle is documented in [`.claude/README.md`](.claude/README.md).

## First-time setup

1. **Wire your config.** Copy `config.example.json` to `config.json` (git-ignored) and fill in
   your campaign `title`, the Discord webhook(s), and the character→player `roster`.
2. **Scaffold a group.** In Claude Code, run `/retriever-table-init <group>`, or directly:
   `python _tools/scaffold.py --group <group> --title "<Display Title>"`.
3. **Add player sheets** as the roster firms up:
   `python _tools/new_note.py --kind player --group <group> --name <Character> --player "<Real Name>" --playbook "The Heavy"`.
4. **Drop in your map.** The kit ships placeholder map templates in `attachments/`; replace
   them with your own keyed map image (see [`attachments/README.md`](attachments/README.md)).

> Requires **Python 3** (standard library only, except `transcribe.py`, which needs
> `faster-whisper` in a `.venv` — see [`_tools/README.md`](_tools/README.md)). No build step.

## Recommended Obsidian setup

This repo is a ready-to-open Obsidian vault. Graph view and Templates work out of the box.
For the full relationship experience, install these community plugins once
(Settings → Community plugins → Browse):

- **Dataview** — query relationships and roll them up on entity pages.
- **Breadcrumbs** — navigate typed relationships (kin, allegiance, etc.).
- **Juggl** *(optional)* — a richer interactive relationship graph.

GitHub renders `relationships.md` as a diagram natively, so players who don't use Obsidian
still get the map.

## Capturing a session (transcripts)

Record the table, then transcribe **after** the session with `_tools/transcribe.sh`
(`_tools/transcribe.py` on Windows), which runs faster-whisper: free, offline, private. The in-the-moment `/retriever-track` and
`/retriever-relate` skills cover anything you want captured live. See
**[`_tools/README.md`](_tools/README.md)** for capture modes, the remote-player setup, and GPU
options. Audio and raw transcripts are never committed (see `.gitignore`).

---

*An unofficial, fan-made companion. Not affiliated with, endorsed by, or sponsored by
Lampblack & Brimstone or Jeremy Strandberg. Stonetop is the creation of Jeremy Strandberg.*
