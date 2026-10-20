import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine  # noqa: E402
from app.migrations import SCHEMA_VERSION, run_migrations  # noqa: E402


def main() -> None:
    current = run_migrations(engine)
    print(f"schema_version={current} target={SCHEMA_VERSION}")


if __name__ == "__main__":
    main()
