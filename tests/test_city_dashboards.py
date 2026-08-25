import requests

auth = ('admin', 'admin')

for city, uid in [("London", "weather-london-insights"), ("Manila", "weather-manila-insights")]:
    dash = requests.get(f'http://localhost:3000/api/dashboards/uid/{uid}', auth=auth).json()
    panels = dash.get('dashboard', {}).get('panels', [])
    print(f"\n{'='*50}\nTesting {city} Dashboard ({len(panels)} panels)\n{'='*50}")
    for p in panels:
        if p.get('type') == 'text' or not p.get('targets'):
            continue
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
            print(f"[FAIL] Panel {pid} ({title[:35]}): {err}")
        elif frames and frames[0]['data']['values']:
            fields = [f['name'] for f in frames[0]['schema']['fields']]
            num_rows = len(frames[0]['data']['values'][0])
            print(f"[PASS] Panel {pid} ({title[:35]}): {num_rows} rows | {fields}")
        else:
            print(f"[WARN] Panel {pid} ({title[:35]}): 0 rows")
