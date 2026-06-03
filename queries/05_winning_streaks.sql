 select tournament_id,team_a_id from matches
group by tournament_id,team_a_id  having count(*)>3 order by tournament_id ,team_a_id