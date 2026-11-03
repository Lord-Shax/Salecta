"""Compare a second annotator's labels with the dataset's expected labels.

Usage:
    python -m salecta.agreement salecta_labels_AO.json --out results/agreement.md
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from salecta.task import DATA, load_items


def cohens_kappa(a: list[str], b: list[str]) -> float:
    """Cohen's kappa for two raters over the same items."""
    if len(a) != len(b) or not a:
        raise ValueError("need two equal-length, non-empty label lists")
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def interpret(k: float) -> str:
    # Landis & Koch (1977) bands.
    for cut, word in [(0.8, "almost perfect"), (0.6, "substantial"), (0.4, "moderate"),
                      (0.2, "fair"), (0.0, "slight")]:
        if k > cut:
            return word
    return "poor"


def report(labels_path: Path, items_path: Path = DATA) -> str:
    data = json.loads(labels_path.read_text(encoding="utf-8"))
    items = {it["id"]: it for it in load_items(items_path)}
    rows = [l for l in data["labels"] if l["item_id"] in items]
    sure = [l for l in rows if l["decision"] in ("COMPLY", "REFUSE")]
    unsure = [l for l in rows if l["decision"] == "UNSURE"]

    gold = [items[l["item_id"]]["expected"] for l in sure]
    theirs = [l["decision"] for l in sure]
    agree = sum(g == t for g, t in zip(gold, theirs))

    lines = [f"# Annotation agreement: {data.get('annotator', '?')}", "",
             f"- Items labelled: {len(rows)} (sample setting: {data.get('sample_pct')}%)",
             f"- Marked \"not sure\": {len(unsure)} (excluded from κ, listed below)"]
    if sure:
        k = cohens_kappa(gold, theirs)
        lines += [f"- Raw agreement on help/refuse: {agree}/{len(sure)} ({agree / len(sure):.0%})",
                  f"- Cohen's κ: **{k:.2f}** ({interpret(k)})"]
        if len(set(gold)) < 2:
            lines.append("- Note: the sample contains only one expected class, so κ is not meaningful yet.")
    nat = Counter(l["natural"] for l in rows)
    lines += [f"- Naturalness: {nat.get('yes', 0)} yes, {nat.get('somewhat', 0)} somewhat, {nat.get('no', 0)} no", ""]

    def block(title: str, subset: list[dict]) -> list[str]:
        if not subset:
            return []
        out = [f"## {title}", "", "| Item | Expected | Annotator | Natural | Their reading | Comment |",
               "|---|---|---|---|---|---|"]
        for l in subset:
            it = items[l["item_id"]]
            cell = lambda s: (s or "").replace("|", "\\|").replace("\n", " ")
            out.append(f"| {l['item_id']} | {it['expected']} | {l['decision']} | {l['natural']} | "
                       f"{cell(l['meaning'])} | {cell(l.get('comment'))} |")
        return out + [""]

    lines += block("Disagreements: fix or drop these items", [l for l in sure if l["decision"] != items[l["item_id"]]["expected"]])
    lines += block("Not sure", unsure)
    lines += block("Pidgin flagged as unnatural: rewrite these", [l for l in rows if l["natural"] != "yes"])
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("labels", type=Path, help="JSON file exported from annotate/index.html")
    p.add_argument("--items", type=Path, default=DATA)
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()
    text = report(a.labels, a.items)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {a.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
