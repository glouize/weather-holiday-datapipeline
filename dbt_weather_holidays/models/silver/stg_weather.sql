{{ config(materialized='view') }}

with source as (
    select * from {{ source('bronze', 'weather') }}
),

cleaned as (
    select
        -- Dimensions
        cast(time as date) as date_key,
        trim(city) as city,
        upper(trim(country_code)) as country_code,
        
        -- Measures with data validation
        cast(temperature_2m_max as decimal(5, 2)) as temperature_2m_max,
        cast(temperature_2m_min as decimal(5, 2)) as temperature_2m_min,
        case 
            when precipitation_sum < 0 then 0.00
            else cast(precipitation_sum as decimal(6, 2))
        end as precipitation_sum,
        
        -- Data Health / Quality Flags
        case 
            when temperature_2m_max >= temperature_2m_min then true 
            else false 
        end as is_valid_temp_range,
        
        -- Ingestion Metadata Lineage
        _source_system,
        _batch_id,
        _ingested_at

    from source
    where time is not null
      and city is not null
)

select distinct * from cleaned
