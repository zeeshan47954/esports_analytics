from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from api.dependencies import get_db, get_redis
from api.schemas.players import LeaderboardEntry
import redis

router = APIRouter(
    prefix="/leaderboard",
    tags=["leaderboard"]
)

@router.get("/global", response_model=List[LeaderboardEntry])
def get_global_leaderboard(
    limit: int = Query(100, ge=1, le=500),
    r: redis.Redis = Depends(get_redis),
    db: Session = Depends(get_db)
):
    try:
        # Try Redis first
        entries = r.zrevrange("leaderboard:global", 0, limit-1, withscores=True)
        if entries:
            result = []
            for rank, (player_id, elo) in enumerate(entries, start=1):
                meta = r.hgetall(f"player:meta:{player_id}")
                result.append({
                    "rank": rank,
                    "player_id": player_id,
                    "username": meta.get("username", "unknown"),
                    "elo_rating": int(elo),
                    "country": meta.get("country")
                })
            return result
    except:
        pass  # Redis failed, fallback to DB

    # Fallback to Database
    result = db.execute(
        text("""
            SELECT 
                id::text as player_id,
                username,
                country,
                elo_rating,
                RANK() OVER (ORDER BY elo_rating DESC) as rank
            FROM players
            
            ORDER BY elo_rating DESC 
            LIMIT :limit
        """),
        {"limit": limit}
    ).mappings().all()
    
    return [dict(row) for row in result]