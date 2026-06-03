{{config(materialized='table')}}



select * from  {{ref('tournament_standings')}} 