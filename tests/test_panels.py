import requests, json

auth = ('admin', 'admin')
ds_uid = 'dfw4qvaapn668b'

panels = {
    "Summary table": "SELECT city AS City, day_type AS `Day Type`, num_days AS `Days`, avg_max_temp AS `Avg Max Temp (C)` FROM summary ORDER BY city, day_type",
    "Temp bar":      "SELECT city AS City, ROUND(AVG(CASE WHEN day_type = 'Holiday' THEN avg_max_temp END), 1) AS `Holiday Max (°C)`, ROUND(AVG(CASE WHEN day_type = 'Regular Day' THEN avg_max_temp END), 1) AS `Regular Day Max (°C)` FROM summary GROUP BY city",
    "Rain prob":     "SELECT city AS City, ROUND(AVG(CASE WHEN day_type = 'Holiday' THEN pct_rainy END), 1) AS `Holiday Rain %`, ROUND(AVG(CASE WHEN day_type = 'Regular Day' THEN pct_rainy END), 1) AS `Regular Day Rain %` FROM rain_probability GROUP BY city",
    "Per-holiday":   "SELECT city AS City, holiday_name AS Holiday, occurrences AS `# Years`, avg_max_temp AS `Avg Max C` FROM per_holiday ORDER BY city, avg_max_temp DESC LIMIT 5",
    "Yearly":        "SELECT year AS Year, ROUND(AVG(CASE WHEN city = 'London' THEN avg_max_temp END), 1) AS `London Max (°C)`, ROUND(AVG(CASE WHEN city = 'Manila' THEN avg_max_temp END), 1) AS `Manila Max (°C)` FROM yearly_trend GROUP BY year",
    "Monthly":       "SELECT month AS Month, ROUND(AVG(CASE WHEN city = 'London' AND day_type = 'Holiday' THEN avg_max_temp END), 1) AS `London Holiday (°C)` FROM monthly_trend GROUP BY month",
    "Wettest":       "SELECT date_key AS Date, city AS City, holiday_name AS Holiday, precipitation_mm AS `Precip (mm)` FROM wettest_holidays ORDER BY precipitation_mm DESC LIMIT 5",
}

for name, sql in panels.items():
    payload = {
        "queries": [{
            "refId": "A",
            "rawSql": sql,
            "rawQuery": True,
            "format": "table",
            "datasource": {"type": "mysql", "uid": ds_uid},
            "intervalMs": 86400000,
            "maxDataPoints": 10000
        }],
        "from": "1609459200000",
        "to": "1798761600000"
    }
    r = requests.post('http://localhost:3000/api/ds/query', auth=auth, json=payload)
    data = r.json()
    result = data.get('results', {}).get('A', {})
    error = result.get('error', '')
    frames = result.get('frames', [])
    if error:
        print(f"[FAIL] {name}: {error}")
    elif frames:
        vals = frames[0]['data']['values']
        cols = [f['name'] for f in frames[0]['schema']['fields']]
        row_count = len(vals[0]) if (vals and len(vals) > 0 and len(vals[0]) > 0) else 0
        print(f"[OK  ] {name}: {row_count} rows | Cols: {cols}")
        if row_count > 0:
            sample_rows = list(zip(*[v[:2] for v in vals]))
            print(f"       Sample: {sample_rows}")
    else:
        print(f"[EMPTY] {name}: no frames")
