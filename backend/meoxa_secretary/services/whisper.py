"""Transcription audio via faster-whisper.

Choix par défaut :
- Modèle `small` (~466 Mo, bonne qualité FR, rapide en CPU int8)
- Compute type `int8` (CPU)
- VAD activé (saute les silences)

Le modèle est chargé une seule fois par processus (lazy init). Le cache
Hugging Face est stocké sous `HF_HOME` (=/var/lib/meoxa/huggingface dans le
conteneur), persisté via le volume `meoxa_data` — donc pas de re-download
à chaque redémarrage.

Les paramètres sont surcharcheables via platform_settings :
- whisper.model         (tiny | base | small | medium | large-v3)
- whisper.compute_type  (int8 | int8_float16 | float16 | float32)
- whisper.language      (code ISO, ex: "fr" ; vide = détection auto)
"""

from __future__ import annotations

import threading
from typing import Any

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)


class WhisperService:
    _model: Any = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        s = SettingsService()
        self._model_name = s.get_platform("whisper.model") or "small"
        self._compute_type = s.get_platform("whisper.compute_type") or "int8"
        self._language = s.get_platform("whisper.language") or "fr"

    # ---------------- Public ----------------

    def transcribe(self, file_path: str) -> str:
        """Transcrit un fichier audio/vidéo et renvoie le texte concaténé."""
        model = self._get_model()
        segments, info = model.transcribe(
            file_path,
            language=self._language or None,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        parts: list[str] = []
        for seg in segments:
            txt = seg.text.strip()
            if txt:
                parts.append(txt)
        logger.info(
            "whisper.transcribe.done",
            file=file_path,
            lang=info.language,
            duration=getattr(info, "duration", None),
            segments=len(parts),
        )
        return " ".join(parts)

    # ---------------- Lazy loader ----------------

    def _get_model(self) -> Any:
        if WhisperService._model is not None:
            return WhisperService._model
        with WhisperService._lock:
            if WhisperService._model is None:
                # Import ici pour ne pas forcer le chargement de ctranslate2
                # quand on n'utilise pas la transcription (p.ex. en dev léger).
                from faster_whisper import WhisperModel

                logger.info(
                    "whisper.model.loading",
                    model=self._model_name,
                    compute_type=self._compute_type,
                )
                WhisperService._model = WhisperModel(
                    self._model_name,
                    device="cpu",
                    compute_type=self._compute_type,
                )
                logger.info("whisper.model.loaded")
        return WhisperService._model
