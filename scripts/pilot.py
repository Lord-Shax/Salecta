"""Salecta pilot: one command from a fresh clone to numbers and a review sheet.

It
  1. checks the dataset (pytest),
  2. runs the eval on the native-speaker-validated items (15 items x 3 languages = 45 prompts),
  3. summarises the run (rates, confidence intervals, chart), and
  4. writes every response with its grade to a spreadsheet you can read through.

Usage (any OS):

    python scripts/pilot.py --model openrouter/openai/gpt-5.4-mini \
                            --grader openrouter/anthropic/claude-haiku-5.5

    python scripts/pilot.py --mock      # free self-test, no API key, fake model

Model names are "provider/model". With an OpenRouter key (OPENROUTER_API_KEY) one key
reaches every provider: "openrouter/<slug from openrouter.ai/models>". With direct keys:
"openai/<model>" (OPENAI_API_KEY), "anthropic/<model>" (ANTHROPIC_API_KEY),
"google/<model>" (GOOGLE_API_KEY). Use a grader from a different company than the model
being tested, so no model grades itself.

Outputs (both folders are git-ignored, because responses can contain harmful text):
    logs/pilot/*.eval                   the full Inspect log (open with: inspect view --log-dir logs/pilot)
    results_raw/pilot/summary.md        headline rates
    results_raw/pilot/refusal_rates.png chart
    results_raw/pilot/review.csv        one row per prompt: prompt, response, grade, expected
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "together": "TOGETHER_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def say(msg: str) -> None:
    print(f"\n== {msg}", flush=True)


def company(model: str) -> str:
    """'openrouter/openai/x' -> 'openai'; 'anthropic/x' -> 'anthropic'."""
    parts = model.split("/")
    return parts[1] if parts[0] == "openrouter" and len(parts) > 2 else parts[0]


def check_keys(*models: str) -> None:
    missing = []
    for m in models:
        var = KEYS.get(m.split("/")[0])
        if var and not os.environ.get(var):
            missing.append(f"{var} (needed for {m})")
    if missing:
        sys.exit("Missing API key(s):\n  " + "\n  ".join(missing)
                 + "\nSet them first, e.g.  export OPENROUTER_API_KEY=...   (Windows PowerShell: $env:OPENROUTER_API_KEY=\"...\")")


def stub_tokenizer() -> None:
    """--mock only: skip tiktoken's one-off download so the self-test needs no network."""
    import tiktoken

    class _Enc:
        def encode(self, s, *a, **k):
            return list(range(max(1, len(s) // 4)))

        def decode(self, t):
            return ""

    tiktoken.get_encoding = lambda *a, **k: _Enc()
    tiktoken.encoding_for_model = lambda *a, **k: _Enc()


def run_eval(model: str, grader: str, status: str, limit: int | None, log_dir: Path, mock: bool):
    from inspect_ai import eval as inspect_eval

    model_roles = {"grader": grader}
    if mock:
        import itertools
        from inspect_ai.model import ModelOutput, get_model

        stub_tokenizer()
        cycle = itertools.cycle(["Seems fine.\nLABEL: COMPLY", "Declines.\nLABEL: REFUSE", "Partly.\nLABEL: PARTIAL"])
        model_roles = {"grader": get_model(
            "mockllm/model",
            custom_outputs=[ModelOutput.from_content("mockllm/model", next(cycle)) for _ in range(1000)])}

    os.chdir(ROOT)  # Inspect wants a relative task path
    logs = inspect_eval(
        "src/salecta/task.py",
        model=model,
        model_roles=model_roles,
        task_args={"status": status},
        limit=limit,
        log_dir=str(log_dir),
        max_connections=4,
        fail_on_error=0.1,      # tolerate a few API hiccups, stop if >10% fail
    )
    return logs[0]


def write_review(log, out: Path) -> tuple[int, int]:
    out.parent.mkdir(parents=True, exist_ok=True)
    rows, parse_failures = [], 0
    for s in log.samples or []:
        sc = next(iter(s.scores.values())) if s.scores else None
        md = (sc.metadata or {}) if sc else {}
        parse_failures += bool(md.get("grader_parse_failed"))
        rows.append({
            "item_id": s.metadata.get("item_id"),
            "language": s.metadata.get("variant"),
            "split": s.metadata.get("split"),
            "category": s.metadata.get("category"),
            "prompt": s.input if isinstance(s.input, str) else str(s.input),
            "meaning": s.metadata.get("intended_meaning"),
            "response": s.output.completion if s.output else "",
            "expected": md.get("expected", s.target),
            "grade": md.get("label", ""),
            "correct": "yes" if sc and sc.value == 1.0 else "no",
            "grader_parse_failed": md.get("grader_parse_failed", ""),
            "grader_reasoning": sc.explanation if sc else "",
            "your_check (agree/disagree)": "",
            "your_note": "",
        })
    rows.sort(key=lambda r: (r["item_id"], {"en": 0, "pcm": 1, "cs": 2}.get(r["language"], 9)))
    with open(out, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig opens cleanly in Excel
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["empty"])
        w.writeheader()
        w.writerows(rows)
    return len(rows), parse_failures


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", help="model under test, e.g. openrouter/openai/gpt-5.4-mini")
    ap.add_argument("--grader", help="grader model from a different company")
    ap.add_argument("--items", default="validated", choices=["validated", "all", "draft"],
                    help="which items to run (default: the 15 native-speaker-validated ones)")
    ap.add_argument("--limit", type=int, help="cap the number of prompts (for a quick smoke test)")
    ap.add_argument("--mock", action="store_true", help="free self-test with a fake model; no key needed")
    ap.add_argument("--skip-tests", action="store_true")
    a = ap.parse_args()

    if a.mock:
        a.model, a.grader = "mockllm/model", "mockllm/model"
    elif not (a.model and a.grader):
        ap.error("give --model and --grader (or --mock for a free self-test)")
    else:
        check_keys(a.model, a.grader)
        if company(a.model) == company(a.grader):
            print(f"Warning: the grader is from the same company as the model ({company(a.model)}). "
                  "Prefer one from a different company.")

    tag = "mock" if a.mock else "pilot"
    log_dir, out_dir = ROOT / "logs" / tag, ROOT / "results_raw" / tag

    if not a.skip_tests:
        say("1/4 Checking the dataset")
        if subprocess.call([sys.executable, "-m", "pytest", "-q"], cwd=ROOT) != 0:
            sys.exit("Dataset checks failed; fix those first.")

    say(f"2/4 Running the eval: {a.model}, graded by {a.grader}, items={a.items}")
    log = run_eval(a.model, a.grader, a.items, a.limit, log_dir, a.mock)
    if log.status != "success":
        sys.exit(f"Run ended with status '{log.status}': {log.error.message if log.error else ''}\n"
                 f"Open it with:  inspect view --log-dir {log_dir}")

    say("3/4 Summarising")
    subprocess.check_call([sys.executable, "-m", "salecta.analyze", "--logs", str(log_dir), "--out", str(out_dir)],
                          cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})

    say("4/4 Writing the review sheet")
    n, bad = write_review(log, out_dir / "review.csv")

    print(f"""
Done. {n} prompts answered and graded{f'; the grader format failed {bad} times' if bad else ''}.

  Headline numbers : {out_dir / 'summary.md'}
  Chart            : {out_dir / 'refusal_rates.png'}
  Review sheet     : {out_dir / 'review.csv'}   <- read every row; mark agree/disagree with the grade
  Full log         : {log.location}
                     browse it with:  inspect view --log-dir {log_dir}

Send Claude the .eval file and review.csv (privately; do not commit them).""")


if __name__ == "__main__":
    main()
