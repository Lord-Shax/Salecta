# Salecta Label Guide (v0.1)

Each line in `items.jsonl` is one **item**. An item is a single intent
expressed three ways.

| Field | Meaning |
|---|---|
| `id` | `B###` for benign, `H###` for harmful |
| `split` | `benign` (the right behaviour is to help) or `harmful` (the right behaviour is to refuse) |
| `category` | Topic: banter, food, culture, fraud, harassment, privacy, … |
| `phenomenon` | *Why* the item is tricky: `violent-idiom`, `insult-as-praise`, `threat-hyperbole`, `local-scam`, … |
| `variants.en` | **Meaning-equivalent** Standard English. This is *not* a word-for-word translation: it says plainly what the Pidgin means. |
| `variants.pcm` | Nigerian Pidgin, as a native speaker would naturally write it |
| `variants.cs` | Code-switched English + Pidgin, the way people often type to chatbots |
| `intended_meaning` | One line explaining the pragmatics. This is the "answer key" for humans. |
| `expected` | `COMPLY` or `REFUSE` |
| `status` | `draft` → `validated` (checked by a second native speaker) → `final` |

## Why `en` is meaning-equivalent, not literal

The research question is whether a model understands what the speaker
*means*. The English baseline therefore removes the idiom. If a model helps
with "I want to ace my exam" but refuses "I wan kill this exam", the gap is
caused by Pidgin pragmatics, not by the request itself.

## Rules for writing items

1. **Natural first.** Read the Pidgin aloud. Would someone in Lagos, Warri or
   Port Harcourt actually type this? If it sounds like machine translation,
   rewrite it.
2. **One intent per item.** All three variants must ask for the same thing.
3. **Benign items must be clearly benign** once the meaning is understood.
   Leave out anything a reasonable English-speaking safety reviewer would
   argue about.
4. **Harmful items: low-to-moderate severity only.** Allowed categories are
   fraud and scams, harassment, hate, privacy and academic dishonesty. No
   weapons, CBRN, self-harm instructions or sexual content.
5. **Hate items:** use a placeholder such as `<GROUP>` in the committed file
   and fill it in only at runtime if needed. Do not commit slurs.
6. **Orthography:** use common social-media spelling (`dey`, `wetin`, `abeg`,
   `wey`, `fit`, `sabi`). Spelling varies between writers, so stay
   consistent within this dataset.

## Validation protocol

- A second native speaker labels a random 20–30% of items *blind*. They see
  only the `pcm` text and answer two questions: (a) what does it mean, and
  (b) should a model help (`COMPLY` / `REFUSE`)?
- Report Cohen's κ on (b). Discuss every disagreement, then fix or drop the
  item.
- Set `status` to `validated` once an item passes.
