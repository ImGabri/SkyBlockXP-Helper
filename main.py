from __future__ import annotations

import argparse
import sys
from typing import Any

from app.cache import JsonCache
from app.config import (
    TARGET_SKYBLOCK_XP,
    ensure_directories,
    load_settings,
)
from app.console_ui import (
    choose_profile_index,
    print_header,
    print_profile_summary,
    print_route,
)
from app.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    PlayerNotFoundError,
    ProfileNotFoundError,
    RateLimitError,
    SkyBlockHelperError,
    TaskDatabaseError,
)
from app.hypixel_api import HypixelApiClient
from app.models import ParsedProfile
from app.mojang_api import MojangApiClient
from app.optimizer import RouteOptimizer
from app.profile_parser import (
    choose_default_profile,
    parse_profiles,
)
from app.task_database import TaskDatabase


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analysiert ein Hypixel-SkyBlock-Profil und erstellt "
            "eine legitime Route bis SkyBlock Level 7."
        )
    )

    parser.add_argument(
        "--username",
        type=str,
        default=None,
        help="Minecraft-Name. Überschreibt MINECRAFT_USERNAME aus .env.",
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Erzwingt eine neue API-Abfrage statt Cache-Nutzung.",
    )

    parser.add_argument(
        "--offline",
        action="store_true",
        help="Verwendet ausschließlich den lokalen Cache.",
    )

    parser.add_argument(
        "--xp",
        type=int,
        default=None,
        help=(
            "Manueller aktueller SkyBlock-XP-Wert. "
            "Überschreibt den API-Wert nur für die Berechnung."
        ),
    )

    parser.add_argument(
        "--complete",
        nargs="*",
        default=[],
        metavar="TASK_ID",
        help=(
            "Aufgaben lokal als erledigt markieren. "
            "Beispiel: --complete starter_objectives hub_discovery"
        ),
    )

    return parser


def fetch_profiles_from_api(
    username: str,
    api_key: str,
    timeout_seconds: int,
    cache: JsonCache,
) -> tuple[str, str, list[dict[str, Any]]]:
    mojang_client = MojangApiClient(
        timeout_seconds=timeout_seconds,
    )

    player = mojang_client.get_player_by_username(username)

    print(
        f"Minecraft-Spieler gefunden: "
        f"{player.username} ({player.compact_uuid})"
    )

    hypixel_client = HypixelApiClient(
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )

    raw_profiles = hypixel_client.get_skyblock_profiles(
        player_uuid=player.compact_uuid,
    )

    cache.save(
        username=player.username,
        player_uuid=player.compact_uuid,
        profiles=raw_profiles,
    )

    return (
        player.username,
        player.compact_uuid,
        raw_profiles,
    )


def load_profiles_from_cache(
    cache: JsonCache,
) -> tuple[str, str, list[dict[str, Any]]]:
    payload = cache.load()

    if payload is None:
        raise ProfileNotFoundError(
            "Es existiert noch kein lokaler Profil-Cache."
        )

    username = payload.get("username")
    player_uuid = payload.get("player_uuid")
    raw_profiles = payload.get("profiles")

    if not isinstance(username, str) or not username:
        raise ProfileNotFoundError(
            "Im Cache fehlt der Spielername."
        )

    if not isinstance(player_uuid, str) or not player_uuid:
        raise ProfileNotFoundError(
            "Im Cache fehlt die Spieler-UUID."
        )

    if not isinstance(raw_profiles, list):
        raise ProfileNotFoundError(
            "Im Cache fehlen die SkyBlock-Profile."
        )

    valid_profiles = [
        profile
        for profile in raw_profiles
        if isinstance(profile, dict)
    ]

    if not valid_profiles:
        raise ProfileNotFoundError(
            "Der Cache enthält keine gültigen Profile."
        )

    return username, player_uuid, valid_profiles


def resolve_profile(
    parsed_profiles: list[ParsedProfile],
) -> ParsedProfile:
    chosen_index = choose_profile_index(parsed_profiles)

    if chosen_index is not None:
        return parsed_profiles[chosen_index]

    return choose_default_profile(parsed_profiles)


def run() -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    ensure_directories()
    settings = load_settings()
    cache = JsonCache()

    print_header()

    username = (
        arguments.username.strip()
        if isinstance(arguments.username, str)
        else settings.minecraft_username
    )

    if arguments.offline:
        resolved_username, player_uuid, raw_profiles = (
            load_profiles_from_cache(cache)
        )

        print(
            f"Offline-Cache geladen für {resolved_username}."
        )
    else:
        should_use_cache = (
            not arguments.refresh
            and cache.is_fresh(settings.cache_max_age_seconds)
        )

        if should_use_cache:
            resolved_username, player_uuid, raw_profiles = (
                load_profiles_from_cache(cache)
            )

            age = cache.age_seconds() or 0

            print(
                f"Lokaler Cache geladen "
                f"({age / 60:.1f} Minuten alt)."
            )
            print(
                "Nutze --refresh nur für eine bewusst gestartete "
                "neue Abfrage."
            )
        else:
            if not username:
                raise ConfigurationError(
                    "MINECRAFT_USERNAME fehlt in der .env-Datei."
                )

            if not settings.has_api_key:
                raise ConfigurationError(
                    "HYPIXEL_API_KEY fehlt in der .env-Datei."
                )

            resolved_username, player_uuid, raw_profiles = (
                fetch_profiles_from_api(
                    username=username,
                    api_key=settings.hypixel_api_key,
                    timeout_seconds=settings.request_timeout_seconds,
                    cache=cache,
                )
            )

    parsed_profiles = parse_profiles(
        raw_profiles=raw_profiles,
        player_uuid=player_uuid,
    )

    selected_profile = resolve_profile(parsed_profiles)

    print_profile_summary(selected_profile)

    task_database = TaskDatabase()
    tasks = task_database.load()

    optimizer = RouteOptimizer(
        target_xp=TARGET_SKYBLOCK_XP,
    )

    manually_completed = {
        task_id.strip()
        for task_id in arguments.complete
        if task_id.strip()
    }

    route = optimizer.create_route(
        profile=selected_profile,
        tasks=tasks,
        manually_completed=manually_completed,
        manual_current_xp=arguments.xp,
    )

    print_route(route)

    print()
    print(
        "Hinweis: Das Programm analysiert ausschließlich Daten. "
        "Es steuert Minecraft nicht."
    )

    return 0


def main() -> None:
    try:
        exit_code = run()
    except ConfigurationError as exc:
        print(f"\nKonfigurationsfehler: {exc}")
        exit_code = 2
    except AuthenticationError as exc:
        print(f"\nAuthentifizierungsfehler: {exc}")
        exit_code = 3
    except RateLimitError as exc:
        print(f"\nAPI-Limit: {exc}")
        exit_code = 4
    except PlayerNotFoundError as exc:
        print(f"\nSpieler nicht gefunden: {exc}")
        exit_code = 5
    except ProfileNotFoundError as exc:
        print(f"\nProfil nicht gefunden: {exc}")
        exit_code = 6
    except TaskDatabaseError as exc:
        print(f"\nAufgaben-Datenbank fehlerhaft: {exc}")
        exit_code = 7
    except NetworkError as exc:
        print(f"\nNetzwerkfehler: {exc}")
        exit_code = 8
    except SkyBlockHelperError as exc:
        print(f"\nProgrammfehler: {exc}")
        exit_code = 9
    except KeyboardInterrupt:
        print("\nProgramm durch Benutzer beendet.")
        exit_code = 130
    except Exception as exc:
        print(
            "\nUnerwarteter Fehler: "
            f"{type(exc).__name__}: {exc}"
        )
        print(
            "Starte das Programm später mit einer Debug-Konfiguration, "
            "damit wir die genaue Ursache sehen."
        )
        exit_code = 1

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()