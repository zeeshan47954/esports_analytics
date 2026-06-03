
{{ config(materialized='table') }}

WITH summary AS (
    SELECT * FROM {{ ref('int_player_match_summary') }}
)

SELECT
    player_id,
    username,
    country,
    elo_rating,
    COUNT(*) AS total_matches,
    SUM(kills) AS total_kills,
    ROUND(AVG(kills), 2) AS avg_kills,
    ROUND(AVG(kda), 2) AS career_kda,
    RANK() OVER (ORDER BY elo_rating DESC) AS global_rank
FROM summary
GROUP BY player_id, username, country, elo_rating
HAVING COUNT(*) >= 3
ORDER BY global_rank



