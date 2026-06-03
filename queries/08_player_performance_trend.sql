 WITH RankedStats AS (
    SELECT *,
           ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY match_id DESC) as rnk
    FROM player_stats
)
SELECT * FROM RankedStats 
WHERE rnk <= 10
ORDER BY player_id, match_id ASC;