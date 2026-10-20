import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def post(path, payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


print("reindex:", post("/api/admin/reindex"))
print("seed:", post("/api/admin/seed", {"count": 320, "reset": True}))
print("stats:", get("/api/stats"))
