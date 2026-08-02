from __future__ import annotations

import math
from typing import Any, Iterable

from app.config import XP_PER_SKYBLOCK_LEVEL
from app.exceptions import ProfileNotFoundError
from app.models import ParsedProfile


SKILL_API_KEYS: dict[str, str] = {
    "farming": "experience_skill_farming",
    "mining": "experience_skill_mining",
    "combat": "experience_skill_combat",
    "foraging": "experience_skill_foraging",
    "fishing": "experience_skill_fishing",
    "enchanting": "experience_skill_enchanting",
    "alchemy": "experience_skill_alchemy",
    "taming": "experience_skill_taming",
    "carpentry": "experience_skill_carpentry",
    "runecrafting": "experience_skill_runecrafting",
    "social": "experience_skill_social2",
}


# Standard-Skill-XP für frühe Level.
# Für unser erstes Ziel bis Level 7 sind vor allem die ersten Skill-Level relevant.
STANDARD_SKILL_CUMULATIVE_XP: tuple[int, ...] = (
    0,
    50,
    175,
    375,
    675,
    1175,
    1925,
    2925,
    4425,
    6425,
    9925,
    14925,
    22425,
    32425,
    47425,
    67425,
    97425,
    147425,
    222425,
    322425,
    522425,
    822425,
    1222425,
    1722425,
    2322425,
    3022425,
    3822425,
    4722425,
    5722425,
    6822425,
    8022425,
    9322425,
    10722425,
    12222425,
    13822425,
    15522425,
    17322425,
    19222425,
    21222425,
    23322425,
    25522425,
    27822425,
    30222425,
    32722425,
    35322425,
    38072425,
    40872425,
    43772425,
    46772425,
    49872425,
    53072425,
    56372425,
    59772425,
    63272425,
    66872425,
    70572425,
    74372425,
    78272425,
    82272425,
    86472425,
    90772425,
    95172425,
    99672425,
    104272425,
)


def safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return default
        return int(value)

    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default

    return default


def safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)

    if isinstance(value, (int, float)):
        converted = float(value)

        if math.isnan(converted) or math.isinf(converted):
            return default

        return converted

    if isinstance(value, str):
        try:
            converted = float(value)
        except ValueError:
            return default

        if math.isnan(converted) or math.isinf(converted):
            return default

        return converted

    return default


def skill_level_from_experience(
    experience: float,
    cumulative_table: tuple[int, ...] = STANDARD_SKILL_CUMULATIVE_XP,
) -> int:
    """
    Gibt den vollständig erreichten Skill-Level zurück.

    Beispiel:
    - 0 XP -> Level 0
    - 50 XP -> Level 1
    - 175 XP -> Level 2
    """
    normalized_experience = max(0.0, experience)
    level = 0

    for index, required_experience in enumerate(cumulative_table):
        if normalized_experience >= required_experience:
            level = index
        else:
            break

    return level


def normalize_member_lookup(
    members: dict[str, Any],
    player_uuid: str,
) -> tuple[str, dict[str, Any]]:
    """
    Hypixel-UUIDs können mit oder ohne Bindestriche vorkommen.
    """
    compact_target = player_uuid.replace("-", "").lower()

    for member_key, member_value in members.items():
        compact_member_key = str(member_key).replace("-", "").lower()

        if compact_member_key == compact_target:
            return str(member_key), safe_dict(member_value)

    raise ProfileNotFoundError(
        "Der Spieler ist nicht als Mitglied dieses Profils enthalten."
    )


def extract_skyblock_experience(member: dict[str, Any]) -> int:
    """
    Unterstützt mehrere bekannte oder mögliche Feldpositionen.

    Die Reihenfolge ist absichtlich defensiv, weil API-Strukturen
    im Laufe der Zeit verändert werden können.
    """
    direct_candidates = (
        member.get("leveling"),
        member.get("skyblock_experience"),
        member.get("experience"),
    )

    leveling = safe_dict(member.get("leveling"))

    nested_candidates = (
        leveling.get("experience"),
        leveling.get("skyblock_experience"),
        leveling.get("xp"),
    )

    for candidate in (*nested_candidates, *direct_candidates):
        if isinstance(candidate, dict):
            continue

        numeric = safe_int(candidate, default=-1)

        if numeric >= 0:
            return numeric

    return 0


def extract_collections(member: dict[str, Any]) -> dict[str, int]:
    raw_collection = safe_dict(member.get("collection"))
    result: dict[str, int] = {}

    for key, value in raw_collection.items():
        normalized_key = str(key).upper()
        result[normalized_key] = max(0, safe_int(value))

    return result


def extract_crafted_minions(member: dict[str, Any]) -> set[str]:
    candidates: list[Any] = [
        member.get("crafted_generators"),
        member.get("crafted_minions"),
    ]

    player_data = safe_dict(member.get("player_data"))
    candidates.extend(
        [
            player_data.get("crafted_generators"),
            player_data.get("crafted_minions"),
        ]
    )

    for candidate in candidates:
        if isinstance(candidate, list):
            return {
                str(item).upper()
                for item in candidate
                if isinstance(item, str) and item.strip()
            }

    return set()


def extract_fairy_souls(member: dict[str, Any]) -> int:
    candidates = [
        member.get("fairy_souls_collected"),
        member.get("fairy_souls"),
    ]

    fairy_soul_data = safe_dict(member.get("fairy_soul"))
    candidates.extend(
        [
            fairy_soul_data.get("total_collected"),
            fairy_soul_data.get("fairy_souls_collected"),
        ]
    )

    for candidate in candidates:
        numeric = safe_int(candidate, default=-1)

        if numeric >= 0:
            return numeric

    return 0


def extract_objectives(member: dict[str, Any]) -> dict[str, Any]:
    objectives = member.get("objectives")

    if isinstance(objectives, dict):
        return objectives

    player_data = safe_dict(member.get("player_data"))
    nested = player_data.get("objectives")

    if isinstance(nested, dict):
        return nested

    return {}


def extract_skill_data(
    member: dict[str, Any],
) -> tuple[dict[str, float], dict[str, int]]:
    skill_experience: dict[str, float] = {}
    skill_levels: dict[str, int] = {}

    player_data = safe_dict(member.get("player_data"))
    experience_data = safe_dict(player_data.get("experience"))

    for skill_name, legacy_key in SKILL_API_KEYS.items():
        experience = 0.0

        # Neuere mögliche Struktur:
        if skill_name in experience_data:
            experience = safe_float(experience_data.get(skill_name))

        # Alternative Schreibweisen:
        elif skill_name.upper() in experience_data:
            experience = safe_float(experience_data.get(skill_name.upper()))

        # Ältere flache Struktur:
        elif legacy_key in member:
            experience = safe_float(member.get(legacy_key))

        skill_experience[skill_name] = max(0.0, experience)
        skill_levels[skill_name] = skill_level_from_experience(experience)

    return skill_experience, skill_levels


def parse_profile(
    raw_profile: dict[str, Any],
    player_uuid: str,
) -> ParsedProfile:
    members = safe_dict(raw_profile.get("members"))

    member_key, member = normalize_member_lookup(
        members=members,
        player_uuid=player_uuid,
    )

    skill_experience, skill_levels = extract_skill_data(member)
    skyblock_xp = extract_skyblock_experience(member)

    return ParsedProfile(
        profile_id=str(raw_profile.get("profile_id", "")),
        cute_name=str(raw_profile.get("cute_name", "Unbekannt")),
        selected=bool(raw_profile.get("selected", False)),
        game_mode=(
            str(raw_profile["game_mode"])
            if raw_profile.get("game_mode") is not None
            else None
        ),
        member_uuid=member_key,
        skyblock_xp=skyblock_xp,
        skyblock_level=skyblock_xp / XP_PER_SKYBLOCK_LEVEL,
        skill_levels=skill_levels,
        skill_experience=skill_experience,
        collections=extract_collections(member),
        crafted_minion_tiers=extract_crafted_minions(member),
        fairy_souls_collected=extract_fairy_souls(member),
        objectives=extract_objectives(member),
        raw_member=member,
        raw_profile=raw_profile,
    )


def parse_profiles(
    raw_profiles: Iterable[dict[str, Any]],
    player_uuid: str,
) -> list[ParsedProfile]:
    parsed: list[ParsedProfile] = []

    for raw_profile in raw_profiles:
        try:
            parsed.append(
                parse_profile(
                    raw_profile=raw_profile,
                    player_uuid=player_uuid,
                )
            )
        except ProfileNotFoundError:
            continue

    if not parsed:
        raise ProfileNotFoundError(
            "Keines der Profile enthält den angegebenen Spieler."
        )

    return parsed


def choose_default_profile(
    profiles: list[ParsedProfile],
) -> ParsedProfile:
    if not profiles:
        raise ProfileNotFoundError(
            "Es steht kein SkyBlock-Profil zur Auswahl."
        )

    selected_profiles = [
        profile
        for profile in profiles
        if profile.selected
    ]

    if selected_profiles:
        return selected_profiles[0]

    # Fallback: Profil mit den meisten auslesbaren SkyBlock-XP.
    return max(
        profiles,
        key=lambda profile: profile.skyblock_xp,
    )