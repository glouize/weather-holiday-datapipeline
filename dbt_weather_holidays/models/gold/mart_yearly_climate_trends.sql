{{ config(materialized='table') }}

with fact as (
    select * from {{ ref('fact_daily_weather') }}
)

select
    year,
    city,
    country_code,
    round(avg(temperature_2m_max), 2) as avg_max_temp,
    round(avg(temperature_2m_min), 2) as avg_min_temp,
    round(sum(precipitation_sum), 1) as total_precipitation,
    count(*)::int as days_recorded

from fact
group by year, city, country_code
order by city, year
