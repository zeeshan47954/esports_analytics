from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from api.schemas.players import PlayerCreate, PlayerResponse
from api.dependencies import get_db

router = APIRouter(
    prefix="/players",
    tags=["players"]
)

@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(player_id: UUID, db: Session = Depends(get_db)):
    try:
        result = db.execute(
            text("""
                SELECT 
                    id,
                    username,
                    country,
                    date_of_birth,
                    elo_rating,
                    created_at
                FROM players 
                WHERE id = :id
            """),
            {"id": player_id}
        )
        player = result.mappings().first()
        
        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
        
        player_dict = dict(player)
        player_dict["id"] = str(player_dict["id"])
        
        # Convert datetime to string
        if player_dict.get("created_at"):
            player_dict["created_at"] = player_dict["created_at"].isoformat()
        
        return player_dict
        
    except Exception as e:
        print(f"❌ GET Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
@router.post("/", response_model=PlayerResponse, status_code=201)
def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    try:
        result = db.execute(
            text("""
                INSERT INTO players 
                    (username, country, date_of_birth, elo_rating)
                VALUES 
                    (:username, :country, :date_of_birth, 1200)
                RETURNING id, username, country, date_of_birth, 
                          elo_rating, created_at
            """),
            {
                "username": player.username,
                "country": player.country,
                "date_of_birth": player.date_of_birth,
            }
        )
        db.commit()
        new_player = result.mappings().first()
        
        player_dict = dict(new_player)
        player_dict["id"] = str(player_dict["id"])
        if player_dict.get("created_at"):
            player_dict["created_at"] = player_dict["created_at"].isoformat()
        
        return player_dict
    except Exception as e:
        print(f"❌ CREATE Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))