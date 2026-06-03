{% macro create_streakcount_function() %}

CREATE OR REPLACE FUNCTION {{ target.schema }}.streakcount(a text)
RETURNS int
AS $$
DECLARE
    arr int[];
    current_streak int := 0;
    val int;
BEGIN
    IF a IS NULL OR trim(a) = '' THEN
        RETURN 0;
    END IF;

    arr := regexp_split_to_array(trim(a), '\s*,\s*')::int[];

    FOREACH val IN ARRAY arr
    LOOP
        IF val = 1 THEN
            current_streak := current_streak + 1;
        ELSE
            current_streak := 0;
        END IF;
    END LOOP;

    RETURN current_streak;
END;
$$ LANGUAGE plpgsql;

{% endmacro %}