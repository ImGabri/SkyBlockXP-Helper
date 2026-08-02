from __future__ import annotations

from collections.abc import Iterable

from app.models import (
    EvaluatedTask,
    ParsedProfile,
    Requirement,
    RoutePlan,
    TaskDefinition,
)


class RouteOptimizer:
    def __init__(
        self,
        target_xp: int = 700,
    ) -> None:
        if target_xp <= 0:
            raise ValueError("target_xp muss größer als 0 sein.")

        self.target_xp = target_xp

    def create_route(
        self,
        profile: ParsedProfile,
        tasks: Iterable[TaskDefinition],
        manually_completed: set[str] | None = None,
        manual_current_xp: int | None = None,
    ) -> RoutePlan:
        completed_ids = manually_completed or set()

        current_xp = (
            max(0, manual_current_xp)
            if manual_current_xp is not None
            else max(0, profile.skyblock_xp)
        )

        plan = RoutePlan(
            current_xp=current_xp,
            target_xp=self.target_xp,
        )

        if current_xp >= self.target_xp:
            return plan

        evaluated = [
            self.evaluate_task(
                profile=profile,
                task=task,
                manually_completed=completed_ids,
            )
            for task in tasks
        ]

        candidates = [
            item
            for item in evaluated
            if item.available and not item.completed
        ]

        candidates.sort(
            key=lambda item: (
                -item.score,
                -item.xp_per_minute,
                item.estimated_minutes,
                item.task.title.lower(),
            )
        )

        projected_xp = current_xp

        for candidate in candidates:
            if projected_xp >= self.target_xp:
                break

            plan.tasks.append(candidate)
            projected_xp += candidate.xp_reward

        return plan

    def evaluate_task(
        self,
        profile: ParsedProfile,
        task: TaskDefinition,
        manually_completed: set[str],
    ) -> EvaluatedTask:
        if task.task_id in manually_completed:
            return EvaluatedTask(
                task=task,
                available=True,
                completed=True,
                completion_reason="Lokal als erledigt markiert",
                score=0.0,
            )

        completed, completion_reason = self._is_completed(
            profile=profile,
            task=task,
        )

        available = self._requirement_is_met(
            profile=profile,
            requirement=task.requirement,
        )

        score = self._calculate_score(
            profile=profile,
            task=task,
            available=available,
            completed=completed,
        )

        return EvaluatedTask(
            task=task,
            available=available,
            completed=completed,
            completion_reason=completion_reason,
            score=score,
        )

    def _is_completed(
        self,
        profile: ParsedProfile,
        task: TaskDefinition,
    ) -> tuple[bool, str]:
        kind = task.completion_kind
        key = task.completion_key
        target = task.completion_value

        if kind is None or key is None:
            return False, "Keine automatische Erkennung"

        if kind == "manual":
            return False, "Nur lokal erkennbar"

        if kind == "skill":
            current = profile.skill_levels.get(key.lower(), 0)
            required = self._as_number(target)

            return (
                current >= required,
                f"Skill {key}: {current}/{required:g}",
            )

        if kind == "collection":
            current = profile.collections.get(key.upper(), 0)
            required = self._as_number(target)

            return (
                current >= required,
                f"Collection {key}: {current}/{required:g}",
            )

        if kind == "minion":
            normalized_key = key.upper()
            completed = normalized_key in profile.crafted_minion_tiers

            return (
                completed,
                (
                    "Minion-Tier bereits hergestellt"
                    if completed
                    else "Minion-Tier noch nicht erkannt"
                ),
            )

        if kind == "fairy_souls":
            current = profile.fairy_souls_collected
            required = self._as_number(target)

            return (
                current >= required,
                f"Fairy Souls: {current}/{required:g}",
            )

        if kind == "objective":
            objective = profile.objectives.get(key)
            completed = self._objective_completed(objective)

            return (
                completed,
                (
                    "Objective abgeschlossen"
                    if completed
                    else "Objective noch nicht abgeschlossen"
                ),
            )

        return False, f"Unbekannte Erkennung: {kind}"

    def _requirement_is_met(
        self,
        profile: ParsedProfile,
        requirement: Requirement | None,
    ) -> bool:
        if requirement is None:
            return True

        kind = requirement.kind
        key = requirement.key
        minimum = requirement.minimum

        if kind == "skill":
            current = profile.skill_levels.get(key.lower(), 0)
            return current >= self._as_number(minimum)

        if kind == "collection":
            current = profile.collections.get(key.upper(), 0)
            return current >= self._as_number(minimum)

        if kind == "fairy_souls":
            return (
                profile.fairy_souls_collected
                >= self._as_number(minimum)
            )

        if kind == "skyblock_level":
            return (
                profile.skyblock_level
                >= self._as_number(minimum)
            )

        if kind == "skyblock_xp":
            return (
                profile.skyblock_xp
                >= self._as_number(minimum)
            )

        if kind == "objective":
            objective = profile.objectives.get(key)
            required_state = bool(minimum)

            return self._objective_completed(objective) is required_state

        if kind == "minion":
            has_minion = key.upper() in profile.crafted_minion_tiers
            return has_minion is bool(minimum)

        return False

    def _calculate_score(
        self,
        profile: ParsedProfile,
        task: TaskDefinition,
        available: bool,
        completed: bool,
    ) -> float:
        if completed or not available:
            return 0.0

        score = task.base_xp_per_minute
        score += task.priority_bonus

        # Frühe Skills sind auf einem neuen Profil oft besonders effizient.
        if task.category.lower() == "skills":
            score += 0.75

        # Collections parallel zu Skills sind besonders wertvoll.
        if task.category.lower() == "collections":
            score += 0.5

        # Synergie: Die Aufgabe passt zu einem noch niedrigen Skill.
        for tag in task.tags:
            normalized_tag = tag.lower()

            if normalized_tag in profile.skill_levels:
                current_level = profile.skill_levels[normalized_tag]

                if current_level <= 2:
                    score += 1.0
                elif current_level <= 5:
                    score += 0.5

        # Sehr kleine Aufgaben sollen bei gleichem Nutzen zuerst kommen.
        if task.estimated_minutes <= 2:
            score += 0.5

        # Fallback-Blöcke sollen erst später gewählt werden.
        if "fallback" in task.tags:
            score -= 3.0

        return max(0.0, score)

    @staticmethod
    def _objective_completed(value: object) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, dict):
            if value.get("completed") is True:
                return True

            status = value.get("status")

            if isinstance(status, str):
                return status.lower() in {
                    "complete",
                    "completed",
                    "done",
                }

        return False

    @staticmethod
    def _as_number(value: object) -> float:
        if isinstance(value, bool):
            return float(value)

        if isinstance(value, (int, float)):
            return float(value)

        try:
            return float(str(value))
        except (TypeError, ValueError):
            return 0.0