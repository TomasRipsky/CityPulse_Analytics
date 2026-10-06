{#
    dev/prod: one dataset per layer (staging, intermediate, marts, audit), created by Terraform.
    ci: every layer prefixed with the per-run dataset name, e.g. ci_pr_12_123_marts.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set layer = (custom_schema_name or 'staging') | trim -%}
    {%- if target.name == 'ci' -%}
        {{ target.schema }}_{{ layer }}
    {%- else -%}
        {{ layer }}
    {%- endif -%}
{%- endmacro %}
