import requests, json

auth = ('admin', 'admin')
dash = requests.get('http://localhost:3000/api/dashboards/uid/weather-holiday-mysql', auth=auth).json()
for p in dash['dashboard']['panels']:
    if p['id'] in (3, 6):
        print(f"=== Panel {p['id']}: {p['title']} ===")
        print(json.dumps(p, indent=2))
