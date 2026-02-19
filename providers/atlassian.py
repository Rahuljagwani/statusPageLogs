"""
Atlassian Statuspage adapter: fetches summary.json and normalizes to UnifiedEvent.
"""

from datetime import datetime
from typing import Any

import aiohttp
from pydantic import BaseModel
from providers.base import BaseAdapter
from models import UnifiedEvent


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

    async def fetch_summary(
        self,
        session: aiohttp.ClientSession,
        target: dict[str, Any],
    ) -> StatusPageSummary:
        """GET summary.json and return parsed model."""
        base_url = target["url"].rstrip("/")
        url = f"{base_url}/api/v2/summary.json"
        async with session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return StatusPageSummary(
            page=PageInfo(**data["page"]),
            components=[Component(**c) for c in data.get("components", [])],
            incidents=[Incident(**i) for i in data.get("incidents", [])],
        )

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

    asyncio.run(main())
