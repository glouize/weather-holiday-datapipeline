"""
pipeline/extract_load.py
Ingests weather + holiday data for all cities defined in config.yaml
into DuckDB Bronze Layer with audit lineage metadata.
Run from project root: python pipeline/extract_load.py
"""
import datetime
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb
import pandas as pd
import requests

from config.settings import cfg, DB_FILE, CITIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

_ing             = cfg["ingestion"]
WEATHER_API_URL  = _ing["weather_api_url"]
HOLIDAYS_API_URL = _ing["holidays_api_url"]
WEATHER_TIMEOUT  = _ing["weather_timeout_seconds"]
HOLIDAY_TIMEOUT  = _ing["holiday_timeout_seconds"]
MAX_RETRIES      = _ing["max_retries"]
RETRY_BACKOFF    = _ing["retry_backoff_seconds"]
HOLIDAY_THROTTLE = _ing["holiday_throttle_seconds"]
YEARS_LOOKBACK   = _ing["years_lookback"]
WEATHER_FIELDS   = _ing["weather_fields"]


def fetch_holidays(country_code: str, start_year: int, end_year: int) -> pd.DataFrame:
    logging.info(f"Fetching holidays for {country_code} ({start_year}-{end_year})...")
    records = []
    for year in range(start_year, end_year + 1):
        url = f"{HOLIDAYS_API_URL}/{year}/{country_code}"
        try:
            r = requests.get(url, timeout=HOLIDAY_TIMEOUT)
            if r.status_code == 404:
                logging.warning(f"No holidays for {country_code} in {year} (404).")
                continue
            r.raise_for_status()
            records.extend(r.json())
            time.sleep(HOLIDAY_THROTTLE)
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching holidays for {year}: {e}")
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "date" in df.columns:
        df = df[["date", "localName", "name", "countryCode", "fixed", "global", "types"]]
        df["types"] = df["types"].apply(lambda x: ",".join(x) if isinstance(x, list) else x)
        df["date"] = pd.to_datetime(df["date"])
    return df


def fetch_weather(lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame:
    logging.info(f"Fetching weather for lat={lat}, lon={lon} ({start_date} to {end_date})...")
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": WEATHER_FIELDS,
        "timezone": "auto",
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(WEATHER_API_URL, params=params, timeout=WEATHER_TIMEOUT)
            r.raise_for_status()
            daily = r.json().get("daily", {})
            if not daily:
                return pd.DataFrame()
            df = pd.DataFrame(daily)
            df["time"] = pd.to_datetime(df["time"])
            return df
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
            else:
                logging.error(f"All {MAX_RETRIES} attempts failed for weather fetch.")
    return pd.DataFrame()


def main():
    end_date    = datetime.date.today() - datetime.timedelta(days=7)
    start_date  = end_date.replace(year=end_date.year - YEARS_LOOKBACK)
    start_str   = start_date.strftime("%Y-%m-%d")
    end_str     = end_date.strftime("%Y-%m-%d")
    batch_id    = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    ingested_at = datetime.datetime.utcnow()

    all_weather, all_holidays = [], []

    for city_cfg in CITIES:
        city     = city_cfg["city"]
        cc       = city_cfg["country_code"]
        lat, lon = city_cfg["lat"], city_cfg["lon"]

        wdf = fetch_weather(lat, lon, start_str, end_str)
        if not wdf.empty:
            wdf["city"]           = city
            wdf["country_code"]   = cc
            wdf["_source_system"] = "open-meteo-archive"
            wdf["_batch_id"]      = batch_id
            wdf["_ingested_at"]   = ingested_at
            all_weather.append(wdf)

        hdf = fetch_holidays(cc, start_date.year, end_date.year)
        if not hdf.empty:
            hdf["_source_system"] = "nager-date-api"
            hdf["_batch_id"]      = batch_id
            hdf["_ingested_at"]   = ingested_at
            all_holidays.append(hdf)

    weather_df  = pd.concat(all_weather,  ignore_index=True) if all_weather  else pd.DataFrame()
    holidays_df = pd.concat(all_holidays, ignore_index=True) if all_holidays else pd.DataFrame()

    bronze = cfg["database"]["bronze_schema"]
    raw    = cfg["database"]["raw_schema"]

    conn = duckdb.connect(DB_FILE)
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {bronze};")
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {raw};")

    if not weather_df.empty:
        conn.execute(f"CREATE OR REPLACE TABLE {bronze}.weather  AS SELECT * FROM weather_df")
        conn.execute(f"CREATE OR REPLACE TABLE {raw}.weather     AS SELECT * FROM weather_df")
        logging.info(f"Loaded {len(weather_df)} weather rows into {bronze}.weather & {raw}.weather")

    if not holidays_df.empty:
        conn.execute(f"CREATE OR REPLACE TABLE {bronze}.holidays AS SELECT * FROM holidays_df")
        conn.execute(f"CREATE OR REPLACE TABLE {raw}.holidays    AS SELECT * FROM holidays_df")
        logging.info(f"Loaded {len(holidays_df)} holiday rows into {bronze}.holidays & {raw}.holidays")

    conn.close()
    logging.info("Bronze layer ingestion complete.")


if __name__ == "__main__":
    main()
