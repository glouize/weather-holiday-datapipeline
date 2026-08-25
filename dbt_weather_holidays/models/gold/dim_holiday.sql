{{ config(materialized='table') }}

with unique_holidays as (
    select distinct
        holiday_name,
        local_name,
        country_code,
        is_global,
        holiday_type
    from {{ ref('stg_holidays') }}
),

ranked as (
    select
        dense_rank() over (order by country_code, holiday_name)::int as holiday_id,
        holiday_name,
        local_name,
        country_code,
        is_global,
        holiday_type
    from unique_holidays
),

no_holiday_default as (
    select
        0 as holiday_id,
        'No Holiday' as holiday_name,
        'No Holiday' as local_name,
        'ALL' as country_code,
        true as is_global,
        'None' as holiday_type
)

select * from no_holiday_default
union all
select * from ranked
order by holiday_id
