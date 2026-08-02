class SkyBlockHelperError(Exception):
    """
    Basisklasse für erwartbare Fehler des Programms.
    """


class ConfigurationError(SkyBlockHelperError):
    """
    Fehlerhafte oder fehlende Programmeinstellungen.
    """


class NetworkError(SkyBlockHelperError):
    """
    Netzwerkverbindung fehlgeschlagen.
    """


class AuthenticationError(SkyBlockHelperError):
    """
    API-Key fehlt, ist ungültig oder wurde abgelehnt.
    """


class RateLimitError(SkyBlockHelperError):
    """
    API-Anfragelimit wurde erreicht.
    """


class PlayerNotFoundError(SkyBlockHelperError):
    """
    Minecraft-Spieler konnte nicht gefunden werden.
    """


class ProfileNotFoundError(SkyBlockHelperError):
    """
    Für den Spieler wurde kein passendes SkyBlock-Profil gefunden.
    """


class InvalidApiResponseError(SkyBlockHelperError):
    """
    API-Antwort hat nicht das erwartete Format.
    """


class TaskDatabaseError(SkyBlockHelperError):
    """
    Aufgaben-Datenbank fehlt oder ist ungültig.
    """