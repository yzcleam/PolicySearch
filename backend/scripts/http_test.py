import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def post(path, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        BASE + path, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


result = post(
    "/api/search",
    {
        "query": "增值税留抵退税",
        "mode": "smart",
        "filters": {},
        "page": 1,
        "size": 5,
        "sort": "relevance",
        "slop": 2,
    },
)
print("total:", result["total"], "took:", result["took_ms"], "mode:", result["mode"])
for hit in result["hits"]:
    print(" -", hit["score"], hit["title"][:40], "|", hit["issuer"])
    if hit["highlights"]:
        print("   highlight:", hit["highlights"][0]["field"], hit["highlights"][0]["text"][:90])
print("facets:", {key: len(value) for key, value in result["facets"].items()})

doc = get(f"/api/documents/{result['hits'][0]['doc_id']}")
print("document:", doc["title"], "| content chars:", len(doc["content"]), "| tags:", doc["tags"])

for mode in ("keyword", "exact", "fuzzy"):
    response = post(
        "/api/search",
        {"query": "专精特新", "mode": mode, "filters": {}, "page": 1, "size": 2},
    )
    print(f"{mode}: total={response['total']} took={response['took_ms']}ms")
