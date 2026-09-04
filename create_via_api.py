#使用 API key 建立工單範例

import requests, time

BASE = 'http://127.0.0.1:5003'
API_KEY = 'pep_c7504d551a27f7c74517a4d53ecfd41da023df6faee3f5eee951ed8625fd1400'
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json',
}

tickets = [
    {'title': 'Disk 95%', 'detail': '/dev/sda1 usage 95%', 'priority': 'high', 'type': 'incident'},
    {'title': 'Service Down', 'detail': 'Nginx not responding on port 443', 'priority': 'critical', 'type': 'incident'},
    {'title': 'New user request', 'detail': 'Please create account for John', 'priority': 'low', 'type': 'support'},
]

for t in tickets:
    r = requests.post(f'{BASE}/api/v1/ticket', json=t, headers=headers)
    d = r.json()
    print(f'✅ #{d["number"]} - {d["title"]} (dedupCount={d["dedupCount"]}, source={d["createdBy"]["role"]})')
    time.sleep(0.5)
