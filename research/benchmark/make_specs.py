"""Seeded authoring specs for the benchmark (PREREG_TRANSFER_LADDER.md section 5; P5).

Each spec assigns an authoring *frame* and three seed concepts drawn at random from the lexicon, so the author does not
choose what to write about (which would tilt the items toward whatever the author finds natural or knows the tutor
handles). The author writes one natural sentence using at least two of the seeds in the frame, and may swap a seed that
makes no sense. Seeds come from two pools: roots that occur in the corpus (60%) and lexicon roots that never do (40%,
the heavier half by frequency weight, so the words stay ordinary). Frames are fixed strata: every system sees the same
mix. Nothing here depends on any system's output.

    research/.venv/bin/python research/benchmark/make_specs.py
"""
import json
import random
from pathlib import Path

import bench

SEED = 20260930
FRAMES = {   # frame -> (share, seed classes)
    "declarative":      (0.17, ["VERB", "NOUN", "NOUN"]),
    "copular":          (0.12, ["NOUN", "ADJ", "NOUN"]),
    "negation":         (0.08, ["VERB", "NOUN", "NOUN"]),
    "yes-no question":  (0.08, ["VERB", "NOUN", "ADJ"]),
    "wh question":      (0.09, ["VERB", "NOUN", "NOUN"]),
    "request":          (0.07, ["VERB", "NOUN", "ADJ"]),
    "modal or tense":   (0.09, ["VERB", "NOUN", "NOUN"]),
    "place or time":    (0.10, ["VERB", "NOUN", "NOUN"]),
    "coordination":     (0.06, ["VERB", "NOUN", "VERB"]),
    "subordination":    (0.08, ["VERB", "NOUN", "VERB"]),
    "number or quantity": (0.03, ["NOUN", "NUM", "ADJ"]),
    "possession":       (0.03, ["NOUN", "NOUN", "ADJ"]),
}
SIZES = {"dev": 345, "test": 1070}       # authoring targets: a margin over the final 300 / 930 for review and dedupe losses


def pools(seen_roots):
    seen, unseen = {}, {}
    rows = [json.loads(l) for l in open(bench.TALEMA / "data" / "lexicon.jsonl")]
    by_class = {}
    for r in rows:
        if r["cls"] in bench.CONTENT and r["source"] in ("lexicon", "coin", None) or r["cls"] in bench.CONTENT:
            by_class.setdefault(r["cls"], []).append(r)
    for cls, rs in by_class.items():
        rs = [r for r in rs if r["en"] and not r["en"].startswith("<") and r["root"] in bench.LEX.roots]
        seen[cls] = [r for r in rs if r["root"] in seen_roots]
        rest = sorted((r for r in rs if r["root"] not in seen_roots), key=lambda r: -(r["weight"] or 0))
        unseen[cls] = rest[: max(1, len(rest) // 2)]
    return seen, unseen


def label(r):
    return f"{r['en'].split('|')[0]}/{r['cls']}"


def main():
    rnd = random.Random(SEED)
    seen_roots = bench.corpus_screen()["roots"]
    seen, unseen = pools(seen_roots)
    for name, n in SIZES.items():
        frames = []
        for frame, (share, _) in FRAMES.items():
            frames += [frame] * round(n * share)
        while len(frames) < n:
            frames.append("declarative")
        frames = frames[:n]
        rnd.shuffle(frames)
        used = set()
        lines = ["id\tframe\tseeds"]
        for i, frame in enumerate(frames, 1):
            seeds = []
            for cls in FRAMES[frame][1]:
                pool = (unseen if rnd.random() < 0.4 else seen)[cls]
                weights = [max(r["weight"] or 0, 1e-6) ** 0.5 for r in pool]   # favour ordinary words; keep variety
                for _ in range(200):                 # roots are unique within a set, except numerals (only ~25 exist)
                    r = rnd.choices(pool, weights=weights)[0]
                    if cls == "NUM" or r["root"] not in used:
                        break
                used.add(r["root"])
                seeds.append(r)
            lines.append(f"{name}-{i:04d}\t{frame}\t" + " | ".join(f"{label(r)}{'*' if r['root'] not in seen_roots else ''}" for r in seeds))
        (Path(__file__).parent / "specs" / f"{name}.tsv").write_text("\n".join(lines) + "\n")
        print(name, len(frames), "specs")


if __name__ == "__main__":
    main()
