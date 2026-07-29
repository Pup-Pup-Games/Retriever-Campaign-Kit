---
name: retriever-table-init
description: "Scaffold this Stonetop session-notes repo or stand up a new play group inside it — creates the groups/<group>/ structure (players, world/people|places|things, sessions), seeds the world log/threads/relationship-map stubs, and ensures the shared files exist (README, .gitignore, config.example.json, templates/, the Obsidian vault). Use when setting up a new campaign group, or onboarding another GM to the system. This skill does NOT add players' sheets content (use retriever-track) or write any session material."
user-invocable: true
---

# Initialize the Table

You scaffold the repository and/or a new play group so the other skills have somewhere to
write. Idempotent: only create what's missing; never overwrite existing notes.

`$ARGUMENTS` = `[group]`, e.g. `winterfell` to add a new group. With no argument, verify the
repo-level files exist and report what's set up.

`_tools/scaffold.py` builds the group structure deterministically and idempotently, and
`_tools/new_note.py` stamps player sheets from the template. Use them rather than creating
folders and files by hand.

## Steps

1. **Confirm the shared files exist** (they ship with the repo): `README.md`, `.gitignore`,
   `config.example.json`, `templates/` (`player-sheet.md`, `entity.md`, `session.md`), and
   the `.obsidian/` vault. On a fresh clone these are already present; just verify.

2. **Scaffold the group** (when a name is given) — creates players/, world/{people,places,
   things}/, sessions/, and the events/threads/relationships stubs, skipping anything that
   exists:
   ```powershell
   python _tools/scaffold.py --group <group> --title "<Display Title>"
   ```

3. **Add player sheets** as the roster firms up (the script won't overwrite an existing
   sheet). For a multi-table campaign, tag each PC with their table:
   ```powershell
   python _tools/new_note.py --kind player --group <group> --name <Character> --player "<Real Name>" --playbook "The Heavy" --table <table>
   ```

4. **Remind the GM to wire config.** Copy `config.example.json` to `config.json`
   (git-ignored) and fill the campaign's `title`, the webhook(s), and the character→player
   `roster`. A campaign with several tables (one party each) lists a webhook per table under
   `tables` (and each PC carries a `table:` field); a single-table campaign uses one
   `discord_webhook`. Don't write real values into `config.json` yourself unless they
   provide them.

5. **Report** what was created vs. already present, and next steps: record relationships
   with `/retriever-relate`, then `/retriever-graph` to draw the map.

## Rules

- **Use the scripts.** `scaffold.py` and `new_note.py` are idempotent and won't overwrite a
  populated note — that's the safety. Don't hand-create the structure.
- **No content authoring here.** This sets up empty structure only. Sheets, relationships,
  and recaps come from the other skills.
