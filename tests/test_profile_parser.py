from app.profile_parser import (
    choose_default_profile,
    parse_profile,
    skill_level_from_experience,
)


def test_skill_level_from_experience() -> None:
    assert skill_level_from_experience(0) == 0
    assert skill_level_from_experience(49) == 0
    assert skill_level_from_experience(50) == 1
    assert skill_level_from_experience(175) == 2
    assert skill_level_from_experience(674) == 3
    assert skill_level_from_experience(675) == 4


def test_parse_profile_handles_compact_uuid() -> None:
    player_uuid = "12345678123456781234567812345678"

    raw_profile = {
        "profile_id": "profile-1",
        "cute_name": "Apple",
        "selected": True,
        "members": {
            player_uuid: {
                "leveling": {
                    "experience": 345
                },
                "experience_skill_mining": 175,
                "collection": {
                    "COAL": 500
                },
                "crafted_generators": [
                    "COAL_GENERATOR_1"
                ],
                "fairy_souls_collected": 5
            }
        }
    }

    parsed = parse_profile(
        raw_profile=raw_profile,
        player_uuid=player_uuid,
    )

    assert parsed.skyblock_xp == 345
    assert parsed.skyblock_level == 3.45
    assert parsed.skill_levels["mining"] == 2
    assert parsed.collections["COAL"] == 500
    assert "COAL_GENERATOR_1" in parsed.crafted_minion_tiers
    assert parsed.fairy_souls_collected == 5


def test_choose_selected_profile() -> None:
    player_uuid = "abc"

    raw_a = {
        "profile_id": "a",
        "cute_name": "Apple",
        "selected": False,
        "members": {
            player_uuid: {
                "leveling": {
                    "experience": 500
                }
            }
        }
    }

    raw_b = {
        "profile_id": "b",
        "cute_name": "Banana",
        "selected": True,
        "members": {
            player_uuid: {
                "leveling": {
                    "experience": 100
                }
            }
        }
    }

    profile_a = parse_profile(raw_a, player_uuid)
    profile_b = parse_profile(raw_b, player_uuid)

    chosen = choose_default_profile(
        [profile_a, profile_b]
    )

    assert chosen.cute_name == "Banana"