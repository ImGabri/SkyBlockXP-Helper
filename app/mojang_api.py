from __future__ import annotations

from typing import Any

import requests

from app.config import MOJANG_API_BASE_URL
from app.exceptions import (
    InvalidApiResponseError,
    NetworkError,
    PlayerNotFoundError,
)
from app.models import MinecraftPlayer


class MojangApiClient:
    def __init__(
        self,
        timeout_seconds: int = 15,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "SkyBlock-Level7-Helper/1.0",
            }
        )

    def get_player_by_username(self, username: str) -> MinecraftPlayer:
        cleaned_username = username.strip()

        if not cleaned_username:
            raise PlayerNotFoundError(
                "Es wurde kein Minecraft-Name eingegeben."
            )

        url = (
            f"{MOJANG_API_BASE_URL}/users/profiles/minecraft/"
            f"{cleaned_username}"
        )

        try:
            response = self.session.get(
                url,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise NetworkError(
                "Die Mojang-Anfrage hat zu lange gedauert."
            ) from exc
        except requests.RequestException as exc:
            raise NetworkError(
                f"Verbindung zur Mojang-API fehlgeschlagen: {exc}"
            ) from exc

        if response.status_code in {204, 404}:
            raise PlayerNotFoundError(
                f"Der Minecraft-Spieler '{cleaned_username}' "
                "wurde nicht gefunden."
            )

        if response.status_code != 200:
            raise NetworkError(
                "Die Mojang-API antwortete mit HTTP-Status "
                f"{response.status_code}."
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise InvalidApiResponseError(
                "Die Mojang-API lieferte kein gültiges JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise InvalidApiResponseError(
                "Die Mojang-Antwort ist kein JSON-Objekt."
            )

        player_uuid = payload.get("id")
        resolved_name = payload.get("name")

        if not isinstance(player_uuid, str) or not player_uuid:
            raise InvalidApiResponseError(
                "In der Mojang-Antwort fehlt die UUID."
            )

        if not isinstance(resolved_name, str) or not resolved_name:
            resolved_name = cleaned_username

        return MinecraftPlayer(
            username=resolved_name,
            uuid=player_uuid,
        )