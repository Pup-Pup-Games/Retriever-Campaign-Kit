#!/usr/bin/env python
"""
publish.py — deterministically stage, commit, push, and post a session recap.

One reproducible command for the end-of-session share: it guards against committing
ignored working files, commits with a standard message, pushes the private repo, then
posts the recap to the group's Discord webhook (via post_discord.py). The recap *prose*
is authored by /retriever-recap; the publish mechanics here are identical every time.

Usage:
  python publish.py --group seal --session session-02
  python publish.py --group seal --session session-02 --dry-run     # show, do nothing
  python publish.py --group seal --session session-02 --no-discord  # push only

If --session is omitted, the latest sessions/session-NN.md is used. Pure stdlib.
"""
import argparse, json, os, re, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stonetop_lib as lib

GUARD = re.compile(r"(^|/)(config\.json$|_work/|\.(wav|mp3|m4a|flac|ogg|aac)$)")


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=lib.REPO, text=True,
                          capture_output=True, check=check)


def latest_session(group, table):
    prefix = table if table else "session"
    sdir = os.path.join(lib.group_dir(group), "sessions")
    nums = []
    if os.path.isdir(sdir):
        for fn in os.listdir(sdir):
            m = re.match(rf"{re.escape(prefix)}-(\d+)\.md$", fn)
            if m:
                nums.append(int(m.group(1)))
    if not nums:
        raise SystemExit(f"No {prefix}-NN.md recap found under {sdir}")
    return f"{prefix}-{max(nums):02d}"


def main():
    ap = argparse.ArgumentParser(description="Stage, commit, push, and post a recap.")
    ap.add_argument("--group", required=True)
    ap.add_argument("--table", default="", help="table within a multi-table group")
    ap.add_argument("--session", default="", help="<table>-NN or session-NN (default: latest)")
    ap.add_argument("--message", default="", help="override the commit message")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--no-discord", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="show actions, change nothing")
    args = ap.parse_args()

    lib.require_group(args.group)
    has_tables = bool(lib.load_config().get("groups", {}).get(args.group, {}).get("tables"))
    table = args.table or None
    if has_tables and not table:
        raise SystemExit(f"Group '{args.group}' has tables; pass --table (e.g. weeknight).")
    session = args.session or latest_session(args.group, table)
    nn = re.sub(r"\D", "", session)
    recap = os.path.join(lib.group_dir(args.group), "sessions", f"{session}.md")
    if not os.path.exists(recap):
        raise SystemExit(f"No recap at {recap}. Run /retriever-recap first.")

    # what would be committed. Do NOT strip the whole output — porcelain status codes
    # are column-aligned (e.g. " M path"), and stripping eats the leading space, which
    # would shift every path by one char and could hide a leaked config.json/_work file.
    status_lines = [ln for ln in git("status", "--porcelain").stdout.splitlines()
                    if ln.strip()]
    changed = [ln[3:] for ln in status_lines]
    leaked = [p for p in changed if GUARD.search(p.replace("\\", "/"))]
    if leaked:
        raise SystemExit("Refusing to commit ignored working files (fix .gitignore):\n  "
                         + "\n  ".join(leaked))

    msg = args.message or f"Session {nn}: {lib.display_title(args.group, table)} — recap & updates"
    dtable = ["--table", table] if table else []

    if args.dry_run:
        print("DRY RUN — no changes made.\n")
        print("Would commit these paths:\n  " + ("\n  ".join(changed) if changed else "(none)"))
        print(f"\nCommit message:\n  {msg}")
        print(f"\nPush: {'skipped' if args.no_push else 'origin (current branch)'}")
        if not args.no_discord:
            print("\nDiscord preview:")
            sys.stdout.flush()
            subprocess.run([sys.executable, os.path.join(lib.REPO, "_tools", "post_discord.py"),
                            "--group", args.group, "--file", recap, *dtable, "--dry-run"],
                           check=False)
        return

    if changed:
        git("add", "-A")
        git("commit", "-m", msg)
        print(f"Committed: {msg}")
    else:
        print("Nothing to commit; working tree clean.")

    if not args.no_push:
        r = git("push", check=False)
        print("Pushed." if r.returncode == 0 else f"Push failed:\n{r.stderr.strip()}")

    if not args.no_discord:
        r = subprocess.run([sys.executable, os.path.join(lib.REPO, "_tools", "post_discord.py"),
                            "--group", args.group, "--file", recap, *dtable], check=False)
        if r.returncode != 0:
            print("Discord post skipped or failed (check the webhook in config.json).")


if __name__ == "__main__":
    main()
