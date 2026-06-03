--stg_players.sql
{{config(materialized='view')}}
with source as (select * from {{source('esports','players')}}),
cleaned as (select id,username,country,date_of_birth,elo_rating,created_at from source  )
select * from cleaned 

