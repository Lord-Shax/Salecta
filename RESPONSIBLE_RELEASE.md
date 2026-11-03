# Responsible release

Salecta's harmful split asks whether rephrasing a request in Pidgin gets it
past a model's safety behaviour. Publishing *that this happens* helps
defenders. Publishing a ready-made bypass kit helps attackers. This policy
draws the line between the two.

**Published**
- Harmful-split *prompts*. They are low-to-moderate severity (fraud and
  scams, harassment, privacy, academic dishonesty), and similar prompts are
  already in public English safety benchmarks.
- Aggregate refusal and compliance rates per model and per language variant.
- Benign-split prompts and the full responses to them.

**Not published**
- Harmful *completions* from any model.
- Items involving weapons, CBRN, self-harm instructions or sexual content.
  These are out of scope entirely.
- Slurs. Hate items use a `<GROUP>` placeholder.

**Disclosure**
- If a model shows a large Pidgin-vs-English gap on the harmful split, I will
  notify the provider through its safety or vulnerability reporting channel
  and say so in the write-up.
- Per-model harmful-split results for that provider are published only after
  14 days have passed since notification. Until then, the harmful split is
  reported pooled across models. Benign-split (over-refusal) results are
  published immediately, since they expose no bypass.

**Logs**
- `logs/` and `results_raw/` are git-ignored because they contain full model
  outputs. Only the aggregate `results/summary.*` files and the chart are
  committed.
