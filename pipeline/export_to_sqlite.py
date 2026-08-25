"""Export DuckDB data to SQLite for Metabase consumption."""
import sqlite3
import duckdb
import pandas as pd

conn = duckdb.connect('warehouse.duckdb', read_only=True)
db = sqlite3.connect('warehouse_metabase.db')

# Export raw tables
weather = conn.execute("SELECT * FROM raw.weather").df()
holidays = conn.execute("SELECT * FROM raw.holidays").df()
weather.to_sql('weather', db, if_exists='replace', index=False)
holidays.to_sql('holidays', db, if_exists='replace', index=False)
print(f"Raw: {len(weather)} weather rows, {len(holidays)} holiday rows")

# Create a pre-joined fact table for easy Metabase charting
combined = conn.execute("""
    SELECT
        w.time::VARCHAR       AS date_key,
        w.city,
        w.country_code,
        w.temperature_2m_max,
        w.temperature_2m_min,
        w.precipitation_sum,
        EXTRACT(YEAR FROM w.time)::INT    AS year,
        EXTRACT(MONTH FROM w.time)::INT   AS month,
        CASE WHEN EXTRACT(ISODOW FROM w.time) IN (6,7) THEN 1 ELSE 0 END AS is_weekend,
        COALESCE(h.name, 'Not a Holiday') AS holiday_name,
        CASE WHEN h.date IS NOT NULL THEN 'Holiday' ELSE 'Regular Day' END AS day_type
    FROM raw.weather w
    LEFT JOIN raw.holidays h
        ON w.time::DATE = h.date::DATE
        AND w.country_code = h.countryCode
    ORDER BY w.city, w.time
""").df()
combined.to_sql('fact_weather_holiday', db, if_exists='replace', index=False)
print(f"Fact table: {len(combined)} rows")

# Create summary views as tables for Metabase
summary = conn.execute("""
    SELECT
        w.city,
        CASE WHEN h.date IS NOT NULL THEN 'Holiday' ELSE 'Regular Day' END AS day_type,
        COUNT(*)::INT AS num_days,
        ROUND(AVG(w.temperature_2m_max), 2) AS avg_max_temp,
        ROUND(AVG(w.temperature_2m_min), 2) AS avg_min_temp,
        ROUND(AVG(w.precipitation_sum), 2) AS avg_precipitation,
        ROUND(SUM(w.precipitation_sum), 2) AS total_precipitation
    FROM raw.weather w
    LEFT JOIN raw.holidays h
        ON w.time::DATE = h.date::DATE
        AND w.country_code = h.countryCode
    GROUP BY w.city, day_type
""").df()
summary.to_sql('summary_holiday_vs_regular', db, if_exists='replace', index=False)
print(f"Summary table: {len(summary)} rows")

# Per-holiday breakdown
per_holiday = conn.execute("""
    SELECT
        w.city,
        h.name AS holiday_name,
        COUNT(*)::INT AS occurrences,
        ROUND(AVG(w.temperature_2m_max), 1) AS avg_max_temp,
        ROUND(AVG(w.temperature_2m_min), 1) AS avg_min_temp,
        ROUND(AVG(w.precipitation_sum), 1) AS avg_precip,
        ROUND(MAX(w.temperature_2m_max), 1) AS record_high,
        ROUND(MIN(w.temperature_2m_min), 1) AS record_low
    FROM raw.weather w
    JOIN raw.holidays h
        ON w.time::DATE = h.date::DATE
        AND w.country_code = h.countryCode
    GROUP BY w.city, h.name
    ORDER BY w.city, avg_max_temp DESC
""").df()
per_holiday.to_sql('per_holiday_weather', db, if_exists='replace', index=False)
print(f"Per-holiday table: {len(per_holiday)} rows")

# Yearly trend
yearly = conn.execute("""
    SELECT
        w.city,
        EXTRACT(YEAR FROM w.time)::INT AS year,
        ROUND(AVG(w.temperature_2m_max), 2) AS avg_max_temp,
        ROUND(AVG(w.temperature_2m_min), 2) AS avg_min_temp,
        ROUND(SUM(w.precipitation_sum), 1) AS total_precipitation,
        COUNT(*)::INT AS days_recorded
    FROM raw.weather w
    GROUP BY w.city, year
    ORDER BY w.city, year
""").df()
yearly.to_sql('yearly_trend', db, if_exists='replace', index=False)
print(f"Yearly trend table: {len(yearly)} rows")

db.close()
conn.close()
print("Done! SQLite database created: warehouse_metabase.db")
