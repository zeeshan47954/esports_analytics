 select match_id,player_id,avg(damage_dealt)over(partition by match_id order by player_id) as avg_dmg
from player_stats order by match_id,player_id