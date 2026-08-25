# Weather & Public Holiday Intelligence Platform
## System Architecture & Technical Design Document (HLD & DLD)

---

## 1. High-Level Design (HLD)

### 1.1 Architectural Pattern: Medallion Architecture
The platform implements a multi-tier **Medallion Architecture (Bronze $\rightarrow$ Silver $\rightarrow$ Gold)** to guarantee data quality, lineage traceability, and high-performance analytical querying across multi-city data (London & Manila, 2021–2026).

```mermaid
flowchart TD
    subgraph DataSources["1. External API Sources"]
        A1["🌤️ Open-Meteo Historical Archive API\n(Daily Temp Max/Min, Precip)"]
        A2["📅 Nager.Date Public Holiday API\n(National & Regional Holidays)"]
    end

    subgraph BronzeLayer["2. 🥉 Bronze Layer (Raw Storage)"]
        B1[("bronze.weather (3,654 rows)\n+ _ingested_at, _source_system, _batch_id")]
        B2[("bronze.holidays (193 rows)\n+ _ingested_at, _source_system, _batch_id")]
    end

    subgraph SilverLayer["3. 🥈 Silver Layer (Cleaned & Conformed)"]
        S1["silver.stg_weather (View)\n• ISO date casting, deduplication, range validation"]
        S2["silver.stg_holidays (View)\n• Standardized snake_case, boolean typing"]
        S3[("silver.silver_weather_holidays (Table)\n• Unified daily observation grain\n• Holiday flags & calendar attributes")]
    end

    subgraph GoldLayer["4. 🥇 Gold Layer (Star Schema & Business Marts)"]
        G_DIM["Dimensional Star Schema:\n• gold.dim_date (1,827 rows)\n• gold.dim_location (2 rows)\n• gold.dim_holiday (38 rows)"]
        G_FACT[("gold.fact_daily_weather (Table, 3,654 rows)\n• PK: fact_id, FKs: date_key, location_id, holiday_id")]
        G_MARTS["Aggregated Business Marts:\n• gold.mart_weather_summary (4 rows)\n• gold.mart_per_holiday (37 rows)\n• gold.mart_yearly_climate_trends (12 rows)\n• gold.mart_monthly_seasonality (44 rows)\n• gold.mart_rain_probability (4 rows)\n• gold.mart_extreme_weather_events (162 rows)"]
    end

    subgraph ServingLayer["5. Serving Bridge & BI Dashboards"]
        P1["mysql_server.py (port 3306)\n• MySQL Wire Protocol\n• TLS/SSL Encryption\n• In-Memory DuckDB Bridge"]
        BI1["📊 Streamlit Web App (port 8501)\n• Dark Mode UI\n• City Switcher (London/Manila)\n• 7 Narrative Insight Modules"]
        BI2["📈 Grafana BI Platform (port 3000)\n• 🇬🇧 Dedicated London Dashboard\n• 🇵🇭 Dedicated Manila Dashboard\n• 🌐 Comparative Overview Dashboard"]
    end

    A1 -->|Python HTTP GET with Exponential Backoff| B1
    A2 -->|Python HTTP GET with Throttling| B2
    B1 --> S1
    B2 --> S2
    S1 --> S3
    S2 --> S3
    S3 --> G_DIM
    S3 --> G_FACT
    G_FACT --> G_MARTS
    G_MARTS -->|Direct In-Process SQL| BI1
    G_MARTS -->|DuckDB In-Memory OLAP| P1
    P1 -->|MySQL Protocol| BI2
```

---

### 1.2 Data Lifecycle Management (DLM) Flow

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Operator (Manual / Scheduled)
    participant EL as extract_load.py
    participant Bronze as DuckDB (Bronze Schema)
    participant dbt as dbt Core Engine
    participant Silver as DuckDB (Silver Schema)
    participant Gold as DuckDB (Gold Schema)
    participant BI as Streamlit & Grafana

    Operator->>EL: Run `python pipeline/extract_load.py` (manual or scheduled)
    EL->>EL: Fetch Open-Meteo & Nager.Date with retry + exponential backoff
    EL->>Bronze: Write raw JSON into bronze.weather & bronze.holidays with audit tags
    Note over EL,Bronze: Logs print to console (stdout). No external monitoring system connected.
    Operator->>dbt: Run `dbt run --profiles-dir .` (separate manual step)
    dbt->>Silver: Compile stg_weather, stg_holidays & silver_weather_holidays
    dbt->>Gold: Build Star Schema (dim_date, dim_location, dim_holiday, fact_daily_weather)
    dbt->>Gold: Materialize aggregated Business Marts (mart_*)
    Operator->>dbt: Run `dbt test --profiles-dir .` (separate manual step)
    dbt->>dbt: Execute 27 data quality tests (unique, not_null, FK relationships)
    Note over dbt: On failure: dbt exits non-zero and prints to console.<br/>No automated alert or pipeline gate is wired up.
    Operator->>BI: Start `serving/mysql_server.py` and `serving/dashboard.py`
    Gold->>BI: Serve OLAP queries via in-memory DuckDB for interactive dashboards
```

---

## 2. Detailed Low-Level Design (DLD)

### 2.1 Medallion Layer Specifications

#### 🥉 Bronze Layer (`bronze.*`)
* **Purpose**: Raw, unaltered data landing zone preserving source API fidelity.
* **Tables**:
  - `bronze.weather`: 3,654 raw daily weather observations for London and Manila.
  - `bronze.holidays`: 193 public holiday records for GB and PH across 2021–2026.
* **Audit Lineage Columns**:
  - `_ingested_at` (`TIMESTAMP`): UTC ingestion timestamp.
  - `_source_system` (`VARCHAR`): `'open-meteo-archive'` or `'nager-date-api'`.
  - `_batch_id` (`VARCHAR`): Unique execution batch ID (e.g. `'20260824_182900'`).

#### 🥈 Silver Layer (`main_silver.*`)
* **Purpose**: Cleansed, standardized, conformed, and deduplicated intermediate layer.
* **Models**:
  - `stg_weather` (View): Enforces ISO date formats, validates temperature ranges (`is_valid_temp_range`), and ensures precipitation $\ge 0$.
  - `stg_holidays` (View): Standardizes snake_case naming and types `global` as `is_global` boolean.
  - `silver_weather_holidays` (Table): Joins weather and holiday observations at the daily grain, generating calendar flags (`is_weekend`, `year`, `month`).

#### 🥇 Gold Layer (`main_gold.*`)
* **Purpose**: Highly optimized dimensional star schema and pre-computed business marts ready for consumption.
* **Dimensional Model**:
  - `dim_date`: 1,827 unique calendar dates with English day names, weekend flags, and seasons.
  - `dim_location`: Surrogate location keys for London (`1`) and Manila (`2`) with climate zones.
  - `dim_holiday`: Surrogate holiday keys with a default `0` (`"No Holiday"`) record to preserve referential integrity.
  - `fact_daily_weather`: Central fact table linking foreign keys with numeric weather measures.
* **Business Marts**:
  - `mart_weather_summary`: Holiday vs. Regular Day high-level metrics.
  - `mart_per_holiday`: Holiday-by-holiday performance rankings and records.
  - `mart_yearly_climate_trends`: 5-year longitudinal temperature and rainfall trends.
  - `mart_monthly_seasonality`: 12-month seasonal benchmark controlling for calendar timing.
  - `mart_rain_probability`: Probability percentages for rainy and heavy-rain days.
  - `mart_extreme_weather_events`: Leaderboard of top single-day precipitation events on holidays.

---

### 2.2 Data Quality & Automated Testing Matrix (dbt)

27 automated schema assertions run upon every pipeline build:
* **Uniqueness**: `unique` on all primary surrogate keys (`dim_date.date_key`, `dim_location.location_id`, `dim_holiday.holiday_id`, `fact_daily_weather.fact_id`).
* **Nullability**: `not_null` assertions on all dimensions, foreign keys, and grain identifiers.
* **Referential Integrity**: `relationships` assertions validating that `fact_daily_weather` foreign keys strictly resolve to `dim_date`, `dim_location`, and `dim_holiday`.

---

### 2.3 Consumption Layer Architecture
1. **Streamlit App (`dashboard.py`)**:
   - Queries `main_gold.fact_daily_weather` directly via in-process DuckDB connection.
   - Features city switcher, dark mode styling, and 7 insight modules.
2. **Grafana BI Platform**:
   - Connects to `mysql_server.py` on port 3306.
   - Separate dedicated dashboards for London (`/d/weather-london-insights`) and Manila (`/d/weather-manila-insights`).
