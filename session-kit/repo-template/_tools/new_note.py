#!/usr/bin/env python
"""
new_note.py — deterministically stamp a player sheet or entity note from a template.

Given structured fields, fills the {{TOKEN}} placeholders in templates/player-sheet.md
or templates/entity.md and writes the note. Never overwrites an existing file, so it is
safe to re-run. The skills parse your language into these flags and call this, instead of
hand-formatting the file (which drifts run to run).

Usage:
  python new_note.py --kind player --group seal --name Brann --player Alex --playbook "The Heavy"
  python new_note.py --kind npc   --group seal --name "Old Yarrow" --desc "Stonetop's eldest"
  python new_note.py --kind place --group seal --name "The Drowned Mill"
  python new_note.py --kind thing --group seal --name "The Muster-Horn" --session session-02

Pure stdlib.
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stonetop_lib as lib

DEFAULT_STATUS = {"npc": "alive", "place": "active", "thing": "intact", "player": "alive"}


def make_note(group, kind, name, player="", playbook="", desc="",
              status="", session="unknown", table=""):
    """Create the note if absent. Returns (path, created_bool)."""
    lib.require_group(group)
    out = os.path.join(lib.entity_dir(group, kind), f"{name}.md")
    if os.path.exists(out):
        return out, False
    status = status or DEFAULT_STATUS.get(kind, "active")
    if kind == "player":
        text = lib.stamp("player-sheet.md", {
            "GROUP": group, "TABLE": table, "PLAYER": player or "<real name>",
            "PLAYBOOK": playbook or "<playbook>", "NAME": name,
            "DESC": desc or "a new hero of Stonetop",
        })
    else:
        # places carry the extra map scaffolding (frontmatter + Map/Location block)
        template = "place.md" if kind == "place" else "entity.md"
        text = lib.stamp(template, {
            "TYPE": kind, "GROUP": group, "STATUS": status,
            "SESSION": session, "NAME": name,
            "DESC": desc or f"({kind} — add a description)",
        })
    lib.write_new(out, text)
    return out, True


def main():
    ap = argparse.ArgumentParser(description="Create a player sheet or entity note.")
    ap.add_argument("--kind", required=True, choices=["player", "npc", "place", "thing"])
    ap.add_argument("--group", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--player", default="", help="real player name (player kind)")
    ap.add_argument("--playbook", default="", help="playbook (player kind)")
    ap.add_argument("--table", default="", help="table, e.g. weeknight (player kind)")
    ap.add_argument("--desc", default="", help="one-line description")
    ap.add_argument("--status", default="", help="alive|dead|active|lost|hidden|intact")
    ap.add_argument("--session", default="unknown", help="first_seen, e.g. weeknight-02")
    args = ap.parse_args()

    path, created = make_note(args.group, args.kind, args.name, args.player,
                              args.playbook, args.desc, args.status, args.session,
                              args.table)
    rel = os.path.relpath(path, lib.REPO)
    print(("Created " if created else "Exists, unchanged: ") + rel)


if __name__ == "__main__":
    main()
