"""
System profiles for the Retriever campaign kit.

Retriever ships a Stonetop toolkit today; this is the seam that lets it instance
other systems. Each profile holds the system-specific vocabulary the kit's tools
reason over — playbooks, the character stats, harm/condition model, and the name
the shared home base goes by (a Stonetop "steading" vs a Forged "crew") — plus the
sheet/entity template variants and the map templates to lay down.

`bootstrap.py --system <key>` records the choice in config.json; `scaffold.py`
and the other `_tools/*.py` load the matching profile here instead of hard-coding
Stonetop terms. Adding a system = add an entry to PROFILES (+ its templates and
map SVGs). Stonetop's values are unchanged, so the default behaves as before.
"""

PROFILES = {
    "stonetop": {
        "key": "stonetop",
        "name": "Stonetop",
        # The character stats a sheet tracks.
        "stats": ["STR", "DEX", "CON", "INT", "WIS", "CHA"],
        # Playbook names accepted by new_note.py --playbook.
        "playbooks": [
            "The Blessed", "The Fox", "The Heavy", "The Judge", "The Lightbearer",
            "The Marshal", "The Ranger", "The Seeker", "The Would-Be Hero",
        ],
        # How the sheet models lasting conditions.
        "conditions": ["weakened", "dazed", "miserable"],
        # What the party's shared home base is called (steading vs crew).
        "home_base": "steading",
        # Sheet + entity template variants (files under templates/, unsuffixed =
        # Stonetop for back-compat).
        "player_sheet_template": "player-sheet.md",
        "entity_template": "entity.md",
        "place_template": "place.md",
        # Map templates copied into a new campaign's attachments/.
        "map_templates": [
            "stonetop-steading.svg", "the-vicinity.svg",
        ],
    },
    "forged": {
        "key": "forged",
        "name": "Forged in the Dark",
        # Action ratings (0–4) grouped under Insight / Prowess / Resolve.
        "stats": [
            "Hunt", "Study", "Survey", "Tinker",           # Insight
            "Finesse", "Prowl", "Skirmish", "Wreck",       # Prowess
            "Attune", "Command", "Consort", "Sway",        # Resolve
        ],
        "playbooks": [
            "Cutter", "Hound", "Leech", "Lurk", "Slide", "Spider", "Whisper",
        ],
        # Trauma conditions (a representative starter set; the sheet lists more).
        "conditions": [
            "Cold", "Haunted", "Obsessed", "Paranoid",
            "Reckless", "Soft", "Unstable", "Vicious",
        ],
        "home_base": "crew",
        "player_sheet_template": "player-sheet.forged.md",
        "entity_template": "entity.forged.md",
        "place_template": "place.forged.md",
        "map_templates": [
            "the-city.svg",
        ],
    },
}


def get_profile(name):
    """Return the profile dict for `name` (default 'stonetop'). Raises on unknown."""
    key = (name or "stonetop").lower()
    if key not in PROFILES:
        raise SystemExit(
            f"ERROR: unknown system '{name}'. Known: {', '.join(sorted(PROFILES))}"
        )
    return PROFILES[key]
