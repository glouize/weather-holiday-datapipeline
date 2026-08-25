import requests

auth = ('admin', 'admin')

# Check datasource
ds = requests.get('http://localhost:3000/api/datasources/name/WeatherMySQL', auth=auth).json()
current_uid = ds.get('uid')
current_id  = ds.get('id')
print('Current DS uid:', current_uid, '| id:', current_id)

# Fetch dashboard panels
dash = requests.get('http://localhost:3000/api/dashboards/uid/weather-holiday-mysql', auth=auth).json()
panels = dash.get('dashboard', {}).get('panels', [])
uids_in_panels = set()
for p in panels:
    panel_uid = p.get('datasource', {}).get('uid', '')
    uids_in_panels.add(panel_uid)
    tgt_uid = p.get('targets', [{}])[0].get('datasource', {}).get('uid', '') if p.get('targets') else ''
    uids_in_panels.add(tgt_uid)
    print(f"  Panel '{p.get('title','')[:35]}': panel_uid={panel_uid} | target_uid={tgt_uid}")

print()
print('UIDs found in dashboard panels:', uids_in_panels)
print('Current datasource UID:        ', current_uid)
print('UID MATCH:', current_uid in uids_in_panels)
