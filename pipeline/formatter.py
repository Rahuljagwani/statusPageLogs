"""
Format UnifiedEvent as console output.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import UnifiedEvent


def format_event(event: UnifiedEvent) -> str:
    """Turn one event into the required console lines: [timestamp] Product: ... / Status: ..."""
    ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return f"[{ts}] Product: {event.product_name}\nStatus: {event.message}"


if __name__ == "__main__":
    from datetime import datetime

    from models import UnifiedEvent

    e = UnifiedEvent(
        source_id="OpenAI",
        product_name="OpenAI API - Chat Completions",
        status="degraded_performance",
        message="Degraded performance due to upstream issue",
        timestamp=datetime.now(),
        event_id="demo-1",
    )
    print(format_event(e))
