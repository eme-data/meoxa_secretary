"""Smart scheduling — trouve des créneaux libres dans le calendrier d'un utilisateur.

Algorithme :
1. Récupère les événements du calendrier via Graph sur la plage [start, end].
2. Génère la grille de créneaux candidats (pas = 15 min par défaut),
   restreinte aux heures et jours ouvrés configurés au niveau tenant.
3. Filtre ceux qui chevauchent un événement existant.
4. Filtre ceux qui chevauchent la pause déjeuner.
5. Retourne les N premiers non-chevauchants.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from meoxa_secretary.services.microsoft_graph import MicrosoftGraphService
from meoxa_secretary.services.settings import SettingsService

SLOT_STEP_MIN = 15


@dataclass
class Slot:
    start: datetime
    end: datetime

    def to_dict(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}


@dataclass
class WorkingHours:
    start_hour: int = 9
    end_hour: int = 18
    lunch_start_hour: int = 12
    lunch_end_hour: int = 14
    working_weekdays: tuple[int, ...] = (0, 1, 2, 3, 4)  # lundi-vendredi


class SchedulingService:
    async def find_free_slots(
        self,
        *,
        tenant_id: str,
        user_id: str,
        duration_min: int,
        from_date: datetime,
        to_date: datetime,
        max_slots: int = 5,
    ) -> list[Slot]:
        tz = ZoneInfo(
            SettingsService().get_tenant(tenant_id, "general.timezone") or "Europe/Paris"
        )
        working = WorkingHours()

        graph = await MicrosoftGraphService.for_user(tenant_id, user_id)
        try:
            events_raw = await graph.list_upcoming_events(
                start=from_date.astimezone(UTC).isoformat(),
                end=to_date.astimezone(UTC).isoformat(),
                top=200,
            )
        finally:
            await graph.aclose()

        busy = [_parse_event_window(e) for e in events_raw]
        busy = [b for b in busy if b is not None]

        duration = timedelta(minutes=duration_min)
        candidates = _generate_candidates(
            from_date=from_date.astimezone(tz),
            to_date=to_date.astimezone(tz),
            duration=duration,
            tz=tz,
            working=working,
        )

        free: list[Slot] = []
        for slot in candidates:
            if any(_overlaps(slot, b) for b in busy):
                continue
            free.append(slot)
            if len(free) >= max_slots:
                break
        return free


def _parse_event_window(event: dict) -> tuple[datetime, datetime] | None:
    try:
        start = datetime.fromisoformat(event["start"]["dateTime"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(event["end"]["dateTime"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    return (start, end)


def _generate_candidates(
    *,
    from_date: datetime,
    to_date: datetime,
    duration: timedelta,
    tz: ZoneInfo,
    working: WorkingHours,
) -> list[Slot]:
    slots: list[Slot] = []
    # On arrondit à l'heure pleine ou demi pour des propositions lisibles.
    cursor = from_date.replace(minute=0, second=0, microsecond=0)
    if cursor < from_date:
        cursor += timedelta(hours=1)

    step = timedelta(minutes=SLOT_STEP_MIN)

    while cursor + duration <= to_date:
        local = cursor.astimezone(tz)
        if local.weekday() not in working.working_weekdays:
            cursor += step
            continue

        day_start = local.replace(
            hour=working.start_hour, minute=0, second=0, microsecond=0
        )
        day_end = local.replace(
            hour=working.end_hour, minute=0, second=0, microsecond=0
        )
        if local < day_start:
            cursor = day_start.astimezone(UTC)
            continue
        if local + duration > day_end:
            cursor = (day_start + timedelta(days=1)).astimezone(UTC)
            continue

        # Pause déjeuner
        lunch_start = local.replace(
            hour=working.lunch_start_hour, minute=0, second=0, microsecond=0
        )
        lunch_end = local.replace(
            hour=working.lunch_end_hour, minute=0, second=0, microsecond=0
        )
        slot = Slot(start=cursor, end=cursor + duration)
        if _overlaps((slot.start, slot.end), (lunch_start, lunch_end)):
            cursor = lunch_end.astimezone(UTC)
            continue

        slots.append(slot)
        cursor += step

    return slots


def _overlaps(a, b) -> bool:
    if isinstance(a, Slot):
        a = (a.start, a.end)
    if isinstance(b, Slot):
        b = (b.start, b.end)
    return a[0] < b[1] and b[0] < a[1]
