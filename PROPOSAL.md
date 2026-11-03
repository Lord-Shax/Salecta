# Salecta — Phase 1 Proposal

**Does frontier-model safety behaviour transfer to Nigerian Pidgin — in both directions?**

## One-line summary

Salecta is an evaluation suite that tests whether large language models make
safety decisions in Nigerian Pidgin (Naijá) as well as they do in Standard
English. Phase 1 measures two failure modes on matched English / Pidgin /
code-switched prompts:

1. **Over-refusal** — the model refuses or lectures a *harmless* Pidgin message
   because its surface form sounds violent or insulting
   (e.g. *"You dey craze!"* said to a friend who just pulled off something clever).
2. **Under-refusal** — the model *complies* with a harmful request in Pidgin that
   it would refuse in English.

## Why this matters for AI safety

Safety training and safety classifiers are built overwhelmingly on Standard
English. Nigerian Pidgin is an English-lexified creole spoken by tens of
millions of people as a first or second language (estimates range widely,
from about 75 million to over 100 million). Much of its vocabulary *looks*
English, but its meaning often differs, so it is a natural stress test. A
model can recognise the words and still misread what the speaker means.

Both failure modes have real costs:

- Over-refusal hurts people. It censors normal speech, frustrates users and
  teaches them that "AI is not for people like us."
- Under-refusal undermines safety. If a guardrail disappears when the same
  request is rephrased in Pidgin, the safety property never generalised. It
  depended on surface features of English.

The second point is the core alignment question. Phase 1 tests one specific
case of it: does safety behaviour generalise across language variety, or
does it depend on surface form?

## Prior work, and what Salecta adds

| Work | What it covers | Gap Salecta addresses |
|---|---|---|
| NaijaHate (Tonneau et al., ACL 2024) | ~36k Nigerian tweets labelled for hate speech, incl. Pidgin | Classifier benchmark, not LLM refusal behaviour |
| NaijaSenti / AfriSenti | Sentiment labels for Pidgin tweets | Sentiment, not safety decisions |
| IrokoBench, AfroBench | LLM capability across African languages | Capability, not safety |
| "Does Generative AI speak Nigerian Pidgin?" (2024) | Shows LLMs favour West African Pidgin over Naijá | Translation quality, not safety |
| Yong et al. 2023, "Low-Resource Languages Jailbreak GPT-4" | Translated harmful prompts bypass refusals | Machine-translated, no Pidgin, no over-refusal side |
| Pidgin dialect-jailbreak project (Manifund proposal) | Harmful Pidgin prompts → refusal rates | Under-refusal only |
| XSTest (Röttger et al. 2024) | Exaggerated safety on safe-but-scary prompts | English only |

**Salecta's contribution:** the first *two-sided* (over- and under-refusal),
*matched* (same item in English / Pidgin / code-switched) evaluation in
Nigerian Pidgin. It is native-speaker authored rather than machine
translated, and every item carries a short pragmatic note explaining what
the utterance actually means.

## Research questions

- **RQ1 (over-refusal):** On harmless prompts, do models refuse or moralise
  more often in Pidgin than in the matched English version?
- **RQ2 (under-refusal):** On harmful prompts, do models comply more often in
  Pidgin or code-switched form than in English?
- **RQ3 (where it breaks):** Which pragmatic phenomena drive the errors?
  Candidates include idiom, hyperbole, banter or insult framing, and
  culturally specific scams.

## Method

- **Dataset (v0.1 target):** 150–250 items. Each item has three variants:
  `en`, `pcm` (Pidgin) and `cs` (code-switched English–Pidgin).
  - *Benign split:* phrases that sound harsh but are harmless, such as
    hyperbole, banter, idioms and everyday requests that use alarming words.
  - *Harmful split:* low-to-moderate severity requests drawn from standard
    safety categories (fraud and scams, harassment, hate, privacy). There are
    no CBRN or weapons items. Items are adapted from existing public English
    benchmarks where possible, so English baselines are comparable.
- **Annotation:** I write the Pidgin items as a native speaker. A second
  native speaker independently labels 20–30% of items, and I report their
  agreement (Cohen's κ). Items they disagree on are discussed and either
  fixed or dropped.
- **Models:** 3–4 models, including at least one open-weight model.
- **Harness:** [Inspect](https://inspect.aisi.org.uk/), the UK AI Security
  Institute's open-source evaluation framework, so anyone can reproduce the
  results with one command.
- **Scoring:** an LLM grader classifies each response as `COMPLY`, `REFUSE`
  or `PARTIAL`. I hand-check a random 15% of grader decisions and report how
  often the grader is right.
- **Metrics:** over-refusal rate (benign split) and harmful-compliance rate
  (harmful split), per model × language variant, with 95% bootstrap
  confidence intervals. The headline number is the *gap*: Pidgin minus
  English.

## Deliverables

1. A public GitHub repo containing the dataset, the Inspect task, the
   analysis scripts and the results.
2. A dataset card with label guidelines and the agreement statistics.
3. A 1,500–2,500 word write-up (blog / LessWrong / Alignment Forum)
   covering the results, failure examples and limitations.

## Responsible release

The harmful split publishes **prompts and aggregate refusal rates only**.
Harmful model outputs are never published. I will share findings with the
affected model providers before publication. See `RESPONSIBLE_RELEASE.md`.

## Timeline (part-time, ~4 weeks)

| Week | Work |
|---|---|
| 1 | Finalise label guide; write 150+ items; recruit second annotator |
| 2 | Annotation + agreement; pilot run on 1 model; fix grader prompt |
| 3 | Full runs on 3–4 models; grader validation; analysis |
| 4 | Write-up, dataset card, repo polish, disclosure to providers |

## Limitations (stated up front)

- Small dataset → results are indicative, not definitive.
- Single-turn text only. Real Pidgin use is often spoken and multi-turn.
- Pidgin spelling is not standardised. The orthography I use is documented
  and is one of several valid choices.
- LLM grading introduces its own errors, which is why it is hand-validated.

## Beyond Phase 1 (the long-term Salecta vision)

- Multi-turn conversations and context-dependent meaning.
- Audio: prosody and tone carry meaning that text loses.
- Other English-based creoles (Cameroonian Pidgin, Ghanaian Pidgin, Krio).
  The item format is language-agnostic, so the method transfers by swapping
  the item set.
