"""
Format UnifiedEvent as console output.
"""
from __future__ import annotations

from models import UnifiedEvent


def format_event(event: UnifiedEvent) -> str:
    """Turn one event into the required console lines: [timestamp] Product: ... / Status: ..."""
    ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return f"[{ts}] Product: {event.product_name}\nStatus: {event.message}"
