"""Salecta full run: every model, all 60 validated items, three languages, in one command.

    export OPENROUTER_API_KEY=...
    python scripts/full_run.py            # runs the three default models (180 prompts each)
    python scripts/full_run.py --mock     # free self-test, no key

For each model it runs the eval, then writes the summary, chart and a review sheet, and packs
everything into salecta_full_run.zip for analysis. A model that already has a finished log in
logs/full is skipped, so an interrupted run can simply be started again.

Each model is graded by a model from a different company (no model grades its own answers).
Outputs are git-ignored: replies to harmful requests must never be published.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pilot import ROOT, check_keys, company, run_eval, say, write_review  # noqa: E402

# (model under test, grader). Slugs from openrouter.ai/models.
DEFAULT = [
    ("openrouter/openai/gpt-5.4-mini", "openrouter/anthropic/claude-haiku-5.5"),
    ("openrouter/meta-llama/llama-3.3-70b-instruct", "openrouter/anthropic/claude-haiku-5.5"),
    ("openrouter/anthropic/claude-haiku-5.5", "openrouter/openai/gpt-5.4-mini"),
]


def finished(log_dir: Path, model: str) -> bool:
    from inspect_ai.log import list_eval_logs, read_eval_log

    for info in list_eval_logs(str(log_dir)):
        h = read_eval_log(info, header_only=True)
        if h.status == "success" and h.eval.model in (model, model.removeprefix("openrouter/")):
            return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", action="append", metavar="MODEL=GRADER",
                    help="replace the default models; repeat for each, e.g. --pair openrouter/a/x=openrouter/b/y")
    ap.add_argument("--limit", type=int, help="cap prompts per model (quick smoke test)")
    ap.add_argument("--rerun", action="append", default=[], metavar="MODEL",
                    help="run this model again even if it already finished, e.g. --rerun claude-haiku-5.5")
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()

    pairs = [tuple(p.split("=", 1)) for p in a.pair] if a.pair else DEFAULT
    if a.mock:
        pairs = [("mockllm/model", "mockllm/model")]
    else:
        check_keys(*[m for p in pairs for m in p])
        for m, g in pairs:
            if company(m) == company(g):
                sys.exit(f"{m} would be graded by its own company ({g}). Choose another grader.")

    tag = "mock_full" if a.mock else "full"
    log_dir, out_dir = ROOT / "logs" / tag, ROOT / "results_raw" / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    say("Checking the dataset")
    if subprocess.call([sys.executable, "-m", "pytest", "-q"], cwd=ROOT) != 0:
        sys.exit("Dataset checks failed; fix those first.")

    failed = []
    for i, (model, grader) in enumerate(pairs, 1):
        say(f"Model {i}/{len(pairs)}: {model}  (graded by {grader})")
        forced = any(r in model for r in a.rerun)
        if not a.mock and not forced and log_dir.exists() and finished(log_dir, model):
            print("  already finished in an earlier run; skipping")
            continue
        try:
            log = run_eval(model, grader, "validated", a.limit, log_dir, a.mock)
        except Exception as e:  # keep going so one bad model doesn't lose the others
            print(f"  FAILED: {str(e)[:600]}")
            failed.append(model)
            continue
        if log.status != "success":
            print(f"  ended with status '{log.status}': {(log.error.message if log.error else '')[:600]}")
            failed.append(model)
            continue
        n, bad = write_review(log, out_dir / f"review_{model.split('/')[-1]}.csv")
        print(f"  {n} prompts graded" + (f"; grader format failed {bad} times" if bad else ""))

    if len(failed) == len(pairs):
        sys.exit("\nNo model finished, so there is nothing to summarise. The reason is in the lines marked "
                 "FAILED or 'ended with status' above.\nMost common causes: the OpenRouter key was pasted wrongly "
                 "(its length should be 73), or the account has no credit left.")

    say("Summarising all models")
    if subprocess.call([sys.executable, "-m", "salecta.analyze", "--logs", str(log_dir), "--out", str(out_dir)],
                       cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}) != 0:
        print("  The summary step failed; the raw logs are still packed below so nothing is lost.")

    bundle = ROOT / "salecta_full_run.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
        for folder in (log_dir, out_dir):
            for f in sorted(folder.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(ROOT))
    print(f"\nDone. Send Claude this one file (privately; never commit it):\n  {bundle}")
    if failed:
        print("These models did not finish: " + ", ".join(failed)
              + "\nRun the same command again to retry only those.")


if __name__ == "__main__":
    main()
