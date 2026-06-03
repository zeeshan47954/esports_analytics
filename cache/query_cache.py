import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import time
import json
import redis

load_dotenv()

# ====================== CONNECTIONS ======================
r = redis.Redis(host='localhost', port=6379, decode_responses=True, password="secret123")
url = os.getenv("fullpath")
engine = create_engine(url, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

# ====================== QUERY DEFINITIONS (Defined ONLY ONCE) ======================
QUERIES = {
    "KDA_Ranking": """
        SELECT player_id, (kills + assists)::numeric / NULLIF(deaths, 0) AS kda
        FROM player_stats
        ORDER BY kda DESC NULLS LAST LIMIT 10
    """,

    "Winrate_Per_Tournament": """
        SELECT tournament_id, team_a_id,
               ROUND(COUNT(*) FILTER (WHERE team_a_id = winner_id)::numeric
                     / NULLIF(COUNT(*),0)::numeric * 100, 2) AS winrate
        FROM matches
        GROUP BY tournament_id, team_a_id
        ORDER BY tournament_id, team_a_id LIMIT 10
    """,

    "Avg_Damage_Per_Match": """
        SELECT match_id, player_id,
               AVG(damage_dealt) OVER (PARTITION BY match_id ORDER BY player_id) AS avg_dmg
        FROM player_stats
        ORDER BY match_id, player_id LIMIT 10
    """,

    "Elo_Gainers_Last_30d": """
        WITH cte AS (
            SELECT player_id, elo_after - elo_before AS diff
            FROM elo_history
            WHERE changed_at >= NOW() - INTERVAL '30 days'
        )
        SELECT player_id, diff, DENSE_RANK() OVER (ORDER BY diff DESC)
        FROM cte LIMIT 1
    """,

    "Tournaments_With_Many_Matches": """
        SELECT tournament_id, team_a_id
        FROM matches
        GROUP BY tournament_id, team_a_id
        HAVING COUNT(*) > 3
    """,

    "Top_Prize_Players": """
        SELECT player_id, SUM(amount) AS total
        FROM prize_payouts
        GROUP BY player_id LIMIT 10
    """,

    "Top_Elo_Players": """
        SELECT * FROM players
        ORDER BY elo_rating DESC LIMIT 10
    """,

    "Last_10_Matches_Per_Player": """
        WITH r AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY match_id DESC) AS rn
            FROM player_stats
        )
        SELECT * FROM r WHERE rn <= 10
        ORDER BY player_id, match_id LIMIT 10
    """
}

# ====================== HELPER FUNCTIONS ======================
def has_query_cache():
    try:
        for key in r.scan_iter(match="*slowquery:*", count=1000):
            print(f"Found cached query: {key}")
            return True
        return False
    except Exception as e:
        print(f"Redis error: {e}")
        return False


def safe_to_json(df: pd.DataFrame) -> str:
    """Safe JSON serialization that handles Unicode/encoding errors"""
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).apply(
            lambda x: x.encode('utf-8', errors='replace').decode('utf-8')
        )
    
    try:
        return df.to_json(orient='records', date_format='iso')
    except Exception:
        df = df.astype(str)
        return df.to_json(orient='records', date_format='iso')


def cache_query_result(query_name: str, ttl: int):
    """Cache a query using its name"""
    redis_key = f"slowquery:{query_name}"
    query_sql = QUERIES.get(query_name)
    
    if not query_sql:
        print(f"❌ Unknown query: {query_name}")
        return None

    try:
        cached = r.get(redis_key)
        if cached:
            print(f"✅ Loaded from cache → {query_name} ({len(json.loads(cached))} rows)")
            return pd.DataFrame(json.loads(cached))
       
        print(f"⚡ Executing & caching → {query_name}")
        session = Session()
        try:
            result = session.execute(text(query_sql))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
           
            json_data = safe_to_json(df)
            r.setex(redis_key, ttl, json_data)
           
            print(f"✅ Successfully cached {len(df)} rows → {query_name} | TTL: {ttl}s")
            return df
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Error caching {query_name}: {e}")
        return None


def get_cached_query(name: str):
    """Get query result from cache with fallback to database"""
    redis_key = f"slowquery:{name}"
    start_time = time.time()
   
    cached_json = r.get(redis_key)
   
    if cached_json:
        df = pd.DataFrame(json.loads(cached_json))
        elapsed = time.time() - start_time
        print(f"✅ Cache Hit → {name}")
        print(f"⏱️ Time taken: {elapsed:.4f} seconds")
        print(f"📊 Rows returned: {len(df)}")
        return df
    else:
        print(f"❌ Cache Miss → {name} | Running from database...")
        start_time = time.time()
        session = Session()
       
        try:
            query_sql = QUERIES.get(name)
            if not query_sql:
                print(f"❌ Unknown query name: {name}")
                return None
           
            result = session.execute(text(query_sql))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
           
            elapsed = time.time() - start_time
            json_data = safe_to_json(df)
            r.setex(redis_key, 3600, json_data)
           
            print(f"✅ Query executed and cached | {elapsed:.4f}s | {len(df)} rows")
            return df
        finally:
            session.close()


# ====================== MAIN EXECUTION ======================
print("🔍 Checking Redis for existing cached queries...\n")

if has_query_cache():
    print("✅ Queries are already cached. Skipping benchmark.\n")
else:
    print("❌ No cache found → Running benchmark...\n")
   
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT pg_stat_statements_reset();"))
       
        print("Running benchmark (100 iterations each)...\n")
       
        timings = {}
        with engine.connect() as conn:
            for name, sql in QUERIES.items():
                print(f"Running {name} × 50 ...")
                start = time.time()
                for _ in range(50):
                    conn.execute(text(sql))
                duration = time.time() - start
                timings[name] = duration
                print(f" → Done in {duration:.2f} seconds\n")
       
        print("✅ Benchmark completed!\n")
       
        # Show slowest queries
        print("🔥 TOP 5 SLOWEST QUERIES:")
        sorted_timings = sorted(timings.items(), key=lambda x: x[1], reverse=True)
        for name, secs in sorted_timings[:5]:
            print(f"   {name:35} → {secs:.2f} seconds")
       
        # Cache the slowest 3 + the demo query
        for name, _ in sorted_timings[:3]:
            cache_query_result(name, 3600)
       
        cache_query_result("Last_10_Matches_Per_Player", 3600)
       
    except Exception as e:
        print(f"❌ Critical error: {e}")

print("\n🎉 Process finished successfully!\n")


# ====================== USAGE ======================
if __name__ == "__main__":
    print("="*70)
    df = get_cached_query("Last_10_Matches_Per_Player")
    print("="*70)
   
    if df is not None:
        print("\nFirst 10 rows:")
        print(df.head(10))
    print("="*70)

    #####################output###################################
    """
     Checking Redis for existing cached queries...

❌ No cache found → Running benchmark...

Running benchmark (100 iterations each)...

Running KDA_Ranking × 50 ...
 → Done in 15.64 seconds

Running Winrate_Per_Tournament × 50 ...
 → Done in 14.48 seconds

Running Avg_Damage_Per_Match × 50 ...
 → Done in 16.00 seconds

Running Elo_Gainers_Last_30d × 50 ...
 → Done in 13.60 seconds

Running Tournaments_With_Many_Matches × 50 ...
 → Done in 15.21 seconds

Running Top_Prize_Players × 50 ...
 → Done in 13.57 seconds

Running Top_Elo_Players × 50 ...
 → Done in 13.61 seconds

Running Last_10_Matches_Per_Player × 50 ...
 → Done in 16.41 seconds

✅ Benchmark completed!

🔥 TOP 5 SLOWEST QUERIES:
   Last_10_Matches_Per_Player          → 16.41 seconds
   Avg_Damage_Per_Match                → 16.00 seconds
   KDA_Ranking                         → 15.64 seconds
   Tournaments_With_Many_Matches       → 15.21 seconds
   Winrate_Per_Tournament              → 14.48 seconds
⚡ Executing & caching → Last_10_Matches_Per_Player
✅ Successfully cached 10 rows → Last_10_Matches_Per_Player | TTL: 3600s
⚡ Executing & caching → Avg_Damage_Per_Match
✅ Successfully cached 10 rows → Avg_Damage_Per_Match | TTL: 3600s
⚡ Executing & caching → KDA_Ranking
✅ Successfully cached 10 rows → KDA_Ranking | TTL: 3600s
✅ Loaded from cache → Last_10_Matches_Per_Player (10 rows)

🎉 Process finished successfully!

======================================================================
✅ Cache Hit → Last_10_Matches_Per_Player
⏱️ Time taken: 0.0064 seconds
📊 Rows returned: 10
======================================================================

First 10 rows:
      id                              match_id                             player_id  kills  deaths  assists damage_dealt headshot_pct  rn
0  74949  f6c0c458-cc04-448c-8eb3-0244df5fe1e3  00609999-87c3-4e9d-89d1-0e8fb794632c      7      12        2      1766.81        50.59   1
1  75470  f6c0c458-cc04-448c-8eb3-0244df5fe1e3  00609999-87c3-4e9d-89d1-0e8fb794632c     12      20        3      4493.59        76.93   2
2  76743  f6c0c458-cc04-448c-8eb3-0244df5fe1e3  00609999-87c3-4e9d-89d1-0e8fb794632c      8      18       19      3228.99        62.52   3
3  75446  f6c0c458-cc04-448c-8eb3-0244df5fe1e3  00609999-87c3-4e9d-89d1-0e8fb794632c     26       7       13      2363.28        62.62   4
4  75324  f6c0c458-cc04-448c-8eb3-0244df5fe1e3  00609999-87c3-4e9d-89d1-0e8fb794632c     11      19       14       932.95        75.22   5
5  75228  f6c0c458-cc04-448c-8eb3-0244df5fe1e3  00609999-87c3-4e9d-89d1-0e8fb794632c      5      21       18      1628.36        69.06   6
6  74599  f6c0c458-cc04-448c-8eb3-0244df5fe1e3  00609999-87c3-4e9d-89d1-0e8fb794632c      6       2        0      4011.03        59.40   7
7  77464  f6c0c458-cc04-448c-8eb3-0244df5fe1e3  00609999-87c3-4e9d-89d1-0e8fb794632c      8      10        0      4186.38        70.42   8
8  72397  f6c0c458-cc04-448c-8eb3-0244df5fe1e3  00609999-87c3-4e9d-89d1-0e8fb794632c     31      17        9       296.37        46.50   9
9  74700  f6c0c458-cc04-448c-8eb3-0244df5fe1e3  00609999-87c3-4e9d-89d1-0e8fb794632c     26       8       13      3089.32        28.47  10
    
    """