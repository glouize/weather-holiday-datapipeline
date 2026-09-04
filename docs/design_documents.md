# Weather & Public Holiday Intelligence Platform
## System Architecture & Technical Design Document (HLD & DLD)

---

## 1. High-Level Design (HLD)

### 1.1 Architectural Pattern: Medallion Architecture
The platform implements a multi-tier **Medallion Architecture (Bronze $\rightarrow$ Silver $\rightarrow$ Gold)** to guarantee data quality, lineage traceability, and high-performance analytical querying across multi-city data (London & Manila, 2021–2026).

![High-Level Design — Medallion Architecture](images/hld_architecture.jpg)

> 🔍 **Interactive Vector Diagram**: A standalone vector SVG diagram is available at [`docs/hld_architecture.html`](hld_architecture.html).

```mermaid
flowchart TD
    subgraph DataSources["1. External API Sources"]
        A1["🌤️ Open-Meteo Historical Archive API\n(Daily Temp Max/Min, Precip)"]
        A2["📅 Nager.Date Public Holiday API\n(National & Regional Holiday Calendars)"]
    end

    subgraph Ingestion["2. Ingestion Engine (Python EL)"]
        EL["extract_load.py\n• Exponential backoff (max 3 retries, 5s delay)\n• 60s/15s HTTP timeouts\n• 500ms holiday rate-limit throttle\n• Audit metadata tagging"]
    end

    subgraph BronzeLayer["3. 🥉 Bronze Layer (DuckDB: bronze.* & raw.*)"]
        B1[("bronze.weather (3,654 rows)\nRaw daily weather observations\n+ _ingested_at, _source_system, _batch_id")]
        B2[("bronze.holidays (193 rows)\nRaw public holiday entries (GB & PH)\n+ _ingested_at, _source_system, _batch_id")]
    end

    subgraph SilverLayer["4. 🥈 Silver Layer (DuckDB: main_silver.* via dbt)"]
        S1["main_silver.stg_weather (View)\n• ISO date casting & deduplication\n• Range validation (is_valid_temp_range)\n• Precipitation ≥ 0 constraint"]
        S2["main_silver.stg_holidays (View)\n• Snake_case standardization\n• Boolean flag casting (is_global)\n• Public holiday categorization"]
        S3[("main_silver.silver_weather_holidays (Table)\n• Unified daily observation grain\n• Calendar flags (is_weekend, year, month)\n• Holiday name & day_type join")]
    end

    subgraph GoldLayer["5. 🥇 Gold Layer (DuckDB: main_gold.* via dbt Star Schema & Marts)"]
        subgraph Dimensions["Conformed Dimensions"]
            G_DATE["main_gold.dim_date (1,827 rows)\n• PK: date_key\n• Day name, weekend flag, seasons"]
            G_LOC["main_gold.dim_location (2 rows)\n• PK: location_id (London, Manila)\n• Timezone & climate zones"]
            G_HOL["main_gold.dim_holiday (38 rows)\n• PK: holiday_id (0 = 'No Holiday')\n• Local name & global flag"]
        end
        G_FACT[("main_gold.fact_daily_weather (Table, 3,654 rows)\n• PK: fact_id\n• FKs: date_key, location_id, holiday_id\n• Measures: max/min temp, precipitation_sum")]
        G_MARTS["Aggregated Business Marts (6 Models):\n• mart_weather_summary (Holiday vs Regular Day KPIs)\n• mart_per_holiday (Per-holiday records & averages)\n• mart_yearly_climate_trends (5-yr climate shift)\n• mart_monthly_seasonality (12-month seasonality)\n• mart_rain_probability (Rain & heavy rain %)\n• mart_extreme_weather_events (Top precipitation on holidays)"]
    end

    subgraph ServingLayer["6. Serving & Analytics Layer"]
        P_MYSQL["MySQL Bridge (mysql_server.py)\n• Port: 3306 (Loopback 127.0.0.1)\n• TLS/SSL Encryption (server.crt/key)\n• In-Memory DuckDB OLAP Cache"]
        BI_GRAFANA["📈 Grafana BI Platform (Port 3000)\n• 🇬🇧 London Dashboard\n• 🇵🇭 Manila Dashboard\n• 🌐 Overview Comparison Dashboard"]
        BI_STREAMLIT["📊 Streamlit Web App (Port 8501)\n• Direct in-process DuckDB engine\n• Dark Mode UI & City Switcher\n• 7 Narrative Analytical Modules"]
    end

    A1 -->|HTTP GET with Retry| EL
    A2 -->|HTTP GET with Throttle| EL
    EL -->|Idempotent Atomic Load| B1
    EL -->|Idempotent Atomic Load| B2
    B1 -->|dbt source| S1
    B2 -->|dbt source| S2
    S1 --> S3
    S2 --> S3
    S1 --> G_DATE
    S1 --> G_LOC
    S2 --> G_HOL
    S3 --> G_FACT
    G_LOC -.->|FK lookup| G_FACT
    G_HOL -.->|FK lookup| G_FACT
    G_FACT --> G_MARTS
    G_FACT -->|In-Process DuckDB SQL| BI_STREAMLIT
    G_MARTS -->|In-Process DuckDB SQL| BI_STREAMLIT
    G_FACT -->|Memory Replication| P_MYSQL
    G_MARTS -->|Memory Replication| P_MYSQL
    P_MYSQL -->|TLS MySQL Wire Protocol| BI_GRAFANA
```

---

### 1.2 Data Lifecycle Management (DLM) Flow

![Detailed Low-Level Design — Pipeline Sequence](images/dld_sequence.jpg)

> 🔍 **Interactive Vector Diagram**: A standalone vector SVG diagram is available at [`docs/dld_sequence.html`](dld_sequence.html).

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
