from fastapi import FastAPI, Depends,BackgroundTasks
from api.routers.players import router as players_router
from api.routers.leaderboard import router as leaderboards_router
from api.dependencies import get_db,get_redis
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
import asyncio

app = FastAPI(
    title="Esports Intelligence API",
    description="Learning FastAPI for Database Engineers",
    version="0.4"
)

@app.get("/", tags=["health"])
def root():
    return {
        "service": "Esports Intelligence API",
        "status": "running",
        "version": "0.4",
        "docs": "/docs"
    }

# Database Health Check
@app.get("/health/db", tags=["health"])
def db_health(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1"))
        return {"database": "healthy", "message": "PostgreSQL is connected"}
    except Exception as e:
        return {"database": "unhealthy", "error": str(e)}
@app.get("/health/redis", tags=["health"])
def db_health(r: redis.Redis = Depends(get_redis)):
    try:
        if r.ping():
        
         return {"redis": "listening"}
    except Exception as e:
        return {"redis": "not listening", "error": str(e)}    

async def refresh_leaderboard(r: redis.Redis, db: Session):
    try:
        result = db.execute(
            text("""
                SELECT id::text as player_id, username, elo_rating, country
                FROM players 
                ORDER BY elo_rating DESC
                LIMIT 500
            """)
        ).mappings().all()
        
        # Clear old leaderboard
        r.delete("leaderboard:global")
        
        pipeline = r.pipeline()
        for player in result:
            pipeline.zadd("leaderboard:global", {player["player_id"]: player["elo_rating"]})
            pipeline.hset(f"player:meta:{player['player_id']}", mapping={
                "username": player["username"],
                "country": player.get("country", "")
            })
        pipeline.execute()
        
        print("✅ Leaderboard cache refreshed")
    except Exception as e:
        print(f"❌ Leaderboard refresh failed: {e}")

# Add this endpoint
@app.post("/admin/refresh-leaderboard")
async def trigger_refresh(background_tasks: BackgroundTasks, db: Session = Depends(get_db), r: redis.Redis = Depends(get_redis)):
    background_tasks.add_task(refresh_leaderboard, r, db)
    return {"message": "Leaderboard refresh started in background"}

app.include_router(players_router)
app.include_router(leaderboards_router)