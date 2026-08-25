{{ config(materialized='table') }}

with date_spine as (
    select distinct date_key
    from {{ ref('stg_weather') }}
)

select
    date_key,
    extract(year from date_key)::int as year,
    extract(month from date_key)::int as month,
    extract(day from date_key)::int as day,
    extract(isodow from date_key)::int as day_of_week,
    case extract(isodow from date_key)
        when 1 then 'Monday'
        when 2 then 'Tuesday'
        when 3 then 'Wednesday'
        when 4 then 'Thursday'
        when 5 then 'Friday'
        when 6 then 'Saturday'
        when 7 then 'Sunday'
    end as day_name,
    case 
        when extract(isodow from date_key) in (6, 7) then true 
        else false 
    end as is_weekend,
    case 
        when extract(month from date_key) in (12, 1, 2) then 'Winter'
        when extract(month from date_key) in (3, 4, 5) then 'Spring'
        when extract(month from date_key) in (6, 7, 8) then 'Summer'
        else 'Autumn'
    end as season_temperate

from date_spine
order by date_key
