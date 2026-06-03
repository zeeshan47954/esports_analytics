
{{config(materialized='table')}}

with source as(

 select team_a_id as team_id,sum(total_matches) as total_matches,sum(wins)as total_wins,
sum(losses) as total_losses from {{ref('int_team_match_summary_aggregated')}} as itmsa  group by itmsa.team_a_id 
)
,
source2 as (select *,dense_rank()over(order by total_wins desc) as rank from source)

select * from source2 order by rank

