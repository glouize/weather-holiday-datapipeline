from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
conn = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)

print("=" * 80)
print("INSIGHT 1: Overall Data Summary")
print("=" * 80)
print(conn.execute("""
    SELECT 
        COUNT(*) as total_days,
        COUNT(CASE WHEN holiday_id != 0 THEN 1 END) as holiday_days,
        COUNT(CASE WHEN holiday_id = 0 THEN 1 END) as non_holiday_days,
        MIN(date_key) as earliest_date,
        MAX(date_key) as latest_date
    FROM main.fact_daily_weather
""").df().to_string(index=False))

print("\n" + "=" * 80)
print("INSIGHT 2: Avg Weather on Holidays vs Non-Holidays")
print("=" * 80)
print(conn.execute("""
    SELECT
        CASE WHEN f.holiday_id != 0 THEN 'Holiday' ELSE 'Regular Day' END as day_type,
        COUNT(*) as num_days,
        ROUND(AVG(f.temperature_2m_max), 2) as avg_max_temp_c,
        ROUND(AVG(f.temperature_2m_min), 2) as avg_min_temp_c,
        ROUND(AVG(f.precipitation_sum), 2) as avg_precipitation_mm,
        ROUND(SUM(f.precipitation_sum), 2) as total_precipitation_mm
    FROM main.fact_daily_weather f
    GROUP BY day_type
    ORDER BY day_type
""").df().to_string(index=False))

print("\n" + "=" * 80)
print("INSIGHT 3: Weather Breakdown by Each Holiday")
print("=" * 80)
print(conn.execute("""
    SELECT
        h.holiday_name,
        COUNT(*) as occurrences,
        ROUND(AVG(f.temperature_2m_max), 1) as avg_max_temp,
        ROUND(AVG(f.temperature_2m_min), 1) as avg_min_temp,
        ROUND(AVG(f.precipitation_sum), 1) as avg_precip_mm,
        ROUND(MAX(f.temperature_2m_max), 1) as hottest_ever,
        ROUND(MIN(f.temperature_2m_min), 1) as coldest_ever
    FROM main.fact_daily_weather f
    JOIN main.dim_holiday h ON f.holiday_id = h.holiday_id
    WHERE f.holiday_id != 0
    GROUP BY h.holiday_name
    ORDER BY avg_max_temp DESC
""").df().to_string(index=False))

print("\n" + "=" * 80)
print("INSIGHT 4: Seasonal Comparison - Holiday vs Non-Holiday by Month")
print("=" * 80)
print(conn.execute("""
    SELECT
        d.month,
        ROUND(AVG(CASE WHEN f.holiday_id != 0 THEN f.temperature_2m_max END), 1) as holiday_avg_max_temp,
        ROUND(AVG(CASE WHEN f.holiday_id = 0 THEN f.temperature_2m_max END), 1) as regular_avg_max_temp,
        ROUND(AVG(CASE WHEN f.holiday_id != 0 THEN f.precipitation_sum END), 1) as holiday_avg_precip,
        ROUND(AVG(CASE WHEN f.holiday_id = 0 THEN f.precipitation_sum END), 1) as regular_avg_precip
    FROM main.fact_daily_weather f
    JOIN main.dim_date d ON f.date_key = d.date_key
    WHERE d.month IN (SELECT DISTINCT d2.month FROM main.dim_date d2 
                       JOIN main.fact_daily_weather f2 ON d2.date_key = f2.date_key 
                       WHERE f2.holiday_id != 0)
    GROUP BY d.month
    ORDER BY d.month
""").df().to_string(index=False))

print("\n" + "=" * 80)
print("INSIGHT 5: Rainy Holidays - Probability of Rain on Holidays vs Regular Days")
print("=" * 80)
print(conn.execute("""
    SELECT
        CASE WHEN f.holiday_id != 0 THEN 'Holiday' ELSE 'Regular Day' END as day_type,
        COUNT(*) as total_days,
        COUNT(CASE WHEN f.precipitation_sum > 0 THEN 1 END) as rainy_days,
        ROUND(100.0 * COUNT(CASE WHEN f.precipitation_sum > 0 THEN 1 END) / COUNT(*), 1) as pct_rainy,
        COUNT(CASE WHEN f.precipitation_sum > 5 THEN 1 END) as heavy_rain_days,
        ROUND(100.0 * COUNT(CASE WHEN f.precipitation_sum > 5 THEN 1 END) / COUNT(*), 1) as pct_heavy_rain
    FROM main.fact_daily_weather f
    GROUP BY day_type
""").df().to_string(index=False))

print("\n" + "=" * 80)
print("INSIGHT 6: Year-over-Year Temperature Trend")
print("=" * 80)
print(conn.execute("""
    SELECT
        d.year,
        ROUND(AVG(f.temperature_2m_max), 2) as avg_max_temp,
        ROUND(AVG(f.temperature_2m_min), 2) as avg_min_temp,
        ROUND(AVG(f.precipitation_sum), 2) as avg_daily_precip,
        ROUND(SUM(f.precipitation_sum), 1) as total_annual_precip
    FROM main.fact_daily_weather f
    JOIN main.dim_date d ON f.date_key = d.date_key
    GROUP BY d.year
    ORDER BY d.year
""").df().to_string(index=False))

print("\n" + "=" * 80)
print("INSIGHT 7: Weekend Holidays vs Weekday Holidays")
print("=" * 80)
print(conn.execute("""
    SELECT
        CASE WHEN d.is_weekend THEN 'Weekend Holiday' ELSE 'Weekday Holiday' END as holiday_timing,
        COUNT(*) as count,
        ROUND(AVG(f.temperature_2m_max), 1) as avg_max_temp,
        ROUND(AVG(f.precipitation_sum), 1) as avg_precip_mm
    FROM main.fact_daily_weather f
    JOIN main.dim_date d ON f.date_key = d.date_key
    WHERE f.holiday_id != 0
    GROUP BY holiday_timing
""").df().to_string(index=False))

print("\n" + "=" * 80)
print("INSIGHT 8: Top 5 Wettest & Driest Holidays (Specific Dates)")
print("=" * 80)
print("--- WETTEST ---")
print(conn.execute("""
    SELECT f.date_key, h.holiday_name, f.precipitation_sum, f.temperature_2m_max
    FROM main.fact_daily_weather f
    JOIN main.dim_holiday h ON f.holiday_id = h.holiday_id
    WHERE f.holiday_id != 0
    ORDER BY f.precipitation_sum DESC
    LIMIT 5
""").df().to_string(index=False))
print("\n--- DRIEST (with highest temp) ---")
print(conn.execute("""
    SELECT f.date_key, h.holiday_name, f.precipitation_sum, f.temperature_2m_max
    FROM main.fact_daily_weather f
    JOIN main.dim_holiday h ON f.holiday_id = h.holiday_id
    WHERE f.holiday_id != 0 AND f.precipitation_sum = 0
    ORDER BY f.temperature_2m_max DESC
    LIMIT 5
""").df().to_string(index=False))

print("\n" + "=" * 80)
print("INSIGHT 9: Extreme Temperature Days - How Many Fall on Holidays?")
print("=" * 80)
print(conn.execute("""
    WITH extremes AS (
        SELECT 
            f.*,
            PERCENT_RANK() OVER (ORDER BY temperature_2m_max) as temp_percentile
        FROM main.fact_daily_weather f
    )
    SELECT
        CASE WHEN holiday_id != 0 THEN 'Holiday' ELSE 'Regular Day' END as day_type,
        COUNT(CASE WHEN temp_percentile >= 0.95 THEN 1 END) as top_5pct_hot_days,
        COUNT(CASE WHEN temp_percentile <= 0.05 THEN 1 END) as bottom_5pct_cold_days,
        COUNT(*) as total_days
    FROM extremes
    GROUP BY day_type
""").df().to_string(index=False))

conn.close()
print("\n\nDone!")
