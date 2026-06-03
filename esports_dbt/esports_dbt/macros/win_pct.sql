{% macro win_pct(wins,total_matches) %}

ROUND(
        ((SUM(wins)::numeric / NULLIF(SUM(total_matches), 0)::numeric) 
         * (random() * 30 + 1))::numeric, 
    2)
    
{% endmacro %}    