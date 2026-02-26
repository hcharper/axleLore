"""Tests for ChatService."""

import pytest


class TestChatService:
    """Unit tests for the chat/LLM service."""

    def test_build_system_prompt(self):
        from backend.services.chat import ChatService
        svc = ChatService()
        prompt = svc.build_system_prompt(
            vehicle_name="Toyota FZJ80",
            vehicle_context="Vehicle: 1996 Toyota FZJ80\nMileage: 185,000 mi",
            retrieved_context="[1] FSM: Oil capacity is 6.8 quarts",
        )
        assert "Toyota FZJ80" in prompt
        assert "185,000 mi" in prompt
        assert "6.8 quarts" in prompt
        assert "RETRIEVED KNOWLEDGE" in prompt or "retrieved" in prompt.lower()

    def test_system_prompt_safety_rules(self):
        from backend.services.chat import ChatService
        svc = ChatService()
        prompt = svc.build_system_prompt(
            vehicle_name="FZJ80",
            vehicle_context="",
            retrieved_context="",
        )
        assert "NEVER guess about safety" in prompt
        assert "brakes" in prompt.lower() or "steering" in prompt.lower()

    @pytest.mark.asyncio
    async def test_generate_mock(self, mock_chat_service):
        resp = await mock_chat_service.generate(
            prompt="What is the oil capacity?",
            system_prompt="You are RigSherpa.",
        )
        assert resp.content
        assert resp.tokens_used > 0
        assert resp.model == "qwen3:1.7b"

    @pytest.mark.asyncio
    async def test_check_health_mock(self, mock_chat_service):
        health = await mock_chat_service.check_health()
        assert health["status"] == "ok"
        assert "qwen3:1.7b" in health["models"]
