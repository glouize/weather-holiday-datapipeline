{{ config(materialized='table') }}

with fact as (
    select * from {{ ref('fact_daily_weather') }}
    where is_holiday = true
)

select
    date_key,
    city,
    country_code,
    holiday_name,
    precipitation_sum as precipitation_mm,
    temperature_2m_max as max_temp_c,
    temperature_2m_min as min_temp_c,
    case 
        when precipitation_sum >= 20 then 'Extreme Downpour (>20mm)'
        when precipitation_sum >= 10 then 'Heavy Rain (10-20mm)'
        when precipitation_sum > 0 then 'Light/Moderate Rain'
        else 'Dry'
    end as rain_category

from fact
order by precipitation_sum desc
