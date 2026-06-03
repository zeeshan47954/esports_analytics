-- 1. Expression index on KDA calculation
--we have added a line to indicate that changes have been made
--again added some more things to tell about git pull
1.
explain analyze select * from
(select player_id,(kills+assists)::numeric/(deaths)::numeric as kda 
from player_stats)order by kda desc limit 10

select * from players
CREATE INDEX idx_kda_computed ON player_stats 
  (( (kills+assists)::numeric / deaths::numeric ));

/* OVERHEAD ADDED:
 * - Storage overhead: Each index row stores the pre-computed KDA value (8 bytes for numeric) + tuple pointer (~6 bytes)
 * - Write overhead: On every INSERT/UPDATE of kills, assists, or deaths, PostgreSQL must re-compute and store the KDA value
 * - UPDATE overhead: Even if other columns change, this index is unaffected, but if any of the three referenced columns change, index must update
 * - Maintenance overhead: AUTO VACUUM must scan this index periodically; index bloat possible with frequent updates to these columns
 * - Memory overhead: Index pages compete with table pages in shared_buffers cache
 */

-- 2. Composite index on (tournament_id, team_a_id)
explain analyze select tournament_id,team_a_id
,round(((count(team_a_id )filter(where team_a_id =winner_id))::numeric/(count(team_a_id))::numeric)*100,2) as winrate_per_tournament 
from matches
group by tournament_id,team_a_id order by tournament_id ,team_a_id

CREATE INDEX win_rate_index ON matches(tournament_id, team_a_id);

/* OVERHEAD ADDED:
 * - Storage: Each entry stores two integers + tuple pointer (approx 16-20 bytes per row)
 * - Write overhead: Every INSERT/UPDATE to tournament_id or team_a_id requires index maintenance
 * - Limited benefit: As noted, GROUP BY with aggregates often triggers sequential scans anyway
 * - Partial waste: If matches table has high churn (tournaments ending/starting), many index entries become "dead" before VACUUM cleans them
 * - Sorting overhead: Index maintains ordering on (tournament_id, team_a_id), which adds CPU cost on writes
 */

-- 3. Composite index on (match_id, player_id)
3.select match_id,player_id,avg(damage_dealt)over(partition by match_id order by player_id) as avg_dmg
from player_stats order by match_id,player_id
CREATE INDEX avg_damage_index ON player_stats(match_id, player_id);

/* OVERHEAD ADDED:
 * - Storage: Two integers + tuple pointer (~20 bytes per row). For large player_stats tables, this can be significant
 * - Write overhead: Every new player statistic entry (common in logging scenarios) must update this index
 * - Duplication: player_id and match_id already exist in the table; this creates a full copy for indexing
 * - Window function limitation: The index helps ORDER BY but cannot pre-compute the windowed AVG() - PostgreSQL still computes aggregates on the fly
 * - Maintenance: If player_stats is insert-heavy (common for game stats), this index will bloat quickly and require frequent vacuuming
 */

-- 4. Composite index on (changed_at, elo_before, elo_after)
explain analyze with cte as (

select player_id,elo_after-elo_before as difference_in_elos from elo_history
where changed_at >= now()-interval '30 days' and changed_at<now()
)

select player_id,difference_in_elos,dense_rank()over(order  by difference_in_elos desc ) from cte limit 1

CREATE INDEX improved_elo_index ON elo_history(changed_at, elo_before, elo_after);

/* OVERHEAD ADDED - SIGNIFICANT:
 * - Large storage: Three numeric columns (each up to 8 bytes) + tuple pointer ≈ 30+ bytes per row
 * - Most expensive index: Every elo change (which happens every match per player) triggers update to all three columns
 * - Write amplification: For an elo_history table that grows with every competitive match, this index adds 3x write amplification
 * - Query specificity: Only helps the exact query filtering on changed_at + selecting elo_before/elo_after
 * - Cache pressure: Large index reduces effective cache size for hot data
 * - Recommended alternative: Consider partial index if only recent data queried (changed_at > now() - interval '30 days')
 */

-- 5. No new index (reusing win_rate_index from #2)
explain analyze select tournament_id,team_a_id from matches
group by tournament_id,team_a_id  having count(*)>3 order by tournament_id ,team_a_id
-- Index was already created previously

/* OVERHEAD ADDED: None (reusing existing index)
 * Note: This query uses GROUP BY with HAVING COUNT(*)>3 - index may help grouping but COUNT(*) still requires visibility checks
 */

-- 6. Single-column index on prize_payouts(player_id)
CREATE INDEX prize_earnings ON prize_payouts(player_id);
explain analyze select player_id,sum(amount) as total_amount from prize_payouts pp group by player_id

/* OVERHEAD ADDED:
 * - Storage: Single integer + tuple pointer (~12 bytes per prize payout record)
 * - Write overhead: Each INSERT into prize_payouts (when players earn prizes) updates this index
 * - JOIN benefit: Helps if you later JOIN with players table; for standalone SUM() GROUP BY, PostgreSQL might still seq scan if table is small
 * - Moderate overhead: Prize payouts are typically less frequent than player_stats updates, making this index relatively cheap
 */

-- 7. No index (query with LIMIT and window function)
explain analyze select *,dense_rank()over(order by elo_rating desc) from players p limit 10
-- Indexing won't help

/* OVERHEAD ADDED: None
 * Reason: ORDER BY elo_rating DESC LIMIT 10 requires scanning all rows to find top 10 unless index exists on elo_rating
 * But as noted, indexing won't help here - actually an index on elo_rating DESC would help tremendously!
 * Correction: An index on (elo_rating DESC) would allow index-only scan for top 10 - but original comment said "won't help at all"
 */

-- 8. Composite index on (player_id, match_id ASC)
explain analyze WITH RankedStats AS (
    SELECT *,
           ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY match_id DESC) as rnk
    FROM player_stats
)
SELECT * FROM RankedStats 
WHERE rnk <= 10
ORDER BY player_id, match_id ASC;
CREATE INDEX player_performance_index ON player_stats(player_id, match_id ASC);

/* OVERHEAD ADDED:
 * - Storage: Two integers + tuple pointer (~20 bytes per row in player_stats)
 * - Write overhead: Every new performance record (likely very frequent) updates this index
 * - Most active index: player_stats is typically the most frequently written table in gaming databases
 * - Maintenance burden: Requires frequent VACUUM and ANALYZE to prevent bloat
 * - Query benefit: ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY match_id DESC) with WHERE rnk <= 10
 *   → The ASC index helps but PostgreSQL must still scan from end for DESC ordering
 *   → Better alternative: CREATE INDEX ON player_stats(player_id, match_id DESC) for this specific query
 * - Memory overhead: Index pages compete with frequently-accessed table pages in cache
 */
