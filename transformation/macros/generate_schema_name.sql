-- generate_schema_name.sql
-- Por defecto DBT concatena el dataset del profiles.yml con el +schema
-- definido en dbt_project.yml, produciendo nombres como:
-- citypulse_marts_citypulse_staging
--
-- Esta macro sobreescribe ese comportamiento para usar el +schema
-- directamente como nombre del dataset, sin concatenación.

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
