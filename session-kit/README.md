# Stonetop session kit

A reusable toolkit for **running** a Stonetop campaign — not adventure text, but the
machinery that keeps a table organised: an Obsidian-ready notes vault plus a set of Claude
Code skills that maintain player sheets, session recaps, a world log, and a typed relationship
map of everyone the party has met.

This is the generalised, sharable version of the system the Pup Pup table runs its own
campaigns with. It's Stonetop-flavoured but contains **no copyrighted Stonetop text** — only
empty note templates, code, and placeholder maps. You bring your own copy of the book and your
own campaign.

## What you get

| Piece | What it is |
|---|---|
| `.claude/skills/` | Eight `/retriever-*` Claude Code skills (track, relate, recap, graph, map, distance, table-init, table-publish). |
| `_tools/` | The deterministic Python scripts the skills call — every file change runs through these, so output is identical every time. |
| `templates/` | Note templates for players, NPCs/places/things, and sessions (no rules text). |
| `attachments/` | Placeholder SVG map templates (see [the map templates](../maps/)). |
| `.obsidian/` | A ready-to-open Obsidian vault config. |
| `config.example.json`, `.gitignore` | Wiring for your roster, Discord webhooks, and what stays local. |

These live under [`repo-template/`](repo-template/) — that whole folder is what gets copied
into your new campaign repo.

## Quick start

From a clone of this repository:

```powershell
# Windows / PowerShell
python session-kit/bootstrap.py --target ..\my-campaign --group winterfell --title "Winterfell Falls"
```

```bash
# macOS / Linux
python3 session-kit/bootstrap.py --target ../my-campaign --group winterfell --title "Winterfell Falls"
```

That creates `../my-campaign/` with the full structure, scaffolds the `winterfell` group,
seeds a `config.json`, and runs `git init`. Then:

1. **`cd ../my-campaign`** and edit `config.json` — add your Discord webhook and your
   character→player roster. (For a multi-table campaign, copy the `tables` shape from
   `config.example.json`.)
2. **Add player sheets:** `python _tools/new_note.py --kind player --group winterfell --name Brann --player "Your Player" --playbook "The Heavy"`.
3. **Drop in your map** image (see [`attachments/README.md`](repo-template/attachments/README.md)).
4. **Open the folder in Claude Code** — the `/retriever-*` skills are ready — and in **Obsidian**,
   which already recognises it as a vault.
5. **Give your players a home on GitHub.** Create a **private** repo and add it as `origin` —
   `gh repo create <name> --private --source . --remote origin`, or create it as **Private** on
   github.com and `git remote add origin <url>`. `/retriever-table-publish` pushes there; the first
   publish sets the upstream for you.

### Options

| Flag | Meaning |
|---|---|
| `--target PATH` | where to create the campaign repo (required; created if missing) |
| `--group NAME` | scaffold a first play group with this folder name |
| `--title "…"` | display title for that group (defaults to the group name) |
| `--no-git` | skip `git init` |
| `--force` | overwrite kit files with the kit's current versions (your `groups/` content is never touched) |

The bootstrapper is **idempotent**: re-run it any time to add anything missing without
clobbering your notes. Pure standard library, Python 3.8+.

## How it works once it's running

The skills only parse your plain-language instructions and write recap prose; every actual
file mutation is done by a `_tools/` script, so templating and publishing are deterministic.
The lifecycle — init → track/relate at the table → transcribe → recap → graph/map → publish —
is documented in [`repo-template/.claude/README.md`](repo-template/.claude/README.md), and the
scripts (including local, offline session transcription) in
[`repo-template/_tools/README.md`](repo-template/_tools/README.md).

---

*Unofficial, fan-made tooling. Not affiliated with, endorsed by, or sponsored by Lampblack &
Brimstone or Jeremy Strandberg. Stonetop is the creation of Jeremy Strandberg; you'll need a
copy of the book to play.*
