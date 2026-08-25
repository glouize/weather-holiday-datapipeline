{{ config(materialized='view') }}

with source as (
    select * from {{ source('bronze', 'holidays') }}
),

cleaned as (
    select
        cast(date as date) as date_key,
        trim(name) as holiday_name,
        coalesce(trim(localName), trim(name)) as local_name,
        upper(trim(countryCode)) as country_code,
        cast("global" as boolean) as is_global,
        cast(coalesce(types, 'Public') as varchar) as holiday_type,
        
        -- Ingestion Metadata Lineage
        _source_system,
        _batch_id,
        _ingested_at

    from source
    where date is not null
      and countryCode is not null
)

select distinct * from cleaned
