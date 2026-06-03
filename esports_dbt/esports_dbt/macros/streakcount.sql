{% macro streakcount(column_name) %}
    {{ target.schema }}.streakcount({{ column_name }})
{% endmacro %}