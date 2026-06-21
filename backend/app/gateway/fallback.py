import json
from pathlib import Path

_FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "recommendations"

_DEFAULT = "Recommendation unavailable at this time. Please consult your advisor."


def get(stage: str) -> dict:
    path = _FIXTURES / f"{stage}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"stage": stage, "result": _DEFAULT, "source": "fallback"}
