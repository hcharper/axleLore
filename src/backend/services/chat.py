"""Chat / LLM service for RigSherpa.

Wraps the Ollama REST API.  System prompt is kept short and structured
so the 1.7 B-parameter model can follow instructions reliably.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    content: str
    tokens_used: int
    model: str


# ---------------------------------------------------------------------------
# System prompt — intentionally concise for a small model
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are RigSherpa, a technician expert on the {vehicle_name}.

RULES (follow strictly):
- Answer ONLY from the RETRIEVED KNOWLEDGE below.  If the knowledge does not cover the question, say "I don't have that information."
- NEVER guess about safety items (brakes, steering, fuel, structural).
- Cite sources: [FSM], [IH8MUD], or [PARTS].
- Include part numbers and torque specs when available.
- Keep answers focused and structured.

{vehicle_context}
{retrieved_context}"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ChatService:
    """Async Ollama client with prompt management."""

    def __init__(
        self,
        ollama_host: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.ollama_host = ollama_host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.fallback_model = settings.ollama_fallback_model
        self.timeout = timeout or settings.ollama_timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)

    # -- generation -------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Non-streaming generation via Ollama."""
        temp = temperature if temperature is not None else settings.llm_temperature
        max_tok = max_tokens or settings.llm_max_tokens

        model = self.model
        try:
            return await self._call_generate(model, prompt, system_prompt, temp, max_tok)
        except httpx.HTTPError:
            # Attempt fallback model
            logger.warning("Primary model failed, trying fallback: %s", self.fallback_model)
            model = self.fallback_model
            return await self._call_generate(model, prompt, system_prompt, temp, max_tok)

    async def _call_generate(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        response = await self.client.post(
            f"{self.ollama_host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        return LLMResponse(
            content=data.get("response", ""),
            tokens_used=data.get("eval_count", 0),
            model=model,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Stream tokens from Ollama."""
        temp = temperature if temperature is not None else settings.llm_temperature
        try:
            async with self.client.stream(
                "POST",
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": True,
                    "options": {"temperature": temp},
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
        except httpx.HTTPError as e:
            logger.error("Ollama streaming failed: %s", e)
            raise

    # -- health -----------------------------------------------------------

    async def check_health(self) -> dict:
        """Return Ollama status and available models."""
        try:
            resp = await self.client.get(f"{self.ollama_host}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return {"status": "ok", "models": models}
            return {"status": "error", "models": []}
        except httpx.HTTPError:
            return {"status": "unreachable", "models": []}

    # -- prompt helpers ---------------------------------------------------

    def build_system_prompt(
        self,
        vehicle_name: str,
        vehicle_context: str = "",
        retrieved_context: str = "",
    ) -> str:
        return SYSTEM_PROMPT.format(
            vehicle_name=vehicle_name,
            vehicle_context=vehicle_context,
            retrieved_context=retrieved_context,
        )

    # -- lifecycle --------------------------------------------------------

    async def close(self) -> None:
        await self.client.aclose()
