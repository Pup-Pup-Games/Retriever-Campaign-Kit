#!/usr/bin/env python
"""
track.py — deterministically apply one change to a player sheet and log it.

The skill parses your at-the-table sentence into a structured op and calls this; the file
edit and the change-log line then come out identically every time. Move *text* is supplied
by the caller (the model fills it from the books) — everything else is mechanical here.

Ops:
  add-move    --name "Hack and Slash" --ref "Book I p.XX" [--text "..."]
  set-stat    --stat STR --value +2
  set-level   --value 3
  set-xp      --value 5
  adj-xp      --value +1            (delta, may be negative)
  add-gear    --value "silver ring (from the Greenmother)"
  remove-gear --value "shield"
  add-bond    --value "[[Wren]] — owes me for the bridge"
  add-harm    --value "2 harm: bruised ribs"
  clear-harm
  add-note    --value "swore to find the broken glyph-stone's name"
  session-note --value "the party freed the Hewn"   (logs only; no character edit)

Usage:
  python track.py --group seal --character Brann --op add-move --name "Hack and Slash" \
                  --ref "Book I p.XX" --text "When you attack in melee, roll +STR..."
  python track.py --group seal --op session-note --value "party freed the Hewn"

Every op also appends a line to the active session's _work/changes.md. Pure stdlib.
"""
import argparse, datetime, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stonetop_lib as lib

STATS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]


def signed(v):
    v = v.strip()
    return v if v[:1] in "+-" else ("+" + v)


def active_session(group, table, override):
    """Latest session id for this table. Multi-table groups use `<table>-NN`;
    single-table groups use `session-NN`."""
    if override:
        return override
    prefix = table if table else "session"
    sdir = os.path.join(lib.group_dir(group), "sessions")
    nums = []
    if os.path.isdir(sdir):
        for fn in os.listdir(sdir):
            m = re.match(rf"{re.escape(prefix)}-(\d+)(?:\.md)?$", fn)
            if m:
                nums.append(int(m.group(1)))
    n = max(nums) if nums else 1
    return f"{prefix}-{n:02d}"


def log_change(group, session, who, what):
    path = os.path.join(lib.group_dir(group), "sessions", session, "_work", "changes.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.datetime.now().strftime("%H:%M")
    if not os.path.exists(path):
        header = f"# Change log — {session}\n\n<!-- Working file, not committed. Source for /retriever-recap. -->\n\n"
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(header)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"- [{now}] {who}: {what}\n")
    return path


def set_stat(sheet, stat, value):
    with open(sheet, encoding="utf-8") as f:
        text = f.read()
    val = signed(value)
    new, n = re.subn(rf"\b{stat}\s*[+-]?\d+", f"{stat} {val}", text, count=1)
    if not n:
        raise SystemExit(f"Could not find stat {stat} in {sheet}")
    with open(sheet, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)


def adj_xp(sheet, delta):
    with open(sheet, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^xp:\s*(\d+)", text, re.MULTILINE)
    cur = int(m.group(1)) if m else 0
    new_val = max(0, cur + int(delta))
    lib.update_frontmatter(sheet, "xp", new_val)
    return new_val


def remove_gear(sheet, value):
    with open(sheet, encoding="utf-8") as f:
        lines = f.read().split("\n")
    start, end = lib.section_bounds(lines, "Gear")
    if start is None:
        raise SystemExit("No ## Gear section")
    needle = value.strip().lower()
    kept = [ln for k, ln in enumerate(lines)
            if not (start < k < end and ln.strip().startswith("-")
                    and needle in ln.lower())]
    if len(kept) == len(lines):
        raise SystemExit(f"No gear matching '{value}'")
    with open(sheet, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(kept))


def main():
    ap = argparse.ArgumentParser(description="Apply one tracked change to a player sheet.")
    ap.add_argument("--group", required=True)
    ap.add_argument("--character", default="", help="character name (omit for session-note)")
    ap.add_argument("--op", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--ref", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--stat", default="", choices=[""] + STATS)
    ap.add_argument("--value", default="")
    ap.add_argument("--table", default="", help="table within a multi-table group")
    ap.add_argument("--session", default="", help="override active session, e.g. weeknight-02")
    args = ap.parse_args()

    lib.require_group(args.group)
    # resolve the table: explicit flag, else inferred from the character's sheet
    table = args.table or (lib.player_table(args.group, args.character)
                           if args.character else None)
    has_tables = bool(lib.load_config().get("groups", {}).get(args.group, {}).get("tables"))
    if has_tables and not table and not args.session:
        raise SystemExit(f"Group '{args.group}' has tables; pass --table "
                         "(or --character so I can infer it, or --session).")
    session = active_session(args.group, table, args.session)
    op = args.op

    if op == "session-note":
        log_change(args.group, session, "(table)", args.value)
        print(f"Logged session note to {session}/_work/changes.md")
        return

    if not args.character:
        raise SystemExit(f"--character is required for op '{op}'")
    sheet = lib.find_note(args.group, args.character)
    if not sheet:
        raise SystemExit(f"No sheet for '{args.character}'. Create it with new_note.py "
                         f"--kind player --group {args.group} --name {args.character} ...")

    if op == "add-move":
        ref = args.ref or "Book ? p.??"
        text = args.text or "<!-- confirm move text -->"
        line = f"- **{args.name}** ({ref}) — {text}"
        lib.add_bullet(sheet, "Moves", line, placeholder_startswith=("- **<",))
        what = f"gained move {args.name} ({ref})"
    elif op == "set-stat":
        if not args.stat:
            raise SystemExit("--stat is required for set-stat")
        set_stat(sheet, args.stat, args.value)
        what = f"{args.stat} now {signed(args.value)}"
    elif op == "set-level":
        lib.update_frontmatter(sheet, "level", int(args.value))
        what = f"level now {args.value}"
    elif op == "set-xp":
        lib.update_frontmatter(sheet, "xp", int(args.value))
        what = f"XP now {args.value}"
    elif op == "adj-xp":
        nv = adj_xp(sheet, args.value)
        what = f"XP {signed(args.value)} (now {nv})"
    elif op == "add-gear":
        lib.add_bullet(sheet, "Gear", f"- {args.value}", placeholder_startswith=("- <",))
        what = f"gained {args.value}"
    elif op == "remove-gear":
        remove_gear(sheet, args.value)
        what = f"lost {args.value}"
    elif op == "add-bond":
        lib.add_bullet(sheet, "Bonds", f"- {args.value}", placeholder_startswith=("- <",))
        what = f"bond: {args.value}"
    elif op == "add-harm":
        lib.add_bullet(sheet, "Harm / Conditions", f"- {args.value}")
        what = f"harm: {args.value}"
    elif op == "clear-harm":
        with open(sheet, encoding="utf-8") as f:
            lines = f.read().split("\n")
        s, e = lib.section_bounds(lines, "Harm / Conditions")
        if s is not None:
            lines = lines[:s + 1] + ["- (none)"] + lines[e:]
            with open(sheet, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines))
        what = "cleared harm"
    elif op == "add-note":
        lib.add_bullet(sheet, "Notes", f"- {args.value}")
        what = args.value
    else:
        raise SystemExit(f"Unknown op: {op}")

    log_change(args.group, session, args.character, what)
    print(f"{args.character}: {what}")
    print(f"  {os.path.relpath(sheet, lib.REPO)} updated; logged to {session}/_work/changes.md")


if __name__ == "__main__":
    main()
