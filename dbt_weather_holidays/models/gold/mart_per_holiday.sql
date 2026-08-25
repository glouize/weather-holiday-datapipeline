{{ config(materialized='table') }}

with fact as (
    select * from {{ ref('fact_daily_weather') }}
    where is_holiday = true
)

select
    city,
    country_code,
    holiday_name,
    count(*)::int as occurrences,
    round(avg(temperature_2m_max), 1) as avg_max_temp,
    round(avg(temperature_2m_min), 1) as avg_min_temp,
    round(avg(precipitation_sum), 1) as avg_precip,
    round(max(temperature_2m_max), 1) as record_high,
    round(min(temperature_2m_min), 1) as record_low

from fact
group by city, country_code, holiday_name
order by city, avg_max_temp desc
