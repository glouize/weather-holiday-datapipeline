# Weather & Public Holiday Intelligence Platform

> **Stack**: Python · DuckDB · dbt · Streamlit · Grafana
> **Architecture**: Medallion Architecture (Bronze → Silver → Gold)
> **Cities**: London (GB) & Manila (PH) · **Period**: 2021–2026 (5 years)

---
## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Data Model](#data-model)
6. [Quickstart](#quickstart)
7. [Running the Pipeline](#running-the-pipeline)
8. [Running the Dashboards](#running-the-dashboards)
9. [Data Quality](#data-quality)
10. [Observability](#observability)
11. [Dashboards](#dashboards)

---

## Project Overview

This platform answers a single analytical question:

> **Does the weather on public holidays differ from regular days — and how has that changed year over year?**

It ingests 5 years (2021–2026) of daily weather observations and national public holiday calendars for **London, UK** and **Manila, Philippines** from free, open REST APIs. The data is modelled using a **Medallion Architecture** (Bronze → Silver → Gold) with dbt, then served through two BI frontends: a Streamlit web app and a Grafana dashboard suite.

---

## Architecture

```text
+-----------------------------------------------------------------+
|  External APIs (no API key required)                            |
|  - Open-Meteo Historical Archive -> daily temperature and rain  |
|  - Nager.Date Public Holidays    -> national holiday calendars  |
+-----------------------+-----------------------------------------+
                        | Python HTTP with retry and backoff
                        v
+-----------------------------------------------------------------+
|  Bronze Layer (warehouse.duckdb / bronze.*)                     |
|  Raw, immutable tables with audit lineage columns:              |
|  _ingested_at, _source_system, _batch_id                        |
|  - bronze.weather    3,654 rows                                 |
|  - bronze.holidays     193 rows                                 |
+-----------------------+-----------------------------------------+
                        | dbt run
                        v
+-----------------------------------------------------------------+
|  Silver Layer (main_silver.*)                                   |
|  Cleansed, standardized, deduplicated intermediate layer        |
|  - stg_weather              (view)  ISO dates, range checks     |
|  - stg_holidays             (view)  snake_case, boolean types   |
|  - silver_weather_holidays  (table) joined daily observations   |
+-----------------------+-----------------------------------------+
                        | dbt run
                        v
+-----------------------------------------------------------------+
|  Gold Layer (main_gold.*) - star schema and business marts      |
|
|  Dimensions:                  Facts and marts:                  |
|  - dim_date       1,827 rows  - fact_daily_weather  3,654 rows  |
|  - dim_location       2 rows  - mart_weather_summary    4 rows  |
|  - dim_holiday       38 rows  - mart_per_holiday       37 rows  |
|                               - mart_yearly_trends     12 rows  |
|                               - mart_monthly_season    44 rows  |
|                               - mart_rain_probability   4 rows  |
|                               - mart_extreme_events   162 rows  |
+-----------+---------------------------------------+-------------+
            | Direct DuckDB (read-only)             | MySQL protocol
            v                                       v
   Streamlit App (port 8501)             mysql_server.py (port 3306)
   serving/dashboard.py                  serving/mysql_server.py
                                                        |
                                                        v
                                               Grafana OSS (port 3000)
                                               - London Dashboard
                                               - Manila Dashboard
                                               - Overview Dashboard
```

---

## Tech Stack

| Component | Technology | Version |
|---|---|---|
| Data warehouse | DuckDB | 1.5.5 |
| Transformation | dbt-core + dbt-duckdb | 1.9.4 / 1.11.0 |
| Web dashboard | Streamlit | 1.62.0 |
| Charts | Plotly | 6.9.0 |
| BI platform | Grafana OSS | Latest |
| MySQL bridge | mysql-mimic | 3.0.4 |
| SQL transpiler | sqlglot | 30.17.0 |
| TLS certs | cryptography | 44.0.3 |
| HTTP client | requests | 2.32.3 |
| Dataframes | pandas | 2.3.1 |
| Language | Python | 3.10 / 3.11 |

---

## Project Structure

`
weather_holiday_dbt_pipeline/
│
├── pipeline/                   # Data ingestion & export
│   ├── extract_load.py         #   API → Bronze Layer EL script
│   ├── export_to_sqlite.py     #   Export warehouse to SQLite
│   └── schema.sql              #   Raw SQL schema definitions
│
├── serving/                    # BI serving layer (keep running)
│   ├── mysql_server.py         #   MySQL bridge → DuckDB Gold (port 3306)
│   ├── dashboard.py            #   Streamlit dashboard (port 8501)
│   └── grafana_api.py          #   JSON API for Grafana Infinity (port 8888)
│
├── grafana/                    # Grafana provisioning (run once)
│   ├── setup_grafana_mysql.py  #   Datasource + Overview dashboard
│   ├── create_city_dashboards.py #  London & Manila dashboards
│   ├── setup_grafana.py        #   Legacy Grafana setup
│   └── setup_metabase.py       #   Metabase provisioning
│
│   ├── test_city_dashboards.py #   City dashboard panel tests
│   ├── test_all_panels.py      #   Full panel data verification
│   └── test_panels.py          #   Individual panel tests
│
├── utils/                      # Debug & inspection tools
│   ├── view_data.py            #   Print data insights to console
│   ├── inspect_db_schemas.py   #   List DuckDB schemas & row counts
│   ├── inspect_panels.py       #   Inspect Grafana panel config
│   └── diagnose.py             #   Diagnose datasource UID mismatches
│
├── certs/                      # TLS certificates
│   ├── gen_certs.py            #   Generate server.crt & server.key
│   ├── server.crt              #   Self-signed certificate
│   └── server.key              #   Private key
│
├── dbt_weather_holidays/       # dbt project (Bronze → Silver → Gold)
│   ├── dbt_project.yml
│   ├── profiles.yml            #   DuckDB connection (path: ../warehouse.duckdb)
│   └── models/
│       ├── silver/             #   stg_weather, stg_holidays, silver_weather_holidays
│       └── gold/               #   dim_*, fact_*, mart_*
│
├── .streamlit/
│   └── config.toml             # Dark mode theme config
├── warehouse.duckdb            # Main DuckDB data warehouse (~6 MB)
└── requirements.txt            # Python dependencies
`

---

## Data Model

### Medallion Layers

| Layer | Schema | Materialization | Purpose |
|---|---|---|---|
| Bronze | ronze.* | Table | Raw immutable API data with audit lineage |
| Silver | main_silver.* | View / Table | Cleaned, typed, deduplicated observations |
| Gold | main_gold.* | Table | Star schema + pre-aggregated business marts |

### Gold Star Schema

`
        dim_date          dim_location        dim_holiday
       (1,827 rows)         (2 rows)           (38 rows)
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
                    fact_daily_weather
                       (3,654 rows)
                                │
                    ┌───────────┼───────────┐
                    │           │           │
         mart_weather_summary   │  mart_per_holiday
         mart_yearly_trends     │  mart_monthly_seasonality
         mart_rain_probability   │  mart_extreme_weather_events
`

### Key Columns in act_daily_weather

| Column | Type | Description |
|---|---|---|
| act_id | BIGINT PK | Auto-generated surrogate key |
| date_key | DATE FK | Links to dim_date |
| location_id | INT FK | Links to dim_location (1=London, 2=Manila) |
| holiday_id | INT FK | Links to dim_holiday (0=Not a holiday) |
| 	emperature_2m_max | DECIMAL | Daily maximum temperature (°C) |
| 	emperature_2m_min | DECIMAL | Daily minimum temperature (°C) |
| precipitation_sum | DECIMAL | Daily total precipitation (mm) |
| is_holiday | BOOLEAN | True if the day is a public holiday |
| is_weekend | BOOLEAN | True if Saturday or Sunday |
| year / month | INT | Extracted calendar attributes |

---

## Quickstart

### 1. Prerequisites
- Python 3.10 or 3.11
- Grafana OSS installed and running on port 3000 (https://grafana.com/grafana/download)

### 2. Install dependencies

`ash
# Windows — fix execution policy first (once)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

python -m venv venv
.\venv\Scripts\Activate.ps1          # Windows
# source venv/bin/activate           # macOS / Linux

pip install -r requirements.txt
`

### 3. Windows Unicode fix (run in each new session)
`powershell
="utf-8"
`

---

## Running the Pipeline

> [!IMPORTANT]
> DuckDB on Windows requires exclusive write access. **Stop** serving/mysql_server.py and serving/dashboard.py before running ingestion or dbt.

### Step 1 — Generate TLS Certificates (once)
`ash
python certs/gen_certs.py
`

### Step 2 — Ingest Bronze Layer data
`ash
python pipeline/extract_load.py
`
Expected: 3,654 weather rows + 193 holiday rows written to warehouse.duckdb.

### Step 3 — Run dbt Transformations
`ash
cd dbt_weather_holidays
dbt run --profiles-dir .
`
Expected: PASS=13 WARN=0 ERROR=0 SKIP=0 TOTAL=13

### Step 4 — Run dbt Data Quality Tests
`ash
dbt test --profiles-dir .
cd ..
`
Expected: PASS=27 WARN=0 ERROR=0 SKIP=0 TOTAL=27

---

## Running the Dashboards

Open **3 separate terminals** (all from the project root):

`ash
# Terminal 1 — MySQL bridge for Grafana (keep open)
python serving/mysql_server.py

# Terminal 2 — Streamlit web app (keep open)
streamlit run serving/dashboard.py

# Terminal 3 — Grafana provisioning (run once, then close)
python grafana/setup_grafana_mysql.py
python grafana/create_city_dashboards.py
`

### Access URLs

| Interface | URL |
|---|---|
| Streamlit Dashboard | http://localhost:8501 |
| Grafana — London | http://localhost:3000/d/weather-london-insights |
| Grafana — Manila | http://localhost:3000/d/weather-manila-insights |
| Grafana — Overview | http://localhost:3000/d/weather-holiday-mysql |

Grafana default credentials: dmin / dmin

---

## Data Quality

27 automated dbt assertions run on every pipeline build:

| Test Type | Count | Models Covered |
|---|---|---|
ot_null | 18 | All dimension and fact key columns |
elationships (FK) | 3 | act_daily_weather → dim_date, dim_location, dim_holiday |
ot_null | 9 | stg_weather, stg_holidays, silver_weather_holidays |
| unique (PK) | 4 | dim_date, dim_location, dim_holiday, fact_daily_weather |
| not_null | 18 | All dimension and fact key columns |
| relationships (FK) | 3 | fact_daily_weather -> dim_date, dim_location, dim_holiday |
| Silver not_null | 9 | stg_weather, stg_holidays, silver_weather_holidays |

Run tests manually:
`ash
cd dbt_weather_holidays
dbt test --profiles-dir .
`

To benchmark Grafana panel query speed:
`ash
python tests/benchmark_queries.py
`
Expected: All 8 panels respond in < 20 ms each (< 100 ms total sequential).

---

## Observability

This project uses **console-based observability only**:

| What | How |
|---|---|
| API fetch success/failure | logging.INFO / logging.ERROR in pipeline/extract_load.py |
| dbt test failures | dbt prints to console + non-zero exit code |
| Query performance | python tests/benchmark_queries.py (manual run) |
| DuckDB schema inspection | python utils/inspect_db_schemas.py |
| Grafana datasource diagnosis | python utils/diagnose.py |

No external monitoring platform (Datadog, ELK, Grafana Loki, Prometheus) is integrated.

---

## Dashboards

### Streamlit App (port 8501)
- Dark mode with hidden Streamlit branding
- City switcher: London / Manila
- 7 insight modules:
  - KPI metrics (total days, holiday count, avg temperatures)
  - Holiday vs Regular Day temperature comparison
  - Rain probability chart
  - Year-over-Year temperature trends
  - Monthly seasonality breakdown
  - Per-holiday weather rankings table
  - Medallion architecture sidebar

### Grafana (port 3000)
- **Separate dedicated dashboards** for London and Manila
- **Overview dashboard** with comparative London vs Manila panels
- Each dashboard includes:
  - 🔄 Refresh All Tiles button (HTML panel)
  - City navigation pills
  - Native Grafana timepicker with auto-refresh intervals
  - 8 data panels per city:
    1. Avg Max Temperature: Holiday vs Regular Day
    2. Year-over-Year Avg Max Temperature
    3. Monthly Temperature Seasonality (Holiday vs Regular)
    4. Top 10 Wettest Holidays (by rainfall)
    5. Per-Holiday Avg Precipitation
    6. Rain Probability (%)
    7. Holiday vs Regular Day Summary Table
    8. Per-Holiday Full Stats Table

---

