"""
Provisions Grafana with a MySQL datasource and the Overview dashboard.
All connection settings are driven by config.yaml.
Run from project root: python grafana/setup_grafana_mysql.py
"""
import sys
import os
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import cfg

_g      = cfg["grafana"]
GRAFANA = os.getenv("GRAFANA_URL",      _g["url"])
USER    = os.getenv("GRAFANA_USER",     _g["username"])
PASS    = os.getenv("GRAFANA_PASSWORD", _g["password"])
auth    = (USER, PASS)

def g(method, path, data=None):
    r = getattr(requests, method)(
        f"{GRAFANA}{path}", auth=auth, json=data,
        headers={"Content-Type": "application/json"}, timeout=15
    )
    if r.status_code not in (200, 409):
        print(f"  [{r.status_code}] {method.upper()} {path}: {r.text[:200]}")
    return r.json() if r.text else {}

# â”€â”€ 1. Delete old broken datasource â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Step 1: Cleaning up old datasources...")
all_ds = g("get", "/api/datasources")
for ds in all_ds:
    if ds.get("name") in ("WeatherHolidayAPI", "WeatherMySQL"):
        g("delete", f"/api/datasources/{ds['id']}")
        print(f"  Deleted: {ds['name']}")

# â”€â”€ 2. Create MySQL datasource â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Step 2: Creating MySQL datasource...")
ds_payload = {
    "name": "WeatherMySQL",
    "type": "mysql",
    "url": "127.0.0.1:3306",
    "database": "weather",
    "user": "root",
    "secureJsonData": {"password": ""},
    "jsonData": {
        "tlsAuth": False,
        "tlsAuthWithCACert": False,
        "tlsSkipVerify": True,
        "tlsMode": "skip-verify",
        "maxOpenConns": 10,
        "maxIdleConns": 10,
        "connMaxLifetime": 14400,
    },
    "access": "proxy",
    "isDefault": True,
}
ds_result = g("post", "/api/datasources", ds_payload)
ds_uid = (ds_result.get("datasource") or ds_result).get("uid", "")
ds_id  = (ds_result.get("datasource") or ds_result).get("id", "")
if not ds_uid:
    ds_result = g("get", "/api/datasources/name/WeatherMySQL")
    ds_uid = ds_result.get("uid", "")
    ds_id  = ds_result.get("id", "")
print(f"  MySQL datasource uid={ds_uid}, id={ds_id}")

# â”€â”€ 3. Test connection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Step 3: Testing connection...")
test = g("post", f"/api/datasources/{ds_id}/health")
print(f"  Health: {test.get('status','?')} - {test.get('message','')}")

# â”€â”€ Panel builder helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
pid = [1]
def panel(title, ptype, x, y, w, h, targets, opts=None, field_cfg=None, desc=""):
    pid[0] += 1
    for i, t in enumerate(targets):
        t["refId"] = chr(65 + i)
        t["datasource"] = {"type": "mysql", "uid": ds_uid}
        t.setdefault("format", "table")
    p = {
        "id": pid[0], "type": ptype, "title": title, "description": desc,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "mysql", "uid": ds_uid},
        "targets": targets,
        "options": opts or {},
        "fieldConfig": field_cfg or {
            "defaults": {"color": {"mode": "palette-classic"}},
            "overrides": []
        },
    }
    return p

def sql_target(raw_sql):
    return {
        "rawSql": raw_sql,
        "rawQuery": True,
        "format": "table",
        "intervalMs": 86400000,
        "maxDataPoints": 10000,
    }

# â”€â”€ 4. Build panels â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Step 4: Building dashboard panels...")

panels = [
    # â”€â”€ Row 1: KPI summary table (full width) â”€â”€
    panel(
        "Holiday vs Regular Day â€” Average Weather (London & Manila)",
        "table", 0, 0, 24, 7,
        [sql_target("""
            SELECT city AS City,
                   day_type AS `Day Type`,
                   num_days AS Days,
                   avg_max_temp AS `Avg Max Temp (C)`,
                   avg_min_temp AS `Avg Min Temp (C)`,
                   avg_precipitation AS `Avg Precip (mm)`
            FROM summary
            ORDER BY city, day_type
        """)],
        opts={"sortBy": [{"displayName": "City"}]},
        desc="Key question: do public holidays have different weather than regular days?",
    ),

    # â”€â”€ Row 2: Bar charts â”€â”€
    panel(
        "Avg Max Temperature: Holiday vs Regular",
        "barchart", 0, 7, 12, 9,
        [sql_target("""
            SELECT city AS City,
                   ROUND(AVG(CASE WHEN day_type = 'Holiday' THEN avg_max_temp END), 1) AS `Holiday Max Temp`,
                   ROUND(AVG(CASE WHEN day_type = 'Regular Day' THEN avg_max_temp END), 1) AS `Regular Day Max Temp`
            FROM summary
            GROUP BY city
            ORDER BY city
        """)],
        opts={
            "xField": "City", "orientation": "auto",
            "groupWidth": 0.7, "barWidth": 0.9,
            "legend": {"displayMode": "list", "placement": "bottom"},
            "tooltip": {"mode": "multi"},
        },
        field_cfg={"defaults": {"unit": "celsius"}, "overrides": []},
        desc="London holidays are ~0.6C cooler; Manila holidays are slightly warmer",
    ),
    panel(
        "Rain Probability: Holiday vs Regular (%)",
        "barchart", 12, 7, 12, 9,
        [sql_target("""
            SELECT city AS City,
                   ROUND(AVG(CASE WHEN day_type = 'Holiday' THEN pct_rainy END), 1) AS `Holiday Rain %`,
                   ROUND(AVG(CASE WHEN day_type = 'Regular Day' THEN pct_rainy END), 1) AS `Regular Day Rain %`
            FROM rain_probability
            GROUP BY city
            ORDER BY city
        """)],
        opts={
            "xField": "City", "orientation": "auto",
            "groupWidth": 0.7, "barWidth": 0.9,
            "legend": {"displayMode": "list", "placement": "bottom"},
        },
        field_cfg={"defaults": {"unit": "percent"}, "overrides": []},
        desc="~60% of days see rain in London regardless of holiday status",
    ),

    # â”€â”€ Row 3: Per-holiday table â”€â”€
    panel(
        "Per-Holiday Weather Ranking (click column to sort)",
        "table", 0, 16, 24, 10,
        [sql_target("""
            SELECT city AS City, holiday_name AS Holiday,
                   occurrences AS `Years Recorded`, avg_max_temp AS `Avg Max (C)`,
                   avg_min_temp AS `Avg Min (C)`, avg_precip AS `Avg Rain (mm)`,
                   record_high AS `Record High (C)`, record_low AS `Record Low (C)`
            FROM per_holiday ORDER BY city, avg_max_temp DESC
        """)],
        desc="Every holiday ranked by temperature. Summer Bank Holiday & Battle of the Boyne are warmest; New Year coldest.",
    ),

    # â”€â”€ Row 4: Year-over-year â”€â”€
    panel(
        "Year-over-Year Avg Max Temperature",
        "barchart", 0, 26, 12, 9,
        [sql_target("""
            SELECT CAST(year AS VARCHAR) AS Year,
                   ROUND(AVG(CASE WHEN city = 'London' THEN avg_max_temp END), 1) AS `London Max Temp`,
                   ROUND(AVG(CASE WHEN city = 'Manila' THEN avg_max_temp END), 1) AS `Manila Max Temp`
            FROM yearly_trend
            GROUP BY year
            ORDER BY year
        """)],
        opts={"xField": "Year", "stacking": "none",
              "legend": {"displayMode": "list", "placement": "bottom"}},
        field_cfg={"defaults": {"unit": "celsius"}, "overrides": []},
        desc="2026 is tracking as the warmest year across both cities",
    ),
    panel(
        "Annual Total Precipitation (mm)",
        "barchart", 12, 26, 12, 9,
        [sql_target("""
            SELECT CAST(year AS VARCHAR) AS Year,
                   ROUND(AVG(CASE WHEN city = 'London' THEN total_precipitation END), 1) AS `London Precip`,
                   ROUND(AVG(CASE WHEN city = 'Manila' THEN total_precipitation END), 1) AS `Manila Precip`
            FROM yearly_trend
            GROUP BY year
            ORDER BY year
        """)],
        opts={"xField": "Year", "legend": {"displayMode": "list", "placement": "bottom"}},
        field_cfg={"defaults": {"unit": "mm"}, "overrides": []},
        desc="Manila receives ~3-5x more annual rainfall than London",
    ),

    # â”€â”€ Row 5: Monthly comparison â”€â”€
    panel(
        "Monthly Avg Max Temp: London vs Manila",
        "barchart", 0, 35, 12, 9,
        [sql_target("""
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
                   ROUND(AVG(CASE WHEN city = 'London' AND day_type = 'Holiday' THEN avg_max_temp END), 1) AS `London Holiday`,
                   ROUND(AVG(CASE WHEN city = 'London' AND day_type = 'Regular Day' THEN avg_max_temp END), 1) AS `London Regular`,
                   ROUND(AVG(CASE WHEN city = 'Manila' AND day_type = 'Holiday' THEN avg_max_temp END), 1) AS `Manila Holiday`,
                   ROUND(AVG(CASE WHEN city = 'Manila' AND day_type = 'Regular Day' THEN avg_max_temp END), 1) AS `Manila Regular`
            FROM monthly_trend
            GROUP BY month
            ORDER BY month
        """)],
        opts={"xField": "Month", "legend": {"displayMode": "list", "placement": "bottom"}},
        field_cfg={"defaults": {"unit": "celsius"}, "overrides": []},
        desc="Controls for seasonality: compare holiday vs regular within the same month",
    ),

    # â”€â”€ Row 5b: Wettest holidays â”€â”€
    panel(
        "Top 15 Wettest Holidays on Record",
        "table", 12, 35, 12, 9,
        [sql_target("""
            SELECT date_key AS Date, city AS City,
                   holiday_name AS Holiday,
                   precipitation_mm AS `Precip (mm)`,
                   max_temp_c AS `Max Temp (C)`
            FROM wettest_holidays ORDER BY precipitation_mm DESC
        """)],
        desc="New Year and Easter dominate the wettest holidays list",
    ),
]

header_action_panel = {
    "id": 100,
    "type": "text",
    "title": "",
    "gridPos": {"x": 0, "y": 0, "w": 24, "h": 3},
    "options": {
        "mode": "html",
        "content": """
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.35rem; font-weight: 700; color: #FAFAFA;">ðŸŒ Multi-City Weather & Holiday Intelligence Overview</span>
                <span style="font-size: 0.85rem; color: #8F90A6; background: rgba(255,255,255,0.06); padding: 3px 8px; border-radius: 4px;">Medallion Gold Layer Â· Author: Louise Guerrero</span>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <a href="/d/weather-london-insights" style="text-decoration: none; padding: 6px 12px; font-size: 0.85rem; border-radius: 4px; background: rgba(78,205,196,0.15); color: #4ECDC4; border: 1px solid rgba(78,205,196,0.3); font-weight: 600;">🇬🇧 London</a>
                <a href="/d/weather-manila-insights" style="text-decoration: none; padding: 6px 12px; font-size: 0.85rem; border-radius: 4px; background: rgba(255,107,107,0.15); color: #FF6B6B; border: 1px solid rgba(255,107,107,0.3); font-weight: 600;">🇵🇭 Manila</a>
                <a href="" target="_self" style="text-decoration: none; background: linear-gradient(135deg, #6C63FF, #4ECDC4); color: #ffffff; border: none; border-radius: 5px; padding: 7px 16px; font-weight: 700; font-size: 0.85rem; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(108,99,255,0.4);">
                    🔄 Refresh All Tiles
                </a>
            </div>
        </div>
        """
    },
}

all_panels = [header_action_panel] + panels

# â”€â”€ 5. Push dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Step 5: Creating dashboard...")
payload = {
    "dashboard": {
        "uid": "weather-holiday-mysql",
        "title": "Weather x Holiday Insights - by Louise Guerrero",
        "description": "Comparing weather on public holidays vs regular days for London & Manila (2021-2026). Data: Open-Meteo + Nager.Date.",
        "tags": ["weather", "holiday", "london", "manila", "duckdb"],
        "schemaVersion": 39,
        "version": 1,
        "refresh": "",
        "liveNow": False,
        "graphTooltip": 1,
        "panels": all_panels,
        "annotations": {"list": []},
        "time": {"from": "2021-01-01T00:00:00.000Z", "to": "2026-12-31T23:59:59.000Z"},
        "timepicker": {
            "hidden": False,
            "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"]
        },
    },
    "folderId": 0,
    "overwrite": True,
    "message": "Auto-provisioned via setup_grafana_mysql.py with Full Refresh button",
}
result = g("post", "/api/dashboards/db", payload)
dash_url = result.get("url", "/")
status = result.get("status", "?")

print(f"\n{'='*60}")
print(f"STATUS : {status}")
print(f"OPEN   : {GRAFANA}{dash_url}")
print(f"LOGIN  : {USER} / {PASS}")
print(f"{'='*60}")

