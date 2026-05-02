"""
Internal System Hooks for event-driven workflows.

Allows external systems to react to tax decisions:
- Webhooks for high-risk decisions
- Event bus for internal integrations
- Async notifications
"""

import logging
from typing import Optional, List, Dict, Callable
from enum import Enum
from datetime import datetime, timezone
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events that can be triggered."""
    DECISION_CREATED = "decision.created"
    DECISION_HIGH_RISK = "decision.high_risk"
    DECISION_VALIDATED = "decision.validated"
    DECISION_UNCERTAIN = "decision.uncertain"
    LEGISLATION_UPDATED = "legislation.updated"
    CACHE_INVALIDATED = "cache.invalidated"


class WebhookEvent(BaseModel):
    """Event payload for webhooks."""
    event_type: EventType
    timestamp: datetime
    decision_id: Optional[str] = None
    payload: Dict


class SystemHooks:
    """
    Internal system hooks for event-driven integrations.
    
    Supports:
    - Webhook registration and calling
    - Callback functions
    - Event filtering
    """
    
    def __init__(self):
        self._webhooks: List[Dict] = []
        self._callbacks: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
    
    def register_webhook(
        self,
        url: str,
        events: List[EventType],
        secret: Optional[str] = None,
        enabled: bool = True,
    ):
        """Register a webhook URL for specific events."""
        self._webhooks.append({
            "url": url,
            "events": events,
            "secret": secret,
            "enabled": enabled,
        })
        logger.info(f"Registered webhook: {url} for {len(events)} events")
    
    def register_callback(
        self,
        event_type: EventType,
        callback: Callable,
    ):
        """Register a callback function for an event type."""
        self._callbacks[event_type].append(callback)
        logger.info(f"Registered callback for {event_type.value}")
    
    async def trigger(
        self,
        event_type: EventType,
        payload: Optional[Dict] = None,
        decision_id: Optional[str] = None,
    ):
        """Trigger an event to all registered hooks."""
        event = WebhookEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            decision_id=decision_id,
            payload=payload or {},
        )
        
        for webhook in self._webhooks:
            if not webhook["enabled"]:
                continue
            if event_type not in webhook["events"]:
                continue
            
            try:
                await self._call_webhook(webhook, event)
            except Exception as e:
                logger.error(f"Webhook failed: {webhook['url']} - {e}")
        
        for callback in self._callbacks.get(event_type, []):
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Callback failed: {e}")
    
    async def _call_webhook(self, webhook: Dict, event: WebhookEvent):
        """Call a webhook URL."""
        import httpx
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            data = event.model_dump()
            
            headers = {"Content-Type": "application/json"}
            if webhook.get("secret"):
                import hmac
                import hashlib
                import json
                
                signature = hmac.new(
                    webhook["secret"].encode(),
                    json.dumps(data).encode(),
                    hashlib.sha256,
                ).hexdigest()
                headers["X-Webhook-Signature"] = signature
            
            await client.post(webhook["url"], json=data, headers=headers)
    
    def disable_webhook(self, url: str):
        """Disable a webhook by URL."""
        for webhook in self._webhooks:
            if webhook["url"] == url:
                webhook["enabled"] = False
                logger.info(f"Disabled webhook: {url}")
    
    def list_webhooks(self) -> List[Dict]:
        """List all registered webhooks."""
        return [{"url": w["url"], "enabled": w["enabled"]} for w in self._webhooks]


_hooks: Optional[SystemHooks] = None


def get_system_hooks() -> SystemHooks:
    global _hooks
    if _hooks is None:
        _hooks = SystemHooks()
    return _hooks