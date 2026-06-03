--stg_matches.sql
{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('esports', 'matches') }}
),

cleaned AS (
    SELECT
        id AS match_id,
        tournament_id,
        team_a_id,
        team_b_id,
        winner_id,
        
        played_at
        
    FROM source
   
)

SELECT * FROM cleaned


