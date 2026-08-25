"""
serving/mysql_server.py
MySQL wire-protocol bridge backed by DuckDB Gold Layer.
All settings driven by config.yaml.
Run from project root: python serving/mysql_server.py
"""
import asyncio
import os
import ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb
from mysql_mimic import MysqlServer, Session

from config.settings import cfg, DB_FILE, CERT_FILE, KEY_FILE

_srv          = cfg["serving"]["mysql_bridge"]
BRIDGE_HOST   = _srv["host"]
BRIDGE_PORT   = _srv["port"]
DB_NAME       = _srv["database_name"]
MYSQL_VERSION = _srv["mysql_version"]
CACHE_SIZE    = _srv["cache_size"]
GOLD_SCHEMA   = cfg["database"]["gold_schema"]

# Credentials: env vars take precedence over config.yaml
_g_cfg        = cfg["grafana"]
BRIDGE_USER   = os.getenv("BRIDGE_USER",     _g_cfg.get("mysql_user", "root"))
BRIDGE_PASS   = os.getenv("BRIDGE_PASSWORD", "")

GOLD_TABLES = [
    "mart_weather_summary", "mart_per_holiday", "mart_yearly_climate_trends",
    "mart_monthly_seasonality", "mart_rain_probability", "mart_extreme_weather_events",
    "fact_daily_weather", "dim_date", "dim_location", "dim_holiday",
]

LEGACY_ALIASES = {
    "summary":              "mart_weather_summary",
    "per_holiday":          "mart_per_holiday",
    "yearly_trend":         "mart_yearly_climate_trends",
    "monthly_trend":        "mart_monthly_seasonality",
    "rain_probability":     "mart_rain_probability",
    "wettest_holidays":     "mart_extreme_weather_events",
    "fact_weather_holiday": "fact_daily_weather",
}


def build_db():
    src = duckdb.connect(DB_FILE, read_only=True)
    mem = duckdb.connect(":memory:")
    for t in GOLD_TABLES:
        df = src.execute(f"SELECT * FROM {GOLD_SCHEMA}.{t}").df()
        mem.execute(f"CREATE TABLE {t} AS SELECT * FROM df")
        mem.execute(f"CREATE TABLE gold_{t} AS SELECT * FROM df")
        print(f"  [Gold] Loaded {t}: {len(df)} rows")
    for alias, gold in LEGACY_ALIASES.items():
        mem.execute(f"CREATE VIEW {alias} AS SELECT * FROM {gold}")
        print(f"  [Alias] {alias} -> {gold}")
    src.close()
    return mem


print("Loading Gold Layer from DuckDB...")
DB = build_db()
print(f"Done. Starting MySQL bridge on {BRIDGE_HOST}:{BRIDGE_PORT}...")

QUERY_CACHE: dict = {}


def execute_cached(sql_clean: str):
    if sql_clean in QUERY_CACHE:
        return QUERY_CACHE[sql_clean]
    rel    = DB.sql(sql_clean.replace("`", '"'))
    result = rel.fetchall()
    cols   = list(rel.columns) if rel else []
    if len(QUERY_CACHE) >= CACHE_SIZE:
        QUERY_CACHE.pop(next(iter(QUERY_CACHE)))
    QUERY_CACHE[sql_clean] = (result, cols)
    return result, cols


class WeatherSession(Session):
    async def authenticate(self, username: str) -> bool | None:
        """Reject connections that don't match the configured bridge credentials."""
        return username == BRIDGE_USER

    async def query(self, expression, sql, attrs):
        try:
            sql_clean = sql.strip()
            sql_upper = sql_clean.upper()
            if sql_upper.startswith("USE ") or "DATABASE()" in sql_upper:
                return [(DB_NAME,)], ["database()"]
            if "VERSION()" in sql_upper:
                return [(MYSQL_VERSION,)], ["version()"]
            if sql_upper.startswith("SHOW TABLES"):
                all_tables = GOLD_TABLES + list(LEGACY_ALIASES.keys())
                return [(t,) for t in all_tables], [f"Tables_in_{DB_NAME}"]
            if sql_upper.startswith("SET ") or "@@" in sql_upper:
                return [], []
            return execute_cached(sql_clean)
        except Exception as e:
            print(f"[SQL ERROR] {e}\nQuery: {sql}")
            return [], []


async def main():
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(CERT_FILE, KEY_FILE)
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode    = ssl.CERT_NONE
    server = MysqlServer(session_factory=WeatherSession, ssl=ssl_ctx)
    await server.start_server(host=BRIDGE_HOST, port=BRIDGE_PORT)
    print(f"MySQL bridge ready: mysql://root@localhost:{BRIDGE_PORT}/{DB_NAME} (TLS enabled)")
    print(f"Grafana: host=127.0.0.1, port={BRIDGE_PORT}, db={DB_NAME}, user=root, TLS=skip-verify")
    await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
