import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402,F401
from app.database import engine  # noqa: E402
from app.migrations import run_migrations  # noqa: E402
from app.models import Document  # noqa: E402
from app.services import catalog  # noqa: E402
from app.services.index_service import index_service, to_source  # noqa: E402
from app.services.sample_data import generate_documents  # noqa: E402


def main() -> None:
    count = 320
    reset = "--reset" in sys.argv
    if_empty = "--if-empty" in sys.argv

    for arg in sys.argv[1:]:
        if arg.isdigit():
            count = int(arg)
        elif arg.startswith("--count="):
            count = int(arg.split("=", 1)[1])

    run_migrations(engine)
    mode = index_service.ensure_index()

    existing = catalog.stats()["documents"]
    if if_empty and not reset and existing > 0:
        if index_service.count() == 0:
            indexed = index_service.index_documents(catalog.all_sources())
            print(
                f"skip seed: database has {existing} documents; "
                f"rebuilt {indexed} OpenSearch documents"
            )
        else:
            print(f"skip seed: database already has {existing} documents")
        return

    if reset:
        catalog.clear_all()
        index_service.delete_all()

    docs = generate_documents(count)
    imported = catalog.upsert_documents(docs)
    indexed = index_service.index_documents([to_source(Document(**doc)) for doc in docs])
    total = catalog.stats()["documents"]

    print(
        f"analyzer={mode} imported={imported} indexed={indexed} total={total}"
    )


if __name__ == "__main__":
    main()
