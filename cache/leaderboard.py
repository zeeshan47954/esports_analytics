import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import redis
import time
import json
import uuid

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


# ====================== CACHE PLAYERS TABLE ======================
def cache_all_players():
    redis_key = "cache:players:all"
    
    start_time = time.time()
    
    if r.exists(redis_key):
        print(f"✅ Players already cached in Redis (key: {redis_key})")
        return True
    
    print("⚡ Loading all players from database...")
    
    session = Session()
    try:
        query = "SELECT * FROM players"
        result = session.execute(text(query))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        row_count = len(df)
        print(f"✅ Fetched {row_count:,} players from database")
        
        json_data = safe_to_json(df)
        r.setex(redis_key, 3600, json_data)
        
        elapsed = time.time() - start_time
        memory_mb = len(json_data) / (1024 * 1024)
        
        print(f"✅ Successfully cached {row_count:,} players")
        print(f"   ⏱️ Time : {elapsed:.2f}s | 💾 Size : {memory_mb:.2f} MB")
        return True
        
    except Exception as e:
        print(f"❌ Error caching players: {e}")
        return False
    finally:
        session.close()


# ====================== LOAD FROM CACHE ======================
def get_cached_players():
    redis_key = "cache:players:all"
    start = time.time()
    
    cached_json = r.get(redis_key)
    if cached_json:
        df = pd.DataFrame.from_records(json.loads(cached_json))
        print(f"✅ Loaded from Redis cache → {len(df):,} players | {time.time()-start:.3f}s")
        return df
    else:
        print("❌ Cache miss. Loading from database...")
        cache_all_players()
        return get_cached_players()


# ====================== UPDATE ELO ======================
def update_player_elo(player_id: str, new_elo: int):
    """Fixed for column name 'id'"""
    redis_key = "cache:players:all"
    
    try:
        player_uuid = uuid.UUID(player_id) if isinstance(player_id, str) else player_id
    except ValueError:
        print(f"❌ Invalid UUID: {player_id}")
        return False
    
    session = Session()
    try:
        # FIXED: Use 'id' instead of 'player_id'
        update_query = """
            UPDATE players 
            SET elo_rating = :new_elo 
            WHERE id = :player_id
        """
        session.execute(text(update_query), {"new_elo": new_elo, "player_id": player_uuid})
        session.commit()
        
        print(f"✅ Database updated → id={player_id} | elo={new_elo}")
        
        # Update Redis Cache
        cached_json = r.get(redis_key)
        if not cached_json:
            cache_all_players()
            return True
        
        df = pd.DataFrame.from_records(json.loads(cached_json))
        
        # Safe update in cache
        df['id_str'] = df['id'].astype(str)
        mask = df['id_str'] == str(player_uuid)
        
        if mask.any():
            df.loc[mask, 'elo_rating'] = new_elo
            print(f"✅ Cache updated for player {player_id}")
        else:
            print(f"⚠️ Player {player_id} not found in cache")
        
        r.setex(redis_key, 3600, safe_to_json(df))
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error updating elo: {e}")
        return False
    finally:
        session.close()


# ====================== GET TOP PLAYERS ======================
def get_top_players(n: int = 10):
    redis_key = "cache:players:all"
    
    cached_json = r.get(redis_key)
    if not cached_json:
        print("⚠️ Cache empty. Refreshing...")
        cache_all_players()
        cached_json = r.get(redis_key)
    
    if not cached_json:
        print("❌ Failed to load cache")
        return None
    
    df = pd.DataFrame.from_records(json.loads(cached_json))
    
    if 'elo_rating' not in df.columns:
        print("❌ Column 'elo_rating' not found")
        return None
    
    # FIXED: Use correct column names
    result = df.sort_values(by='elo_rating', ascending=False).head(n)
    
    print(f"\n🏆 Top {n} Players by Elo:")
    print(result[['id', 'username', 'elo_rating', 'country']].to_string(index=False))
    
    return result


# ====================== MAIN ======================
if __name__ == "__main__":
    print("="*70)
    print("Caching All Players into Redis")
    print("="*70)
    
    success = cache_all_players()
    
    if success:
        df = get_cached_players()
        if df is not None:
            print(f"\nFirst 5 rows:")
            print(df.head())
    
    # Test update
    update_player_elo('8f4d633d-51ba-45f3-b639-e883b3253e60', 1200)
    
    # Get Top 10
    get_top_players(10)

"""
output
======================================================================
Caching All Players into Redis
======================================================================
✅ Players already cached in Redis (key: cache:players:all)
✅ Loaded from Redis cache → 501 players | 0.007s

First 5 rows:
                                     id username  country date_of_birth  elo_rating                created_at
0  8f4d633d-51ba-45f3-b639-e883b3253e60  player1    India    2005-03-26        1180  2023-08-13T00:43:17.775Z
1  6addbf22-fe3e-471a-9194-4e63954bbecd  player2   Poland    2001-04-05        1181  2025-11-13T08:16:09.020Z
2  3c0e24e2-da64-4b58-af31-469a6acc0fc0  player3  Germany    2007-09-15        1182  2024-02-24T06:18:07.474Z
3  fc4019b9-a667-4db7-9e3f-8e2add54cd67  player4   Poland    2000-08-22        1180  2026-01-13T12:05:16.412Z
4  aa1cce81-5bc5-4b4c-a728-62781e9ed0e2  player5    China    1996-01-26        1183  2025-05-01T13:50:46.393Z
✅ Database updated → id=8f4d633d-51ba-45f3-b639-e883b3253e60 | elo=1200
✅ Cache updated for player 8f4d633d-51ba-45f3-b639-e883b3253e60

🏆 Top 10 Players by Elo:
                                  id  username  elo_rating     country
cd509ca0-a218-4614-8ee9-c5f73d0b9281 player473        1651       Japan
7cfa9b8f-1265-4b9d-a322-d4eb9de8033d player486        1650       India
704f4807-fe05-4b0e-9abe-9806a5e0195a player484        1644      Poland
60f850a1-64b7-4928-a82f-b38b4544c21f player477        1624      Poland
4d89007b-bc9a-4a40-820e-c46e21a5c7e7 player493        1617 South Korea
cfa19f60-e886-4c42-a963-72afa1cd28fa player489        1615     Vietnam
dfd3d949-1ff5-423a-b121-6e46c174fd87 player483        1589     Vietnam
8f657e4f-f0c4-4979-a91c-2340d5abf333 player435        1588      France
5b9e6619-5cd8-4511-8c53-ef07543f7ec8 player490        1585          UK
746e5125-eba0-46a6-8169-d016e514c60d player459        1574       China

"""