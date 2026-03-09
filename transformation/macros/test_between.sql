{% macro test_between(model, column_name, min_value, max_value) %}
-- Test genérico reutilizable: verifica que una columna numérica
-- esté siempre dentro de un rango plausible.
-- Devuelve las filas que violan el rango — el test falla si hay alguna.

select *
from {{ model }}
where {{ column_name }} < {{ min_value }}
   or {{ column_name }} > {{ max_value }}

{% endmacro %}