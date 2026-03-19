import requests
import json

url = "http://127.0.0.1:5000/api/recommend"
payload = {
    "location": "Chembarambakkam",
    "symptom": "regular check up for 3-months pregnancy"
}

try:
    print("Testing API with payload:", payload)
    res = requests.post(url, json=payload, timeout=5)
    print("Status Code:", res.status_code)
    print("Response JSON:\n", json.dumps(res.json(), indent=2))
except Exception as e:
    print("Error calling API:", e)
