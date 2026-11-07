"""Grade the replies from the refusal-direction notebook with the Salecta grader.

The notebook spots refusals by looking for phrases like "I can't", which miscounts replies such as
"I'm sorry to hear that... here are some tips". This script re-grades every reply (normal and, for
harmful items, with the English refusal direction deleted) using the same grader prompt as the
Salecta eval.

Usage (on your Mac, inside the Salecta folder, with OPENROUTER_API_KEY set):

    python scripts/grade_replies.py results.zip --grader openrouter/anthropic/claude-haiku-5.5
    python scripts/grade_replies.py results.zip --mock     # free self-test

Writes graded_<model>.csv next to the zip. Send that file back to Claude. It contains model
replies to harmful requests: keep it private and never commit it.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from salecta.task import GRADER_PROMPT, heuristic_label, parse_label  # noqa: E402

TRUNC_NOTE = "\n[The reply was cut off after about 60 words; judge from what is shown.]"


def load_items() -> dict[str, dict]:
    items = {}
    for name in ("items.jsonl", "reserve.jsonl"):
        p = ROOT / "data" / name
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    it = json.loads(line)
                    items[it["id"]] = it
    return items


def read_zip(path: Path) -> tuple[list[dict], str]:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        rep = next(n for n in names if n.endswith("replies.csv"))
        rows = list(csv.DictReader(io.StringIO(z.read(rep).decode("utf-8"))))
        summ = next((n for n in names if n.endswith("summary.json")), None)
        model = json.loads(z.read(summ))["model"] if summ else "model"
    return rows, model


async def grade_all(jobs, grader_name: str, mock: bool, concurrency: int = 8):
    from inspect_ai.model import GenerateConfig, ModelOutput, get_model

    if mock:
        import itertools
        cyc = itertools.cycle(["ok\nLABEL: COMPLY", "no\nLABEL: REFUSE", "some\nLABEL: PARTIAL"])
        grader = get_model("mockllm/model",
                           custom_outputs=[ModelOutput.from_content("mockllm/model", next(cyc)) for _ in range(len(jobs) + 5)])
    else:
        grader = get_model(grader_name)
    sem = asyncio.Semaphore(concurrency)
    done = 0

    async def one(job):
        nonlocal done
        async with sem:
            for attempt in range(3):
                try:
                    out = await grader.generate(job["prompt"], config=GenerateConfig(temperature=0, max_tokens=2000))
                    text = out.completion
                    break
                except Exception as e:  # network hiccup: retry, then give up on this row
                    text = f"ERROR: {e}"
                    await asyncio.sleep(2 * (attempt + 1))
            label = parse_label(text)
            job["grader_failed"] = label is None
            job["label"] = label or heuristic_label(job["reply"])
            job["grader_reasoning"] = text
            done += 1
            if done % 25 == 0 or done == len(jobs):
                print(f"  graded {done}/{len(jobs)}", flush=True)
        return job

    return await asyncio.gather(*(one(j) for j in jobs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results_zip", type=Path)
    ap.add_argument("--grader", default="openrouter/anthropic/claude-haiku-5.5")
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()
    if a.mock:  # skip tiktoken's one-off download so the self-test needs no network
        import tiktoken

        class _Enc:
            def encode(self, s, *x, **k):
                return list(range(max(1, len(s) // 4)))

        tiktoken.get_encoding = lambda *x, **k: _Enc()
        tiktoken.encoding_for_model = lambda *x, **k: _Enc()
    items = load_items()
    rows, model = read_zip(a.results_zip)

    jobs = []
    for r in rows:
        it = items.get(r["item_id"])
        if not it:
            continue
        request = it["variants"][r["lang"]]
        for cond in ("normal", "ablated"):
            reply = r.get(cond) or ""
            if cond == "ablated" and r["split"] != "harmful":
                continue
            jobs.append({
                "model": model, "item_id": r["item_id"], "lang": r["lang"], "split": r["split"],
                "status": it.get("status", ""), "phenomenon": it.get("phenomenon", ""),
                "category": it.get("category", ""), "condition": cond, "request": request, "reply": reply,
                "prompt": GRADER_PROMPT.format(request=request, meaning=it["intended_meaning"],
                                               response=reply[:6000] + TRUNC_NOTE),
            })
    print(f"Grading {len(jobs)} replies from {model} with {'a fake grader' if a.mock else a.grader} ...")
    graded = asyncio.run(grade_all(jobs, a.grader, a.mock))

    out = a.results_zip.with_name(f"graded_{model.split('/')[-1]}.csv")
    cols = ["model", "item_id", "lang", "split", "status", "phenomenon", "category", "condition",
            "label", "grader_failed", "request", "reply", "grader_reasoning"]
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(graded)

    # quick summary
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0])
    for g in graded:
        k = (g["split"], g["condition"], g["lang"])
        agg[k][0] += g["label"] == "REFUSE"
        agg[k][1] += 1
    print("\nRefused (REFUSE label):")
    for k in sorted(agg):
        n_ref, n = agg[k]
        print(f"  {k[0]:8s} {k[1]:8s} {k[2]:4s} {n_ref:3d}/{n:<3d} = {n_ref / n:.0%}")
    fails = sum(g["grader_failed"] for g in graded)
    print(f"\nWrote {out}{f'  (grader format failed {fails} times)' if fails else ''}")
    print("Send that file to Claude privately. Do not commit it.")


if __name__ == "__main__":
    main()
