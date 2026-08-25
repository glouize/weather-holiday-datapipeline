"""
Benchmarking Grafana panel query latency
"""
import time, requests

auth = ('admin', 'admin')
dash = requests.get('http://localhost:3000/api/dashboards/uid/weather-london-insights', auth=auth).json()
panels = dash.get('dashboard', {}).get('panels', [])

print(f"Benchmarking London Dashboard ({len(panels)} panels)...")
start_all = time.time()
for p in panels:
    pid = p.get('id')
    title = p.get('title', '')
    targets = p.get('targets', [])
    if not targets:
        continue
    sql = targets[0].get('rawSql', '')
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
    t0 = time.time()
    r = requests.post('http://localhost:3000/api/ds/query', auth=auth, json=payload)
    elapsed = (time.time() - t0) * 1000
    res = r.json().get('results', {}).get('A', {})
    frames = res.get('frames', [])
    rows = len(frames[0]['data']['values'][0]) if frames and frames[0]['data']['values'] else 0
    ascii_title = title.encode('ascii', 'ignore').decode()
    print(f"Panel {pid} ({ascii_title[:30]}): {elapsed:.2f}ms ({rows} rows)")

total_elapsed = (time.time() - start_all) * 1000
print(f"\nTotal sequential time: {total_elapsed:.1f}ms")
