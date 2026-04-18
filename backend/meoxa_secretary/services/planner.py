"""Poussée des actions d'un CR vers Microsoft Planner.

Flux :
1. Après `summarize_meeting`, on appelle `LLMService.extract_actions` qui renvoie
   une liste `[{title, owner_email?, due_date?}]`.
2. Pour chaque action, on crée une tâche dans le plan configuré via le setting
   tenant `planner.default_plan_id` (optionnel — si vide, on skip).
3. Les IDs des tâches créées sont sauvegardés dans `MeetingTranscript.planner_task_ids_json`.

Le tenant fournit son `plan_id` via l'admin tenant settings (il doit l'avoir
créé côté Microsoft Planner et avoir les bons droits sur le groupe M365 associé).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.meeting import MeetingTranscript
from meoxa_secretary.services.microsoft_graph import MicrosoftGraphService
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)


class PlannerService:
    async def push_actions_for_meeting(
        self,
        *,
        tenant_id: str | UUID,
        user_id: str | UUID,
        meeting_id: str | UUID,
        actions: list[dict],
    ) -> list[str]:
        if not actions:
            return []

        plan_id = SettingsService().get_tenant(str(tenant_id), "planner.default_plan_id")
        if not plan_id:
            logger.info("planner.skipped.no_plan_id", tenant_id=str(tenant_id))
            return []

        graph = await MicrosoftGraphService.for_user(str(tenant_id), str(user_id))
        task_ids: list[str] = []
        try:
            for action in actions:
                title = str(action.get("title", "")).strip()
                if not title:
                    continue
                due_iso = self._normalize_due(action.get("due_date"))
                assignee_id: str | None = None
                owner_email = action.get("owner_email")
                if owner_email:
                    assignee_id = await graph.resolve_user_id(owner_email)
                try:
                    task = await graph.create_planner_task(
                        plan_id=plan_id,
                        title=title,
                        due_date_iso=due_iso,
                        assignee_user_id=assignee_id,
                    )
                    task_ids.append(task.get("id", ""))
                except Exception as exc:
                    logger.exception(
                        "planner.task.create_failed", title=title, error=str(exc)
                    )
        finally:
            await graph.aclose()

        self._persist(meeting_id, task_ids)
        return task_ids

    @staticmethod
    def _normalize_due(value) -> str | None:
        if not value:
            return None
        try:
            # Accepte YYYY-MM-DD ou ISO complet.
            if isinstance(value, str) and len(value) == 10:
                dt = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
            else:
                dt = datetime.fromisoformat(str(value))
            return dt.isoformat().replace("+00:00", "Z")
        except ValueError:
            return None

    @staticmethod
    def _persist(meeting_id: str | UUID, task_ids: list[str]) -> None:
        with SessionLocal() as db:
            transcript = db.scalar(
                select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting_id)
            )
            if transcript:
                db.execute(
                    text("SELECT set_config('app.tenant_id', :tid, true)"),
                    {"tid": str(transcript.tenant_id)},
                )
                transcript.planner_task_ids_json = json.dumps(task_ids)
                db.commit()
