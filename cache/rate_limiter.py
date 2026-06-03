import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import redis
import time
import json
import uuid
from functools import wraps

load_dotenv()

# ====================== CONNECTIONS ======================
url = os.getenv("fullpath")
engine = create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)
Session = sessionmaker(bind=engine)

r = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True,
    password='secret123'
)

# ====================== SAFE JSON HELPER ======================
def safe_to_json(df: pd.DataFrame) -> str:
    df = df.copy()
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).apply(
            lambda x: x.encode('utf-8', errors='replace').decode('utf-8')
        )
    try:
        return df.to_json(orient='records', date_format='iso')
    except Exception:
        df = df.astype(str)
        return df.to_json(orient='records', date_format='iso')


# ====================== CACHE FUNCTIONS ======================
def cache_all_players():
    redis_key = "cache:players:all"
    
    if r.exists(redis_key):
        print(f"✅ Players already cached")
        return True
    
    print("⚡ Loading all players from database...")
    session = Session()
    try:
        result = session.execute(text("SELECT * FROM players"))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        json_data = safe_to_json(df)
        r.setex(redis_key, 3600, json_data)
        
        print(f"✅ Cached {len(df)} players | Size: {len(json_data)/1024/1024:.2f} MB")
        return True
    finally:
        session.close()


def get_cached_players():
    redis_key = "cache:players:all"
    cached_json = r.get(redis_key)
    
    if cached_json:
        return pd.DataFrame.from_records(json.loads(cached_json))
    else:
        print("❌ Cache miss. Loading from DB...")
        cache_all_players()
        return get_cached_players()  # retry


# ====================== RATE LIMIT DECORATOR ======================
def rate_limiter(max_calls: int = 100, seconds: int = 60):
    def decorator(func):
        @wraps(func)
        def wrapper(player_id: str):
            # Use hash key per user
            hash_key = f"rate:{player_id}"
            
            # Get current counter
            current = r.hget(hash_key, "counter")
            
            if current is None:
                # First request → initialize
                r.hset(hash_key, mapping={"counter": 1})
                r.expire(hash_key, seconds)
                return func(player_id)
            
            current = int(current)
            
            if current >= max_calls:
                return f"sorry u have reached your limit for {seconds} seconds"
            
            # Increment counter
            r.hincrby(hash_key, "counter", 1)
            return func(player_id)
        
        return wrapper
    return decorator


# ====================== QUERY FUNCTION ======================
@rate_limiter(max_calls=100, seconds=60)
def get_player_by_id(player_id: str):
    """Return single player row if under rate limit"""
    df = get_cached_players()
    
    if df is None or df.empty:
        return "Error: No player data available"
    
    # Filter by id (UUID)
    result = df[df['id'].astype(str) == str(player_id)]
    
    if result.empty:
        return f"Player with id {player_id} not found"
    
    return result.iloc[0].to_dict()   # Return as dictionary (clean)


# ====================== MAIN ======================
if __name__ == "__main__":
    print("="*60)
    cache_all_players()   # Ensure cache is loaded
    
    test_id = '8f4d633d-51ba-45f3-b639-e883b3253e60'
    
    for i in range(105):   # Test rate limit
        result = get_player_by_id(test_id)
        print(f"Request {i+1}: {result if isinstance(result, dict) else result}")
        time.sleep(0.05)   # Small delay for demo

