{{config(materialized='view')}}

with t1 as (
select tournament_id,team_a_id,count(*) as total_matches,count(team_a_id)filter(where team_a_id=winner_id)
as wins,count(team_a_id)filter(where team_a_id<>winner_id)as losses
from {{ref('stg_matches')}} as matches join {{ref('stg_tournaments')}} as tournaments on matches.tournament_id=tournaments.id group by tournament_id,team_a_id order by tournament_id ,team_a_id
)
,
t2 AS (
    SELECT 
        tournament_id, 
        team_a_id, 
         
        winner_id,
        CASE WHEN team_a_id = winner_id THEN '1' ELSE '0' END AS streak
   from {{ref('stg_matches')}} as matches join {{ref('stg_tournaments')}} as tournaments on matches.tournament_id=tournaments.id order by tournament_id ,team_a_id
    
),
t3 AS (
    SELECT 
        *,
        string_agg(streak, ', ') OVER (
            PARTITION BY tournament_id, team_a_id
                      -- ← You must have some ordering column
            
        ) AS streak_history
    FROM t2 order by tournament_id asc,team_a_id asc
),
t4 as (select distinct tournament_id,team_a_id,streak_history from t3),
t5 as (select tournament_id,team_a_id,{{streakcount('streak_history')}} as current_streak from t3 order by tournament_id asc,team_a_id desc)

select distinct t5.tournament_id,t5.team_a_id,total_matches,wins,losses,current_streak from t5 join t1 
on t5.tournament_id=t1.tournament_id and t5.team_a_id=t1.team_a_id order by t5.tournament_id,t5.team_a_id


