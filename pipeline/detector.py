"""
In-memory change detector: tracks seen event_ids per source, returns only new events.
"""
from models import UnifiedEvent


class ChangeDetector:
    """Tracks seen event_ids per source_id; filter_new() returns only events not seen before."""

    def __init__(self) -> None:
        self._seen: dict[str, set[str]] = {}

    def filter_new(self, events: list[UnifiedEvent]) -> list[UnifiedEvent]:
        """Return only events whose event_id has not been seen for their source_id. Mark them seen."""
        new: list[UnifiedEvent] = []
        for e in events:
            source_seen = self._seen.setdefault(e.source_id, set())
            if e.event_id not in source_seen:
                source_seen.add(e.event_id)
                new.append(e)
        return new
