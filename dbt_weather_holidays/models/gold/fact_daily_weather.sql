{{ config(materialized='table') }}

with enriched as (
    select * from {{ ref('silver_weather_holidays') }}
),

locations as (
    select * from {{ ref('dim_location') }}
),

holidays as (
    select * from {{ ref('dim_holiday') }}
)

select
    row_number() over (order by e.date_key, e.city)::bigint as fact_id,
    e.date_key,
    l.location_id,
    coalesce(h.holiday_id, 0) as holiday_id,
    e.city,
    e.country_code,
    e.temperature_2m_max,
    e.temperature_2m_min,
    e.precipitation_sum,
    e.is_holiday,
    e.holiday_name,
    e.is_weekend,
    e.year,
    e.month

from enriched e
inner join locations l
    on e.city = l.city_name
    and e.country_code = l.country_code
left join holidays h
    on e.holiday_name = h.holiday_name
    and e.country_code = h.country_code
order by fact_id
