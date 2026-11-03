"""Convert the Google Sheet of labels into one file per annotator.

In the sheet: File → Download → Comma-separated values (.csv), with the
"labels" tab open. Then:

    python scripts/labels_from_sheet.py salecta_labels.csv --out annotations/final

Each annotator session becomes annotations/final/labels_<name>_<n>.json, in
the format `python -m salecta.agreement` reads. Use --codes to replace names
with codes, e.g. --codes "Ada=A1,Tunde=A2".
"""

import argparse
import csv
import json
import re
from collections import OrderedDict
from pathlib import Path


def convert(csv_path: Path, codes: dict[str, str]) -> list[dict]:
    sessions: "OrderedDict[str, dict]" = OrderedDict()
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sid = row["session_id"]
            s = sessions.setdefault(sid, {
                "tool": "salecta-annotate", "version": 1, "source": "google-sheet",
                "annotator": codes.get(row["annotator"], row["annotator"]),
                "session_id": sid, "dataset_fp": row["dataset_fp"],
                "sample_pct": int(row["sample_pct"]) if row["sample_pct"].isdigit() else None,
                "labels": OrderedDict(),
            })
            # A later row for the same item replaces an earlier one.
            s["labels"][row["item_id"]] = {
                "item_id": row["item_id"], "decision": row["decision"], "natural": row["natural"],
                "meaning": row["meaning"].lstrip("'"), "comment": row["comment"].lstrip("'"),
                "text": row["text"], "ts": row["labelled_at"],
            }
    out = []
    for s in sessions.values():
        s["labels"] = list(s["labels"].values())
        s["n_items"] = len(s["labels"])
        out.append(s)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--out", type=Path, default=Path("annotations/final"))
    p.add_argument("--codes", default="", help='e.g. "Ada=A1,Tunde=A2"')
    a = p.parse_args()
    codes = dict(kv.split("=", 1) for kv in a.codes.split(",") if "=" in kv)
    a.out.mkdir(parents=True, exist_ok=True)
    seen: dict[str, int] = {}
    for s in convert(a.csv, codes):
        base = re.sub(r"[^A-Za-z0-9_-]+", "_", s["annotator"]) or "annotator"
        seen[base] = seen.get(base, 0) + 1
        path = a.out / f"labels_{base}_{seen[base]}.json"
        path.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {path}: {s['n_items']} labels from {s['annotator']}")


if __name__ == "__main__":
    main()
