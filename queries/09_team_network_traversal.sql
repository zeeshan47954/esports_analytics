--we are going to traverse a tree to check which teams are connected 

select distinct team_a_id,team_b_id from matches order by team_a_id,team_b_id 
WITH RECURSIVE cte AS (
    SELECT distinct
        team_a_id::text AS teamname,
        team_b_id::text AS direction,
        1 AS level,
        team_a_id::text || '->' || team_b_id::text AS full_path
    FROM matches

    UNION ALL

    SELECT 
        m.team_a_id::text,
        c.direction || '->' || m.team_b_id::text,
        c.level + 1,
        c.full_path || '->' || m.team_b_id::text
    FROM matches m
    JOIN cte c ON c.direction = m.team_a_id::text
    WHERE c.level < 8                    -- Reduced for testing
      AND c.full_path NOT LIKE '%->' || m.team_b_id::text || '%'
)
SELECT teamname, direction, level, full_path
FROM cte
ORDER BY teamname, level
;          -- ← Important: Don't fetch everything yet


/*
 * AND c.full_path NOT LIKE '%->' || m.team_b_id::text || '%'
 * why we used this
 * Imagine this small situation:
There are only 3 teams: A, B, C
And they have played matches like this:

A vs B
B vs C
C vs A

So the matches table has these rows (among others):

A → B
B → C
C → A


What your current recursive CTE does:
Level 1 (Anchor):

A → B     (teamname=A, direction=B, level=1)

Level 2:
From direction = 'B', it finds matches starting with B → C
→ So it creates:
A → B → C     (teamname=A, direction=A->B->C, level=2)
Level 3:
From direction = 'C', it finds matches starting with C → A
→ It creates:
A → B → C → A     (teamname=A, direction=A->B->C->A, level=3)
Level 4:
From direction = 'A', it finds matches starting with A → B
→ It creates:
A → B → C → A → B     (level=4)
Level 5:
→ A → B → C → A → B → C     (level=5)
Level 6:
→ A → B → C → A → B → C → A
And it will keep going forever...
A→B→C→A→B→C→A→B→C→A→B→C... and so on.
 * 
 * */






