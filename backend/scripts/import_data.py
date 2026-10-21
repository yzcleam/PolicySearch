import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402,F401
from app.database import engine  # noqa: E402
from app.migrations import run_migrations  # noqa: E402
from app.services import importer  # noqa: E402
from app.services.index_service import index_service  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Import policy documents from JSON, Excel or SQL")
    parser.add_argument("path", help="JSON / XLSX / SQL / ZIP file path")
    parser.add_argument(
        "--format",
        choices=["auto", "json", "excel", "sql"],
        default="auto",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=0, help="0 means all records")
    parser.add_argument("--reset", action="store_true", help="clear existing documents and index first")
    parser.add_argument("--no-index", action="store_true", help="only write PostgreSQL")
    parser.add_argument("--zip-password", default=None)
    parser.add_argument("--sheet", default=None, help="Excel sheet name")
    args = parser.parse_args()

    run_migrations(engine)
    if not args.no_index:
        index_service.ensure_index()

    def progress(result: importer.ImportResult) -> None:
        print(
            f"\r{result.total} read / {result.imported} imported / "
            f"{result.indexed} indexed / {result.skipped} skipped / {result.failed} failed",
            end="",
            flush=True,
        )

    result = importer.import_source(
        args.path,
        fmt=args.format,
        batch_size=args.batch_size,
        limit=args.limit,
        index=not args.no_index,
        reset=args.reset,
        zip_password=args.zip_password,
        sheet=args.sheet,
        progress=progress,
    )
    print("\n" + result.message)
    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
