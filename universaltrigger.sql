select * from audit_log

CREATE OR REPLACE FUNCTION universal_audittrigger_function()
RETURNS TRIGGER
AS $$
DECLARE
    tablename TEXT;
    operation TEXT;
    old_data JSONB;
    new_data JSONB;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN 
        old_data := TO_JSONB(OLD);
    END IF;
    
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        new_data := TO_JSONB(NEW);
    END IF;
    
    INSERT INTO audit_log(table_name, operation, old_data, new_data, changed_at)
    VALUES (TG_TABLE_NAME, TG_OP, old_data, new_data, NOW());
    
    RETURN CASE 
        WHEN TG_OP = 'DELETE' THEN OLD 
        ELSE NEW 
    END;
END;
$$ LANGUAGE plpgsql;

-- Create triggers (note: need unique names for each table)
CREATE OR REPLACE TRIGGER universaltrigger_player
AFTER INSERT OR DELETE OR UPDATE ON players
FOR EACH ROW EXECUTE FUNCTION universal_audittrigger_function();

CREATE OR REPLACE TRIGGER universaltrigger_matches
AFTER INSERT OR DELETE OR UPDATE ON matches
FOR EACH ROW EXECUTE FUNCTION universal_audittrigger_function();

CREATE OR REPLACE TRIGGER universaltrigger_player_bans
AFTER INSERT OR DELETE OR UPDATE ON player_bans
FOR EACH ROW EXECUTE FUNCTION universal_audittrigger_function();


--below is the query to invoke the trigger
insert into players(id,username,country,date_of_birth,elo_rating,created_at)values(gen_random_uuid(),'player501','poland','2005-01-01',1281,
now());

select * from audit_log

