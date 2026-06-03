-- EXTENSION
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- PLAYERS
CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE,
    country VARCHAR(50),
    date_of_birth DATE,
    elo_rating INT CHECK (elo_rating BETWEEN 0 AND 4000),
    created_at TIMESTAMPTZ
);

-- TEAMS
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE,
    region VARCHAR(50),
    founded_at DATE,
    prize_pool NUMERIC,
    is_active BOOLEAN
);

-- TEAM ROSTERS
CREATE TABLE team_rosters (
    id serial PRIMARY KEY,
    team_id UUID REFERENCES teams(id),
    player_id UUID REFERENCES players(id),
    role VARCHAR(40),
    joined_at DATE,
    left_at DATE
);

-- TOURNAMENTS ✅ fixed name
CREATE TABLE tournaments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50),
    game VARCHAR(50),
    prize_pool NUMERIC,
    starts_at TIMESTAMPTZ,
    status VARCHAR(20) CHECK (
        status IN ('upcoming', 'ongoing', 'completed', 'cancelled')
    )
);

-- MATCHES
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tournament_id UUID REFERENCES tournaments(id),
    team_a_id UUID REFERENCES teams(id),
    team_b_id UUID REFERENCES teams(id),
    winner_id UUID REFERENCES teams(id),
    played_at TIMESTAMPTZ
);

-- PLAYER STATS
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

-- ELO HISTORY
CREATE TABLE elo_history (
    id INT PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    match_id UUID REFERENCES matches(id),
    elo_before INT,
    elo_after INT,
    changed_at TIMESTAMPTZ
);

-- PRIZE PAYOUTS (composite key fix)
CREATE TABLE prize_payouts (
    id INT,
    tournament_id UUID REFERENCES tournaments(id),
    team_id UUID REFERENCES teams(id),
    player_id UUID REFERENCES players(id),
    amount NUMERIC,
    paid_at TIMESTAMPTZ,
    PRIMARY KEY (id, player_id)
);

-- PLAYER BANS
CREATE TABLE player_bans (
    id INT PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    reason TEXT,
    banned_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_permanent BOOLEAN
);

-- AUDIT LOG
CREATE TABLE audit_log (
    id bigserial PRIMARY KEY,
    table_name VARCHAR(20),
    operation VARCHAR(50),
    old_data JSONB,
    new_data JSONB,
    changed_at TIMESTAMPTZ
);



CREATE UNIQUE INDEX unique_active_player
ON team_rosters(player_id)
WHERE left_at IS NULL;