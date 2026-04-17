"""
AOS Event Bus
Event publishing and subscription via Redis Streams.
Backbone for event-driven architecture.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.core.redis import redis_client


class EventBus:
    """Publish and consume events via Redis Streams."""

    STREAM_PREFIX = "aos:events:"

    @staticmethod
    async def publish(
        stream: str,
        event_type: str,
        payload: dict[str, Any],
        actor_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> str:
        """Publish an event to a Redis stream."""
        event_id = str(uuid4())
        event = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor_id": actor_id or "system",
            "org_id": org_id or "",
            "payload": json.dumps(payload),
        }
        stream_key = f"{EventBus.STREAM_PREFIX}{stream}"
        await redis_client.xadd(stream_key, event, maxlen=10000)
        return event_id

    @staticmethod
    async def consume(
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block: int = 5000,
    ) -> list[dict[str, Any]]:
        """Consume events from a Redis stream consumer group."""
        stream_key = f"{EventBus.STREAM_PREFIX}{stream}"

        # Create consumer group if not exists
        try:
            await redis_client.xgroup_create(stream_key, group, id="0", mkstream=True)
        except Exception:
            pass  # Group already exists

        messages = await redis_client.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream_key: ">"},
            count=count,
            block=block,
        )

        events = []
        for _stream_name, entries in messages:
            for entry_id, data in entries:
                event = dict(data)
                if "payload" in event:
                    event["payload"] = json.loads(event["payload"])
                event["_stream_id"] = entry_id
                events.append(event)
                # Acknowledge the message
                await redis_client.xack(stream_key, group, entry_id)

        return events

    @staticmethod
    async def publish_domain_event(
        domain: str,
        event_type: str,
        entity_id: str,
        entity_type: str,
        data: dict[str, Any],
        actor_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> str:
        """Publish a domain-specific business event."""
        payload = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "data": data,
        }
        return await EventBus.publish(
            stream=domain,
            event_type=event_type,
            payload=payload,
            actor_id=actor_id,
            org_id=org_id,
        )


# Convenience shortcuts
event_bus = EventBus()
