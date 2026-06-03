 with cte as (

select player_id,elo_after-elo_before as difference_in_elos from elo_history
where changed_at >= now()-interval '30 days' and changed_at<now()
)

 select player_id,difference_in_elos,dense_rank()over(order  by difference_in_elos desc ) from cte limit 1