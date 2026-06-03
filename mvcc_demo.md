--first let us check the size of say players table

--we check the size using the following query
select pg_size_pretty(
pg_total_relation_size('players'))

/*
 * pg_size_pretty|
--------------+
160 kB        |
 * */

--let us update elo of each player by 100
update players set elo_rating=elo_rating+100

-let us again CHECK the SIZE OF the TABLE
/*pg_size_pretty|
--------------+
224 kB        |*/almost 1.5x the original SIZE


--let us run vacuum analyze on players 
What is VACUUM ANALYZE?
VACUUM ANALYZE is a maintenance command that does two important things at once:


Command              What it does                                                    Purpose
VACUUM              Cleans up dead rows (bloat) and reclaims SPACE                Performance & SPACE
ANALYZE            Updates table statistics (how many rows, data distribution)     Query planner accuracy

--the following command tells us about the last vacuum which may be either manual or automatic done by optmimizer
SELECT relname,
last_vacuum,
last_autovacuum,
vacuum_count,
autovacuum_count
FROM pg_stat_all_tables
WHERE relname = 'players';

/*relname|last_vacuum                  |last_autovacuum              |vacuum_count|autovacuum_count|
-------+-----------------------------+-----------------------------+------------+----------------+
players|2026-05-02 14:27:48.891 +0530|2026-05-02 14:17:04.490 +0530|           1|               1|*/



//let  us do an vacuum now AND see how the TABLE SIZE reduces
vacuum FULL players

--again running the command to check the table size 

pg_size_pretty|
--------------+
112 kB        |