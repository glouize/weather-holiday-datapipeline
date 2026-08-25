{{ config(materialized='table') }}

with fact as (
    select * from {{ ref('fact_daily_weather') }}
)

select
    month,
    case month
        when 1 then '01-Jan'
        when 2 then '02-Feb'
        when 3 then '03-Mar'
        when 4 then '04-Apr'
        when 5 then '05-May'
        when 6 then '06-Jun'
        when 7 then '07-Jul'
        when 8 then '08-Aug'
        when 9 then '09-Sep'
        when 10 then '10-Oct'
        when 11 then '11-Nov'
        when 12 then '12-Dec'
    end as month_name,
    city,
    country_code,
    case when is_holiday then 'Holiday' else 'Regular Day' end as day_type,
    round(avg(temperature_2m_max), 1) as avg_max_temp,
    round(avg(temperature_2m_min), 1) as avg_min_temp,
    round(avg(precipitation_sum), 1) as avg_precip

from fact
group by month, city, country_code, day_type
order by city, month, day_type
