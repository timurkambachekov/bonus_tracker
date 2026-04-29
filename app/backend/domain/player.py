from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.backend.domain.team import Team


@dataclass
class Player:
    id: int
    name: str
    transfermarkt_player_id: Optional[int] = None
    position: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[str] = None
    height_m: Optional[float] = None
    foot: Optional[str] = None
    market_value_eur: Optional[float] = None
    team: Optional[Team] = None
