from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.config import PROFILE_CACHE_PATH


class JsonCache:
    def __init__(
        self,
        path: Path = PROFILE_CACHE_PATH,
    ) -> None:
        self.path = path

    def save(
        self,
        username: str,
        player_uuid: str,
        profiles: list[dict[str, Any]],
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "saved_at_unix": int(time.time()),
            "username": username,
            "player_uuid": player_uuid,
            "profiles": profiles,
        }

        temporary_path = self.path.with_suffix(".tmp")

        temporary_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(self.path)

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None

        try:
            raw_text = self.path.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict):
            return None

        return payload

    def age_seconds(self) -> float | None:
        payload = self.load()

        if payload is None:
            return None

        saved_at = payload.get("saved_at_unix")

        if not isinstance(saved_at, (int, float)):
            return None

        return max(0.0, time.time() - float(saved_at))

    def is_fresh(self, max_age_seconds: int) -> bool:
        age = self.age_seconds()

        if age is None:
            return False

        return age <= max_age_seconds