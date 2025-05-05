{{ config(materialized='view') }}
{{ pool_hourly_base('pool_hourly_uniswap') }}
