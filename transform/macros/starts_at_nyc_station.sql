{#- A trip that starts at a New York City station: a known station, positioned inside the city.
    Citi Bike's files also hold a few trips from demo stations elsewhere ("LA Metro Demo 1–3",
    Los Angeles): they count in every total, but they are not on the station map. -#}
{% macro starts_at_nyc_station() -%}
start_station_id is not null and start_lat between 40.4 and 41.0 and start_lng between -74.3 and -73.6
{%- endmacro %}
