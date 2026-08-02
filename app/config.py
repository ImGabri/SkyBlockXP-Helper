from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_ROOT / "data"
CACHE_DIRECTORY = PROJECT_ROOT / "cache"

TASK_DATABASE_PATH = DATA_DIRECTORY / "tasks.json"
PROFILE_CACHE_PATH = CACHE_DIRECTORY / "profile_snapshot.json"

HYPIXEL_API_BASE_URL = "https://api.hypixel.net/v2"
MOJANG_API_BASE_URL = "https://api.mojang.com"

DEFAULT_REQUEST_TIMEOUT_SECONDS = 15
DEFAULT_CACHE_MAX_AGE_SECONDS = 60 * 60

TARGET_SKYBLOCK_LEVEL = 7
XP_PER_SKYBLOCK_LEVEL = 100
TARGET_SKYBLOCK_XP = TARGET_SKYBLOCK_LEVEL * XP_PER_SKYBLOCK_LEVEL


@dataclass(frozen=True, slots=True)
class Settings:
    hypixel_api_key: str
    minecraft_username: str
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS
    cache_max_age_seconds: int = DEFAULT_CACHE_MAX_AGE_SECONDS

    @property
    def has_api_key(self) -> bool:
        return bool(self.hypixel_api_key.strip())

    @property
    def has_username(self) -> bool:
        return bool(self.minecraft_username.strip())


def load_settings() -> Settings:
    """
    Lädt die lokale .env-Datei.

    Der API-Key wird nicht in den Quellcode geschrieben.
    """
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("HYPIXEL_API_KEY", "").strip()
    username = os.getenv("MINECRAFT_USERNAME", "").strip()

    return Settings(
        hypixel_api_key=api_key,
        minecraft_username=username,
    )


def ensure_directories() -> None:
    """
    Erstellt alle benötigten lokalen Ordner.
    """
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)