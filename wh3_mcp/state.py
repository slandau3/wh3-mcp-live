"""Live campaign state reader with per-file caching."""
import json
from config import (
    CAMPAIGN_STATE_FILE, FACTIONS_STATE_FILE, REGIONS_STATE_FILE,
    CHARACTERS_STATE_FILE, DIPLOMACY_STATE_FILE, CARAVANS_STATE_FILE,
    TECHNOLOGY_STATE_FILE, COMPASS_STATE_FILE,
)

# Per-file caches: {path: (mtime, data)}
_cache: dict = {}


def _read_file(path) -> dict:
    """Read and cache a single JSON dump file."""
    if not path.exists():
        return {}
    try:
        mtime = path.stat().st_mtime
        cached = _cache.get(path)
        if cached and cached[0] == mtime:
            return cached[1]
        data = json.loads(path.read_text(encoding="utf-8"))
        _cache[path] = (mtime, data)
        return data
    except Exception:
        return {}


def read_campaign_state() -> dict:
    """Read campaign metadata: turn_number, local_faction, turn_faction."""
    return _read_file(CAMPAIGN_STATE_FILE)


def read_factions() -> list:
    """Read faction metadata (treasury, culture, etc. — no nested regions/characters)."""
    data = _read_file(FACTIONS_STATE_FILE)
    return data.get("factions", [])


def read_regions() -> list:
    """Read all regions across all factions (flat list with owner_key)."""
    data = _read_file(REGIONS_STATE_FILE)
    return data.get("regions", [])


def read_characters() -> list:
    """Read all characters across all factions (flat list with faction_key)."""
    data = _read_file(CHARACTERS_STATE_FILE)
    return data.get("characters", [])


def read_diplomacy() -> dict:
    """Read diplomacy data."""
    return _read_file(DIPLOMACY_STATE_FILE)


def read_diplomacy_factions() -> dict:
    """Read diplomacy factions dict (handles both old flat format and new nested format)."""
    data = read_diplomacy()
    if "factions" in data:
        return data["factions"]
    return data


def read_pending_deals() -> list:
    """Read pending diplomatic deals."""
    data = read_diplomacy()
    return data.get("pending_deals", [])


def read_caravans() -> dict:
    """Read caravan data."""
    return _read_file(CARAVANS_STATE_FILE)


def read_technology() -> dict:
    """Read technology data."""
    return _read_file(TECHNOLOGY_STATE_FILE)


def read_compass() -> dict:
    """Read compass data."""
    return _read_file(COMPASS_STATE_FILE)


def read_live_state() -> dict:
    """Read full combined state (for tools that need everything)."""
    return {
        **read_campaign_state(),
        "factions": read_factions(),
        "regions": read_regions(),
        "characters": read_characters(),
        "diplomacy": read_diplomacy(),
        "caravans": read_caravans(),
        "technology": read_technology(),
        "compass": read_compass(),
    }


def find_faction(key: str) -> dict | None:
    for f in read_factions():
        if f.get("key") == key:
            return f
    return None


def find_region(key: str) -> dict | None:
    for r in read_regions():
        if r.get("key") == key:
            return r
    return None


def find_character(cqi: int) -> dict | None:
    for c in read_characters():
        if c.get("cqi") == cqi:
            return c
    return None


def all_characters(faction_key: str = None, char_type: str = None) -> list:
    result = []
    for c in read_characters():
        if faction_key and c.get("faction_key") != faction_key:
            continue
        if char_type and c.get("character_type") != char_type:
            continue
        result.append(c)
    return result


def all_armies(faction_key: str = None) -> list:
    """Read armies from factions (armies are still nested in faction data)."""
    result = []
    for f in read_factions():
        if faction_key and f["key"] != faction_key:
            continue
        for mf in f.get("military_forces", []):
            mf["faction_key"] = f["key"]
            result.append(mf)
    return result
