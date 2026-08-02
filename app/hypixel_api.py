from __future__ import annotations

from typing import Any

import requests

from app.config import HYPIXEL_API_BASE_URL
from app.exceptions import (
    AuthenticationError,
    InvalidApiResponseError,
    NetworkError,
    ProfileNotFoundError,
    RateLimitError,
)


class HypixelApiClient:
    def __init__(
        self,
        api_key: str,
        timeout_seconds: int = 15,
        session: requests.Session | None = None,
    ) -> None:
        cleaned_key = api_key.strip()

        if not cleaned_key:
            raise AuthenticationError(
                "Der Hypixel-API-Key fehlt."
            )

        self.api_key = cleaned_key
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

        self.session.headers.update(
            {
                "Accept": "application/json",
                "API-Key": self.api_key,
                "User-Agent": "SkyBlock-Level7-Helper/1.0",
            }
        )

    def get_skyblock_profiles(
        self,
        player_uuid: str,
    ) -> list[dict[str, Any]]:
        compact_uuid = player_uuid.replace("-", "").strip().lower()

        if not compact_uuid:
            raise ValueError("Die Spieler-UUID fehlt.")

        url = f"{HYPIXEL_API_BASE_URL}/skyblock/profiles"

        payload = self._get_json(
            url=url,
            params={"uuid": compact_uuid},
        )

        profiles = payload.get("profiles")

        if profiles is None:
            raise ProfileNotFoundError(
                "Für diesen Spieler wurden keine SkyBlock-Profile gefunden."
            )

        if not isinstance(profiles, list):
            raise InvalidApiResponseError(
                "Das Feld 'profiles' ist keine Liste."
            )

        valid_profiles = [
            profile
            for profile in profiles
            if isinstance(profile, dict)
        ]

        if not valid_profiles:
            raise ProfileNotFoundError(
                "Der Spieler besitzt kein auslesbares SkyBlock-Profil."
            )

        return valid_profiles

    def _get_json(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise NetworkError(
                "Die Hypixel-Anfrage hat zu lange gedauert."
            ) from exc
        except requests.RequestException as exc:
            raise NetworkError(
                f"Verbindung zur Hypixel-API fehlgeschlagen: {exc}"
            ) from exc

        if response.status_code == 403:
            raise AuthenticationError(
                "Hypixel hat den API-Key abgelehnt. "
                "Prüfe den Key und die registrierte Anwendung."
            )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")

            message = "Das Hypixel-API-Limit wurde erreicht."

            if retry_after:
                message += f" Erneut möglich in ungefähr {retry_after} Sekunden."

            raise RateLimitError(message)

        if response.status_code == 400:
            raise InvalidApiResponseError(
                "Hypixel meldet, dass erforderliche Daten fehlen."
            )

        if response.status_code == 422:
            raise InvalidApiResponseError(
                "Hypixel hat einen ungültigen Parameter erhalten."
            )

        if response.status_code < 200 or response.status_code >= 300:
            raise NetworkError(
                "Hypixel antwortete mit HTTP-Status "
                f"{response.status_code}."
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise InvalidApiResponseError(
                "Hypixel lieferte kein gültiges JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise InvalidApiResponseError(
                "Die Hypixel-Antwort ist kein JSON-Objekt."
            )

        if payload.get("success") is False:
            cause = payload.get("cause", "Unbekannter API-Fehler")
            raise InvalidApiResponseError(
                f"Hypixel-API-Fehler: {cause}"
            )

        return payload