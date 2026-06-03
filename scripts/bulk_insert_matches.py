
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
Session=sessionmaker(bind=engine)
session=Session()
session.execute(text("""
CREATE TABLE player_stats (
    id INT PRIMARY KEY,
    match_id UUID REFERENCES matches(id),
    player_id UUID REFERENCES players(id),
    kills INT CHECK (kills >= 0),
    deaths INT CHECK (deaths >= 0),
    assists INT CHECK (assists >= 0),
    damage_dealt NUMERIC,
    headshot_pct NUMERIC CHECK (headshot_pct BETWEEN 0 AND 100)
);
 """))

session.execute(text("""
DO $$
DECLARE
    match_ids UUID[] := '{}';
    player_ids UUID[] := '{}';
    used_players UUID[];
    m_id UUID;
    p_id UUID;
    kills INT;
    deaths INT;
    assists INT;
    damage NUMERIC;
    hs_pct NUMERIC;
    row_counter INT := 1;
BEGIN
    -- Load all match and player IDs
    SELECT array_agg(id) INTO match_ids FROM matches;
    SELECT array_agg(id) INTO player_ids FROM players;

    IF array_length(match_ids, 1) < 10 THEN
        RAISE EXCEPTION 'Not enough matches. Found only %', array_length(match_ids, 1);
    END IF;

    -- Generate 80,000 rows
    FOR i IN 1..10 LOOP                     -- 10 matches
        m_id := match_ids[i];
        
        FOR j IN 1..1000 LOOP               -- 1000 groups per match
            used_players := '{}';           -- reset unique players for this group

            FOR s IN 1..8 LOOP              -- 8 unique players per group
                -- Pick unique player
                LOOP
                    p_id := player_ids[ceil(random() * array_length(player_ids, 1))];
                    EXIT WHEN NOT p_id = ANY(used_players);
                END LOOP;

                used_players := array_append(used_players, p_id);

                -- Random stats
                kills     := floor(random() * 40)::INT;           -- 0-39
                deaths    := floor(random() * 25)::INT;           -- 0-24
                assists   := floor(random() * 20)::INT;           -- 0-19
                damage    := round((random() * 4500 + 100)::NUMERIC, 2);
                hs_pct    := round((random() * 55 + 25)::NUMERIC, 2);  -- 25% to 80%

                INSERT INTO player_stats (id, match_id, player_id, kills, deaths, assists, damage_dealt, headshot_pct)
                VALUES (row_counter, m_id, p_id, kills, deaths, assists, damage, hs_pct);

                row_counter := row_counter + 1;
            END LOOP;
        END LOOP;
    END LOOP;

    RAISE NOTICE '✅ Successfully inserted 80,000 rows into player_stats';
END $$;


"""))
session.commit()