from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.storage import Storage


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply idempotent SQLite storage migrations.")
    parser.add_argument("--db", default=".runtime/quiz.db")
    args = parser.parse_args()

    storage = Storage(args.db)
    print(json.dumps(storage.migration_status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
