from app.models import ParsedProfile, TaskDefinition
from app.optimizer import RouteOptimizer


def make_profile(
    skyblock_xp: int = 0,
    mining_level: int = 0,
) -> ParsedProfile:
    return ParsedProfile(
        profile_id="test-profile",
        cute_name="Apple",
        selected=True,
        game_mode=None,
        member_uuid="abc",
        skyblock_xp=skyblock_xp,
        skyblock_level=skyblock_xp / 100,
        skill_levels={"mining": mining_level},
    )


def test_optimizer_reaches_target() -> None:
    profile = make_profile(skyblock_xp=650)

    tasks = [
        TaskDefinition(
            task_id="task_a",
            title="Aufgabe A",
            category="Test",
            description="Test",
            xp_reward=30,
            estimated_minutes=2,
        ),
        TaskDefinition(
            task_id="task_b",
            title="Aufgabe B",
            category="Test",
            description="Test",
            xp_reward=25,
            estimated_minutes=1,
        ),
    ]

    optimizer = RouteOptimizer(target_xp=700)

    route = optimizer.create_route(
        profile=profile,
        tasks=tasks,
    )

    assert route.reaches_target
    assert route.projected_xp >= 700


def test_completed_skill_task_is_skipped() -> None:
    profile = make_profile(
        skyblock_xp=100,
        mining_level=5,
    )

    task = TaskDefinition(
        task_id="mining_5",
        title="Mining 5",
        category="Skills",
        description="Test",
        xp_reward=5,
        estimated_minutes=1,
        completion_kind="skill",
        completion_key="mining",
        completion_value=5,
    )

    optimizer = RouteOptimizer(target_xp=700)

    evaluated = optimizer.evaluate_task(
        profile=profile,
        task=task,
        manually_completed=set(),
    )

    assert evaluated.completed is True
    assert evaluated.score == 0


def test_manual_completion_is_respected() -> None:
    profile = make_profile()

    task = TaskDefinition(
        task_id="starter",
        title="Starter",
        category="Objectives",
        description="Test",
        xp_reward=50,
        estimated_minutes=5,
    )

    optimizer = RouteOptimizer(target_xp=700)

    evaluated = optimizer.evaluate_task(
        profile=profile,
        task=task,
        manually_completed={"starter"},
    )

    assert evaluated.completed is True
    assert evaluated.completion_reason == "Lokal als erledigt markiert"