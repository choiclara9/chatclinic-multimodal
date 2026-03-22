from __future__ import annotations

import json
import sys

from app.models import PlinkRequest
from app.services.plink import run_plink


def main() -> int:
    payload = json.load(sys.stdin)
    result = run_plink(PlinkRequest(**payload))
    json.dump(result.model_dump(), sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
