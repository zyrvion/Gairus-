from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Optional


class RuntimeMemory:
    """
    Mémoire opérationnelle légère de Gaïrus.

    Cette mémoire sert au contexte courant :
    - conversations ;
    - tâches ;
    - décisions ;
    - résultats ;
    - événements récents.

    Elle ne remplace pas la mémoire persistante de Gaïrus.
    """

    def __init__(
        self,
        max_items: int = 200,
    ):
        self.max_items = max(1, int(max_items))

        self._events = deque(
            maxlen=self.max_items,
        )

        self._values: Dict[str, Any] = {}

        self.created_at = time.time()
        self.updated_at = self.created_at

    def _touch(self):
        self.updated_at = time.time()

    def set(
        self,
        key: str,
        value: Any,
    ) -> Any:
        if not key:
            raise ValueError("Memory key cannot be empty")

        self._values[key] = value

        self._touch()

        return value

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        return self._values.get(
            key,
            default,
        )

    def has(
        self,
        key: str,
    ) -> bool:
        return key in self._values

    def delete(
        self,
        key: str,
    ) -> Any:
        value = self._values.pop(
            key,
            None,
        )

        self._touch()

        return value

    def remember(
        self,
        event_type: str,
        content: Any,
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not event_type:
            raise ValueError(
                "event_type is required"
            )

        event = {
            "timestamp": time.time(),
            "type": event_type,
            "content": content,
            "actor_id": actor_id,
            "metadata": metadata or {},
        }

        self._events.append(event)

        self._touch()

        return dict(event)

    def add_message(
        self,
        role: str,
        content: str,
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.remember(
            event_type="message",
            content={
                "role": role,
                "content": content,
            },
            actor_id=actor_id,
            metadata=metadata,
        )

    def add_task(
        self,
        task: Any,
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.remember(
            event_type="task",
            content=task,
            actor_id=actor_id,
            metadata=metadata,
        )

    def add_decision(
        self,
        decision: Any,
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.remember(
            event_type="decision",
            content=decision,
            actor_id=actor_id,
            metadata=metadata,
        )

    def add_result(
        self,
        result: Any,
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.remember(
            event_type="result",
            content=result,
            actor_id=actor_id,
            metadata=metadata,
        )

    def recent(
        self,
        limit: int = 20,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        limit = max(0, int(limit))

        events = list(self._events)

        if event_type is not None:
            events = [
                event
                for event in events
                if event.get("type") == event_type
            ]

        if limit == 0:
            return []

        return [
            dict(event)
            for event in events[-limit:]
        ]

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        if not query:
            return []

        needle = query.lower()

        matches = []

        for event in reversed(self._events):
            text = str(
                event.get("content", "")
            ).lower()

            if needle in text:
                matches.append(
                    dict(event)
                )

            if len(matches) >= limit:
                break

        return matches

    def context(
        self,
        limit: int = 20,
    ) -> Dict[str, Any]:
        return {
            "values": dict(self._values),
            "recent_events": self.recent(
                limit=limit,
            ),
        }

    def snapshot(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "value_count": len(self._values),
            "event_count": len(self._events),
            "values": dict(self._values),
            "events": self.recent(
                limit=self.max_items,
            ),
        }

    def clear_events(self):
        self._events.clear()

        self._touch()

    def clear_values(self):
        self._values.clear()

        self._touch()

    def clear(self):
        self.clear_events()
        self.clear_values()

    def count_events(
        self,
        event_type: Optional[str] = None,
    ) -> int:
        if event_type is None:
            return len(self._events)

        return sum(
            1
            for event in self._events
            if event.get("type") == event_type
        )

    def export(self) -> Dict[str, Any]:
        return self.snapshot()

    def import_snapshot(
        self,
        snapshot: Dict[str, Any],
    ):
        if not isinstance(snapshot, dict):
            raise TypeError(
                "snapshot must be a dictionary"
            )

        values = snapshot.get(
            "values",
            {},
        )

        events = snapshot.get(
            "events",
            [],
        )

        if isinstance(values, dict):
            self._values.update(values)

        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    self._events.append(
                        dict(event)
                    )

        self._touch()

        return self.snapshot()

    def status(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "events": len(self._events),
            "values": len(self._values),
            "max_items": self.max_items,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __len__(self):
        return len(self._events)

    def __contains__(self, key: str):
        return self.has(key)
