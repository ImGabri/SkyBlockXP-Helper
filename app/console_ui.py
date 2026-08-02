from __future__ import annotations

from app.models import ParsedProfile, RoutePlan


LINE = "=" * 78


def print_header() -> None:
    print()
    print(LINE)
    print(" HYPIXEL SKYBLOCK LEVEL 7 HELPER")
    print(" Legitime Analyse – keine Gameplay-Automation")
    print(LINE)


def print_profile_summary(profile: ParsedProfile) -> None:
    print()
    print("PROFIL")
    print("-" * 78)
    print(f"Name:             {profile.cute_name}")
    print(f"Profil-ID:        {profile.profile_id or 'Unbekannt'}")
    print(f"Aktiv:            {'Ja' if profile.selected else 'Nein'}")
    print(f"Modus:            {profile.game_mode or 'Normal'}")
    print(f"SkyBlock XP:      {profile.skyblock_xp}")
    print(f"SkyBlock Level:   {profile.skyblock_level:.2f}")
    print(f"Fairy Souls:      {profile.fairy_souls_collected}")
    print(f"Minion-Tiers:     {len(profile.crafted_minion_tiers)}")

    print()
    print("SKILLS")
    print("-" * 78)

    for skill_name, level in sorted(profile.skill_levels.items()):
        experience = profile.skill_experience.get(skill_name, 0.0)
        print(
            f"{skill_name.capitalize():15} "
            f"Level {level:<3} "
            f"XP {experience:,.0f}"
        )

    print()
    print("COLLECTIONS")
    print("-" * 78)

    if not profile.collections:
        print("Keine Collection-Daten auslesbar.")
    else:
        top_collections = sorted(
            profile.collections.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:12]

        for collection_name, amount in top_collections:
            print(f"{collection_name:25} {amount:>10,}")


def print_route(plan: RoutePlan) -> None:
    print()
    print("ROUTE BIS LEVEL 7")
    print("-" * 78)
    print(f"Aktueller XP-Stand:   {plan.current_xp}")
    print(f"Ziel:                  {plan.target_xp}")
    print(f"Noch benötigt:         {plan.remaining_xp_before_route}")
    print(f"Geplante XP:           {plan.planned_xp}")
    print(f"Voraussichtlicher XP:  {plan.projected_xp}")
    print(f"Geschätzte Zeit:       {plan.estimated_minutes:.1f} Minuten")
    print(
        "Ziel erreicht:         "
        f"{'Ja' if plan.reaches_target else 'Nein'}"
    )

    if not plan.tasks:
        print()
        print("Keine weiteren Aufgaben erforderlich.")
        return

    print()
    print(LINE)

    for position, evaluated in enumerate(plan.tasks, start=1):
        task = evaluated.task

        print()
        print(
            f"{position:>2}. {task.title} "
            f"[{task.category}]"
        )
        print(f"    {task.description}")
        print(
            f"    XP: {task.xp_reward} | "
            f"Zeit: {task.estimated_minutes:.1f} min | "
            f"XP/min: {task.base_xp_per_minute:.2f} | "
            f"Score: {evaluated.score:.2f}"
        )

    print()
    print(LINE)


def choose_profile_index(
    profiles: list[ParsedProfile],
) -> int | None:
    if len(profiles) <= 1:
        return 0 if profiles else None

    print()
    print("GEFUNDENE PROFILE")
    print("-" * 78)

    for index, profile in enumerate(profiles, start=1):
        active_label = " [AKTIV]" if profile.selected else ""

        print(
            f"{index}. {profile.cute_name}{active_label} – "
            f"Level {profile.skyblock_level:.2f}"
        )

    print()
    raw_choice = input(
        "Profilnummer eingeben oder Enter für automatische Wahl: "
    ).strip()

    if not raw_choice:
        return None

    try:
        selected_index = int(raw_choice) - 1
    except ValueError:
        print("Ungültige Eingabe. Das aktive Profil wird verwendet.")
        return None

    if selected_index < 0 or selected_index >= len(profiles):
        print("Nummer außerhalb des Bereichs. Aktives Profil wird verwendet.")
        return None

    return selected_index