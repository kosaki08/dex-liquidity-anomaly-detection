{% macro json_str(path) %}
    /* DuckDB: json_extract → TEXT */
    json_extract({{ path.split(':')[0] }}, '$.{{ path.split(':')[1] }}')::TEXT
{% endmacro %}

{% macro json_float(path) %}
    cast({{ json_str(path) }} as DOUBLE)
{% endmacro %}

{% macro json_ts(path) %}
    -- The Graph の Unix 秒 → TIMESTAMP(UTC)
    to_timestamp(cast({{ json_str(path) }} as BIGINT))
{% endmacro %}
