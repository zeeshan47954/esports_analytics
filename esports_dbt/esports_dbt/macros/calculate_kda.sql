{% macro calculate_kda(kills,assists,deaths) %}

round(
({{ kills }} + {{ assists }})::NUMERIC 
        / NULLIF({{ deaths }}, 0),
        2
)

{% endmacro %}






