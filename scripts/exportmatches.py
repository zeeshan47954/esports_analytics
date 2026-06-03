#first we create connection
import pandas as pd
from datetime import datetime
import uuid
from sqlalchemy import create_engine,Column,ForeignKey,text,DateTime,Integer,String,Date,Numeric,Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base,sessionmaker
import os
from dotenv import load_dotenv
load_dotenv()

url = os.getenv("fullpath")
engine = create_engine(url)
Base=declarative_base()
class Team(Base):
    __tablename__ = "teams"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,                    # ← Fixed
        server_default=text("gen_random_uuid()")
    )
    name = Column(String(100), unique=True)
    region = Column(String(50))
    founded_at = Column(Date)
    prize_pool = Column(Numeric(15, 2))
    is_active = Column(Boolean, default=True)


class TeamRoster(Base):
    __tablename__ = "team_rosters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"))
    role = Column(String(40))
    joined_at = Column(Date)
    left_at = Column(Date)


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,                    # ← Fixed
        server_default=text("gen_random_uuid()")
    )
    name = Column(String(50))
    game = Column(String(50))
    prize_pool = Column(Numeric(15, 2))
    starts_at = Column(DateTime(timezone=True))
    status = Column(String(20))


class Match(Base):
    __tablename__ = "matches"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,                    # ← Fixed
        server_default=text("gen_random_uuid()")
    )
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"))
    team_a_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    team_b_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    winner_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    played_at = Column(DateTime(timezone=True))

"""Base.metadata.create_all(
    bind=engine, 
    tables=[Match.__table__]
)"""

####now we insert data into the table

'''
#######################we added the random data#####################################

session.execute(text("""
DO $$
DECLARE
    tournament_ids UUID[] := ARRAY(SELECT id FROM tournaments);
    team_ids       UUID[] := ARRAY(SELECT id FROM teams);
    i              INT;
BEGIN
    -- Safety check
    IF array_length(tournament_ids, 1) = 0 OR array_length(team_ids, 1) = 0 THEN
        RAISE EXCEPTION 'No tournaments or teams found. Cannot generate matches.';
    END IF;

    FOR i IN 1..10000 LOOP
        DECLARE
            t_id      UUID := tournament_ids[floor(random() * array_length(tournament_ids, 1) + 1)];
            team_a    UUID := team_ids[floor(random() * array_length(team_ids, 1) + 1)];
            team_b    UUID := team_ids[floor(random() * array_length(team_ids, 1) + 1)];
            winner_id UUID;
            played    TIMESTAMPTZ;
        BEGIN
            -- Ensure different teams
            WHILE team_a = team_b LOOP
                team_b := team_ids[floor(random() * array_length(team_ids, 1) + 1)];
            END LOOP;

            -- Generate winner (70% chance for stronger team, but here random)
            IF random() < 0.5 THEN
                winner_id := team_a;
            ELSE
                winner_id := team_b;
            END IF;

            played := NOW() + (random() * INTERVAL '365 days');  -- this year

            INSERT INTO matches (id, tournament_id, team_a_id, team_b_id, winner_id, played_at)
            VALUES (gen_random_uuid(), t_id, team_a, team_b, winner_id, played);
        END;
    END LOOP;
END;
$$;
"""))
session.commit()'''

# ====================== GET CURRENT TIME ======================
current_time = datetime.now()   # You can also use datetime.utcnow() if needed

# ====================== READ WATERMARK ======================
df_watermark = pd.read_sql_query(
    "SELECT point_of_time FROM pipeline_watermarks LIMIT 1", 
    engine
)

if df_watermark.empty or df_watermark['point_of_time'].iloc[0] is None:
    watermark = "1900-01-01 00:00:00"   # First run
    print("🔄 First run detected. Exporting all historical matches.")
else:
    watermark = df_watermark['point_of_time'].iloc[0]
    print(f"📌 Last watermark: {watermark}")

# ====================== EXPORT MATCHES ======================
try:
    query = text("""
        SELECT * 
        FROM matches 
        WHERE played_at >= :watermark 
          AND played_at <= :current_time
        ORDER BY played_at DESC
    """)

    df = pd.read_sql_query(query, engine, params={
        "watermark": watermark,
        "current_time": current_time
    })

    if df.empty:
        print("ℹ️ No new matches found since last run.")
        # Still update watermark even if no data (optional - you can remove this)
        should_update = True
    else:
        # Create exports folder if not exists
        export_dir = r"D:\my-postgres-project\exports"
        os.makedirs(export_dir, exist_ok=True)
        
        filename = f"{export_dir}\\matches_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        
        df.to_csv(filename, index=False)
        print(f"✅ Successfully exported {len(df)} matches to: {filename}")
        should_update = True

    # ====================== UPDATE WATERMARK ONLY ON SUCCESS ======================
    if should_update:
        if df_watermark.empty:
            # First time insert
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO pipeline_watermarks (point_of_time)
                    VALUES (:current_time)
                """), {"current_time": current_time})
                conn.commit()
        else:
            # Update existing
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE pipeline_watermarks 
                    SET point_of_time = :current_time
                """), {"current_time": current_time})
            
                conn.commit()
        
        print(f"✅ Watermark updated to: {current_time}")

except Exception as e:
    print(f"❌ Export FAILED: {e}")
    print("⚠️ Watermark was NOT updated. Will try again next run.")
    # Do NOT update watermark - this is what you wanted







