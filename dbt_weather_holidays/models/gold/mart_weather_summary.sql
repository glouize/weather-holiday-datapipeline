{{ config(materialized='table') }}

with fact as (
    select * from {{ ref('fact_daily_weather') }}
)

select
    city,
    country_code,
    case when is_holiday then 'Holiday' else 'Regular Day' end as day_type,
    count(*)::int as num_days,
    round(avg(temperature_2m_max), 2) as avg_max_temp,
    round(avg(temperature_2m_min), 2) as avg_min_temp,
    round(avg(precipitation_sum), 2) as avg_precipitation,
    round(sum(precipitation_sum), 2) as total_precipitation

from fact
group by city, country_code, day_type
order by city, day_type
