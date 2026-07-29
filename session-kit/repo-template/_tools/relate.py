#!/usr/bin/env python
"""
relate.py — deterministically record a typed relationship between two entities.

Normalizes the relation to the canonical vocabulary, finds or creates both entity notes,
writes the inline field on the subject's note and the reciprocal on the object's note, and
never duplicates an existing line. All the variable logic (synonyms, reciprocals, note
creation, idempotent insertion) lives here and in stonetop_lib, so the result is identical
run to run. The skill only parses your sentence into these flags.

Usage:
  python relate.py --group seal --subject Brann --relation "in love with" --object Eirlys
  python relate.py --group seal --subject Hask --relation "next of kin" --object Wren --note brother
  python relate.py --group seal --subject "The Muster-Horn" --object "The Drowned Mill" \
                   --relation "hidden in" --subject-type thing --object-type place

If a note must be created, --subject-type / --object-type set where it goes
(npc -> world/people, place -> world/places, thing -> world/things; an existing PC sheet
is found automatically). Default type for a created note is npc. Pure stdlib.
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stonetop_lib as lib
from new_note import make_note


def resolve(group, name, etype, session):
    """Return (display_name, path), creating the note if it doesn't exist."""
    path = lib.find_note(group, name)
    if path:
        return os.path.splitext(os.path.basename(path))[0], path
    path, _ = make_note(group, etype, name, session=session)
    return name, path


def main():
    ap = argparse.ArgumentParser(description="Record a typed relationship.")
    ap.add_argument("--group", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--relation", required=True, help="canonical or free phrasing")
    ap.add_argument("--object", required=True)
    ap.add_argument("--note", default="", help="optional note on the subject's edge")
    ap.add_argument("--subject-type", default="npc",
                    choices=["npc", "place", "thing", "player"])
    ap.add_argument("--object-type", default="npc",
                    choices=["npc", "place", "thing", "player"])
    ap.add_argument("--session", default="unknown", help="first_seen for created notes")
    args = ap.parse_args()

    lib.require_group(args.group)
    rel = lib.normalize_relation(args.relation)
    recip = lib.reciprocal(rel)
    if rel not in lib.RELATION_CATEGORY:
        print(f"note: '{args.relation}' -> '{rel}' is not in the canonical vocabulary; "
              "it will render in the neutral color.")

    subj_name, subj_path = resolve(args.group, args.subject, args.subject_type, args.session)
    obj_name, obj_path = resolve(args.group, args.object, args.object_type, args.session)

    r1 = lib.add_relationship(subj_path, rel, obj_name, args.note)
    r2 = lib.add_relationship(obj_path, recip, subj_name, "")

    print(f"{subj_name} --{rel}--> {obj_name}")
    print(f"  {os.path.relpath(subj_path, lib.REPO)}: {r1}")
    print(f"  {os.path.relpath(obj_path, lib.REPO)}: {recip} ({r2})")
    print(f"Next: python _tools/build_graph.py --group {args.group}")


if __name__ == "__main__":
    main()
