

 
  /*{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('esports', 'player_stats') }}
),

cleaned AS (
    SELECT
        id AS stat_id,
        match_id,
        player_id,
        kills,
        deaths,
        assists,
        damage_dealt,
        headshot_pct,
        ROUND(
            (kills + assists)::NUMERIC / NULLIF(deaths, 0),
            2
        ) AS kda
    FROM source
    WHERE kills >= 0 AND deaths >= 0
)

SELECT * FROM cleaned*/
--stg_player_stats.sql
 

{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('esports', 'player_stats') }}
)

SELECT
    id AS stat_id,
    match_id,
    player_id,
    kills,
    deaths,
    assists,
    damage_dealt,
    headshot_pct,

    -- More robust KDA calculation
    ROUND(
        (COALESCE(kills, 0) + COALESCE(assists, 0))::NUMERIC 
        / NULLIF(COALESCE(deaths, 0), 0),
        2
    ) AS kda

FROM source