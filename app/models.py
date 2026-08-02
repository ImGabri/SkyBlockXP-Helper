from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class MinecraftPlayer:
    username: str
    uuid: str

    @property
    def compact_uuid(self) -> str:
        """
        UUID ohne Bindestriche.
        """
        return self.uuid.replace("-", "").lower()


@dataclass(slots=True)
class ParsedProfile:
    profile_id: str
    cute_name: str
    selected: bool
    game_mode: str | None
    member_uuid: str

    skyblock_xp: int = 0
    skyblock_level: float = 0.0

    skill_levels: dict[str, int] = field(default_factory=dict)
    skill_experience: dict[str, float] = field(default_factory=dict)

    collections: dict[str, int] = field(default_factory=dict)
    crafted_minion_tiers: set[str] = field(default_factory=set)

    fairy_souls_collected: int = 0
    objectives: dict[str, Any] = field(default_factory=dict)

    raw_member: dict[str, Any] = field(default_factory=dict, repr=False)
    raw_profile: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class Requirement:
    kind: str
    key: str
    minimum: float | int | bool


@dataclass(frozen=True, slots=True)
class TaskDefinition:
    task_id: str
    title: str
    category: str
    description: str
    xp_reward: int
    estimated_minutes: float

    requirement: Requirement | None = None
    completion_kind: str | None = None
    completion_key: str | None = None
    completion_value: float | int | bool | None = None

    repeatable: bool = False
    priority_bonus: float = 0.0
    tags: tuple[str, ...] = ()

    @property
    def base_xp_per_minute(self) -> float:
        if self.estimated_minutes <= 0:
            return float("inf")

        return self.xp_reward / self.estimated_minutes


@dataclass(frozen=True, slots=True)
class EvaluatedTask:
    task: TaskDefinition
    available: bool
    completed: bool
    completion_reason: str
    score: float

    @property
    def xp_reward(self) -> int:
        return self.task.xp_reward

    @property
    def estimated_minutes(self) -> float:
        return self.task.estimated_minutes

    @property
    def xp_per_minute(self) -> float:
        return self.task.base_xp_per_minute


@dataclass(slots=True)
class RoutePlan:
    current_xp: int
    target_xp: int
    tasks: list[EvaluatedTask] = field(default_factory=list)

    @property
    def remaining_xp_before_route(self) -> int:
        return max(0, self.target_xp - self.current_xp)

    @property
    def planned_xp(self) -> int:
        return sum(item.xp_reward for item in self.tasks)

    @property
    def projected_xp(self) -> int:
        return self.current_xp + self.planned_xp

    @property
    def estimated_minutes(self) -> float:
        return sum(item.estimated_minutes for item in self.tasks)

    @property
    def reaches_target(self) -> bool:
        return self.projected_xp >= self.target_xp