"""Summarise Inspect logs into Salecta's headline numbers and a chart.

Usage:
    python -m salecta.analyze --logs logs --out results
"""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log

VARIANTS = ["en", "pcm", "cs"]
VARIANT_NAMES = {"en": "English", "pcm": "Pidgin", "cs": "Code-switched"}
# Metric per split: the *failure* rate we care about.
#   benign  -> over-refusal rate      (label != COMPLY)
#   harmful -> harmful-compliance rate (label != REFUSE)
METRIC_NAMES = {"benign": "Over-refusal rate", "harmful": "Harmful-compliance rate"}

# Validated categorical palette (dataviz default, light mode) + chart ink.
SERIES = {"en": "#2a78d6", "pcm": "#eb6834", "cs": "#1baf7a"}
INK, INK2, MUTED, GRID, AXIS, SURFACE = (
    "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb",
)


def collect(log_dir: Path) -> list[dict]:
    """Read successful logs. If a model was run more than once, keep only its latest run."""
    latest: dict[str, object] = {}
    for info in list_eval_logs(str(log_dir)):
        log = read_eval_log(info)
        if log.status != "success" or not log.samples:
            continue
        prev = latest.get(log.eval.model)
        if prev is None or log.eval.created > prev.eval.created:
            latest[log.eval.model] = log
    rows = []
    for model, log in latest.items():
        for s in log.samples:
            if not s.scores:
                continue
            sc = next(iter(s.scores.values()))
            md = sc.metadata or {}
            rows.append(
                {
                    "model": model,
                    "item_id": md.get("item_id"),
                    "variant": md.get("variant"),
                    "split": md.get("split"),
                    "label": md.get("label"),
                    "failure": 0.0 if sc.value == 1.0 else 1.0,
                    "parse_failed": md.get("grader_parse_failed", False),
                }
            )
    return rows


def bootstrap_ci(values: list[float], n: int = 2000, seed: int = 0) -> tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(values)
    means = sorted(sum(rng.choices(values, k=k)) / k for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def summarise(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[float]] = defaultdict(list)
    for r in rows:
        groups[(r["model"], r["split"], r["variant"])].append(r["failure"])
    out = []
    for (model, split, variant), vals in sorted(groups.items()):
        lo, hi = bootstrap_ci(vals)
        out.append(
            {
                "model": model,
                "split": split,
                "variant": variant,
                "n": len(vals),
                "rate": sum(vals) / len(vals),
                "ci_low": lo,
                "ci_high": hi,
            }
        )
    return out


def paired_gaps(rows: list[dict]) -> list[dict]:
    """Pidgin-minus-English gap on the *same items*, with bootstrap CI over items."""
    by = defaultdict(dict)
    for r in rows:
        by[(r["model"], r["split"], r["item_id"])][r["variant"]] = r["failure"]
    diffs: dict[tuple, list[float]] = defaultdict(list)
    for (model, split, _), v in by.items():
        for other in ("pcm", "cs"):
            if "en" in v and other in v:
                diffs[(model, split, other)].append(v[other] - v["en"])
    out = []
    for (model, split, other), d in sorted(diffs.items()):
        lo, hi = bootstrap_ci(d)
        out.append(
            {"model": model, "split": split, "comparison": f"{other} - en",
             "n_items": len(d), "gap": sum(d) / len(d), "ci_low": lo, "ci_high": hi}
        )
    return out


def write_tables(summary, gaps, rows, out: Path) -> None:
    import csv

    out.mkdir(parents=True, exist_ok=True)
    with open(out / "summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)
    with open(out / "gaps.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(gaps[0].keys()))
        w.writeheader()
        w.writerows(gaps)

    pf = sum(r["parse_failed"] for r in rows)
    lines = ["# Salecta results", ""]
    for split in ("benign", "harmful"):
        lines += [f"## {METRIC_NAMES[split]} ({split} split)", "",
                  "| Model | English | Pidgin | Code-switched |", "|---|---|---|---|"]
        models = sorted({s["model"] for s in summary if s["split"] == split})
        for m in models:
            cells = []
            for v in VARIANTS:
                s = next((x for x in summary if x["model"] == m and x["split"] == split
                          and x["variant"] == v), None)
                cells.append(
                    f"{s['rate']:.0%} [{s['ci_low']:.0%}–{s['ci_high']:.0%}]" if s else "–"
                )
            lines.append(f"| {m} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Paired gap vs English (same items; positive = worse than English)", "",
              "| Model | Split | Comparison | Items | Gap [95% CI] |", "|---|---|---|---|---|"]
    for g in gaps:
        lines.append(
            f"| {g['model']} | {g['split']} | {g['comparison']} | {g['n_items']} | "
            f"{g['gap']:+.0%} [{g['ci_low']:+.0%}, {g['ci_high']:+.0%}] |"
        )
    lines += ["", f"Grader parse failures (keyword fallback used): {pf} of {len(rows)} samples."]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot(summary, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    models = sorted({s["model"] for s in summary})
    splits = [sp for sp in ("benign", "harmful") if any(s["split"] == sp for s in summary)]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, axes = plt.subplots(1, len(splits), figsize=(5.2 * len(splits), 3.6 + 0.15 * len(models)),
                             sharey=True, facecolor=SURFACE, squeeze=False)
    width = 0.24
    for ax, split in zip(axes[0], splits):
        ax.set_facecolor(SURFACE)
        for i, v in enumerate(VARIANTS):
            for j, m in enumerate(models):
                s = next((x for x in summary if x["model"] == m and x["split"] == split
                          and x["variant"] == v), None)
                if not s:
                    continue
                x = j + (i - 1) * (width + 0.02)
                h = s["rate"]
                # Thin bar, rounded data-end, anchored on the baseline.
                ax.add_patch(FancyBboxPatch(
                    (x - width / 2, 0), width, max(h, 0.002),
                    boxstyle="round,pad=0,rounding_size=0.02", mutation_aspect=0.6,
                    linewidth=0, facecolor=SERIES[v],
                    label=VARIANT_NAMES[v] if j == 0 else None))
                ax.vlines(x, s["ci_low"], s["ci_high"], color=INK2, linewidth=1)
                ax.text(x, max(h, s["ci_high"]) + 0.03, f"{h:.0%}", ha="center",
                        va="bottom", fontsize=8, color=INK2)
        ax.set_xlim(-0.6, len(models) - 0.4)
        ax.set_ylim(0, 1.12)
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels([m.split("/")[-1] for m in models], color=INK2)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"], color=MUTED)
        ax.yaxis.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(AXIS)
        ax.tick_params(length=0)
        ax.set_title(f"{METRIC_NAMES[split]}\n({split} prompts; lower is better)",
                     color=INK, fontsize=11, loc="left")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", frameon=False, ncol=3,
               labelcolor=INK2, bbox_to_anchor=(0.99, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out / "refusal_rates.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--logs", default="logs")
    p.add_argument("--out", default="results")
    a = p.parse_args()
    rows = collect(Path(a.logs))
    if not rows:
        raise SystemExit(f"No scored samples found in {a.logs}")
    summary, gaps = summarise(rows), paired_gaps(rows)
    out = Path(a.out)
    write_tables(summary, gaps, rows, out)
    plot(summary, out)
    print(f"Wrote {out}/summary.md, summary.csv, gaps.csv, refusal_rates.png "
          f"({len(rows)} samples, {len({r['model'] for r in rows})} models)")


if __name__ == "__main__":
    main()
