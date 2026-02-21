"""Data source protocols."""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class DataSource(abc.ABC):
    """Base protocol for external data sources."""

    @abc.abstractmethod
    async def fetch(self, **kwargs: Any) -> Dict[str, Any]:
        """Fetch data from source."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Source name."""
