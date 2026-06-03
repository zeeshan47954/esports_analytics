select * from players

select pg_size_pretty(
pg_total_relation_size('players'))



update players set elo_rating=elo_rating+100

vacuum analyze players
SELECT relname,
last_vacuum,
last_autovacuum,
vacuum_count,
autovacuum_count
FROM pg_stat_all_tables
WHERE relname = 'players';

vacuum full players