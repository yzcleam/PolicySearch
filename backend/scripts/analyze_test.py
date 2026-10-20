import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:9200"

TEXTS = ["增值税留抵退税政策与专精特新中小企业", "hello world"]


def analyze(analyzer: str, text: str):
    body = json.dumps({"analyzer": analyzer, "text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/_analyze", data=body, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return [t["token"] for t in json.loads(resp.read().decode("utf-8"))["tokens"]]


for text in TEXTS:
    print(f"text={text!r}")
    for analyzer in ("standard", "ik_smart", "ik_max_word"):
        try:
            print(f"  {analyzer}: {analyze(analyzer, text)}")
        except urllib.error.HTTPError as exc:
            print(f"  {analyzer}: HTTP {exc.code} {exc.read().decode()[:200]}")

with urllib.request.urlopen(BASE + "/_cluster/health", timeout=10) as resp:
    print("health:", resp.status, json.loads(resp.read().decode())["status"])
