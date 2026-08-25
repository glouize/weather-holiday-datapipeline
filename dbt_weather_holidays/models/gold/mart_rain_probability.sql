{{ config(materialized='table') }}

with fact as (
    select * from {{ ref('fact_daily_weather') }}
)

select
    city,
    country_code,
    case when is_holiday then 'Holiday' else 'Regular Day' end as day_type,
    count(*)::int as total_days,
    sum(case when precipitation_sum > 0 then 1 else 0 end)::int as rainy_days,
    sum(case when precipitation_sum > 5 then 1 else 0 end)::int as heavy_rain_days,
    round(100.0 * sum(case when precipitation_sum > 0 then 1 else 0 end) / count(*), 1) as pct_rainy,
    round(100.0 * sum(case when precipitation_sum > 5 then 1 else 0 end) / count(*), 1) as pct_heavy_rain

from fact
group by city, country_code, day_type
order by city, day_type
