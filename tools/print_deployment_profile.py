from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.deployment import load_deployment_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a deployment profile.")
    parser.add_argument("profile", nargs="?", default=None)
    args = parser.parse_args()
    print(json.dumps(load_deployment_profile(args.profile), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
