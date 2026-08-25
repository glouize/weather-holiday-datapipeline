{{ config(materialized='table') }}

with weather as (
    select * from {{ ref('stg_weather') }}
),

holidays as (
    select * from {{ ref('stg_holidays') }}
),

enriched as (
    select
        w.date_key,
        w.city,
        w.country_code,
        w.temperature_2m_max,
        w.temperature_2m_min,
        w.precipitation_sum,
        w.is_valid_temp_range,
        
        -- Calendar attributes
        extract(year from w.date_key) as year,
        extract(month from w.date_key) as month,
        extract(day from w.date_key) as day,
        extract(isodow from w.date_key) as day_of_week,
        case when extract(isodow from w.date_key) in (6, 7) then true else false end as is_weekend,
        
        -- Holiday enrichment
        case when h.holiday_name is not null then true else false end as is_holiday,
        coalesce(h.holiday_name, 'Not a Holiday') as holiday_name,
        h.local_name,
        h.holiday_type,
        coalesce(h.is_global, false) as is_global_holiday,
        
        -- Metadata Lineage
        w._batch_id,
        w._ingested_at

    from weather w
    left join holidays h
        on w.date_key = h.date_key
        and w.country_code = h.country_code
)

select * from enriched
