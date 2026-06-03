
-- the trigger is going to update the matches won and player whenever a insert happens in the matches table

CREATE OR REPLACE FUNCTION update_team_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Increment matches_played for both teams
    UPDATE teams 
    SET matches_played = matches_played + 1
    WHERE id IN (NEW.team_a_id, NEW.team_b_id);

    -- Increment matches_won for the winner
    UPDATE teams 
    SET matches_won = matches_won + 1
    WHERE id = NEW.winner_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- Create the trigger
CREATE OR REPLACE TRIGGER team_stats_trigger
AFTER INSERT ON matches
FOR EACH ROW
EXECUTE FUNCTION update_team_stats();

insert into matches(id,tournament_id,team_a_id,team_b_id,winner_id,played_at) values(
gen_random_uuid(),'c271a6b8-b649-42c1-b134-22856bf28226'::uuid,'99f273eb-148e-4fdc-bf4f-6e29cc6754aa'::uuid,'6a454829-906b-4658-a3c3-a5e55dba7a0d'::uuid
,'99f273eb-148e-4fdc-bf4f-6e29cc6754aa'::uuid,'2026-05-01 08:41:43.267 +0530'
)


drop trigger team_stats_trigger on matches;
