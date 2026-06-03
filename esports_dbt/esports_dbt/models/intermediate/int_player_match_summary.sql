{{ config(materialized='view') }}

WITH player_stats AS (
    SELECT * FROM {{ ref('stg_player_stats') }}
),

matches AS (
    SELECT * FROM {{ ref('stg_matches') }}
),

players AS (
    SELECT * FROM {{ ref('stg_players') }}
)


SELECT
    ps.stat_id,
    ps.match_id,
    ps.player_id,
    p.username,
    p.country,
    p.elo_rating,
    m.tournament_id,
    m.played_at,
    ps.kills,
    ps.deaths,
    ps.assists,
    ps.kda,
    (ps.kills + ps.assists) AS total_contribution
FROM player_stats ps
JOIN matches m ON ps.match_id = m.match_id
JOIN players p ON ps.player_id = p.id

