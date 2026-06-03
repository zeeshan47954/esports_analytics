--stg_teams.sql
{{ config(materialized='view') }}
with source as(select * from {{source('esports','teams')}}),
cleaned as (select id,name,region,round(prize_pool,2) as prize_pool from source )

select * from cleaned 

