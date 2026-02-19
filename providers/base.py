"""
Abstract interface for status-page providers.
Each provider implements fetch_events (pull) and optionally parse_webhook (push).
"""

from abc import ABC, abstractmethod
from typing import Any
import aiohttp
from models import UnifiedEvent


class BaseAdapter(ABC):
    """
    Base class for all providers.
    """

    @abstractmethod
    async def fetch_events(
        self,
        session: "aiohttp.ClientSession",
        target: dict[str, Any],
    ) -> list[UnifiedEvent]:
        """
        Fetch current state from the provider's API and return normalized events.
        target: config dict with at least 'name' and 'url'.
        """
        pass

    def parse_webhook(
        self,
        body: bytes | str,
        headers: dict[str, str],
    ) -> list[UnifiedEvent]:
        """
        Parse a webhook POST body and headers into unified events.
        Optional: override in provider if webhooks are supported.
        """
        return []
