{{config(materialized='table')}}

with source as(

SELECT 
    itmsa.tournament_id AS id,
    itmsa.team_a_id AS team_id,
    SUM(total_matches) AS total_matches,
    SUM(wins) AS total_wins,
    SUM(losses) AS total_losses,
    {{win_pct('wins','total_matches')}} as win_pct
   
FROM {{ref('int_team_match_summary_aggregated')}} as itmsa
GROUP BY itmsa.tournament_id, itmsa.team_a_id
),
source2 as (select * ,dense_rank() over(partition by id order by win_pct desc ) from source order by id,team_id),
source3 as(select * from source2 where dense_rank=1)
select t.id,t.name,s.team_id,t.prize_pool,total_matches,total_wins,total_losses,win_pct from source3 s  join tournaments t on s.id=t.id 

