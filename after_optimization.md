1.
explain analyze select * from
(select player_id,(kills+assists)::numeric/(deaths)::numeric as kda 
from player_stats)order by kda desc limit 10


/*QUERY PLAN(Before optimization i.e before adding the indexing)                                                                                                                      |
---------------------------------------------------------------------------------------------------------------------------------+
Planning:                                                                                                                        |
Planning Time: 1.597 ms                                                                                                          |
Limit  (cost=4238.77..4238.80 rows=10 width=48) (actual time=254.480..254.483 rows=10.00 loops=1)                                |
Execution Time: 254.642 ms                                                                                                       |
  Buffers: shared hit=913                                                                                                        |
  Buffers: shared hit=112                                                                                                        |
  ->  Sort  (cost=4238.77..4438.77 rows=80000 width=48) (actual time=254.475..254.476 rows=10.00 loops=1)                        |
        Sort Method: top-N heapsort  Memory: 26kB                                                                                |
        Sort Key: ((((player_stats.kills + player_stats.assists))::numeric / (player_stats.deaths)::numeric)) DESC               |
        Buffers: shared hit=913                                                                                                  |
        ->  Seq Scan on player_stats  (cost=0.00..2510.00 rows=80000 width=48) (actual time=0.245..205.429 rows=80000.00 loops=1)|
              Buffers: shared hit=910                                                                                            |*/


/*QUERY PLAN(After optimization i.e adding the indexing )                                                                                                                                            |
--------------------------------------------------------------------------------------------------------------------------------------------------------+
Limit  (cost=0.42..1.26 rows=10 width=48) (actual time=0.162..0.188 rows=10.00 loops=1)                                                                 |
  Buffers: shared hit=10 read=3                                                                                                                         |
  ->  Index Scan Backward using idx_kda_computed on player_stats  (cost=0.42..6708.42 rows=80000 width=48) (actual time=0.160..0.183 rows=10.00 loops=1)|
        Index Searches: 1                                                                                                                               |
        Buffers: shared hit=10 read=3                                                                                                                   |
Planning:                                                                                                                                               |
  Buffers: shared hit=95 read=1                                                                                                                         |
Planning Time: 1.342 ms                                                                                                                                 |
Execution Time: 0.232 ms                                                                                                                                |
 * */


2.
explain analyze select tournament_id,team_a_id
,round(((count(team_a_id )filter(where team_a_id =winner_id))::numeric/(count(team_a_id))::numeric)*100,2) as winrate_per_tournament 
from matches
group by tournament_id,team_a_id order by tournament_id ,team_a_id

/*QUERY PLAN(Before optimization i.e before indexing)                                                                                                              |
-------------------------------------------------------------------------------------------------------------------------+
Sort  (cost=440.33..442.83 rows=1000 width=64) (actual time=54.254..54.750 rows=4324.00 loops=1)                         |
  Sort Key: tournament_id, team_a_id                                                                                     |
  Sort Method: quicksort  Memory: 429kB                                                                                  |
  Buffers: shared hit=146 dirtied=1                                                                                      |
  ->  HashAggregate  (cost=368.00..390.50 rows=1000 width=64) (actual time=19.738..40.229 rows=4324.00 loops=1)          |
        Group Key: tournament_id, team_a_id                                                                              |
        Batches: 1  Memory Usage: 665kB                                                                                  |
        Buffers: shared hit=143 dirtied=1                                                                                |
        ->  Seq Scan on matches  (cost=0.00..243.00 rows=10000 width=48) (actual time=0.034..2.955 rows=10001.00 loops=1)|
              Buffers: shared hit=143 dirtied=1                                                                          |
Planning:                                                                                                                |
  Buffers: shared hit=76                                                                                                 |
Planning Time: 1.132 ms                                                                                                  |
Execution Time: 55.605 ms                                                                                                |

*/

/*QUERY PLAN(After optimization i.e after indexing)                                                                                                              |
-------------------------------------------------------------------------------------------------------------------------+
Sort  (cost=440.35..442.85 rows=1000 width=64) (actual time=22.197..23.060 rows=4324.00 loops=1)                         |
  Sort Key: tournament_id, team_a_id                                                                                     |
  Sort Method: quicksort  Memory: 429kB                                                                                  |
  Buffers: shared hit=143                                                                                                |
  ->  HashAggregate  (cost=368.02..390.52 rows=1000 width=64) (actual time=9.301..16.464 rows=4324.00 loops=1)           |
        Group Key: tournament_id, team_a_id                                                                              |
        Batches: 1  Memory Usage: 665kB                                                                                  |
        Buffers: shared hit=143                                                                                          |
        ->  Seq Scan on matches  (cost=0.00..243.01 rows=10001 width=48) (actual time=0.032..1.109 rows=10001.00 loops=1)|
              Buffers: shared hit=143                                                                                    |
Planning:                                                                                                                |
  Buffers: shared hit=57 read=1                                                                                          |
Planning Time: 1.575 ms                                                                                                  |
Execution Time: 24.832 ms                                                                                                |*/



3.select match_id,player_id,avg(damage_dealt)over(partition by match_id order by player_id) as avg_dmg
from player_stats order by match_id,player_id
/*QUERY PLAN(before optimization)                                                                                                                      |
--------------------------------------------------------------------------------------------------------------------------------+
WindowAgg  (cost=10412.60..12012.58 rows=80000 width=64) (actual time=149.167..869.693 rows=80000.00 loops=1)                   |
  Window: w1 AS (PARTITION BY match_id ORDER BY player_id)                                                                      |
  Storage: Memory  Maximum Storage: 17kB                                                                                        |
  Buffers: shared hit=913, temp read=481 written=482                                                                            |
  ->  Sort  (cost=10412.58..10612.58 rows=80000 width=38) (actual time=149.070..185.905 rows=80000.00 loops=1)                  |
        Sort Key: match_id, player_id                                                                                           |
        Sort Method: external merge  Disk: 3848kB                                                                               |
        Buffers: shared hit=913, temp read=481 written=482                                                                      |
        ->  Seq Scan on player_stats  (cost=0.00..1710.00 rows=80000 width=38) (actual time=0.036..40.668 rows=80000.00 loops=1)|
              Buffers: shared hit=910                                                                                           |
Planning:                                                                                                                       |
  Buffers: shared hit=105                                                                                                       |
Planning Time: 1.619 ms                                                                                                         |
Execution Time: 883.517 ms                                                                                                      |*/

/*QUERY PLAN (after optimization)                                                                                                                                         |
----------------------------------------------------------------------------------------------------------------------------------------------------+
WindowAgg  (cost=0.52..8191.28 rows=80000 width=64) (actual time=1.153..321.728 rows=80000.00 loops=1)                                              |
  Window: w1 AS (PARTITION BY match_id ORDER BY player_id)                                                                                          |
  Storage: Memory  Maximum Storage: 17kB                                                                                                            |
  Buffers: shared hit=9988 read=484                                                                                                                 |
  ->  Index Scan using avg_damage_index on player_stats  (cost=0.42..6791.28 rows=80000 width=38) (actual time=0.466..101.016 rows=80000.00 loops=1)|
        Index Searches: 1                                                                                                                           |
        Buffers: shared hit=9988 read=484                                                                                                           |
Planning:                                                                                                                                           |
  Buffers: shared hit=25 read=1                                                                                                                     |
Planning Time: 1.431 ms                                                                                                                             |
Execution Time: 327.784 ms                                                                                                                          |*/




4.
explain analyze with cte as (

select player_id,elo_after-elo_before as difference_in_elos from elo_history
where changed_at >= now()-interval '30 days' and changed_at<now()
)

select player_id,difference_in_elos,dense_rank()over(order  by difference_in_elos desc ) from cte limit 1

/*QUERY PLAN(before optimization)                                                                                                                        |
------------------------------------------------------------------------------------------------------------------------------------+
Limit  (cost=2898.92..2898.94 rows=1 width=28) (actual time=182.518..182.520 rows=1.00 loops=1)                                     |
  Buffers: shared hit=828                                                                                                           |
  ->  WindowAgg  (cost=2898.92..2985.94 rows=4352 width=28) (actual time=182.516..182.517 rows=1.00 loops=1)                        |
        Window: w1 AS (ORDER BY ((elo_history.elo_after - elo_history.elo_before)) ROWS UNBOUNDED PRECEDING)                        |
        Storage: Memory  Maximum Storage: 17kB                                                                                      |
        Buffers: shared hit=828                                                                                                     |
        ->  Sort  (cost=2898.90..2909.78 rows=4352 width=20) (actual time=182.470..182.470 rows=1.00 loops=1)                       |
              Sort Key: ((elo_history.elo_after - elo_history.elo_before)) DESC                                                     |
              Sort Method: quicksort  Memory: 361kB                                                                                 |
              Buffers: shared hit=828                                                                                               |
              ->  Seq Scan on elo_history  (cost=0.00..2635.88 rows=4352 width=20) (actual time=1.440..178.592 rows=4302.00 loops=1)|
                    Filter: ((changed_at < now()) AND (changed_at >= (now() - '30 days'::interval)))                                |
                    Rows Removed by Filter: 75698                                                                                   |
                    Buffers: shared hit=825                                                                                         |
Planning:                                                                                                                           |
  Buffers: shared hit=109                                                                                                           |
Planning Time: 4.275 ms                                                                                                             |
Execution Time: 182.836 ms                                                                                                          |*/

/*QUERY PLAN(after optimization)                                                                                                                                      |
------------------------------------------------------------------------------------------------------------------------------------------------------+
Limit  (cost=1308.84..1308.86 rows=1 width=28) (actual time=8.962..8.964 rows=1.00 loops=1)                                                           |
  Buffers: shared hit=823 read=16                                                                                                                     |
  ->  WindowAgg  (cost=1308.84..1395.67 rows=4342 width=28) (actual time=8.960..8.961 rows=1.00 loops=1)                                              |
        Window: w1 AS (ORDER BY ((elo_history.elo_after - elo_history.elo_before)) ROWS UNBOUNDED PRECEDING)                                          |
        Storage: Memory  Maximum Storage: 17kB                                                                                                        |
        Buffers: shared hit=823 read=16                                                                                                               |
        ->  Sort  (cost=1308.83..1319.68 rows=4342 width=20) (actual time=8.943..8.944 rows=1.00 loops=1)                                             |
              Sort Key: ((elo_history.elo_after - elo_history.elo_before)) DESC                                                                       |
              Sort Method: quicksort  Memory: 360kB                                                                                                   |
              Buffers: shared hit=823 read=16                                                                                                         |
              ->  Bitmap Heap Scan on elo_history  (cost=112.93..1046.48 rows=4342 width=20) (actual time=2.104..5.680 rows=4283.00 loops=1)          |
                    Recheck Cond: ((changed_at >= (now() - '30 days'::interval)) AND (changed_at < now()))                                            |
                    Heap Blocks: exact=820                                                                                                            |
                    Buffers: shared hit=823 read=16                                                                                                   |
                    ->  Bitmap Index Scan on improved_elo_index  (cost=0.00..111.84 rows=4342 width=0) (actual time=1.916..1.917 rows=4283.00 loops=1)|
                          Index Cond: ((changed_at >= (now() - '30 days'::interval)) AND (changed_at < now()))                                        |
                          Index Searches: 1                                                                                                           |
                          Buffers: shared hit=3 read=16                                                                                               |
Planning:                                                                                                                                             |
  Buffers: shared hit=78 read=4                                                                                                                       |
Planning Time: 3.497 ms                                                                                                                               |
Execution Time: 9.384 ms                                                                                                                              |*/

5.
explain analyze select tournament_id,team_a_id from matches
group by tournament_id,team_a_id  having count(*)>3 order by tournament_id ,team_a_id

/*QUERY PLAN(before optimization)                                                                                                               |
-------------------------------------------------------------------------------------------------------------------------+
Sort  (cost=344.45..345.28 rows=333 width=32) (actual time=20.286..20.432 rows=731.00 loops=1)                           |
  Sort Key: tournament_id, team_a_id                                                                                     |
  Sort Method: quicksort  Memory: 59kB                                                                                   |
  Buffers: shared hit=146                                                                                                |
  ->  HashAggregate  (cost=318.00..330.50 rows=333 width=32) (actual time=16.415..18.189 rows=731.00 loops=1)            |
        Group Key: tournament_id, team_a_id                                                                              |
        Filter: (count(*) > 3)                                                                                           |
        Batches: 1  Memory Usage: 665kB                                                                                  |
        Rows Removed by Filter: 3593                                                                                     |
        Buffers: shared hit=143                                                                                          |
        ->  Seq Scan on matches  (cost=0.00..243.00 rows=10000 width=32) (actual time=0.031..2.827 rows=10001.00 loops=1)|
              Buffers: shared hit=143                                                                                    |
Planning:                                                                                                                |
  Buffers: shared hit=73                                                                                                 |
Planning Time: 1.052 ms                                                                                                  |
Execution Time: 20.900 ms                                                                                                |*/

/*QUERY PLAN (after optimization)                                                                                                              |
-------------------------------------------------------------------------------------------------------------------------+
Sort  (cost=344.47..345.30 rows=333 width=32) (actual time=14.419..14.493 rows=731.00 loops=1)                           |
  Sort Key: tournament_id, team_a_id                                                                                     |
  Sort Method: quicksort  Memory: 59kB                                                                                   |
  Buffers: shared hit=143                                                                                                |
  ->  HashAggregate  (cost=318.02..330.52 rows=333 width=32) (actual time=12.092..13.662 rows=731.00 loops=1)            |
        Group Key: tournament_id, team_a_id                                                                              |
        Filter: (count(*) > 3)                                                                                           |
        Batches: 1  Memory Usage: 665kB                                                                                  |
        Rows Removed by Filter: 3593                                                                                     |
        Buffers: shared hit=143                                                                                          |
        ->  Seq Scan on matches  (cost=0.00..243.01 rows=10001 width=32) (actual time=0.024..1.787 rows=10001.00 loops=1)|
              Buffers: shared hit=143                                                                                    |
Planning:                                                                                                                |
  Buffers: shared hit=3                                                                                                  |
Planning Time: 0.200 ms                                                                                                  |
Execution Time: 14.756 ms                                                                                                |

clearly,the index wasnt used,instead caching got the job done in a lesser time
 * 
 *  * */

6.explain analyze select player_id,sum(amount) as total_amount from prize_payouts pp group by player_id 

/*QUERY PLAN (before optimization)                                                                                                          |
----------------------------------------------------------------------------------------------------------------------+
HashAggregate  (cost=20.20..22.70 rows=200 width=48) (actual time=0.481..0.522 rows=50.00 loops=1)                    |
  Group Key: player_id                                                                                                |
  Batches: 1  Memory Usage: 40kB                                                                                      |
  Buffers: shared hit=1                                                                                               |
  ->  Seq Scan on prize_payouts pp  (cost=0.00..16.80 rows=680 width=48) (actual time=0.352..0.361 rows=50.00 loops=1)|
        Buffers: shared hit=1                                                                                         |
Planning:                                                                                                             |
  Buffers: shared hit=109                                                                                             |
Planning Time: 1.577 ms                                                                                               |
Execution Time: 0.657 ms                                                                                              |
*/
/*QUERY PLAN(after optimization) (however the index wasnt used at all)                                                                                                      |
--------------------------------------------------------------------------------------------------------------------+
HashAggregate  (cost=1.75..2.38 rows=50 width=48) (actual time=0.124..0.161 rows=50.00 loops=1)                     |
  Group Key: player_id                                                                                              |
  Batches: 1  Memory Usage: 40kB                                                                                    |
  Buffers: shared hit=1                                                                                             |
  ->  Seq Scan on prize_payouts pp  (cost=0.00..1.50 rows=50 width=48) (actual time=0.031..0.039 rows=50.00 loops=1)|
        Buffers: shared hit=1                                                                                       |
Planning:                                                                                                           |
  Buffers: shared hit=40 read=1                                                                                     |
Planning Time: 3.924 ms                                                                                             |
Execution Time: 0.224 ms                                                                                            |*/

7.explain analyze select *,dense_rank()over(order by elo_rating desc) from players p limit 10
/*QUERY PLAN  (no need for optimization)                                                                                                               |
----------------------------------------------------------------------------------------------------------------------------+
Limit  (cost=33.43..33.61 rows=10 width=56) (actual time=0.560..0.588 rows=10.00 loops=1)                                   |
  Buffers: shared hit=6                                                                                                     |
  ->  WindowAgg  (cost=33.43..42.16 rows=500 width=56) (actual time=0.559..0.584 rows=10.00 loops=1)                        |
        Window: w1 AS (ORDER BY elo_rating ROWS UNBOUNDED PRECEDING)                                                        |
        Storage: Memory  Maximum Storage: 17kB                                                                              |
        Buffers: shared hit=6                                                                                               |
        ->  Sort  (cost=33.41..34.66 rows=500 width=48) (actual time=0.538..0.540 rows=10.00 loops=1)                       |
              Sort Key: elo_rating DESC                                                                                     |
              Sort Method: quicksort  Memory: 58kB                                                                          |
              Buffers: shared hit=6                                                                                         |
              ->  Seq Scan on players p  (cost=0.00..11.00 rows=500 width=48) (actual time=0.029..0.218 rows=501.00 loops=1)|
                    Buffers: shared hit=6                                                                                   |
Planning Time: 0.163 ms                                                                                                     |
Execution Time: 0.633 ms                                                                                                    |


*/
8.explain analyze WITH RankedStats AS (
    SELECT *,
           ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY match_id DESC) as rnk
    FROM player_stats
)
SELECT * FROM RankedStats 
WHERE rnk <= 10
ORDER BY player_id, match_id ASC;

/*QUERY PLAN(before optimization)                                                                                                                           |
--------------------------------------------------------------------------------------------------------------------------------------+
Incremental Sort  (cost=11244.16..16773.86 rows=80000 width=68) (actual time=233.367..305.885 rows=5000.00 loops=1)                   |
  Sort Key: player_stats.player_id, player_stats.match_id                                                                             |
  Presorted Key: player_stats.player_id                                                                                               |
  Full-sort Groups: 125  Sort Method: quicksort  Average Memory: 28kB  Peak Memory: 28kB                                              |
  Buffers: shared hit=913, temp read=705 written=707                                                                                  |
  ->  WindowAgg  (cost=11235.10..12835.08 rows=80000 width=68) (actual time=232.842..298.148 rows=5000.00 loops=1)                    |
        Window: w1 AS (PARTITION BY player_stats.player_id ORDER BY player_stats.match_id ROWS UNBOUNDED PRECEDING)                   |
        Run Condition: (row_number() OVER w1 <= 10)                                                                                   |
        Storage: Memory  Maximum Storage: 17kB                                                                                        |
        Buffers: shared hit=910, temp read=705 written=707                                                                            |
        ->  Sort  (cost=11235.08..11435.08 rows=80000 width=60) (actual time=232.815..269.348 rows=80000.00 loops=1)                  |
              Sort Key: player_stats.player_id, player_stats.match_id DESC                                                            |
              Sort Method: external merge  Disk: 5640kB                                                                               |
              Buffers: shared hit=910, temp read=705 written=707                                                                      |
              ->  Seq Scan on player_stats  (cost=0.00..1710.00 rows=80000 width=60) (actual time=0.046..45.814 rows=80000.00 loops=1)|
                    Buffers: shared hit=910                                                                                           |
Planning:                                                                                                                             |
  Buffers: shared hit=129                                                                                                             |
Planning Time: 1.307 ms                                                                                                               |
Execution Time: 308.434 ms                                                                                                            |*/


/*QUERY PLAN(after optimization)                                                                                                                                                             |
------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
Incremental Sort  (cost=50.09..16069.96 rows=80000 width=68) (actual time=3.321..246.150 rows=5000.00 loops=1)                                                          |
  Sort Key: player_stats.player_id, player_stats.match_id                                                                                                               |
  Presorted Key: player_stats.player_id                                                                                                                                 |
  Full-sort Groups: 125  Sort Method: quicksort  Average Memory: 28kB  Peak Memory: 28kB                                                                                |
  Buffers: shared hit=79938 read=484                                                                                                                                    |
  ->  WindowAgg  (cost=20.01..12131.19 rows=80000 width=68) (actual time=0.757..241.329 rows=5000.00 loops=1)                                                           |
        Window: w1 AS (PARTITION BY player_stats.player_id ORDER BY player_stats.match_id ROWS UNBOUNDED PRECEDING)                                                     |
        Run Condition: (row_number() OVER w1 <= 10)                                                                                                                     |
        Storage: Memory  Maximum Storage: 17kB                                                                                                                          |
        Buffers: shared hit=79938 read=484                                                                                                                              |
        ->  Incremental Sort  (cost=19.86..10731.19 rows=80000 width=60) (actual time=0.739..216.728 rows=80000.00 loops=1)                                             |
              Sort Key: player_stats.player_id, player_stats.match_id DESC                                                                                              |
              Presorted Key: player_stats.player_id                                                                                                                     |
              Full-sort Groups: 500  Sort Method: quicksort  Average Memory: 30kB  Peak Memory: 30kB                                                                    |
              Pre-sorted Groups: 500  Sort Method: quicksort  Average Memory: 38kB  Peak Memory: 38kB                                                                   |
              Buffers: shared hit=79938 read=484                                                                                                                        |
              ->  Index Scan using player_performance_index on player_stats  (cost=0.42..6792.42 rows=80000 width=60) (actual time=0.139..123.298 rows=80000.00 loops=1)|
                    Index Searches: 1                                                                                                                                   |
                    Buffers: shared hit=79938 read=484                                                                                                                  |
Planning:                                                                                                                                                               |
  Buffers: shared hit=34 read=1                                                                                                                                         |
Planning Time: 0.858 ms                                                                                                                                                 |
Execution Time: 246.634 ms                                                                                                                                              |*/


/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////Using pg_stat_statements/////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


we are using pg_stat_statements to find the slowest queries

/*

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

*/

here is the output
/*rank|calls|mean_exec_time     |total_exec_time    |rows   |query                                                                                                                                                                             |
----+-----+-------------------+-------------------+-------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   1|    1|          39116.191|          39116.191|      0|DO $$¶DECLARE¶    i INT;¶BEGIN¶    FOR i IN 1..100 LOOP¶¶        -- === Your queries with PERFORM ===¶        ¶        PERFORM * FROM (¶            SELECT player_id, (kill       |
   2|  100| 205.50291800000002| 20550.291799999995|8000000|SELECT match_id, player_id, ¶                avg(damage_dealt) OVER (PARTITION BY match_id ORDER BY player_id) as avg_dmg¶        FROM player_stats ¶        ORDER BY match_id, p |
   3|  100| 155.50702900000002| 15550.702900000004| 500000|SELECT * FROM (¶            SELECT *,¶                   ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY match_id DESC) as rnk¶            FROM player_stats¶        ) Ranked  |
   4|  100| 14.891909999999998| 1489.1909999999993| 432400|SELECT tournament_id, team_a_id, ¶                round(((count(team_a_id) FILTER (WHERE team_a_id = winner_id))::numeric / ¶                       count(team_a_id)) * $1, $2) as|
   5|  100|  6.896159999999998|  689.6159999999998|  73100|SELECT tournament_id, team_a_id ¶        FROM matches¶        GROUP BY tournament_id, team_a_id ¶        HAVING count(*) > $1 ¶        ORDER BY tournament_id, team_a_id          |
   6|  100| 4.3036460000000005|           430.3646|    100|SELECT player_id, difference_in_elos, ¶                dense_rank() OVER (ORDER BY difference_in_elos DESC)¶        FROM (¶            SELECT player_id, elo_after - elo_before a |
   7|    1|             0.5629|             0.5629|     10|select * from pg_stat_statements                                                                                                                                                  |
   8|    1|0.38499999999999995|0.38499999999999995|      1|SELECT pg_stat_statements_reset()                                                                                                                                                 |
   9|  100|0.35526699999999994| 35.526699999999984|   1000|SELECT * FROM (¶            SELECT *, dense_rank() OVER (ORDER BY elo_rating DESC) ¶            FROM players¶        ) p ¶        LIMIT $1                                        |
  10|  100|0.11773999999999998| 11.774000000000006|   5000|SELECT player_id, sum(amount) as total_amount ¶        FROM prize_payouts ¶        GROUP BY player_id                                                                             |*/



