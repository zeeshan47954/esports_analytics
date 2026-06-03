CREATE EXTENSION pg_stat_statements;


ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';

-- Optional but recommended
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;

SHOW shared_preload_libraries;
-- 1. Reset statistics first (clean start)
SELECT pg_stat_statements_reset();

-- 2. Run your queries 100 times using a DO block (example)
DO $$
DECLARE
    i INT;
BEGIN
    FOR i IN 1..100 LOOP

        -- === Your queries with PERFORM ===
        
        PERFORM * FROM (
            SELECT player_id, (kills+assists)::numeric / deaths::numeric as kda 
            FROM player_stats
        ) ORDER BY kda DESC LIMIT 10;

        PERFORM tournament_id, team_a_id, 
                round(((count(team_a_id) FILTER (WHERE team_a_id = winner_id))::numeric / 
                       count(team_a_id)) * 100, 2) as winrate_per_tournament 
        FROM matches
        GROUP BY tournament_id, team_a_id 
        ORDER BY tournament_id, team_a_id;

        PERFORM match_id, player_id, 
                avg(damage_dealt) OVER (PARTITION BY match_id ORDER BY player_id) as avg_dmg
        FROM player_stats 
        ORDER BY match_id, player_id;

        PERFORM player_id, difference_in_elos, 
                dense_rank() OVER (ORDER BY difference_in_elos DESC)
        FROM (
            SELECT player_id, elo_after - elo_before as difference_in_elos 
            FROM elo_history
            WHERE changed_at >= now() - interval '30 days'
        ) cte 
        LIMIT 1;

        PERFORM tournament_id, team_a_id 
        FROM matches
        GROUP BY tournament_id, team_a_id 
        HAVING count(*) > 3 
        ORDER BY tournament_id, team_a_id;

        PERFORM player_id, sum(amount) as total_amount 
        FROM prize_payouts 
        GROUP BY player_id;

        PERFORM * FROM (
            SELECT *, dense_rank() OVER (ORDER BY elo_rating DESC) 
            FROM players
        ) p 
        LIMIT 10;

        PERFORM * FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY match_id DESC) as rnk
            FROM player_stats
        ) RankedStats
        WHERE rnk <= 10
        ORDER BY player_id, match_id ASC;

    END LOOP;
END $$;



select * from pg_stat_statements;


SELECT 
    rank() OVER (ORDER BY mean_exec_time DESC) as rank,
    calls,
    mean_exec_time ,
    total_exec_time,
    rows,
    substring(query, 1, 180) AS query
FROM pg_stat_statements 
                 -- ignore rarely run queries
ORDER BY mean_exec_time DESC 
LIMIT 10;

