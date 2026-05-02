"""
Tests for system hooks.

Tests the hook system for event-driven actions (webhooks, alerts, etc).
"""

import pytest
from app.services.hooks import (
    EventType,
    SystemHooks,
    get_system_hooks,
)


class TestSystemHooks:
    """Test cases for SystemHooks."""

    @pytest.fixture
    def hooks(self):
        """Create fresh hooks instance."""
        return SystemHooks()

    @pytest.mark.asyncio
    async def test_register_callback_and_trigger(self, hooks):
        """Should register callback and trigger correctly."""
        called = []

        async def handler(event):
            called.append(event)

        hooks.register_callback(EventType.DECISION_HIGH_RISK, handler)

        payload = {"decision": "deductible"}
        await hooks.trigger(EventType.DECISION_HIGH_RISK, payload=payload, decision_id="123")

        assert len(called) == 1
        event = called[0]
        assert event.event_type == EventType.DECISION_HIGH_RISK
        assert event.payload == payload
        assert event.decision_id == "123"

    @pytest.mark.asyncio
    async def test_multiple_callbacks_for_same_event(self, hooks):
        """Should call all callbacks for an event."""
        called1 = []
        called2 = []

        async def handler1(event):
            called1.append(event)

        async def handler2(event):
            called2.append(event)

        hooks.register_callback(EventType.DECISION_HIGH_RISK, handler1)
        hooks.register_callback(EventType.DECISION_HIGH_RISK, handler2)

        payload = {"shared": True}
        await hooks.trigger(EventType.DECISION_HIGH_RISK, payload=payload)

        assert len(called1) == 1
        assert len(called2) == 1

    @pytest.mark.asyncio
    async def test_webhook_http_call(self, hooks, monkeypatch):
        """Webhook should be called on trigger."""
        class MockResponse:
            status_code = 200

        class MockClient:
            def __init__(self, timeout=None):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc, tb):
                pass
            async def post(self, url, json=None, headers=None):
                MockClient.last_call = (url, json)
                return MockResponse()

        import httpx
        monkeypatch.setattr(httpx, "AsyncClient", MockClient)

        hooks.register_webhook("http://example.com/hook", [EventType.DECISION_HIGH_RISK])
        await hooks.trigger(EventType.DECISION_HIGH_RISK, payload={"test": 1})

        assert hasattr(MockClient, "last_call")
        url, json_data = MockClient.last_call
        assert url == "http://example.com/hook"
        assert json_data["event_type"] == "decision.high_risk"

    @pytest.mark.asyncio
    async def test_webhook_disabled(self, hooks, monkeypatch):
        """Disabled webhook should not be called."""
        class MockClient:
            def __init__(self, timeout=None):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc, tb):
                pass
            async def post(self, url, json=None, headers=None):
                MockClient.called = True

        import httpx
        monkeypatch.setattr(httpx, "AsyncClient", MockClient)
        MockClient.called = False

        hooks.register_webhook("http://example.com/hook", [EventType.DECISION_HIGH_RISK], enabled=False)
        await hooks.trigger(EventType.DECISION_HIGH_RISK, payload={})

        assert not MockClient.called

    def test_singleton_system_hooks(self):
        """get_system_hooks should return same instance."""
        h1 = get_system_hooks()
        h2 = get_system_hooks()
        assert h1 is h2

    def test_event_type_values(self):
        """EventType enum values."""
        assert EventType.DECISION_HIGH_RISK.value == "decision.high_risk"
        assert EventType.DECISION_CREATED.value == "decision.created"

    def test_list_webhooks(self, hooks):
        """list_webhooks should return list of webhook info."""
        hooks.register_webhook("http://a.com", [EventType.DECISION_HIGH_RISK])
        hooks.register_webhook("http://b.com", [EventType.DECISION_CREATED], enabled=False)
        webhooks = hooks.list_webhooks()
        assert len(webhooks) == 2
        assert webhooks[0]["url"] == "http://a.com"
        assert webhooks[0]["enabled"] is True
        assert webhooks[1]["enabled"] is False
