--Here we will store  outputs when queries are run together with explain analyze which helps us to see
--how the optimizer actually executes the queries
--this will be used for comparison when we  use indexes
--which make queries run a lot faster

1.
explain analyze select * from
(select player_id,(kills+assists)::numeric/(deaths)::numeric as kda 
from player_stats)order by kda desc limit 10

QUERY PLAN                                                                                                                       |
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
              Buffers: shared hit=910                                                                                            |
              
              

2.
explain analyze select tournament_id,team_a_id
,round(((count(team_a_id )filter(where team_a_id =winner_id))::numeric/(count(team_a_id))::numeric)*100,2) as winrate_per_tournament 
from matches
group by tournament_id,team_a_id order by tournament_id ,team_a_id


QUERY PLAN                                                                                                               |
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




3.select match_id,player_id,avg(damage_dealt)over(partition by match_id order by player_id) as avg_dmg
from player_stats order by match_id,player_id


QUERY PLAN                                                                                                                      |
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
Execution Time: 883.517 ms                                                                                                      |


4.
with cte as (

select player_id,elo_after-elo_before as difference_in_elos from elo_history
where changed_at >= now()-interval '30 days' and changed_at<now()
)

select player_id,difference_in_elos,dense_rank()over(order  by difference_in_elos desc ) from cte limit 1


QUERY PLAN                                                                                                                          |
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
Execution Time: 182.836 ms                                                                                                          |


5.select tournament_id,team_a_id from matches
group by tournament_id,team_a_id  having count(*)>3 order by tournament_id ,team_a_id

QUERY PLAN                                                                                                               |
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
Execution Time: 20.900 ms                                                                                                |



6.select player_id,sum(amount) as total_amount from prize_payouts pp group by player_id 

QUERY PLAN                                                                                                            |
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


7.select *,dense_rank()over(order by elo_rating desc) from players p limit 10
QUERY PLAN                                                                                                                  |
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


8.
WITH RankedStats AS (
    SELECT *,
           ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY match_id DESC) as rnk
    FROM player_stats
)
SELECT * FROM RankedStats 
WHERE rnk <= 10
ORDER BY player_id, match_id ASC;

QUERY PLAN                                                                                                                            |
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
Execution Time: 308.434 ms                                                                                                            |


