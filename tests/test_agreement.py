import json

import pytest

from salecta.agreement import cohens_kappa, report


def test_kappa_perfect_and_chance():
    assert cohens_kappa(["A", "B", "A", "B"], ["A", "B", "A", "B"]) == 1.0
    assert cohens_kappa(["A", "A", "B", "B"], ["A", "B", "A", "B"]) == 0.0


def test_kappa_known_value():
    # 2x2 table: a=20, b=5, c=10, d=15 -> po=0.70, pe=0.50, kappa=0.40
    a = ["Y"] * 25 + ["N"] * 25
    b = ["Y"] * 20 + ["N"] * 5 + ["Y"] * 10 + ["N"] * 15
    assert cohens_kappa(a, b) == pytest.approx(0.4)


def test_report_runs(tmp_path):
    labels = {"annotator": "T", "sample_pct": 100, "labels": [
        {"item_id": "B001", "decision": "COMPLY", "natural": "yes", "meaning": "praise", "comment": ""},
        {"item_id": "H001", "decision": "COMPLY", "natural": "somewhat", "meaning": "bank sms", "comment": "x|y"},
        {"item_id": "B003", "decision": "UNSURE", "natural": "yes", "meaning": "ace exam", "comment": ""},
    ]}
    f = tmp_path / "l.json"
    f.write_text(json.dumps(labels))
    out = report(f)
    assert "Raw agreement on help/refuse: 1/2" in out
    assert "H001" in out and "Not sure" in out
