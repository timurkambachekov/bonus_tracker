from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.competition import Competition


@dataclass
class Team:
    id: int
    name: str
    slug: Optional[str] = None
    transfermarkt_club_id: Optional[int] = None
    competition: Optional[Competition] = None
