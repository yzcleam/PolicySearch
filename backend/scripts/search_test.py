import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas import SearchFilters, SearchRequest  # noqa: E402
from app.services.search_service import search  # noqa: E402

QUERIES = [
    ("增值税留抵退税", None),
    ("专精特新中小企业", None),
    ("碳达峰碳中和", None),
    ("留抵退税", SearchFilters(categories=["税收优惠"])),
]

for query, filters in QUERIES:
    print(f"\n=== {query} filters={filters} ===")
    for mode in ("keyword", "exact", "fuzzy", "smart"):
        result = search(
            SearchRequest(query=query, mode=mode, filters=filters or SearchFilters(), size=3)
        )
        titles = [hit.title[:34] for hit in result.hits]
        print(f"{mode:8s} total={result.total:4d} took={result.took_ms:3d}ms {titles}")

result = search(SearchRequest(query="", size=3))
print("\nfacets issuers:", [(b.value, b.count) for b in result.facets["issuers"][:5]])
print("facets categories:", [(b.value, b.count) for b in result.facets["categories"][:5]])
print("facets tags:", [(b.value, b.count) for b in result.facets["tags"][:5]])
