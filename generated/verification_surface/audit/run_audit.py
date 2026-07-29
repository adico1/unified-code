import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit.generated_audit import audit

result = audit({"value": {}, "depths": (), "axes": (), "evidence": (), "state": "formed"})
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
raise SystemExit({"valid": 0, "invalid": 1}[result["state"]])
