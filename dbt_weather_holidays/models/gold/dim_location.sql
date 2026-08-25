{{ config(materialized='table') }}

with locations as (
    select distinct
        city,
        country_code
    from {{ ref('stg_weather') }}
)

select
    dense_rank() over (order by city, country_code)::int as location_id,
    city as city_name,
    country_code,
    case 
        when country_code = 'GB' then 'Europe/London'
        when country_code = 'PH' then 'Asia/Manila'
        else 'UTC'
    end as timezone,
    case 
        when country_code = 'GB' then 'Temperate Oceanic'
        when country_code = 'PH' then 'Tropical Monsoon'
        else 'Unknown'
    end as climate_zone

from locations
order by location_id
