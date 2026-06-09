import requests
import json

base_url = "http://127.0.0.1:8888/api/workflow/run"
payload = {
    "inputs": {},
    "query": "录入",
    "workflow_type": "suijisuicha",
    "user": "001",
    "response_mode": "streaming"
}

with requests.post(base_url, json=payload, stream=True) as r:
    print(r.status_code)
    for line in r.iter_lines():
        if line:
            print(line.decode('utf-8'))
