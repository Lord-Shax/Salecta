# Annotations

Files exported from the labelling page (`annotate/index.html`) by second
annotators. Each annotator is identified by initials or a code only.

| Folder | What it is |
|---|---|
| `pilot/` | A trial run of the labelling page on the 18 *draft* seed items. It tests the tool and the instructions. These labels are **not** the final agreement figure, because the items have since been rewritten. |
| `round2/` | Native-speaker validation of the 45 draft items in the 60-item set (Nov 2026): meaning, naturalness and help/refuse, with a quality rule and two contested items. See its README. |
| `final/` | Labels on the finished dataset. The κ reported in the write-up comes from here. |

Score a file with:

```bash
python -m salecta.agreement annotations/final/labels_<code>.json --out results/agreement_<code>.md
```
