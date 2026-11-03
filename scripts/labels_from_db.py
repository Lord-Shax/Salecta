"""Turn a label record from the artifact's database into an export file.

The online labelling page (a Claude artifact) stores one record per
annotator at labels/<id>. Claude reads those records and saves each one as
JSON. This script converts such a record into the same format the page's
download button produces, so `salecta.agreement` can score it.

Usage:
    python scripts/labels_from_db.py record.json annotations/final/labels_<code>.json [--code A2]
"""

import argparse
import json
from pathlib import Path


def convert(record: dict, code: str | None = None) -> dict:
    labels = record.get("labels", {})
    queue = record.get("queue") or list(labels)
    return {
        "tool": "salecta-annotate",
        "version": 1,
        "source": "artifact-db",
        "dataset_fp": record.get("dataset_fp"),
        "annotator": code or record.get("annotator", "?"),
        "sample_pct": record.get("sample_pct"),
        "exported_at": record.get("updated_at"),
        "n_items": len(queue),
        "labels": [labels[i] for i in queue if i in labels],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("record", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--code", help="replace the annotator's name with a code, e.g. A2")
    a = p.parse_args()
    out = convert(json.loads(a.record.read_text(encoding="utf-8")), a.code)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {a.out}: {len(out['labels'])} labels from {out['annotator']}")


if __name__ == "__main__":
    main()
