"""Build a self-contained labelling page for publishing as a Claude artifact.

Artifacts can't fetch files from GitHub, so this embeds data/items.jsonl
into a copy of annotate/index.html.

Usage:
    python scripts/build_artifact.py            # writes dist/salecta-annotate.html
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARK = "<script>\n(() => {"


def build(out: Path = ROOT / "dist" / "salecta-annotate.html") -> Path:
    page = (ROOT / "annotate" / "index.html").read_text(encoding="utf-8")
    items = (ROOT / "data" / "items.jsonl").read_text(encoding="utf-8").strip()
    if MARK not in page:
        raise SystemExit("Couldn't find the page script in annotate/index.html")
    # "</" inside a <script> would end it early; "<\/" is the same text in JSON.
    blob = items.replace("</", "<\\/")
    tag = f'<script id="salecta-items" type="application/x-ndjson">\n{blob}\n</script>\n'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page.replace(MARK, tag + MARK, 1), encoding="utf-8")
    return out


if __name__ == "__main__":
    p = build()
    print(f"Wrote {p} ({p.stat().st_size // 1024} KB)")
