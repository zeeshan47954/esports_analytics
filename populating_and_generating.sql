
/*
 * populating the table 
 * CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE,
    country VARCHAR(50),
    date_of_birth DATE,
    elo_rating INT CHECK (elo_rating BETWEEN 0 AND 4000),
    created_at TIMESTAMPTZ
);
 * 
 * 
 * */

INSERT INTO players (id, username, country, date_of_birth, elo_rating, created_at)
SELECT 
    gen_random_uuid(),
    'player' || tt as username,
    country,
    date_of_birth::DATE,
    elo_rating,
    timezone(timezone_name, now() - (random() * interval '3 years'))
FROM (
    SELECT 
        tt,
        (ARRAY[
            'America/Los_Angeles', 'USA',
            'Asia/Shanghai', 'China',
            'Asia/Seoul', 'South Korea',
            'America/Sao_Paulo', 'Brazil',
            'Europe/Moscow', 'Russia',
            'Europe/Paris', 'France',
            'Europe/Berlin', 'Germany',
            'Europe/Stockholm', 'Sweden',
            'Europe/Copenhagen', 'Denmark',
            'Europe/London', 'UK',
            'America/Toronto', 'Canada',
            'Australia/Sydney', 'Australia',
            'Asia/Tokyo', 'Japan',
            'Europe/Warsaw', 'Poland',
            'Europe/Istanbul', 'Turkey',
            'Asia/Jakarta', 'Indonesia',
            'Asia/Manila', 'Philippines',
            'Asia/Ho_Chi_Minh', 'Vietnam',
            'Asia/Kolkata', 'India',
            'Asia/Bangkok', 'Thailand'
        ])[floor(random()*20)*2+1] as timezone_name,
        (ARRAY[
            'USA', 'China', 'South Korea', 'Brazil', 'Russia',
            'France', 'Germany', 'Sweden', 'Denmark', 'UK',
            'Canada', 'Australia', 'Japan', 'Poland', 'Turkey',
            'Indonesia', 'Philippines', 'Vietnam', 'India', 'Thailand'
        ])[floor(random()*20+1)] as country,
        (ARRAY[
            '2007-09-15', '2007-07-02', '2006-11-22', '2006-02-07', '2005-12-05',
            '2004-11-28', '2004-10-01', '2004-08-09', '2005-07-15', '2005-03-26',
            '2003-02-20', '2003-05-10', '2002-06-12', '2001-05-25', '2001-09-18',
            '2001-04-05', '2000-11-14', '2000-08-22', '2000-03-03', '1999-07-19',
            '1999-12-11', '1998-05-25', '1998-06-17', '1997-10-29', '1997-04-08',
            '1996-09-15', '1995-12-23', '1996-01-26', '1995-06-17', '1995-05-25'
        ])[floor(random()*30+1)] as date_of_birth,
        1080 + floor(random() * tt) as elo_rating
    FROM generate_series(1, 500) as tt
) as subquery;

/*
 * 
 * CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE,
    region VARCHAR(50),
    founded_at DATE,
    prize_pool NUMERIC,
    is_active BOOLEAN
);

 * 
 * */

INSERT INTO teams (id, name, region, founded_at, prize_pool, is_active)
SELECT 
    gen_random_uuid(),
    'team' || kk,
    (ARRAY[
        'North America',
        'South America', 
        'Europe',
        'Oceania',
        'Asia'
    ])[floor(random()*5+1)],
    DATE '2001-10-10' + (random()*365) * INTERVAL '1 day',  -- Fixed: random years, not just 50 days
    50000 + random()*50000,  -- Fixed: prize pool between 50k and 100k
    (ARRAY[true, false])[floor(random()*2+1)]
FROM generate_series(1,50) as kk;

/*CREATE TABLE tournaments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50),
    game VARCHAR(50),
    prize_pool NUMERIC,
    starts_at TIMESTAMPTZ,
    status VARCHAR(20) CHECK (
        status IN ('upcoming', 'ongoing', 'completed', 'cancelled')
    )
);
*/
INSERT INTO tournaments (id, name, game, prize_pool, starts_at, status)
SELECT 
    gen_random_uuid(),
    'tournament' || kk,
    (ARRAY[
        'Dota 2',
        'League of Legends',
        'Counter-Strike 2',
        'Valorant',
        'Call of Duty',
        'Rainbow Six Siege',
        'Overwatch 2',
        'Fortnite',
        'PUBG: Battlegrounds',
        'Apex Legends',
        'Rocket League',
        'FIFA (EA FC)',
        'NBA 2K',
        'Street Fighter 6',
        'Tekken 8',
        'Super Smash Bros. Ultimate',
        'Mortal Kombat 1',
        'StarCraft II',
        'Hearthstone',
        'Teamfight Tactics'
    ])[floor(random()*20+1)],
    50000 + random() * 500000,  -- Fixed: prize pool between 50k and 550k
    (TIMESTAMP '2026-01-01 00:00:00' 
     + (random() * 365 * 24 * 60 * 60) * INTERVAL '1 second')::timestamptz,  -- Fixed date format
    (ARRAY['upcoming', 'ongoing', 'completed', 'cancelled'])[floor(random()*4+1)]  -- Added ARRAY keyword
FROM generate_series(1,100) as kk;


/*
 * CREATE TABLE team_rosters (
    id serial PRIMARY KEY,
    team_id UUID REFERENCES teams(id),
    player_id UUID REFERENCES players(id),
    role VARCHAR(40),
    joined_at DATE,
    left_at DATE
);

 * */
WITH player_id AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn
    FROM players
),
team_id AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY RANDOM()) AS rn
    FROM teams
),
assignment AS (
    SELECT 
        p.id AS player_id,
        t.id AS team_id,
        CASE (RANDOM() * 4)::INT
            WHEN 0 THEN 'IGL'
            WHEN 1 THEN 'AWPer'
            WHEN 2 THEN 'Support'
            WHEN 3 THEN 'Entry Fragger'
            ELSE 'Lurker'
        END AS role
    FROM player_id p 
    JOIN team_id t ON t.rn = ((p.rn - 1) / 6) + 1
)
INSERT INTO team_rosters (team_id, player_id, role, joined_at, left_at)
SELECT 
    team_id,
    player_id,
    role,
    joined_at,
    joined_at + INTERVAL '2 days' AS left_at
FROM (
    SELECT 
        player_id,
        team_id,
        role,
        DATE '2001-10-10' + (RANDOM() * 365) * INTERVAL '1 day' AS joined_at
    FROM assignment
) AS subquery;
  



/*CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tournament_id UUID REFERENCES tournaments(id),
    team_a_id UUID REFERENCES teams(id),
    team_b_id UUID REFERENCES teams(id),
    winner_id UUID REFERENCES teams(id),
    played_at TIMESTAMPTZ
);
 * */



do $$
declare
    tournament_ids uuid[];
    team_ids       uuid[];
    t_id           uuid;
    team_a_id      uuid;
    team_b_id      uuid;
    score_a        int;
    score_b        int;
    winner         uuid;
    played_at      timestamptz;
begin
    -- first we populate both the arrays
    select array(select id from tournaments) into tournament_ids;
    select array(select id from teams) into team_ids;
    
    for i in 1..10000 loop
        t_id := tournament_ids[floor(random() * array_length(tournament_ids, 1) + 1)];
        
        team_a_id := team_ids[floor(random() * array_length(team_ids, 1) + 1)];
        team_b_id := team_ids[floor(random() * array_length(team_ids, 1) + 1)];
        
        -- ensure teams are different
        while team_a_id = team_b_id loop
            team_b_id := team_ids[floor(random() * array_length(team_ids, 1) + 1)];
        end loop;
        
        score_a := 5 + (random() * 11)::INT;
        score_b := 5 + (random() * 11)::INT;
        
        -- avoid draws: if equal, give one team the edge
        IF score_a = score_b THEN
            IF random() > 0.5 THEN
                score_a := score_a + 1;
            ELSE
                score_b := score_b + 1;
            END IF;
        END IF;
        
        -- winner is whichever team has higher score
        IF score_a > score_b THEN
            winner := team_a_id;
        ELSE
            winner := team_b_id;
        END IF;
        
        played_at := NOW() - (random() * INTERVAL '730 days');
        
        insert into matches(id, tournament_id, team_a_id, team_b_id, winner_id, played_at)
        values(gen_random_uuid(), t_id, team_a_id, team_b_id, winner, played_at);
    end loop;
end;
$$;

/*
 * CREATE TABLE player_stats (
    id INT PRIMARY KEY,
    match_id UUID REFERENCES matches(id),
    player_id UUID REFERENCES players(id),
    kills INT CHECK (kills >= 0),
    deaths INT CHECK (deaths >= 0),
    assists INT CHECK (assists >= 0),
    damage_dealt NUMERIC,
    headshot_pct NUMERIC CHECK (headshot_pct BETWEEN 0 AND 100)
);

 * 
 * */

/*In gaming, headshot_pct (headshot percentage) measures the proportion of 
your kills that were headshots. It’s calculated as (headshot kills ÷ total kills) × 100*/


DO $$
DECLARE
    match_id uuid[];
    player_id uuid[];
    player_idtemp uuid[] := '{}'; -- initialize empty
    kills int;
    deaths int;
    assists int;
    p_id uuid;
    damage_dealt numeric;
    headshot_pct numeric;
BEGIN
    -- populate arrays
    SELECT array(SELECT id FROM matches) INTO match_id;
    SELECT array(SELECT id FROM players) INTO player_id;

    -- loop over matches
    FOR i IN 1..array_length(match_id,1) LOOP
        player_idtemp := '{}'; -- reset for each match

        -- pick 8 unique players
        FOR s IN 1..8 LOOP
            LOOP
                p_id := player_id[ceil(random()*array_length(player_id,1))];
                -- ensure uniqueness
                EXIT WHEN NOT p_id = ANY(player_idtemp);
            END LOOP;

            -- add to temp array
            player_idtemp := array_append(player_idtemp, p_id);

            -- random stats
            kills := floor(random()*40+1);
            deaths := floor(random()*20+1);
            assists := floor(random()*15+1);
            damage_dealt := round((random()*3000+1)::numeric, 2);
            headshot_pct := round((random()*40+30)::numeric, 2);

            -- insert row
            INSERT INTO player_stats(id, match_id, player_id, kills, deaths, assists, damage_dealt, headshot_pct)
            VALUES ((i*10)+s, match_id[i], p_id, kills, deaths, assists, damage_dealt, headshot_pct);
        END LOOP;
    END LOOP;
END;
$$;


/*CREATE TABLE elo_history (
    id INT PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    match_id UUID REFERENCES matches(id),
    elo_before INT,
    elo_after INT,
    changed_at TIMESTAMPTZ
);
*/ 

WITH cte1 AS (
    SELECT 
        player_id,
        match_id,
        ROW_NUMBER() OVER (ORDER BY player_id) AS number,
        RANDOM() AS randomvalue 
    FROM player_stats
),
cte2 AS (
    SELECT id as player_id, elo_rating 
    FROM players
)
INSERT INTO elo_history (id, player_id, match_id, elo_before, elo_after, changed_at)
SELECT 
    a.number,
    a.player_id,
    a.match_id,
    b.elo_rating AS elo_before,
    CASE WHEN a.randomvalue < 0.5 
         THEN 1200 - FLOOR(RANDOM() * 500)
         ELSE 1200 + FLOOR(RANDOM() * 500)
    END AS elo_after,
    NOW() - (RANDOM() * 365 || ' days')::INTERVAL AS changed_at
FROM cte1 a 
JOIN cte2 b ON a.player_id = b.player_id;


/*CREATE TABLE player_bans (
    id INT PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    reason TEXT,
    banned_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_permanent BOOLEAN
);*/

WITH cte2 AS (
    SELECT id as player_id, elo_rating 
    FROM players
    WHERE RANDOM() < 0.1  -- Only select 10% of players to ban
)
INSERT INTO player_bans (id, player_id, reason, banned_at, expires_at, is_permanent)
SELECT 
    ROW_NUMBER() OVER (ORDER BY player_id) AS id,
    player_id,
    'Violation of terms of service' AS reason,
    NOW() - INTERVAL '7 days' AS banned_at,
    NOW() + INTERVAL '30 days' AS expires_at,
    FALSE AS is_permanent
FROM cte2;
select * from player_bans

/*
 * 
 * CREATE TABLE prize_payouts (
    id INT,
    tournament_id UUID REFERENCES tournaments(id),
    team_id UUID REFERENCES teams(id),
    player_id UUID REFERENCES players(id),
    amount NUMERIC,
    paid_at TIMESTAMPTZ,
    PRIMARY KEY (id, player_id)
);
 * 
 * */
with playerss as(

select id as player_id,row_number() over(order by id) as playerno from players
)
,teamss as(

select id as team_id,row_number() over(order by random()) as teamno from teams
) 
,tournamentss as
(

select id as tournament_id,row_number() over(order by random()) as tournamentno from tournaments

)
insert into prize_payouts (id,tournament_id,team_id,player_id,amount,paid_at)
select k.playerno as player_no ,t.tournament_id as tournament_id ,team_id,player_id as played_id,50000 +floor(random()*50000) as amount,NOW() - (RANDOM() * 365 || ' days')::interval as paid_at from tournamentss t join
(select p.player_id as player_id,t.team_id as team_id,p.playerno as playerno from 
playerss p join  teamss t on p.playerno=t.teamno) as k on t.tournamentno=k.playerno






