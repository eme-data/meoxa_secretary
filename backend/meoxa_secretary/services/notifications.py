"""Notifications via webhooks entrants Slack et/ou Teams.

Le tenant configure une (ou les deux) URLs dans les tenant_settings :
- notifications.slack_webhook_url
- notifications.teams_webhook_url

L'envoi est best-effort : on n'échoue jamais l'action métier (CR généré,
brouillon d'email, etc.) à cause d'un webhook down.
"""

from __future__ import annotations

from typing import Any

import httpx

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)


class NotificationService:
    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id
        self._settings = SettingsService()

    async def notify(self, *, title: str, text: str, link: str | None = None) -> None:
        slack_url = self._settings.get_tenant(self._tenant_id, "notifications.slack_webhook_url")
        teams_url = self._settings.get_tenant(self._tenant_id, "notifications.teams_webhook_url")

        if not slack_url and not teams_url:
            return

        async with httpx.AsyncClient(timeout=10) as client:
            if slack_url:
                await self._send_slack(client, slack_url, title, text, link)
            if teams_url:
                await self._send_teams(client, teams_url, title, text, link)

    async def _send_slack(
        self,
        client: httpx.AsyncClient,
        url: str,
        title: str,
        text: str,
        link: str | None,
    ) -> None:
        payload: dict[str, Any] = {
            "text": f"*{title}*\n{text}",
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": title}},
                {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            ],
        }
        if link:
            payload["blocks"].append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Ouvrir"},
                            "url": link,
                        }
                    ],
                }
            )
        try:
            r = await client.post(url, json=payload)
            r.raise_for_status()
        except Exception as exc:
            logger.warning("notifications.slack.failed", error=str(exc))

    async def _send_teams(
        self,
        client: httpx.AsyncClient,
        url: str,
        title: str,
        text: str,
        link: str | None,
    ) -> None:
        # Format Office 365 Connector (MessageCard) — accepté par les webhooks
        # entrants historiques. Pour Workflows/Adaptive Cards, le payload change.
        actions = []
        if link:
            actions.append(
                {
                    "@type": "OpenUri",
                    "name": "Ouvrir",
                    "targets": [{"os": "default", "uri": link}],
                }
            )

        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": title,
            "themeColor": "0EA5E9",
            "title": title,
            "text": text,
            "potentialAction": actions,
        }
        try:
            r = await client.post(url, json=payload)
            r.raise_for_status()
        except Exception as exc:
            logger.warning("notifications.teams.failed", error=str(exc))
