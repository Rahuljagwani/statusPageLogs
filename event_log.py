"""
Append-only event log (JSONL). Trims to last 24h when file exceeds 100KB.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from models import UnifiedEvent

LOG_PATH = os.environ.get("EVENTS_LOG_PATH", "data/events.jsonl")
MAX_FILE_BYTES = 100 * 1024  # 100KB
KEEP_LAST_N_WHEN_EMPTY = 100


def _ensure_dir() -> None:
    d = os.path.dirname(LOG_PATH)
    if d:
        os.makedirs(d, exist_ok=True)


def _event_to_line(e: UnifiedEvent) -> str:
    d = e.model_dump(mode="json")
    return json.dumps(d) + "\n"


def _parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _parse_ts(d: dict) -> datetime | None:
    raw = d.get("timestamp")
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def append_events(events: list[UnifiedEvent]) -> None:
    """Append events to the log file. If file size > 100KB, rewrite keeping only last 24h of events."""
    if not events:
        return
    _ensure_dir()
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        for e in events:
            f.write(_event_to_line(e))
    if os.path.getsize(LOG_PATH) <= MAX_FILE_BYTES:
        return
    # Trim: keep only events from last 24h (or last KEEP_LAST_N_WHEN_EMPTY if none in 24h)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    kept: list[str] = []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                d = _parse_line(line)
                if not d:
                    continue
                ts = _parse_ts(d)
                if ts and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts and ts >= cutoff:
                    kept.append(line.rstrip())
    except FileNotFoundError:
        return
    if not kept:
        # Keep last N lines so we don't lose everything
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            all_lines = [ln.rstrip() for ln in f if ln.strip()]
        kept = all_lines[-KEEP_LAST_N_WHEN_EMPTY:]
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")


def read_last_events(limit: int = 200) -> list[dict]:
    """Read log file and return the last `limit` events as list of dicts (newest first)."""
    if not os.path.exists(LOG_PATH):
        return []
    lines: list[str] = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                lines.append(line)
    out: list[dict] = []
    for line in reversed(lines[-limit:]):
        d = _parse_line(line)
        if d:
            out.append(d)
    return out
