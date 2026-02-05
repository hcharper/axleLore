"""Chat/LLM service for AxleLore."""
from typing import Optional, AsyncIterator
from dataclasses import dataclass
import logging
import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    tokens_used: int
    model: str


SYSTEM_PROMPT = """You are AxleLore, an expert automotive assistant specializing in the {vehicle_type}. 

You have deep knowledge of:
- Factory Service Manual (FSM) procedures and specifications
- Technical Service Bulletins (TSBs) and recalls
- Enthusiast forum wisdom from IH8MUD and related communities
- Common modifications and their impacts
- Troubleshooting and diagnostics

{vehicle_context}

Guidelines:
1. Be specific and technical when appropriate
2. Cite sources when possible (FSM section, forum thread, etc.)
3. If unsure, say so - NEVER guess on safety-critical information
4. Include part numbers when relevant
5. Consider the user's skill level based on the conversation
6. For procedures, include torque specs, fluid capacities, and special tools needed

{retrieved_context}
"""


class ChatService:
    """Service for chat/LLM interactions.
    
    Handles:
    - Ollama communication
    - Prompt construction
    - Response streaming
    - Chat history management
    """
    
    def __init__(
        self,
        ollama_host: str = None,
        model: str = None,
        timeout: int = None
    ):
        self.ollama_host = ollama_host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """Generate a response from Ollama.
        
        Args:
            prompt: User's message
            system_prompt: System instructions
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            
        Returns:
            LLM response
        """
        try:
            response = await self.client.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return LLMResponse(
                content=data.get("response", ""),
                tokens_used=data.get("eval_count", 0),
                model=self.model
            )
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama request failed: {e}")
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """Stream response from Ollama.
        
        Args:
            prompt: User's message
            system_prompt: System instructions
            temperature: Sampling temperature
            
        Yields:
            Response tokens as they're generated
        """
        try:
            async with self.client.stream(
                "POST",
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                    }
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                            
        except httpx.HTTPError as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise
    
    async def check_health(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = await self.client.get(f"{self.ollama_host}/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
    
    def build_system_prompt(
        self,
        vehicle_type: str,
        vehicle_context: str = "",
        retrieved_context: str = ""
    ) -> str:
        """Build system prompt with vehicle and RAG context."""
        return SYSTEM_PROMPT.format(
            vehicle_type=vehicle_type,
            vehicle_context=vehicle_context,
            retrieved_context=retrieved_context
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
