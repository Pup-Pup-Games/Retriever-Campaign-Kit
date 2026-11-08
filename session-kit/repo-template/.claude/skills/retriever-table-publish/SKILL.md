---
name: retriever-table-publish
description: "Share a Stonetop group's latest updates with the players — commit and push the repo (the players' private GitHub home), then post the session recap to the group's Discord channel via webhook. Use at the end of a session after retriever-recap (and any retriever-track / retriever-relate / retriever-graph updates) are done. Recaps go to Discord; sheets, world notes, and the map live in the repo. This skill does NOT write recaps (retriever-recap) or generate the map (retriever-graph)."
user-invocable: true
---

# Publish to the Table

You push the repo so players can browse the latest sheets, recap, world notes, and map on
GitHub, and you post the recap to Discord for players who'd rather just read it there. This
is outward-facing — confirm before you push or post.

`$ARGUMENTS` = `<group> [table] [session-id]`, e.g. `your-campaign weeknight weeknight-02`. A
multi-table campaign (`your-campaign`: `weeknight`, `weekend`) **requires the table** — it picks
the right session series and Discord webhook. If the session is omitted, the latest
`<table>-NN.md` (or `session-NN.md` for single-table) is used. If the group is omitted, use
`config.json` `default_group` (or ask).

## Preconditions

- A recap exists at `groups/<group>/sessions/<session-id>.md` (from `/retriever-recap`).
- The map is current — if relationships changed this session, run `/retriever-graph <group>`
  (and the `--table` view) first.
- `config.json` exists with the webhook (git-ignored; copy from `config.example.json`). A
  multi-table campaign has one webhook per table under `tables`; a single-table one uses
  `discord_webhook`. If Discord isn't set up, you can still push and skip the post.

One script, `_tools/publish.py`, does the whole sequence deterministically: it guards
against committing ignored working files, commits with a standard message, pushes, and
posts the recap to Discord (frontmatter stripped, `[[wikilinks]]` flattened, chunked under
the 2000-char limit). You confirm; the script does the mechanics.

## Steps

1. **Preview with `--dry-run`** and show the GM the output — the paths that would commit,
   the commit message, and the Discord preview:
   ```powershell
   python _tools/publish.py --group <group> --table <table> --session <session-id> --dry-run
   ```
   (Drop `--table` for a single-table campaign.) If relationships changed this session, run
   `/retriever-graph <group>` first so the map ships current. The script refuses if any
   ignored working file (`_work/`, audio, `config.json`) would be committed — that's a
   backstop, not something to override.

2. **Confirm with the GM, then publish:**
   ```powershell
   python _tools/publish.py --group <group> --table <table> --session <session-id>
   ```
   It commits + pushes the current branch to this repo's own private `origin` (this repo
   *is* the players' destination — nothing is copied) and posts the recap to that table's
   webhook. Use `--no-discord` to push only, or `--no-push` to post only. Omit `--session`
   to use the latest recap for that table.

3. **Report** what the script committed/pushed and whether the recap posted, with the GitHub
   and Discord destinations.

## Rules

- **Confirm before pushing or posting.** Both are outward-facing and seen by players; review
  the diff and the dry-run first.
- **Recaps to Discord, everything else to the repo.** Don't dump full sheets or world files
  into the channel.
- **Never commit secrets.** `config.json` (webhook), `_work/` (transcripts), and audio are
  git-ignored by design, and `publish.py` hard-refuses if any slip through. If it does,
  fix `.gitignore` — don't work around the guard.
- **Private repo.** This contains complete sheets with rules text; keep the GitHub repo
  private. A sanitized public edition is separate future work, not this skill.
