#!/usr/bin/env python
"""
stonetop_lib.py — shared, deterministic helpers for the Stonetop session-notes tools.

This module is the single source of truth for:
  - the relationship vocabulary (categories, reciprocals, synonym normalization)
  - repo/group path resolution
  - deterministic template stamping
  - idempotent inline-field (relationship) writing

Every mutation here is deterministic given the same inputs: the scripts that import
this (build_graph, new_note, scaffold, relate, track, publish) produce byte-identical
output run to run, so the skills can delegate all file changes to them instead of
hand-editing. Pure stdlib.
"""
import os, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
TEMPLATES = os.path.join(REPO, "templates")

# --------------------------------------------------------- relationship vocabulary
# Canonical relations grouped by category. Category drives edge color in the map.
CATEGORIES = {
    "affinity":   ["loves", "loved-by", "betrothed-to", "befriends", "fears",
                   "feared-by", "trusts", "trusted-by", "distrusts", "distrusted-by"],
    "kin":        ["parent-of", "child-of", "sibling-of", "spouse-of", "kin-of"],
    "allegiance": ["ally-of", "serves", "served-by", "member-of", "has-member",
                   "sworn-to", "has-sworn", "owes", "owed-by"],
    "antagonism": ["enemy-of", "rival-of", "hunts", "hunted-by", "claims", "claimed-by"],
    "spatial":    ["lives-in", "home-of", "rules", "ruled-by", "guards", "guarded-by",
                   "located-in", "location-of", "owns", "owned-by", "seeks", "sought-by",
                   "bound-to", "binds", "part-of", "has-part", "near",
                   # map geometry (read by build_gazetteer.py into the gazetteer)
                   "adjacent-to", "north-of", "south-of", "east-of", "west-of",
                   "above", "below", "overlooks", "overlooked-by", "travel-to"],
}
RELATION_CATEGORY = {rel: cat for cat, rels in CATEGORIES.items() for rel in rels}

# Reciprocal of each canonical relation (symmetric ones map to themselves).
RECIPROCAL = {
    "loves": "loved-by", "loved-by": "loves",
    "betrothed-to": "betrothed-to", "befriends": "befriends",
    "fears": "feared-by", "feared-by": "fears",
    "trusts": "trusted-by", "trusted-by": "trusts",
    "distrusts": "distrusted-by", "distrusted-by": "distrusts",
    "parent-of": "child-of", "child-of": "parent-of",
    "sibling-of": "sibling-of", "spouse-of": "spouse-of", "kin-of": "kin-of",
    "ally-of": "ally-of", "serves": "served-by", "served-by": "serves",
    "member-of": "has-member", "has-member": "member-of",
    "sworn-to": "has-sworn", "has-sworn": "sworn-to",
    "owes": "owed-by", "owed-by": "owes",
    "enemy-of": "enemy-of", "rival-of": "rival-of",
    "hunts": "hunted-by", "hunted-by": "hunts",
    "claims": "claimed-by", "claimed-by": "claims",
    "lives-in": "home-of", "home-of": "lives-in",
    "rules": "ruled-by", "ruled-by": "rules",
    "guards": "guarded-by", "guarded-by": "guards",
    "located-in": "location-of", "location-of": "located-in",
    "owns": "owned-by", "owned-by": "owns",
    "seeks": "sought-by", "sought-by": "seeks",
    "bound-to": "binds", "binds": "bound-to",
    "part-of": "has-part", "has-part": "part-of",
    "near": "near",
    "adjacent-to": "adjacent-to", "travel-to": "travel-to",
    "north-of": "south-of", "south-of": "north-of",
    "east-of": "west-of", "west-of": "east-of",
    "above": "below", "below": "above",
    "overlooks": "overlooked-by", "overlooked-by": "overlooks",
}

# Free phrasing -> canonical relation. Keys are lowercase, spaces preserved.
SYNONYMS = {
    "in love with": "loves", "love": "loves", "loves": "loves",
    "loved by": "loved-by",
    "betrothed to": "betrothed-to", "engaged to": "betrothed-to",
    "friends with": "befriends", "friend of": "befriends", "befriends": "befriends",
    "afraid of": "fears", "scared of": "fears", "fears": "fears",
    "feared by": "feared-by",
    "trusts": "trusts", "trust": "trusts", "trusts even more than himself": "trusts",
    "trusted by": "trusted-by",
    "distrusts": "distrusts", "wary of": "distrusts", "suspicious of": "distrusts",
    "parent of": "parent-of", "mother of": "parent-of", "father of": "parent-of",
    "child of": "child-of", "son of": "child-of", "daughter of": "child-of",
    "sibling of": "sibling-of", "brother of": "sibling-of", "sister of": "sibling-of",
    "next of kin": "kin-of", "kin of": "kin-of", "kin to": "kin-of",
    "related to": "kin-of", "relative of": "kin-of",
    "married to": "spouse-of", "spouse of": "spouse-of",
    "wife of": "spouse-of", "husband of": "spouse-of",
    "ally of": "ally-of", "allied with": "ally-of", "allies with": "ally-of",
    "serves": "serves", "works for": "serves", "servant of": "serves",
    "served by": "served-by",
    "member of": "member-of", "belongs to": "member-of",
    "sworn to": "sworn-to", "oath to": "sworn-to", "pledged to": "sworn-to",
    "owes": "owes", "indebted to": "owes", "in debt to": "owes",
    "owed by": "owed-by",
    "enemy of": "enemy-of", "enemies with": "enemy-of",
    "rival of": "rival-of", "rivals with": "rival-of",
    "hunts": "hunts", "hunting": "hunts",
    "hunted by": "hunted-by",
    "claims": "claims",
    "claimed by": "claimed-by",
    "lives in": "lives-in", "dwells in": "lives-in", "resides in": "lives-in",
    "home of": "home-of",
    "rules": "rules", "ruler of": "rules", "governs": "rules", "leads": "rules",
    "ruled by": "ruled-by",
    "guards": "guards", "protects": "guards",
    "guarded by": "guarded-by",
    "located in": "located-in", "is in": "located-in", "found in": "located-in",
    "hidden in": "located-in", "kept in": "located-in", "inside": "located-in",
    "location of": "location-of", "contains": "location-of",
    "owns": "owns", "possesses": "owns", "carries": "owns", "wields": "owns",
    "owned by": "owned-by", "held by": "owned-by",
    "seeks": "seeks", "wants": "seeks", "searching for": "seeks", "looking for": "seeks",
    "sought by": "sought-by",
    "bound to": "bound-to", "tied to": "bound-to",
    "binds": "binds",
    "part of": "part-of",
    "has part": "has-part",
    "near": "near", "close to": "near", "beside": "near",
    "adjacent to": "adjacent-to", "next to": "adjacent-to", "abuts": "adjacent-to",
    "borders": "adjacent-to", "connects to": "adjacent-to",
    "north of": "north-of", "south of": "south-of",
    "east of": "east-of", "west of": "west-of",
    "above": "above", "on top of": "above", "atop": "above",
    "below": "below", "beneath": "below", "under": "below", "underneath": "below",
    "overlooks": "overlooks", "looks over": "overlooks", "overlooked by": "overlooked-by",
    "travel to": "travel-to", "road to": "travel-to", "path to": "travel-to",
    "a day from": "travel-to", "reached from": "travel-to",
}


def normalize_relation(phrase):
    """Map free phrasing to a canonical relation; unknown phrases hyphenate as-is."""
    p = " ".join(phrase.strip().lower().split())
    canon = p.replace(" ", "-")
    if canon in RELATION_CATEGORY:
        return canon
    if p in SYNONYMS:
        return SYNONYMS[p]
    if canon in SYNONYMS:
        return SYNONYMS[canon]
    return canon  # unknown — still works, renders in the neutral "other" color


def reciprocal(rel):
    return RECIPROCAL.get(rel, rel)


# ------------------------------------------------------------------- path resolution
TYPE_DIR = {"npc": "people", "person": "people", "place": "places",
            "thing": "things", "object": "things"}


def group_dir(group):
    return os.path.join(REPO, "groups", group)


def require_group(group):
    d = group_dir(group)
    if not os.path.isdir(d):
        raise SystemExit(f"No such group: {d}  (run scaffold.py --group {group})")
    return d


def entity_dir(group, etype):
    if etype == "player":
        return os.path.join(group_dir(group), "players")
    sub = TYPE_DIR.get(etype.lower())
    if not sub:
        raise SystemExit(f"Unknown entity type: {etype}")
    return os.path.join(group_dir(group), "world", sub)


def search_dirs(group):
    g = group_dir(group)
    return [os.path.join(g, "world", "people"),
            os.path.join(g, "world", "places"),
            os.path.join(g, "world", "things"),
            os.path.join(g, "players")]


def h1_of(text):
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def aliases_of(text):
    m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return []
    am = re.search(r"^aliases:\s*\[(.*?)\]\s*$", m.group(1), re.MULTILINE)
    if not am:
        return []
    return [a.strip().strip('"').strip("'") for a in am.group(1).split(",") if a.strip()]


def find_note(group, name):
    """Return the path to an existing note matching `name` (filename, H1, or alias)."""
    want = name.strip().lower()
    for d in search_dirs(group):
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"):
                continue
            if os.path.splitext(fn)[0].lower() == want:
                return os.path.join(d, fn)
    # fall back to H1 / alias scan
    for d in search_dirs(group):
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"):
                continue
            p = os.path.join(d, fn)
            with open(p, encoding="utf-8") as f:
                t = f.read()
            if (h1_of(t) or "").strip().lower() == want:
                return p
            if want in [a.lower() for a in aliases_of(t)]:
                return p
    return None


# ----------------------------------------------------------- deterministic templating
def stamp(template_name, tokens):
    """Return the template text with {{TOKEN}} placeholders substituted."""
    path = os.path.join(TEMPLATES, template_name)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for key, val in tokens.items():
        text = text.replace("{{" + key + "}}", str(val))
    return text


def write_new(path, text):
    """Write text to path only if it doesn't already exist. Returns True if created."""
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return True


# ------------------------------------------------------ idempotent relationship writing
REL_LINE = re.compile(
    r"^\s*-\s*([A-Za-z][\w-]*)\s*::\s*\[\[([^\]]+)\]\]\s*(?:[—–-]\s*(.*))?$")


def add_relationship(path, relation, target, note=""):
    """Insert `- relation :: [[target]] — note` under ## Relationships, idempotently.

    Returns "added", "exists", or "no-section". Replaces a lone empty `- ` placeholder
    if present; never duplicates an existing relation+target pair.
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    # locate the ## Relationships section extent
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"^##\s+Relationships\s*$", ln):
            start = i
            break
    if start is None:
        return "no-section"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^##\s+", lines[j]):
            end = j
            break

    # already present? (match relation + target, ignore the note)
    for j in range(start + 1, end):
        m = REL_LINE.match(lines[j])
        if m:
            r = m.group(1).strip().lower()
            t = m.group(2).split("|")[0].split("#")[0].strip().lower()
            if r == relation.lower() and t == target.strip().lower():
                return "exists"

    new_line = f"- {relation} :: [[{target}]]" + (f" — {note}" if note else "")

    # replace a lone empty placeholder bullet within the section, if any
    for j in range(start + 1, end):
        if lines[j].strip() in ("-", "- "):
            lines[j] = new_line
            _write_lines(path, lines)
            return "added"

    # otherwise insert after the last non-empty line in the section
    insert_at = start + 1
    for j in range(start + 1, end):
        if lines[j].strip() and not lines[j].strip().startswith("<!--"):
            insert_at = j + 1
        elif lines[j].strip().startswith("<!--"):
            insert_at = max(insert_at, j + 1)
    lines.insert(insert_at, new_line)
    _write_lines(path, lines)
    return "added"


def _write_lines(path, lines):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def section_bounds(lines, heading):
    """Return (start_index, end_index) of a `## heading` section, or (None, None)."""
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"^##\s+{re.escape(heading)}\s*$", ln):
            start = i
            break
    if start is None:
        return None, None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^##\s+", lines[j]):
            end = j
            break
    return start, end


def add_bullet(path, heading, new_line, placeholder_startswith=()):
    """Append `new_line` under `## heading`, replacing a placeholder bullet if present.

    Returns "added" or "no-section". Used by track.py for Moves/Gear/Bonds/Notes/Harm.
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    start, end = section_bounds(lines, heading)
    if start is None:
        return "no-section"
    for j in range(start + 1, end):
        s = lines[j].strip()
        if s in ("-", "- ", "- (none)") or any(s.startswith(p) for p in placeholder_startswith):
            lines[j] = new_line
            _write_lines(path, lines)
            return "added"
    insert_at = start + 1
    for j in range(start + 1, end):
        st = lines[j].strip()
        if st and not st.startswith("<!--"):
            insert_at = j + 1
        elif st.startswith("<!--"):
            insert_at = max(insert_at, j + 1)
    lines.insert(insert_at, new_line)
    _write_lines(path, lines)
    return "added"


def update_frontmatter(path, key, value):
    """Set a top-level frontmatter `key: value`. Returns True if changed."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^(\s*---\s*\n)(.*?)(\n---\s*\n)(.*)$", text, re.DOTALL)
    if not m:
        return False
    head, fm, fence, body = m.groups()
    # [ \t]* not \s* — \s would cross the newline and eat the next field on an empty value
    if re.search(rf"^{re.escape(key)}:[ \t]*.*$", fm, re.MULTILINE):
        fm = re.sub(rf"^{re.escape(key)}:[ \t]*.*$", f"{key}: {value}".rstrip(), fm,
                    count=1, flags=re.MULTILINE)
    else:
        fm = fm + f"\n{key}: {value}"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + fm + fence + body)
    return True


# ------------------------------------------------------------- tables & config
def frontmatter_field(path, key):
    """Return a top-level frontmatter value for `key`, or None."""
    with open(path, encoding="utf-8") as f:
        m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n", f.read(), re.DOTALL)
    if not m:
        return None
    km = re.search(rf"^{re.escape(key)}:\s*(.+)$", m.group(1), re.MULTILINE)
    return km.group(1).strip() if km else None


def player_table(group, character):
    """Which table a PC plays at (from the `table:` field on their sheet), or None."""
    p = find_note(group, character)
    return frontmatter_field(p, "table") if p else None


def load_config():
    """Parse config.json (or return {} if absent)."""
    path = os.path.join(REPO, "config.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def discord_webhook(group, table=None):
    """Resolve the webhook for a group (multi-table groups require `table`)."""
    g = load_config().get("groups", {}).get(group, {})
    tables = g.get("tables")
    if tables:
        if not table:
            raise SystemExit(f"Group '{group}' has tables; pass --table {'/'.join(tables)}.")
        t = tables.get(table)
        if not t:
            raise SystemExit(f"Table '{table}' not found in group '{group}'.")
        return t.get("discord_webhook", "")
    return g.get("discord_webhook", "")


def display_title(group, table=None):
    """A human title for a group (and table, if given)."""
    g = load_config().get("groups", {}).get(group, {})
    base = g.get("title", group)
    if table and g.get("tables", {}).get(table):
        return f"{base}: {g['tables'][table].get('title', table)}"
    return base
