"""Tests de l'algo de proposition de créneaux (pure logique, sans Graph)."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from meoxa_secretary.services.scheduling import (
    Slot,
    WorkingHours,
    _generate_candidates,
    _overlaps,
)

TZ = ZoneInfo("Europe/Paris")


def test_overlaps_detects_conflict() -> None:
    a = (
        datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc),
    )
    b = (
        datetime(2026, 4, 20, 10, 30, tzinfo=timezone.utc),
        datetime(2026, 4, 20, 11, 30, tzinfo=timezone.utc),
    )
    assert _overlaps(a, b)


def test_no_overlap_back_to_back() -> None:
    a = (
        datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc),
    )
    b = (
        datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
    )
    assert not _overlaps(a, b)


def test_candidates_respect_working_hours() -> None:
    # Lundi 20 avril 2026 à 7h UTC = 9h Paris (début horaires ouvrés)
    start = datetime(2026, 4, 20, 5, 0, tzinfo=timezone.utc)  # 7h Paris
    end = start + timedelta(days=1)
    working = WorkingHours()
    slots = _generate_candidates(
        from_date=start,
        to_date=end,
        duration=timedelta(minutes=30),
        tz=TZ,
        working=working,
    )
    assert slots, "Doit trouver au moins un slot dans la journée"
    for slot in slots:
        local = slot.start.astimezone(TZ)
        assert 9 <= local.hour < 18


def test_no_slots_on_weekend() -> None:
    # Samedi 18 avril 2026 — hors jours ouvrés
    start = datetime(2026, 4, 18, 8, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=1)  # dimanche
    working = WorkingHours()
    slots = _generate_candidates(
        from_date=start,
        to_date=end,
        duration=timedelta(minutes=30),
        tz=TZ,
        working=working,
    )
    assert slots == []


def test_lunch_break_skipped() -> None:
    start = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)  # 12h Paris
    end = datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc)   # 14h Paris
    working = WorkingHours()
    slots = _generate_candidates(
        from_date=start,
        to_date=end,
        duration=timedelta(minutes=30),
        tz=TZ,
        working=working,
    )
    # Entre 12h et 14h local = pause déjeuner, aucun slot ne doit matcher
    for slot in slots:
        local = slot.start.astimezone(TZ)
        assert not (12 <= local.hour < 14)


def test_slot_to_dict() -> None:
    s = Slot(
        start=datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc),
        end=datetime(2026, 4, 20, 9, 30, tzinfo=timezone.utc),
    )
    d = s.to_dict()
    assert "start" in d and "end" in d
