"""Service LLM — appels Claude (Anthropic) avec prompt caching + RAG tenant.

La clé API et les modèles sont lus depuis `SettingsService` (éditables
depuis l'UI super-admin). Le tenant peut choisir 'default' ou 'advanced'
via `llm.model_preference`.

Si un `tenant_id` est fourni et que Voyage AI est configuré, on enrichit
les prompts avec le contexte passé pertinent (emails, CR) via `ContextService`.
"""

import asyncio
import json
import re

from anthropic import Anthropic

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.models.memory import MemorySourceType
from meoxa_secretary.models.usage import LlmTaskKind
from meoxa_secretary.services.context import ContextService
from meoxa_secretary.services.settings import SettingsService
from meoxa_secretary.services.usage import UsageService

logger = get_logger(__name__)


class LLMService:
    """Wrapper autour du SDK Anthropic — modèle choisi par tenant, RAG optionnel."""

    def __init__(self, tenant_id: str | None = None) -> None:
        s = SettingsService()
        api_key = s.get_platform("anthropic.api_key")
        if not api_key:
            raise RuntimeError(
                "Clé Anthropic non configurée — renseigner anthropic.api_key dans l'admin."
            )
        self._client = Anthropic(api_key=api_key)
        self._default_model = s.get_platform("anthropic.model_default")
        self._advanced_model = s.get_platform("anthropic.model_advanced")
        self._tenant_id = tenant_id
        self._context = ContextService() if tenant_id else None

    def _model_for_task(self, task: str) -> str:
        """Choisit le modèle en tenant compte de la préférence du tenant."""
        if self._tenant_id:
            pref = SettingsService().get_tenant(self._tenant_id, "llm.model_preference")
            if pref == "advanced":
                return self._advanced_model
        # Synthèse de réunion utilise par défaut le modèle avancé
        if task == "meeting_summary":
            return self._advanced_model
        return self._default_model

    def summarize_meeting(self, transcript: str, context: str = "") -> str:
        """Génère un compte-rendu structuré en markdown."""
        system = (
            "Tu es un assistant qui produit des comptes-rendus de réunions concis, en français, "
            "au format markdown avec : résumé exécutif, décisions, points clés, actions (avec "
            "propriétaire et date si mentionnés)."
        )
        rag = self._retrieve_context(transcript[:1000])
        model = self._model_for_task("meeting_summary")

        message = self._client.messages.create(
            model=model,
            max_tokens=4000,
            system=[
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}},
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        (f"{rag}\n\n" if rag else "")
                        + f"Contexte de la réunion :\n{context}\n\n"
                        f"Transcription brute :\n{transcript}"
                    ),
                }
            ],
        )
        self._record_usage(model, LlmTaskKind.MEETING_SUMMARY, message.usage)
        return message.content[0].text  # type: ignore[union-attr]

    def extract_actions(self, summary_markdown: str) -> list[dict]:
        """Extrait les actions d'un CR en liste de dict (title, owner_email, due_date)."""
        system = (
            "Extrait les tâches à faire d'un compte-rendu de réunion. Renvoie UNIQUEMENT un "
            "JSON array valide, sans explication ni markdown, avec pour chaque item : "
            "title (string obligatoire), owner_email (string|null), due_date (YYYY-MM-DD|null)."
        )
        model = self._model_for_task("action_extraction") or self._default_model
        message = self._client.messages.create(
            model=model,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": summary_markdown}],
        )
        self._record_usage(model, LlmTaskKind.ACTION_EXTRACTION, message.usage)

        text_out = message.content[0].text  # type: ignore[union-attr]
        # Retire un éventuel fence ```json ... ```
        match = re.search(r"\[\s*\{.*\}\s*\]", text_out, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
            return [a for a in data if isinstance(a, dict) and a.get("title")]
        except json.JSONDecodeError as exc:
            logger.warning("llm.actions.parse_failed", error=str(exc))
            return []

    def draft_email_reply(self, email_body: str, thread_context: str = "") -> str:
        """Propose un brouillon de réponse à un email."""
        tone = "professionnel"
        signature = ""
        if self._tenant_id:
            s = SettingsService()
            tone = s.get_tenant(self._tenant_id, "emails.reply_tone") or tone
            signature = s.get_tenant(self._tenant_id, "general.email_signature")

        system = (
            f"Tu es un assistant qui rédige des réponses courtes, ton {tone}, en français, à des "
            "emails professionnels. Tu ne fais que proposer un brouillon — pas d'envoi."
        )
        if signature:
            system += f"\n\nSignature à ajouter en fin de réponse :\n{signature}"

        rag = self._retrieve_context(email_body)

        model = self._model_for_task("email_draft")
        message = self._client.messages.create(
            model=model,
            max_tokens=1000,
            system=[
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}},
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        (f"{rag}\n\n" if rag else "")
                        + f"Historique du fil :\n{thread_context}\n\nDernier email :\n{email_body}"
                    ),
                }
            ],
        )
        self._record_usage(model, LlmTaskKind.EMAIL_DRAFT, message.usage)
        return message.content[0].text  # type: ignore[union-attr]

    # ---------------- Usage tracking ----------------

    def _record_usage(self, model: str, task_kind: LlmTaskKind, usage) -> None:
        if not self._tenant_id:
            return
        UsageService.record(
            tenant_id=self._tenant_id,
            user_id=None,
            model=model,
            task_kind=task_kind,
            usage=usage,
        )

    # ---------------- RAG helper ----------------

    def _retrieve_context(self, query: str) -> str:
        if not self._tenant_id or not self._context:
            return ""
        try:
            entries = asyncio.run(
                self._context.retrieve(tenant_id=self._tenant_id, query=query, top_k=6)
            )
        except Exception as exc:
            logger.warning("llm.rag.retrieve_failed", error=str(exc))
            return ""
        return self._context.format_for_prompt(entries)
