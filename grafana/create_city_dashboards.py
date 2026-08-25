"""
Create separate, dedicated Grafana dashboards for London and Manila,
plus an overview dashboard, with full data visualizations.
"""
import sys
import os
from pathlib import Path
import requests, json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import cfg, CITIES

_g      = cfg["grafana"]
GRAFANA = os.getenv("GRAFANA_URL",      _g["url"])
USER    = os.getenv("GRAFANA_USER",     _g["username"])
PASS    = os.getenv("GRAFANA_PASSWORD", _g["password"])
auth    = (USER, PASS)

# Fetch datasource UID dynamically from Grafana
_ds_resp = requests.get(f"{GRAFANA}/api/datasources/name/{_g['datasource_name']}", auth=auth, timeout=10)
ds_uid   = _ds_resp.json().get("uid", "") if _ds_resp.ok else ""

def g(method, path, data=None):
    r = getattr(requests, method)(
        f"{GRAFANA}{path}", auth=auth, json=data,
        headers={"Content-Type": "application/json"}, timeout=15
    )
    return r.json() if r.text else {}

def sql_target(raw_sql):
    return {
        "rawSql": raw_sql,
        "rawQuery": True,
        "format": "table",
        "intervalMs": 86400000,
        "maxDataPoints": 10000,
        "refId": "A",
        "datasource": {"type": "mysql", "uid": ds_uid}
    }

def panel(pid, title, ptype, x, y, w, h, target_sql, opts=None, field_cfg=None, desc=""):
    return {
        "id": pid,
        "type": ptype,
        "title": title,
        "description": desc,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "mysql", "uid": ds_uid},
        "targets": [sql_target(target_sql)],
        "options": opts or {},
        "fieldConfig": field_cfg or {
            "defaults": {"color": {"mode": "palette-classic"}},
            "overrides": []
        },
    }

def header_panel(city, emoji):
    return {
        "id": 100,
        "type": "text",
        "title": "",
        "gridPos": {"x": 0, "y": 0, "w": 24, "h": 3},
        "options": {
            "mode": "html",
            "content": f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.35rem; font-weight: 700; color: #FAFAFA;">{emoji} {city} Weather & Holiday Intelligence</span>
                    <span style="font-size: 0.85rem; color: #8F90A6; background: rgba(255,255,255,0.06); padding: 3px 8px; border-radius: 4px;">Medallion Gold Layer · Author: Louise Guerrero</span>
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <a href="/d/weather-london-insights" style="text-decoration: none; padding: 6px 12px; font-size: 0.85rem; border-radius: 4px; background: rgba(78,205,196,0.15); color: #4ECDC4; border: 1px solid rgba(78,205,196,0.3); font-weight: 600;">🇬🇧 London</a>
                    <a href="/d/weather-manila-insights" style="text-decoration: none; padding: 6px 12px; font-size: 0.85rem; border-radius: 4px; background: rgba(255,107,107,0.15); color: #FF6B6B; border: 1px solid rgba(255,107,107,0.3); font-weight: 600;">🇵🇭 Manila</a>
                    <a href="/d/weather-holiday-mysql" style="text-decoration: none; padding: 6px 12px; font-size: 0.85rem; border-radius: 4px; background: rgba(108,99,255,0.15); color: #6C63FF; border: 1px solid rgba(108,99,255,0.3); font-weight: 600;">🌐 Overview</a>
                    <a href="" target="_self" style="text-decoration: none; background: linear-gradient(135deg, #6C63FF, #4ECDC4); color: #ffffff; border: none; border-radius: 5px; padding: 7px 16px; font-weight: 700; font-size: 0.85rem; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(108,99,255,0.4);">
                        🔄 Refresh All Tiles
                    </a>
                </div>
            </div>
            """
        },
    }

def build_city_dashboard(city, uid, emoji, country_code, primary_color):
    panels = [
        # 0. Header & Action Control Row
        header_panel(city, emoji),

        # 1. Summary table
        panel(
            1, f"📊 {city} — Holiday vs Regular Day Weather Summary",
            "table", 0, 3, 24, 7,
            f"""
            SELECT day_type AS `Day Type`,
                   num_days AS Days,
                   avg_max_temp AS `Avg Max Temp (C)`,
                   avg_min_temp AS `Avg Min Temp (C)`,
                   avg_precipitation AS `Avg Precip (mm)`
            FROM summary
            WHERE city = '{city}'
            ORDER BY day_type
            """,
            desc=f"Comparison of overall weather averages on public holidays vs normal days in {city}"
        ),
        # 2. Temperature Comparison Bar Chart
        panel(
            2, f"🌡️ {city} — Temperature: Holiday vs Regular Day",
            "barchart", 0, 10, 12, 9,
            f"""
            SELECT day_type AS `Day Type`,
                   avg_max_temp AS `Avg Max Temp`,
                   avg_min_temp AS `Avg Min Temp`
            FROM summary
            WHERE city = '{city}'
            ORDER BY day_type
            """,
            opts={
                "xField": "Day Type",
                "groupWidth": 0.7,
                "barWidth": 0.8,
                "legend": {"displayMode": "list", "placement": "bottom"},
                "tooltip": {"mode": "multi"}
            },
            field_cfg={"defaults": {"unit": "celsius"}, "overrides": []},
            desc=f"Compare average maximum and minimum temperatures in {city}"
        ),
        # 3. Rain Probability Bar Chart
        panel(
            3, f"☂️ {city} — Probability of Rain (%)",
            "barchart", 12, 10, 12, 9,
            f"""
            SELECT day_type AS `Day Type`,
                   pct_rainy AS `Any Rain %`,
                   pct_heavy_rain AS `Heavy Rain (>5mm) %`
            FROM rain_probability
            WHERE city = '{city}'
            ORDER BY day_type
            """,
            opts={
                "xField": "Day Type",
                "groupWidth": 0.7,
                "barWidth": 0.8,
                "legend": {"displayMode": "list", "placement": "bottom"}
            },
            field_cfg={"defaults": {"unit": "percent"}, "overrides": []},
            desc=f"Likelihood of experiencing rain or heavy downpours in {city}"
        ),
        # 4. Per-Holiday Ranking Table
        panel(
            4, f"☀️ {city} — Per-Holiday Weather Ranking (Warmest to Coldest)",
            "table", 0, 19, 24, 10,
            f"""
            SELECT holiday_name AS Holiday,
                   occurrences AS `Years Recorded`,
                   avg_max_temp AS `Avg Max (C)`,
                   avg_min_temp AS `Avg Min (C)`,
                   avg_precip AS `Avg Rain (mm)`,
                   record_high AS `Record High (C)`,
                   record_low AS `Record Low (C)`
            FROM per_holiday
            WHERE city = '{city}'
            ORDER BY avg_max_temp DESC
            """,
            desc=f"All unique public holidays in {city} ranked by temperature. Click any header to re-sort."
        ),
        # 5. Year-over-Year Temperature Trend
        panel(
            5, f"📈 {city} — Year-over-Year Temperature Trends (2021–2026)",
            "barchart", 0, 29, 12, 9,
            f"""
            SELECT CAST(year AS VARCHAR) AS Year,
                   avg_max_temp AS `Avg Max Temp`,
                   avg_min_temp AS `Avg Min Temp`
            FROM yearly_trend
            WHERE city = '{city}'
            ORDER BY year
            """,
            opts={
                "xField": "Year",
                "stacking": "none",
                "legend": {"displayMode": "list", "placement": "bottom"}
            },
            field_cfg={"defaults": {"unit": "celsius"}, "overrides": []},
            desc=f"Historical temperature trends over the 5-year study period in {city}"
        ),
        # 6. Annual Total Rainfall
        panel(
            6, f"🌊 {city} — Annual Total Precipitation",
            "barchart", 12, 29, 12, 9,
            f"""
            SELECT CAST(year AS VARCHAR) AS Year,
                   total_precipitation AS `Annual Rainfall`
            FROM yearly_trend
            WHERE city = '{city}'
            ORDER BY year
            """,
            opts={
                "xField": "Year",
                "legend": {"displayMode": "list", "placement": "bottom"}
            },
            field_cfg={"defaults": {"unit": "mm"}, "overrides": []},
            desc=f"Total annual rainfall accumulated per year in {city}"
        ),
        # 7. Monthly Seasonality Bar Chart
        panel(
            7, f"📅 {city} — Monthly Temperature: Holiday vs Regular Day",
            "barchart", 0, 38, 14, 9,
            f"""
            SELECT CASE month
                       WHEN 1 THEN '01-Jan'
                       WHEN 2 THEN '02-Feb'
                       WHEN 3 THEN '03-Mar'
                       WHEN 4 THEN '04-Apr'
                       WHEN 5 THEN '05-May'
                       WHEN 6 THEN '06-Jun'
                       WHEN 7 THEN '07-Jul'
                       WHEN 8 THEN '08-Aug'
                       WHEN 9 THEN '09-Sep'
                       WHEN 10 THEN '10-Oct'
                       WHEN 11 THEN '11-Nov'
                       WHEN 12 THEN '12-Dec'
                   END AS Month,
                   ROUND(AVG(CASE WHEN day_type = 'Holiday' THEN avg_max_temp END), 1) AS `Holiday Max`,
                   ROUND(AVG(CASE WHEN day_type = 'Regular Day' THEN avg_max_temp END), 1) AS `Regular Day Max`
            FROM monthly_trend
            WHERE city = '{city}'
            GROUP BY month
            ORDER BY month
            """,
            opts={
                "xField": "Month",
                "legend": {"displayMode": "list", "placement": "bottom"}
            },
            field_cfg={"defaults": {"unit": "celsius"}, "overrides": []},
            desc=f"Monthly seasonal control: compare holidays vs regular days within each calendar month in {city}"
        ),
        # 8. Wettest Holidays Table
        panel(
            8, f"🌧️ {city} — Top 10 Wettest Holidays on Record",
            "table", 14, 38, 10, 9,
            f"""
            SELECT date_key AS Date,
                   holiday_name AS Holiday,
                   precipitation_mm AS `Precip (mm)`,
                   max_temp_c AS `Max Temp (C)`
            FROM mart_extreme_weather_events
            WHERE city = '{city}'
            ORDER BY precipitation_mm DESC
            LIMIT 10
            """,
            desc=f"Top 10 highest single-day rainfall holiday events in {city}"
        ),
    ]

    return {
        "dashboard": {
            "uid": uid,
            "title": f"{emoji} {city} Weather × Holiday Insights — by Louise Guerrero",
            "description": f"Dedicated insights dashboard for {city} ({country_code}) comparing weather patterns on public holidays vs regular days (2021-2026).",
            "tags": [city.lower(), "weather", "holidays", country_code.lower()],
            "schemaVersion": 39,
            "version": 1,
            "refresh": "",
            "liveNow": False,
            "graphTooltip": 1,
            "panels": panels,
            "annotations": {"list": []},
            "time": {"from": "2021-01-01T00:00:00.000Z", "to": "2026-12-31T23:59:59.000Z"},
            "timepicker": {
                "hidden": False,
                "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"]
            },
        },
        "folderId": 0,
        "overwrite": True,
        "message": f"Created {city} dedicated dashboard with Full Refresh button",
    }

def main():
    dashboards = [
        (c["city"], c["grafana_uid"], c.get("emoji", ""), c["country_code"], c["primary_color"])
        for c in CITIES
    ]

    print("=" * 60)
    print("PROVISIONING DEDICATED CITY DASHBOARDS IN GRAFANA")
    print("=" * 60)

    for city, uid, emoji, cc, color in dashboards:
        payload = build_city_dashboard(city, uid, emoji, cc, color)
        res = g("post", "/api/dashboards/db", payload)
        url = res.get("url", f"/d/{uid}")
        print(f"\n✅ {city} Dashboard Ready:")
        print(f"   Title: {payload['dashboard']['title']}")
        print(f"   URL:   {GRAFANA}{url}")

    print("\n" + "=" * 60)
    print("ALL DASHBOARDS PROVISIONED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    main()
