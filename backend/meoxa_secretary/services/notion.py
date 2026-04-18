"""Connecteur Notion sortant — pousse les CR de réunions vers une base Notion.

Le tenant fournit :
- `notion.api_key` : clé d'intégration Notion (Internal Integration Token)
- `notion.cr_database_id` : ID de la database destinataire (32 hex chars)

La database doit avoir au minimum :
- une propriété `Name` (title, obligatoire dans Notion)
- optionnel : `Date` (date), `Organizer` (email/rich_text), `Meeting ID` (rich_text)
"""

from __future__ import annotations

import httpx

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionService:
    def __init__(self, tenant_id: str) -> None:
        settings = SettingsService()
        self._api_key = settings.get_tenant(tenant_id, "notion.api_key")
        self._database_id = settings.get_tenant(tenant_id, "notion.cr_database_id")

    def is_configured(self) -> bool:
        return bool(self._api_key and self._database_id)

    async def push_meeting_cr(
        self,
        *,
        title: str,
        starts_at: str,
        organizer_email: str | None,
        meeting_id: str,
        summary_markdown: str,
    ) -> str | None:
        """Crée une page dans la database Notion configurée. Retourne le page_id."""
        if not self.is_configured():
            return None

        properties: dict = {
            "Name": {
                "title": [{"text": {"content": title[:200]}}],
            },
            "Date": {"date": {"start": starts_at}},
            "Meeting ID": {
                "rich_text": [{"text": {"content": meeting_id}}],
            },
        }
        if organizer_email:
            properties["Organizer"] = {
                "rich_text": [{"text": {"content": organizer_email}}],
            }

        # Découpe le markdown en blocs paragraphe Notion (limite 2000 char / bloc).
        children = _markdown_to_notion_blocks(summary_markdown)

        async with httpx.AsyncClient(
            base_url=NOTION_API,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=30,
        ) as client:
            r = await client.post(
                "/pages",
                json={
                    "parent": {"database_id": self._database_id},
                    "properties": properties,
                    "children": children[:100],  # Notion limite à 100 children/requête
                },
            )
            if r.status_code >= 400:
                logger.warning(
                    "notion.push_failed",
                    status=r.status_code,
                    body=r.text[:500],
                )
                return None
            data = r.json()
            page_id = data.get("id")
            logger.info("notion.pushed", page_id=page_id, meeting_id=meeting_id)
            return page_id


def _markdown_to_notion_blocks(md: str) -> list[dict]:
    """Conversion minimaliste markdown → Notion blocks (paragraphes + headings simples)."""
    blocks: list[dict] = []
    for line in md.split("\n"):
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("### "):
            blocks.append(_heading(line[4:].strip(), 3))
        elif line.startswith("## "):
            blocks.append(_heading(line[3:].strip(), 2))
        elif line.startswith("# "):
            blocks.append(_heading(line[2:].strip(), 1))
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append(_bullet(line[2:].strip()))
        else:
            blocks.append(_para(line))
    return blocks


def _para(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
        },
    }


def _heading(text: str, level: int) -> dict:
    block_type = f"heading_{min(level, 3)}"
    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [{"type": "text", "text": {"content": text[:200]}}],
        },
    }


def _bullet(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
        },
    }
