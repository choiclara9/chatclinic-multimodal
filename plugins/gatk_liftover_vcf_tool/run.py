from __future__ import annotations

import json
import sys

from app.models import GatkLiftoverVcfRequest
from app.services.gatk_liftover import run_gatk_liftover_vcf


def main() -> int:
    payload = json.load(sys.stdin)
    result = run_gatk_liftover_vcf(GatkLiftoverVcfRequest(**payload))
    json.dump(result.model_dump(), sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
