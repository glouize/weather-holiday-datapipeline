import requests

auth = ('admin', 'admin')
dash = requests.get('http://localhost:3000/api/dashboards/uid/weather-holiday-mysql', auth=auth).json()
panels = dash.get('dashboard', {}).get('panels', [])

print(f"Testing {len(panels)} panels in Grafana dashboard...")
for p in panels:
    pid = p.get('id')
    title = p.get('title', '')
    sql = p.get('targets', [])[0].get('rawSql', '')
    payload = {
        'queries': [{
            'refId': 'A',
            'rawSql': sql,
            'rawQuery': True,
            'format': 'table',
            'datasource': {'type': 'mysql', 'uid': 'dfw4qvaapn668b'},
            'intervalMs': 86400000,
            'maxDataPoints': 10000
        }],
        'from': '1609459200000',
        'to': '1798761600000'
    }
    r = requests.post('http://localhost:3000/api/ds/query', auth=auth, json=payload)
    res = r.json().get('results', {}).get('A', {})
    err = res.get('error', '')
    frames = res.get('frames', [])
    if err:
        print(f"[FAIL] Panel {pid} ({title[:30]}): {err}")
    elif frames:
        fields = [f['name'] for f in frames[0]['schema']['fields']]
        num_rows = len(frames[0]['data']['values'][0]) if frames[0]['data']['values'] else 0
        print(f"[PASS] Panel {pid} ({title[:30]}): {num_rows} rows | Fields: {fields}")
    else:
        print(f"[WARN] Panel {pid} ({title[:30]}): Empty response")
