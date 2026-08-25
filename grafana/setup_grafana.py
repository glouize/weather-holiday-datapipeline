"""
Auto-provisions a Grafana dashboard for the Weather × Holiday project.
Uses the Infinity datasource (no SQLite plugin needed) pointing to our local JSON API.
"""
import requests
import json
import sys

GRAFANA = "http://localhost:3000"
API_URL  = "http://localhost:8888"
USER, PASS = "admin", "admin"
auth = (USER, PASS)

def g(method, path, data=None):
    r = getattr(requests, method)(f"{GRAFANA}{path}", auth=auth, json=data,
                                  headers={"Content-Type": "application/json"}, timeout=15)
    if r.status_code not in (200, 412):
        print(f"  WARN {method.upper()} {path} -> {r.status_code}: {r.text[:200]}")
    return r.json() if r.text else {}

# ── 1. Install / verify Infinity datasource ─────────────────────────────────────
print("Step 1: Checking Infinity datasource plugin...")
plugins = g("get", "/api/plugins?type=datasource")
infinity_ok = any(p.get("id") == "yesoreyeram-infinity-datasource" for p in plugins)
print(f"  Infinity plugin available: {infinity_ok}")

# ── 2. Create Infinity datasource ───────────────────────────────────────────────
print("Step 2: Creating datasource...")
ds_payload = {
    "name": "WeatherHolidayAPI",
    "type": "yesoreyeram-infinity-datasource",
    "access": "proxy",
    "isDefault": False,
    "jsonData": {"global_queries": []},
}
ds_result = g("post", "/api/datasources", ds_payload)
ds_uid = ds_result.get("datasource", {}).get("uid") or ds_result.get("uid", "")
if not ds_uid:
    # Try to fetch existing
    existing = g("get", "/api/datasources/name/WeatherHolidayAPI")
    ds_uid = existing.get("uid", "infinity")
print(f"  Datasource UID: {ds_uid}")

def infinity_panel(title, url, col_names, panel_type, x, y, w, h, unit="", desc=""):
    """Build a Grafana panel using Infinity datasource pointing to our API."""
    columns = [{"selector": c, "text": c, "type": "string"} for c in col_names]
    return {
        "id": None,
        "type": panel_type,
        "title": title,
        "description": desc,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": ds_uid},
        "options": {
            "tooltip": {"mode": "multi"},
            "legend": {"displayMode": "list", "placement": "bottom"},
        },
        "fieldConfig": {
            "defaults": {"unit": unit, "color": {"mode": "palette-classic"}},
            "overrides": [],
        },
        "targets": [{
            "refId": "A",
            "type": "json",
            "source": "url",
            "url": f"{API_URL}{url}",
            "url_options": {"method": "GET"},
            "format": "table",
            "columns": columns,
            "root_selector": "",
            "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": ds_uid},
        }],
    }

# ── 3. Build dashboard JSON ─────────────────────────────────────────────────────
print("Step 3: Building dashboard...")

panels = [
    # Row 1 — Summary comparison (full width table)
    infinity_panel(
        "📊 Holiday vs Regular Day — Average Weather",
        "/summary",
        ["city","day_type","num_days","avg_max_temp","avg_min_temp","avg_precipitation"],
        "table", 0, 0, 24, 7,
        desc="Pre-aggregated comparison of weather metrics on holidays vs regular days"
    ),
    # Row 2 — Bar charts
    infinity_panel(
        "🌡️ Avg Max Temperature by Day Type & City",
        "/summary",
        ["city","day_type","avg_max_temp"],
        "barchart", 0, 7, 12, 9, unit="celsius",
        desc="Holiday days tend to be cooler due to their clustering in winter/spring months"
    ),
    infinity_panel(
        "☂️ Rain Probability: Holiday vs Regular",
        "/rain_probability",
        ["city","day_type","pct_rainy","pct_heavy_rain"],
        "barchart", 12, 7, 12, 9, unit="percent",
        desc="~60% of days see rain regardless of whether it's a holiday"
    ),
    # Row 3 — Per holiday ranking
    infinity_panel(
        "☀️ Per-Holiday Weather Ranking",
        "/per_holiday",
        ["city","holiday_name","occurrences","avg_max_temp","avg_min_temp","avg_precip","record_high","record_low"],
        "table", 0, 16, 24, 10,
        desc="Every unique holiday ranked by average max temperature. Sortable by any column."
    ),
    # Row 4 — Year-over-year
    infinity_panel(
        "📈 Year-over-Year Avg Max Temperature",
        "/yearly",
        ["year","city","avg_max_temp","avg_min_temp"],
        "timeseries", 0, 26, 14, 9, unit="celsius",
        desc="Annual average temperatures across London and Manila"
    ),
    infinity_panel(
        "🌊 Annual Total Precipitation",
        "/yearly",
        ["year","city","total_precipitation"],
        "barchart", 14, 26, 10, 9, unit="mm",
        desc="2024 was the wettest year in London; Manila receives far more rainfall annually"
    ),
    # Row 5 — Monthly
    infinity_panel(
        "📅 Monthly Avg Temp: Holiday vs Regular",
        "/monthly",
        ["month","city","day_type","avg_max_temp"],
        "timeseries", 0, 35, 14, 9, unit="celsius",
        desc="Compare holiday vs regular day temperatures within the same calendar month to control for seasonality"
    ),
    infinity_panel(
        "🌧️ Top 10 Wettest Holidays on Record",
        "/wettest_holidays",
        ["date","city","holiday_name","precipitation_mm","max_temp_c"],
        "table", 14, 35, 10, 9,
        desc="New Year's period dominates — 3 of the top 5 wettest holidays fall Jan 1–2"
    ),
]

dashboard_payload = {
    "dashboard": {
        "uid": "weather-holiday-insights",
        "title": "🌤️ Weather × Holiday Insights — by Louise Guerrero",
        "description": "Comparing weather patterns on public holidays vs regular days for London and Manila (2021–2026).",
        "tags": ["weather", "holiday", "london", "manila"],
        "schemaVersion": 39,
        "version": 1,
        "refresh": "",
        "time": {"from": "now-5y", "to": "now"},
        "timezone": "browser",
        "panels": panels,
        "annotations": {"list": []},
    },
    "folderId": 0,
    "overwrite": True,
    "message": "Auto-provisioned by setup_grafana.py",
}

result = g("post", "/api/dashboards/db", dashboard_payload)
dash_url = result.get("url", "/")
print(f"\nDONE!")
print(f"   Open: {GRAFANA}{dash_url}")
print(f"   Login: {USER} / {PASS}")
print(f"{'='*60}")
