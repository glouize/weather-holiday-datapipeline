"""
Local JSON API server for Grafana Infinity datasource.
Serves pre-computed analytics from DuckDB as JSON endpoints.
Run: python grafana_api.py
"""
import duckdb
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import urllib.parse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

ROOT    = Path(__file__).resolve().parent.parent   # project root
DB_FILE = str(ROOT / "warehouse.duckdb")
PORT    = 8888

def run_query(sql: str):
    conn = duckdb.connect(DB_FILE, read_only=True)
    df = conn.execute(sql).df()
    conn.close()
    return df.to_dict(orient="records")

ENDPOINTS = {
    "/summary": """
        SELECT
            w.city AS city,
            CASE WHEN h.date IS NOT NULL THEN 'Holiday' ELSE 'Regular Day' END AS day_type,
            COUNT(*)                                          AS num_days,
            ROUND(AVG(w.temperature_2m_max), 2)              AS avg_max_temp,
            ROUND(AVG(w.temperature_2m_min), 2)              AS avg_min_temp,
            ROUND(AVG(w.precipitation_sum), 2)               AS avg_precipitation
        FROM raw.weather w
        LEFT JOIN raw.holidays h
            ON w.time::DATE = h.date::DATE AND w.country_code = h.countryCode
        GROUP BY w.city, day_type
        ORDER BY w.city, day_type
    """,
    "/per_holiday": """
        SELECT
            w.city                             AS city,
            h.name                             AS holiday_name,
            COUNT(*)::INT                      AS occurrences,
            ROUND(AVG(w.temperature_2m_max),1) AS avg_max_temp,
            ROUND(AVG(w.temperature_2m_min),1) AS avg_min_temp,
            ROUND(AVG(w.precipitation_sum),1)  AS avg_precip,
            ROUND(MAX(w.temperature_2m_max),1) AS record_high,
            ROUND(MIN(w.temperature_2m_min),1) AS record_low
        FROM raw.weather w
        JOIN raw.holidays h
            ON w.time::DATE = h.date::DATE AND w.country_code = h.countryCode
        GROUP BY w.city, h.name
        ORDER BY w.city, avg_max_temp DESC
    """,
    "/yearly": """
        SELECT
            EXTRACT(YEAR FROM w.time)::INT      AS year,
            w.city                              AS city,
            ROUND(AVG(w.temperature_2m_max),2)  AS avg_max_temp,
            ROUND(AVG(w.temperature_2m_min),2)  AS avg_min_temp,
            ROUND(SUM(w.precipitation_sum),1)   AS total_precipitation
        FROM raw.weather w
        GROUP BY year, w.city
        ORDER BY w.city, year
    """,
    "/monthly": """
        SELECT
            EXTRACT(MONTH FROM w.time)::INT     AS month,
            w.city                              AS city,
            CASE WHEN h.date IS NOT NULL THEN 'Holiday' ELSE 'Regular Day' END AS day_type,
            ROUND(AVG(w.temperature_2m_max),1)  AS avg_max_temp,
            ROUND(AVG(w.precipitation_sum),1)   AS avg_precip
        FROM raw.weather w
        LEFT JOIN raw.holidays h
            ON w.time::DATE = h.date::DATE AND w.country_code = h.countryCode
        GROUP BY month, w.city, day_type
        ORDER BY w.city, month
    """,
    "/rain_probability": """
        SELECT
            w.city                                                                AS city,
            CASE WHEN h.date IS NOT NULL THEN 'Holiday' ELSE 'Regular Day' END   AS day_type,
            COUNT(*)                                                               AS total_days,
            SUM(CASE WHEN w.precipitation_sum > 0 THEN 1 ELSE 0 END)             AS rainy_days,
            ROUND(100.0 * SUM(CASE WHEN w.precipitation_sum > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_rainy,
            ROUND(100.0 * SUM(CASE WHEN w.precipitation_sum > 5 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_heavy_rain
        FROM raw.weather w
        LEFT JOIN raw.holidays h
            ON w.time::DATE = h.date::DATE AND w.country_code = h.countryCode
        GROUP BY w.city, day_type
    """,
    "/wettest_holidays": """
        SELECT
            w.time::VARCHAR                    AS date,
            w.city                             AS city,
            h.name                             AS holiday_name,
            ROUND(w.precipitation_sum,1)       AS precipitation_mm,
            ROUND(w.temperature_2m_max,1)      AS max_temp_c
        FROM raw.weather w
        JOIN raw.holidays h
            ON w.time::DATE = h.date::DATE AND w.country_code = h.countryCode
        ORDER BY w.precipitation_sum DESC
        LIMIT 10
    """,
    "/timeline": """
        SELECT
            w.time::VARCHAR                   AS date,
            w.city                            AS city,
            w.temperature_2m_max              AS max_temp,
            w.precipitation_sum               AS precipitation,
            CASE WHEN h.date IS NOT NULL THEN 1 ELSE 0 END AS is_holiday,
            COALESCE(h.name,'Regular Day')    AS day_label
        FROM raw.weather w
        LEFT JOIN raw.holidays h
            ON w.time::DATE = h.date::DATE AND w.country_code = h.countryCode
        ORDER BY w.city, w.time
    """,
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.info(f"{self.address_string()} - {format % args}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # CORS headers for Grafana
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if path == "/":
            result = {"status": "ok", "endpoints": list(ENDPOINTS.keys())}
        elif path in ENDPOINTS:
            try:
                result = run_query(ENDPOINTS[path])
            except Exception as e:
                result = {"error": str(e)}
        else:
            result = {"error": f"Unknown endpoint: {path}", "available": list(ENDPOINTS.keys())}

        self.wfile.write(json.dumps(result).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    logging.info(f"🚀 Grafana JSON API running on http://localhost:{PORT}")
    logging.info(f"   Available endpoints: {', '.join(ENDPOINTS.keys())}")
    server.serve_forever()
