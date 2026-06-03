--stg_tournaments.sql

{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('esports', 'tournaments') }}
),

cleaned AS (
    SELECT
        id 
        ,name,game,round(prize_pool,2) as prize_pool,
        
        starts_at,status
        
    FROM source
   
)

SELECT * FROM cleaned

