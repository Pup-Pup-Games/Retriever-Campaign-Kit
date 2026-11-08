#!/usr/bin/env python
"""
bootstrap.py — stand up a new session-notes repo from this kit.

Clone Retriever-Campaign-Kit, then point this script at where you want your campaign to
live. It copies the kit's repo template (skills, tools, note templates, the
Obsidian vault, map placeholders) into that location, scaffolds your first play
group for the chosen game system, seeds a config.json, and (optionally) initialises
a git repo — leaving you a folder you can open in Claude Code and Obsidian and
start running sessions in.

Pass --system to pick the game system the kit instances (default: stonetop; also
'forged' for Forged in the Dark). The choice is recorded in config.json and
selects which vocabulary/sheet/map profile the tools load.

Usage:
  python session-kit/bootstrap.py --target ../my-campaign
  python session-kit/bootstrap.py --target ../my-campaign --group winterfell --title "Winterfell Falls"
  python session-kit/bootstrap.py --target ../my-crew --group doskvol --title "The Crows" --system forged

Idempotent: existing files are left untouched (re-run it any time to add what's
missing). Pass --force to overwrite kit files with the kit's current versions
(your groups/ content is never touched).

Pure standard library. Requires Python 3.8+.
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "repo-template")


def copy_template(target, force):
    """Copy repo-template/ into target. Returns (created, skipped) path lists."""
    created, skipped = [], []
    for root, dirs, files in os.walk(TEMPLATE):
        dirs.sort()
        rel = os.path.relpath(root, TEMPLATE)
        dest_root = target if rel == "." else os.path.join(target, rel)
        os.makedirs(dest_root, exist_ok=True)
        for fn in sorted(files):
            src = os.path.join(root, fn)
            dst = os.path.join(dest_root, fn)
            relpath = os.path.relpath(dst, target)
            if os.path.exists(dst) and not force:
                skipped.append(relpath)
                continue
            shutil.copy2(src, dst)
            created.append(relpath)
    return created, skipped


def seed_config(target, group, title, system="stonetop"):
    """Write a minimal config.json (only if absent) so default_group resolves.
    Records the chosen game `system` so the kit's tools load the right profile."""
    path = os.path.join(target, "config.json")
    if os.path.exists(path):
        return False
    body = (
        "{\n"
        f'  "system": "{system}",\n'
        f'  "default_group": "{group}",\n'
        '  "groups": {\n'
        f'    "{group}": {{\n'
        f'      "title": "{title}",\n'
        f'      "system": "{system}",\n'
        '      "discord_webhook": "",\n'
        '      "roster": {}\n'
        "    }\n"
        "  }\n"
        "}\n"
    )
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    return True


def scaffold_group(target, group, title, system="stonetop"):
    """Run the kit's scaffold.py inside the target to build the group's structure."""
    cmd = [sys.executable, os.path.join("_tools", "scaffold.py"), "--group", group,
           "--system", system]
    if title:
        cmd += ["--title", title]
    subprocess.run(cmd, cwd=target, check=True)


def git_init(target):
    """git init the target if git is available and it isn't already a repo."""
    if os.path.isdir(os.path.join(target, ".git")):
        print("git: already a repository, leaving it alone.")
        return
    if shutil.which("git") is None:
        print("git: not found on PATH, skipping init (you can `git init` yourself).")
        return
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    print("git: initialised a new repository.")


def main():
    ap = argparse.ArgumentParser(
        description="Bootstrap a new Stonetop session-notes repo from this kit.")
    ap.add_argument("--target", required=True,
                    help="where to create the campaign repo (created if missing)")
    ap.add_argument("--group", default="",
                    help="scaffold a first play group with this folder name")
    ap.add_argument("--title", default="",
                    help="display title for the group (defaults to the group name)")
    ap.add_argument("--system", default="stonetop", choices=["stonetop", "forged"],
                    help="game system this campaign runs (default: stonetop). Selects "
                         "which vocabulary/sheet/map profile the kit instances.")
    ap.add_argument("--force", action="store_true",
                    help="overwrite kit files with the kit's current versions")
    ap.add_argument("--no-git", action="store_true",
                    help="do not run `git init` in the target")
    args = ap.parse_args()

    if not os.path.isdir(TEMPLATE):
        sys.exit(f"Can't find the kit template at {TEMPLATE}. Run this from a clone of the "
                 "Retriever-Campaign-Kit repo.")

    target = os.path.abspath(args.target)
    os.makedirs(target, exist_ok=True)
    print(f"Bootstrapping a {args.system} session repo in: {target}\n")

    created, skipped = copy_template(target, args.force)
    print(f"Kit files: {len(created)} copied, {len(skipped)} already present.")

    if args.group:
        title = args.title or args.group
        print(f"\nScaffolding group '{args.group}' ({title}) for {args.system}…")
        scaffold_group(target, args.group, title, args.system)
        if seed_config(target, args.group, title, args.system):
            print(f"Wrote a starter config.json (default_group = {args.group}).")
        else:
            print("config.json already present, left as-is.")

    if not args.no_git:
        print()
        git_init(target)

    print("\nDone. Next steps:")
    print(f"  1. cd {target}")
    if not args.group:
        print("  2. python _tools/scaffold.py --group <group> --title \"<Title>\"")
        print("  3. Copy config.example.json to config.json and fill in your roster + webhook.")
    else:
        print("  2. Edit config.json: add your Discord webhook and character->player roster.")
        print("     (For a multi-table campaign, see config.example.json for the `tables` shape.)")
    print("  - Add player sheets:  python _tools/new_note.py --kind player --group <group> "
          "--name <Character> --player \"<Real Name>\" --playbook \"The Heavy\"")
    print("  - Drop your map image into attachments/ (see attachments/README.md).")
    print("  - Open the folder in Claude Code; the /retriever-* skills are ready.")
    print("  - Open it in Obsidian too; it's already a vault.")
    print("  - Give your players a home: create a PRIVATE GitHub repo and add it as origin,")
    print("    e.g.  gh repo create <name> --private --source . --remote origin")
    print("    (or  git remote add origin <url>). /retriever-table-publish pushes there.")


if __name__ == "__main__":
    main()
