"""
Atlassian Statuspage adapter: fetches summary.json and normalizes to UnifiedEvent.
"""

import json
from datetime import datetime
from typing import Any

import aiohttp
from pydantic import BaseModel

from models import UnifiedEvent
from providers.base import BaseAdapter


class PageInfo(BaseModel):
    id: str
    name: str
    url: str
    updated_at: str | None = None

class IncidentUpdate(BaseModel):
    id: str
    body: str
    status: str
    created_at: str
    updated_at: str | None = None

class Incident(BaseModel):
    id: str
    name: str
    impact: str
    status: str
    incident_updates: list[IncidentUpdate] = []
    created_at: str | None = None
    updated_at: str | None = None

class Component(BaseModel):
    id: str
    name: str
    status: str


class StatusPageSummary(BaseModel):
    """Parsed response from /api/v2/summary.json."""
    page: PageInfo
    components: list[Component] = []
    incidents: list[Incident] = []


class AtlassianAdapter(BaseAdapter):
    """Fetch and normalize Atlassian Statuspage summary.json."""

    def __init__(self) -> None:
        # url -> (summary, last_modified) for conditional GET
        self._cache: dict[str, tuple[StatusPageSummary, str]] = {}

    async def fetch_summary(
        self,
        session: aiohttp.ClientSession,
        target: dict[str, Any],
    ) -> StatusPageSummary:
        """GET summary.json; use If-Modified-Since and return cached summary on 304."""
        base_url = target["url"].rstrip("/")
        url = f"{base_url}/api/v2/summary.json"
        headers: dict[str, str] = {}
        if url in self._cache:
            _, last_modified = self._cache[url]
            headers["If-Modified-Since"] = last_modified
        async with session.get(url, headers=headers or None) as resp:
            if resp.status == 304:
                return self._cache[url][0]
            resp.raise_for_status()
            last_modified = resp.headers.get("Last-Modified") or ""
            data = await resp.json()
        summary = StatusPageSummary(
            page=PageInfo(**data["page"]),
            components=[Component(**c) for c in data.get("components", [])],
            incidents=[Incident(**i) for i in data.get("incidents", [])],
        )
        self._cache[url] = (summary, last_modified)
        return summary

    def _normalize_to_events(self, summary: StatusPageSummary, source_id: str) -> list[UnifiedEvent]:
        """Turn summary incidents and their updates into UnifiedEvents (one per update)."""
        events: list[UnifiedEvent] = []
        for incident in summary.incidents:
            for update in incident.incident_updates:
                ts = update.created_at.replace("Z", "+00:00")
                timestamp = datetime.fromisoformat(ts)
                events.append(
                    UnifiedEvent(
                        source_id=source_id,
                        product_name=incident.name,
                        status=update.status,
                        message=update.body,
                        timestamp=timestamp,
                        event_id=f"{incident.id}_{update.id}",
                    )
                )
        return events

    async def fetch_events(
        self,
        session: aiohttp.ClientSession,
        target: dict[str, Any],
    ) -> list[UnifiedEvent]:
        """Fetch summary and return normalized unified events."""
        summary = await self.fetch_summary(session, target)
        source_id = target.get("name", summary.page.name)
        return self._normalize_to_events(summary, source_id)

    def parse_webhook(
        self,
        body: bytes | str,
        headers: dict[str, str],
    ) -> list[UnifiedEvent]:
        """Parse Statuspage webhook POST (incident or component_update) into unified events."""
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return []
        events: list[UnifiedEvent] = []
        page = data.get("page") or {}
        source_id = page.get("id", "atlassian")
        if "incident" in data:
            inc = data["incident"]
            name = inc.get("name", "Incident")
            inc_id = inc.get("id", "")
            for upd in inc.get("incident_updates", []):
                ts = (upd.get("created_at") or "").replace("Z", "+00:00")
                try:
                    timestamp = datetime.fromisoformat(ts) if ts else datetime.now()
                except ValueError:
                    timestamp = datetime.now()
                events.append(
                    UnifiedEvent(
                        source_id=source_id,
                        product_name=name,
                        status=upd.get("status", ""),
                        message=upd.get("body", ""),
                        timestamp=timestamp,
                        event_id=f"{inc_id}_{upd.get('id', '')}",
                    )
                )
        if "component_update" in data and "component" in data:
            comp = data["component"]
            upd = data["component_update"]
            ts = (upd.get("created_at") or "").replace("Z", "+00:00")
            try:
                timestamp = datetime.fromisoformat(ts) if ts else datetime.now()
            except ValueError:
                timestamp = datetime.now()
            events.append(
                UnifiedEvent(
                    source_id=source_id,
                    product_name=comp.get("name", "Component"),
                    status=upd.get("new_status", ""),
                    message=f"Status: {upd.get('old_status', '')} -> {upd.get('new_status', '')}",
                    timestamp=timestamp,
                    event_id=f"comp_{comp.get('id', '')}_{upd.get('id', '')}",
                )
            )
        return events


if __name__ == "__main__":
    import asyncio
    import sys

    sys.path.insert(0, ".")
    from config import load_config

    async def main() -> None:
        cfg = load_config()
        target = next(t for t in cfg["targets"] if t["provider"] == "atlassian")
        async with aiohttp.ClientSession() as session:
            adapter = AtlassianAdapter()
            events = await adapter.fetch_events(session, target)
        for e in events:
            print(e.model_dump_json())

    def main_webhook_sample() -> None:
        """Run parse_webhook with a sample incident payload and print unified events."""
        sample = """
        {"page":{"id":"test-page","status_indicator":"major","status_description":"Partial Outage"},
         "incident":{"id":"inc-1","name":"API Degradation","status":"monitoring",
         "incident_updates":[{"id":"upd-1","body":"We are monitoring.","status":"monitoring",
         "created_at":"2025-11-03T14:32:00Z"}]}}
        """
        adapter = AtlassianAdapter()
        events = adapter.parse_webhook(sample.strip(), {})
        for e in events:
            print(e.model_dump_json())

    if len(sys.argv) > 1 and sys.argv[1] == "webhook":
        main_webhook_sample()
    else:
        asyncio.run(main())
