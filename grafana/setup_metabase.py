"""
Auto-configure Metabase dashboard via its API.
Run this AFTER Metabase has finished initializing.
"""
import time
import requests
import json
import sys

BASE = "http://localhost:3000"
ADMIN_EMAIL = "louise@example.com"
ADMIN_PASS  = "Weather123!"

def wait_for_metabase():
    """Wait until Metabase health endpoint reports ready."""
    print("Waiting for Metabase to be ready...", end="", flush=True)
    for _ in range(120):
        try:
            r = requests.get(f"{BASE}/api/health", timeout=3)
            if r.status_code == 200 and r.json().get("status") == "ok":
                print(" Ready!")
                return True
        except:
            pass
        print(".", end="", flush=True)
        time.sleep(5)
    print("\nMetabase did not become ready in time.")
    return False

def setup_metabase():
    """Complete the initial Metabase setup wizard via API."""
    # Check if already set up
    r = requests.get(f"{BASE}/api/session/properties")
    props = r.json()
    if props.get("has-user-setup") == True:
        print("Metabase already set up. Logging in...")
        r = requests.post(f"{BASE}/api/session", json={
            "username": ADMIN_EMAIL, "password": ADMIN_PASS
        })
        if r.status_code == 200:
            return r.json()["id"]
        else:
            print(f"Login failed: {r.text}")
            return None

    # Get setup token
    setup_token = props.get("setup-token")
    if not setup_token:
        print("No setup token available.")
        return None

    print("Running first-time setup...")
    setup_payload = {
        "token": setup_token,
        "prefs": {
            "site_name": "Weather Insights",
            "site_locale": "en",
            "allow_tracking": False,
        },
        "user": {
            "first_name": "Louise",
            "last_name": "Guerrero",
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASS,
            "site_name": "Weather Insights",
        },
        "database": None,
    }

    r = requests.post(f"{BASE}/api/setup", json=setup_payload)
    if r.status_code == 200:
        print("Setup complete!")
        return r.json().get("id")
    else:
        print(f"Setup failed: {r.status_code} {r.text}")
        return None

def get_session():
    r = requests.post(f"{BASE}/api/session", json={
        "username": ADMIN_EMAIL, "password": ADMIN_PASS
    })
    r.raise_for_status()
    return r.json()["id"]

def api(method, path, token, json_data=None):
    headers = {"X-Metabase-Session": token}
    r = getattr(requests, method)(f"{BASE}{path}", headers=headers, json=json_data)
    r.raise_for_status()
    return r.json() if r.text else None

def add_sqlite_database(token):
    """Add the SQLite database to Metabase."""
    # Check existing databases
    dbs = api("get", "/api/database", token)
    for db in dbs.get("data", []):
        if db.get("name") == "Weather Holiday Warehouse":
            print(f"Database already exists (id={db['id']}). Syncing...")
            api("post", f"/api/database/{db['id']}/sync_schema", token)
            time.sleep(5)
            return db["id"]

    print("Adding SQLite database...")
    db_payload = {
        "name": "Weather Holiday Warehouse",
        "engine": "sqlite",
        "details": {
            "db": "/data/warehouse_metabase.db"
        },
        "is_full_sync": True,
        "auto_run_queries": True,
    }
    result = api("post", "/api/database", token, db_payload)
    db_id = result["id"]
    print(f"Database added (id={db_id}). Waiting for sync...")
    time.sleep(10)
    return db_id

def get_table_id(token, db_id, table_name):
    """Get the Metabase internal table ID for a given table name."""
    tables = api("get", f"/api/database/{db_id}/metadata", token)
    for table in tables.get("tables", []):
        if table["name"].upper() == table_name.upper():
            return table["id"]
    return None

def create_question(token, name, db_id, query, display="table"):
    """Create a saved question (card) in Metabase."""
    payload = {
        "name": name,
        "dataset_query": {
            "type": "native",
            "native": {"query": query},
            "database": db_id,
        },
        "display": display,
        "visualization_settings": {},
    }
    result = api("post", "/api/card", token, payload)
    print(f"  Created question: '{name}' (id={result['id']})")
    return result["id"]

def create_dashboard_with_cards(token, card_ids):
    """Create a dashboard and add the saved questions to it."""
    dash = api("post", "/api/dashboard", token, {
        "name": "🌤️ Weather × Holiday Insights — by Louise Guerrero",
        "description": "Comparing weather conditions on public holidays vs regular days for London & Manila.",
    })
    dash_id = dash["id"]
    print(f"Dashboard created (id={dash_id})")

    # Layout: 2 columns, cards placed in a grid
    cards_payload = []
    for i, card_id in enumerate(card_ids):
        col = (i % 2) * 9
        row = (i // 2) * 8
        cards_payload.append({
            "id": -(i + 1),
            "card_id": card_id,
            "row": row,
            "col": col,
            "size_x": 9,
            "size_y": 8,
        })

    api("put", f"/api/dashboard/{dash_id}", token, {"dashcards": cards_payload})
    print(f"Added {len(card_ids)} cards to dashboard.")
    return dash_id

def main():
    if not wait_for_metabase():
        sys.exit(1)

    token = setup_metabase()
    if not token:
        token = get_session()

    db_id = add_sqlite_database(token)

    print("\nCreating insight questions...")

    q1 = create_question(token, "📊 Holiday vs Regular Day — Avg Weather", db_id, """
        SELECT day_type AS "Day Type",
               num_days AS "Days",
               avg_max_temp AS "Avg Max Temp (°C)",
               avg_min_temp AS "Avg Min Temp (°C)",
               avg_precipitation AS "Avg Precip (mm)",
               total_precipitation AS "Total Precip (mm)"
        FROM summary_holiday_vs_regular
        ORDER BY city, day_type
    """, "table")

    q2 = create_question(token, "🌡️ Temperature: Holiday vs Regular (Bar)", db_id, """
        SELECT city AS "City",
               day_type AS "Day Type",
               avg_max_temp AS "Avg Max Temp °C"
        FROM summary_holiday_vs_regular
    """, "bar")

    q3 = create_question(token, "☀️ Per-Holiday Weather Ranking", db_id, """
        SELECT holiday_name AS "Holiday",
               city AS "City",
               occurrences AS "Count",
               avg_max_temp AS "Avg Max °C",
               avg_min_temp AS "Avg Min °C",
               avg_precip AS "Avg Rain mm",
               record_high AS "Record High °C",
               record_low AS "Record Low °C"
        FROM per_holiday_weather
        ORDER BY city, avg_max_temp DESC
    """, "table")

    q4 = create_question(token, "🌧️ Top 10 Wettest Holidays", db_id, """
        SELECT date_key AS "Date",
               city AS "City",
               holiday_name AS "Holiday",
               precipitation_sum AS "Precipitation (mm)",
               temperature_2m_max AS "Max Temp °C"
        FROM fact_weather_holiday
        WHERE day_type = 'Holiday'
        ORDER BY precipitation_sum DESC
        LIMIT 10
    """, "table")

    q5 = create_question(token, "📈 Year-over-Year Temperature Trend", db_id, """
        SELECT year AS "Year",
               city AS "City",
               avg_max_temp AS "Avg Max Temp",
               avg_min_temp AS "Avg Min Temp"
        FROM yearly_trend
        ORDER BY city, year
    """, "line")

    q6 = create_question(token, "🌊 Annual Precipitation by City", db_id, """
        SELECT year AS "Year",
               city AS "City",
               total_precipitation AS "Total Precipitation (mm)"
        FROM yearly_trend
        ORDER BY city, year
    """, "bar")

    q7 = create_question(token, "📅 Monthly Avg Temp: Holiday vs Regular", db_id, """
        SELECT month AS "Month",
               city AS "City",
               day_type AS "Day Type",
               ROUND(AVG(temperature_2m_max), 1) AS "Avg Max Temp °C"
        FROM fact_weather_holiday
        GROUP BY month, city, day_type
        ORDER BY city, month
    """, "line")

    q8 = create_question(token, "☂️ Rain Probability: Holiday vs Regular", db_id, """
        SELECT city AS "City",
               day_type AS "Day Type",
               COUNT(*) AS "Total Days",
               SUM(CASE WHEN precipitation_sum > 0 THEN 1 ELSE 0 END) AS "Rainy Days",
               ROUND(100.0 * SUM(CASE WHEN precipitation_sum > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS "% Rainy"
        FROM fact_weather_holiday
        GROUP BY city, day_type
    """, "bar")

    print("\nAssembling dashboard...")
    dash_id = create_dashboard_with_cards(token, [q1, q2, q3, q4, q5, q6, q7, q8])

    print(f"\n{'='*60}")
    print(f"✅ Dashboard ready at: {BASE}/dashboard/{dash_id}")
    print(f"   Login: {ADMIN_EMAIL} / {ADMIN_PASS}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
