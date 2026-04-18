"""Wrapper Voyage AI pour les embeddings.

Voyage AI est le provider recommandé par Anthropic. On utilise `voyage-3-large`
par défaut (1024 dims, multilingue incluant français). API : https://api.voyageai.com
"""

from __future__ import annotations

import httpx

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)

VOYAGE_API = "https://api.voyageai.com/v1/embeddings"


class EmbeddingsService:
    def __init__(self) -> None:
        s = SettingsService()
        self._api_key = s.get_platform("voyage.api_key")
        self._model = s.get_platform("voyage.model") or "voyage-3-large"

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def embed(
        self, texts: list[str], input_type: str = "document"
    ) -> list[list[float]]:
        """Retourne une liste d'embeddings (1024 dims) pour la liste de textes.

        input_type = "document" pour l'indexation, "query" pour la recherche.
        """
        if not self._api_key:
            raise RuntimeError(
                "Voyage AI non configuré — renseigner voyage.api_key dans l'admin plateforme."
            )
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                VOYAGE_API,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "input": texts,
                    "input_type": input_type,
                },
            )
            r.raise_for_status()
            data = r.json()
        return [item["embedding"] for item in data.get("data", [])]
