"""Media tools: text-to-audio generation."""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from nanobot.agent.tools.base import Tool

_DATA_FACT_BASE_URL = "https://iniciativas.data-fact.com/bots"
_DATA_FACT_API_KEY = "uF13kAYTSJNGW414QT9FT2bUD&uDHn9fpZ^d2v3a"
_TIMEOUT = 60.0


class TextToAudioTool(Tool):
    """Convert text to audio via data-fact TTS API."""

    name = "text_to_audio"
    description = (
        "Converts text to speech and returns a URL to the generated audio file. "
        "Use this when the user asks to hear something as audio, generate a voice message, "
        "or convert text to audio/mp3."
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to convert to audio.",
            },
        },
        "required": ["text"],
    }

    async def execute(self, text: str, **kwargs: Any) -> str:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.post(
                    f"{_DATA_FACT_BASE_URL}/obtener-audio-desde-texto",
                    json={"texto_a_convertir": text},
                    headers={
                        "X-API-KEY": _DATA_FACT_API_KEY,
                        "Content-Type": "application/json",
                    },
                )
                r.raise_for_status()
                data = r.json()

            audio_url = data.get("audio_url") or data.get("url") or data.get("audio")
            if not audio_url:
                return f"Error: TTS response did not contain an audio URL. Response: {data}"

            return f"Audio generated successfully: {audio_url}"

        except httpx.HTTPStatusError as e:
            logger.error("TextToAudio HTTP error: {}", e)
            return f"Error: TTS API returned {e.response.status_code}"
        except Exception as e:
            logger.error("TextToAudio error: {}", e)
            return f"Error: {e}"
