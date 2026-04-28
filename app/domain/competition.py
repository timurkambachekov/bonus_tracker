from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Competition:
    id: int
    name: str
    code: Optional[str] = None
    country: Optional[str] = None
    season: Optional[int] = None
