import json
from pathlib import Path


def test_web_json_shape():
    rows = json.loads(Path("web/src/data/top_speeds.json").read_text())
    assert len(rows) > 2000
    r = rows[0]
    assert set(r) == {"match", "team", "jersey", "player", "top_speed_kmh"}
    assert isinstance(r["top_speed_kmh"], (int, float))
