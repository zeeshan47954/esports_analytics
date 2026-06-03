from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class PlayerBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    country: str = Field(..., min_length=2, max_length=60)
    date_of_birth: date

class PlayerCreate(PlayerBase):
    """Used for creating new player"""

class PlayerResponse(PlayerBase):
    """Used for returning player data"""
    id: str
    elo_rating: int
    created_at: Optional[str] = None

class LeaderboardEntry(BaseModel):
    """Used for leaderboard responses"""
    rank: int
    player_id: str
    username: str
    elo_rating: int
    country: Optional[str] = None