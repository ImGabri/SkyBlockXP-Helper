from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import TASK_DATABASE_PATH
from app.exceptions import TaskDatabaseError
from app.models import Requirement, TaskDefinition


class TaskDatabase:
    def __init__(
        self,
        path: Path = TASK_DATABASE_PATH,
    ) -> None:
        self.path = path

    def load(self) -> list[TaskDefinition]:
        if not self.path.exists():
            raise TaskDatabaseError(
                f"Aufgaben-Datei nicht gefunden: {self.path}"
            )

        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except OSError as exc:
            raise TaskDatabaseError(
                f"Aufgaben-Datei konnte nicht gelesen werden: {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise TaskDatabaseError(
                "Die tasks.json enthält ungültiges JSON: "
                f"Zeile {exc.lineno}, Spalte {exc.colno}."
            ) from exc

        if not isinstance(payload, list):
            raise TaskDatabaseError(
                "Die tasks.json muss eine JSON-Liste enthalten."
            )

        tasks: list[TaskDefinition] = []
        seen_ids: set[str] = set()

        for index, raw_task in enumerate(payload):
            if not isinstance(raw_task, dict):
                raise TaskDatabaseError(
                    f"Aufgabe an Position {index} ist kein Objekt."
                )

            task = self._parse_task(raw_task, index)

            if task.task_id in seen_ids:
                raise TaskDatabaseError(
                    f"Doppelte task_id: {task.task_id}"
                )

            seen_ids.add(task.task_id)
            tasks.append(task)

        if not tasks:
            raise TaskDatabaseError(
                "Die Aufgaben-Datenbank ist leer."
            )

        return tasks

    def _parse_task(
        self,
        raw: dict[str, Any],
        index: int,
    ) -> TaskDefinition:
        required_string_fields = (
            "task_id",
            "title",
            "category",
            "description",
        )

        for field_name in required_string_fields:
            value = raw.get(field_name)

            if not isinstance(value, str) or not value.strip():
                raise TaskDatabaseError(
                    f"Aufgabe {index}: Feld '{field_name}' fehlt "
                    "oder ist ungültig."
                )

        xp_reward = raw.get("xp_reward")
        estimated_minutes = raw.get("estimated_minutes")

        if not isinstance(xp_reward, int) or xp_reward < 0:
            raise TaskDatabaseError(
                f"Aufgabe {index}: xp_reward muss eine "
                "nichtnegative Ganzzahl sein."
            )

        if not isinstance(estimated_minutes, (int, float)):
            raise TaskDatabaseError(
                f"Aufgabe {index}: estimated_minutes ist ungültig."
            )

        if estimated_minutes <= 0:
            raise TaskDatabaseError(
                f"Aufgabe {index}: estimated_minutes muss größer 0 sein."
            )

        requirement = self._parse_requirement(
            raw.get("requirement"),
            index=index,
        )

        raw_tags = raw.get("tags", [])

        if not isinstance(raw_tags, list):
            raise TaskDatabaseError(
                f"Aufgabe {index}: tags muss eine Liste sein."
            )

        tags = tuple(
            str(tag).strip()
            for tag in raw_tags
            if str(tag).strip()
        )

        return TaskDefinition(
            task_id=raw["task_id"].strip(),
            title=raw["title"].strip(),
            category=raw["category"].strip(),
            description=raw["description"].strip(),
            xp_reward=xp_reward,
            estimated_minutes=float(estimated_minutes),
            requirement=requirement,
            completion_kind=self._optional_string(
                raw.get("completion_kind")
            ),
            completion_key=self._optional_string(
                raw.get("completion_key")
            ),
            completion_value=raw.get("completion_value"),
            repeatable=bool(raw.get("repeatable", False)),
            priority_bonus=float(raw.get("priority_bonus", 0.0)),
            tags=tags,
        )

    def _parse_requirement(
        self,
        raw_requirement: Any,
        index: int,
    ) -> Requirement | None:
        if raw_requirement is None:
            return None

        if not isinstance(raw_requirement, dict):
            raise TaskDatabaseError(
                f"Aufgabe {index}: requirement muss ein Objekt sein."
            )

        kind = raw_requirement.get("kind")
        key = raw_requirement.get("key")
        minimum = raw_requirement.get("minimum")

        if not isinstance(kind, str) or not kind.strip():
            raise TaskDatabaseError(
                f"Aufgabe {index}: requirement.kind fehlt."
            )

        if not isinstance(key, str) or not key.strip():
            raise TaskDatabaseError(
                f"Aufgabe {index}: requirement.key fehlt."
            )

        if not isinstance(minimum, (int, float, bool)):
            raise TaskDatabaseError(
                f"Aufgabe {index}: requirement.minimum ist ungültig."
            )

        return Requirement(
            kind=kind.strip(),
            key=key.strip(),
            minimum=minimum,
        )

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if value is None:
            return None

        converted = str(value).strip()
        return converted or None