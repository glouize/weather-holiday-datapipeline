# Weather & Holiday Data Platform: Entity-Relationship Diagram (ERD) & Data Dictionary
**Architecture**: Medallion Architecture (Bronze $\rightarrow$ Silver $\rightarrow$ Gold)  

---

## 1. Medallion Entity-Relationship Diagram

```mermaid
erDiagram
    %% ==========================================
    %% 1. BRONZE LAYER (RAW INGESTION)
    %% ==========================================
    bronze_weather {
        varchar city
        varchar country_code
        timestamp time
        double temperature_2m_max
        double temperature_2m_min
        double precipitation_sum
        varchar _source_system
        varchar _batch_id
        timestamp _ingested_at
    }

    bronze_holidays {
        date date
        varchar localName
        varchar name
        varchar countryCode
        boolean global
        varchar types
        varchar _source_system
        varchar _batch_id
        timestamp _ingested_at
    }

    %% ==========================================
    %% 2. SILVER LAYER (CLEANED & ENRICHED)
    %% ==========================================
    silver_stg_weather {
        date date_key
        varchar city
        varchar country_code
        decimal temperature_2m_max
        decimal temperature_2m_min
        decimal precipitation_sum
        boolean is_valid_temp_range
    }

    silver_stg_holidays {
        date date_key
        varchar holiday_name
        varchar local_name
        varchar country_code
        boolean is_global
        varchar holiday_type
    }

    silver_weather_holidays {
        date date_key
        varchar city
        varchar country_code
        decimal temperature_2m_max
        decimal temperature_2m_min
        decimal precipitation_sum
        boolean is_holiday
        varchar holiday_name
        boolean is_weekend
        int year
        int month
    }

    %% ==========================================
    %% 3. GOLD LAYER (STAR SCHEMA & MARTS)
    %% ==========================================
    gold_dim_date {
        date date_key PK
        int year
        int month
        int day
        int day_of_week
        varchar day_name
        boolean is_weekend
        varchar season_temperate
    }

    gold_dim_location {
        int location_id PK
        varchar city_name
        varchar country_code
        varchar timezone
        varchar climate_zone
    }

    gold_dim_holiday {
        int holiday_id PK
        varchar holiday_name
        varchar local_name
        varchar country_code
        boolean is_global
        varchar holiday_type
    }

    gold_fact_daily_weather {
        bigint fact_id PK
        date date_key FK
        int location_id FK
        int holiday_id FK
        varchar city
        varchar country_code
        decimal temperature_2m_max
        decimal temperature_2m_min
        decimal precipitation_sum
        boolean is_holiday
        varchar holiday_name
        boolean is_weekend
        int year
        int month
    }

    %% ==========================================
    %% 4. GOLD BUSINESS MARTS
    %% ==========================================
    gold_mart_weather_summary {
        varchar city
        varchar country_code
        varchar day_type
        int num_days
        double avg_max_temp
        double avg_min_temp
        double avg_precipitation
        double total_precipitation
    }

    gold_mart_per_holiday {
        varchar city
        varchar country_code
        varchar holiday_name
        int occurrences
        double avg_max_temp
        double avg_min_temp
        double avg_precip
        double record_high
        double record_low
    }

    gold_mart_yearly_climate_trends {
        int year
        varchar city
        varchar country_code
        double avg_max_temp
        double avg_min_temp
        double total_precipitation
        int days_recorded
    }

    gold_mart_monthly_seasonality {
        int month
        varchar month_name
        varchar city
        varchar country_code
        varchar day_type
        double avg_max_temp
        double avg_min_temp
        double avg_precip
    }

    gold_mart_rain_probability {
        varchar city
        varchar country_code
        varchar day_type
        int total_days
        int rainy_days
        int heavy_rain_days
        double pct_rainy
        double pct_heavy_rain
    }

    gold_mart_extreme_weather_events {
        date date_key
        varchar city
        varchar country_code
        varchar holiday_name
        decimal precipitation_mm
        decimal max_temp_c
        decimal min_temp_c
        varchar rain_category
    }

    %% ==========================================
    %% LINEAGE & RELATIONSHIPS
    %% ==========================================
    bronze_weather ||--o{ silver_stg_weather : "Transforms"
    bronze_holidays ||--o{ silver_stg_holidays : "Transforms"
    silver_stg_weather ||--o{ silver_weather_holidays : "Joins"
    silver_stg_holidays ||--o{ silver_weather_holidays : "Joins"

    silver_weather_holidays ||--o{ gold_dim_date : "Populates"
    silver_weather_holidays ||--o{ gold_dim_location : "Populates"
    silver_stg_holidays ||--o{ gold_dim_holiday : "Populates"

    gold_dim_date ||--o{ gold_fact_daily_weather : "date_key (1:N)"
    gold_dim_location ||--o{ gold_fact_daily_weather : "location_id (1:N)"
    gold_dim_holiday ||--o{ gold_fact_daily_weather : "holiday_id (1:N, default 0)"

    gold_fact_daily_weather ||--o{ gold_mart_weather_summary : "Aggregates"
    gold_fact_daily_weather ||--o{ gold_mart_per_holiday : "Aggregates"
    gold_fact_daily_weather ||--o{ gold_mart_yearly_climate_trends : "Aggregates"
    gold_fact_daily_weather ||--o{ gold_mart_monthly_seasonality : "Aggregates"
    gold_fact_daily_weather ||--o{ gold_mart_rain_probability : "Aggregates"
    gold_fact_daily_weather ||--o{ gold_mart_extreme_weather_events : "Filters"
```

---

## 2. Medallion Data Dictionary

### 2.1 🥉 Bronze Layer (`bronze`)
*Raw append-only ingestion layer with audit metadata lineage.*

| Table | Column | Type | Description |
|---|---|---|---|
| `bronze.weather` | `city` | `VARCHAR` | Standardized city name |
| | `country_code` | `VARCHAR(2)` | ISO-3166-1 alpha-2 country code |
| | `time` | `TIMESTAMP` | Raw observation date |
| | `temperature_2m_max` | `DOUBLE` | Daily maximum temperature (°C) |
| | `temperature_2m_min` | `DOUBLE` | Daily minimum temperature (°C) |
| | `precipitation_sum` | `DOUBLE` | Total daily precipitation (mm) |
| | `_source_system` | `VARCHAR` | Source identifier (`open-meteo-archive`) |
| | `_batch_id` | `VARCHAR` | Execution batch timestamp |
| | `_ingested_at` | `TIMESTAMP` | UTC ingestion timestamp |
| `bronze.holidays` | `date` | `DATE` | Holiday date |
| | `localName` | `VARCHAR` | Localized native holiday name |
| | `name` | `VARCHAR` | English holiday name |
| | `countryCode` | `VARCHAR(2)` | ISO country code |
| | `global` | `BOOLEAN` | Nationwide observation flag |
| | `types` | `VARCHAR` | Category classification |
| | `_source_system` | `VARCHAR` | Source identifier (`nager-date-api`) |
| | `_batch_id` | `VARCHAR` | Execution batch timestamp |
| | `_ingested_at` | `TIMESTAMP` | UTC ingestion timestamp |

---

### 2.2 🥈 Silver Layer (`main_silver`)
*Cleaned, conformed, and enriched models.*

| Model | Column | Type | Key | Description |
|---|---|---|---|---|
| `silver_weather_holidays` | `date_key` | `DATE` | FK | Calendar observation date |
| | `city` | `VARCHAR` | - | Monitored city name |
| | `country_code` | `VARCHAR(2)` | - | Country code (`GB`, `PH`) |
| | `temperature_2m_max` | `DECIMAL(5,2)`| - | Daily max temperature |
| | `temperature_2m_min` | `DECIMAL(5,2)`| - | Daily min temperature |
| | `precipitation_sum` | `DECIMAL(6,2)`| - | Daily precipitation sum |
| | `is_valid_temp_range` | `BOOLEAN` | - | Quality flag (`max >= min`) |
| | `is_holiday` | `BOOLEAN` | - | True if day is an official holiday |
| | `holiday_name` | `VARCHAR` | - | Name of holiday or 'Not a Holiday' |
| | `is_weekend` | `BOOLEAN` | - | True if Saturday or Sunday |
| | `year` / `month` / `day`| `INTEGER` | - | Extracted calendar components |

---

### 2.3 🥇 Gold Layer (`main_gold`)
*Dimensional star schema and consumption-ready analytical marts.*

#### Star Schema Tables:
* **`gold.dim_date`** (PK: `date_key`): 1,827 rows. Day name, day of week, weekend indicator, temperate season.
* **`gold.dim_location`** (PK: `location_id`): 2 rows (London=1, Manila=2). Timezone, climate classification.
* **`gold.dim_holiday`** (PK: `holiday_id`): 38 rows (including surrogate `0` for `"No Holiday"`).
* **`gold.fact_daily_weather`** (PK: `fact_id`, FKs: `date_key`, `location_id`, `holiday_id`): 3,654 rows.

#### Business Serving Marts:
* **`mart_weather_summary`**: High-level KPI aggregations by city and day type.
* **`mart_per_holiday`**: Individual holiday performance, occurrences, record highs/lows.
* **`mart_yearly_climate_trends`**: 5-year longitudinal trend metrics.
* **`mart_monthly_seasonality`**: 12-month calendar seasonal comparison.
* **`mart_rain_probability`**: Rain (>0mm) and heavy rain (>5mm) percentage likelihoods.
* **`mart_extreme_weather_events`**: Leaderboard of top single-day precipitation events on holidays.
