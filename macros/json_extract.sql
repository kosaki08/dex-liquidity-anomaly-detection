{% macro json_str(path) %}
    {% if target.type == 'snowflake' %}
        {{ path.split(':')[0] }}:{{ path.split(':')[1:] | join(':') }}::STRING
    {% else %}
        json_extract({{ path.split(':')[0] }}, '$.{{ path.split(':')[1:] | join('.') }}')::TEXT
    {% endif %}
{% endmacro %}

{% macro json_float(path) %}
    {% if target.type == 'snowflake' %}
        try_to_double({{ json_str(path) }})
    {% else %}
        cast({{ json_str(path) }} as double)
    {% endif %}
{% endmacro %}

{% macro json_ts(path) %}
    {% if target.type == 'snowflake' %}
        to_timestamp(cast({{ json_str(path) }} as bigint))
    {% else %}
        to_timestamp(cast({{ json_str(path) }} as bigint))
    {% endif %}
{% endmacro %}