"""
Status page monitor: poll configured targets, detect new events, print to console.
"""
import asyncio
from typing import Any
import aiohttp
from config import load_config
from pipeline.detector import ChangeDetector
from pipeline.formatter import format_event
from providers.atlassian import AtlassianAdapter
from providers.base import BaseAdapter


def get_adapter(provider: str) -> BaseAdapter:
    """Return the adapter for the given provider (only atlassian supported for now)."""
    if provider == "atlassian":
        return AtlassianAdapter()
    raise ValueError(f"Unknown provider: {provider}")


async def run_once(
    session: aiohttp.ClientSession,
    target: dict[str, Any],
    adapter: BaseAdapter,
    detector: ChangeDetector,
) -> None:
    """Scrape one target, filter to new events, print formatted."""
    events = await adapter.fetch_events(session, target)
    new = detector.filter_new(events)
    for e in new:
        print(format_event(e))


async def main() -> None:
    cfg = load_config()
    targets = cfg["targets"]
    interval = cfg.get("scrape_interval", 30)
    detector = ChangeDetector()
    adapters = [(t, get_adapter(t["provider"])) for t in targets]

    async with aiohttp.ClientSession() as session:
        for _ in range(2):
            await asyncio.gather(
                *[run_once(session, target, adapter, detector) for target, adapter in adapters]
            )
            await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
