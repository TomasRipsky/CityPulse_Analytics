{#- Fails for every row whose value is outside [min_value, max_value]; nulls are ignored. -#}
{% test in_range(model, column_name, min_value, max_value) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}
{% endtest %}
