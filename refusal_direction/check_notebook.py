"""Run every notebook cell on a tiny random Qwen2 model (CPU, no downloads from Hugging Face).

It can't check the science (a random model has no refusal direction), only that the code runs
end to end and produces every output file.
"""
import json
import os
import sys
import time

import nbformat
import torch
from transformers import BatchEncoding, Qwen2Config, Qwen2ForCausalLM

nb = nbformat.read("refusal_direction_pidgin.ipynb", as_version=4)


class StubTok:
    padding_side = "right"
    pad_token = "<pad>"
    eos_token = "<eos>"
    pad_token_id = 0

    def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=True):
        return "<user>" + msgs[0]["content"] + "<assistant>"

    def __call__(self, texts, return_tensors="pt", padding=True, add_special_tokens=False):
        ids = [[(ord(c) % 250) + 2 for c in t[-48:]] for t in texts]
        n = max(map(len, ids))
        pad = lambda r: [0] * (n - len(r)) + r if self.padding_side == "left" else r + [0] * (n - len(r))
        return BatchEncoding({"input_ids": torch.tensor([pad(r) for r in ids]),
                              "attention_mask": torch.tensor([pad([1] * len(r)) for r in ids])})

    def batch_decode(self, rows, skip_special_tokens=True):
        return ["".join(chr(97 + int(x) % 26) for x in r) for r in rows]


cfg = Qwen2Config(vocab_size=256, hidden_size=64, intermediate_size=128, num_hidden_layers=10,
                  num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=256)
ns = {"__name__": "__main__", "display": lambda *a, **k: print(*a)}
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")

for i, cell in enumerate(nb.cells):
    if cell.cell_type != "code":
        continue
    src = "\n".join(l for l in cell.source.splitlines() if not l.lstrip().startswith("!"))
    if "load-model" in cell.metadata.get("tags", []):
        src = "MODEL_ID='tiny-random'; DEVICE='cpu'; DTYPE=torch.float32"
        ns.update(tok=StubTok(), model=Qwen2ForCausalLM(cfg).eval())
    t = time.time()
    try:
        exec(compile(src, f"cell{i}", "exec"), ns)
    except Exception:
        print(f"\n### FAILED in cell {i}:\n{src[:400]}")
        raise
    print(f"--- cell {i} ok ({time.time() - t:.0f}s)")

print("\nfiles:", sorted(os.listdir("results")))
s = json.load(open("results/summary.json"))
print("summary keys:", list(s))
