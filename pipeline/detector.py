"""
In-memory change detector: tracks seen event_ids per source, returns only new events.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
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


if __name__ == "__main__":
    from datetime import datetime
    from models import UnifiedEvent

    detector = ChangeDetector()
    base = [
        UnifiedEvent(
            source_id="OpenAI",
            product_name="API",
            status="investigating",
            message="We are looking into it.",
            timestamp=datetime.now(),
            event_id="evt-1"),
    ]
    first_new = detector.filter_new(base)
    second_new = detector.filter_new(base)
    print("First scrape new events:", len(first_new))
    print("Second scrape new events:", len(second_new))
