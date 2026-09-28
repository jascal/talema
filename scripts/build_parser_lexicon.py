"""Generate the compact, reviewable lexicon bundled with the exact parser."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "lexicon.jsonl"
TARGET = ROOT / "grammar" / "lexicon.mjs"


def main() -> None:
    words = {}
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        words[row["root"]] = [row["cls"], row["en"], row["de"], row["es"]]
    target = "// Generated from data/lexicon.jsonl by scripts/build_parser_lexicon.py.\n"
    target += "export default " + json.dumps(words, ensure_ascii=False, separators=(",", ":")) + ";\n"
    TARGET.write_text(target, encoding="utf-8")
    print(f"wrote {len(words)} roots to {TARGET}")


if __name__ == "__main__":
    main()
