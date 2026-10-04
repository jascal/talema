"""Candidates for the *exposed* stratum: corpus sentences (P5).

Exposed items are sentences the tutor's books contain and a student is trained on, so the gap between exposed and novel
performance measures memorisation. They are drawn from data/sentences.jsonl with a fixed seed, stratified by book, and
must be a complete English sentence, a single tree inside validate_speech's domain, 3-12 words, with a distinct Talema
text and family. 250 test and 100 dev candidates go through the same blind review as the novel items; the final 100 and
50 are chosen from the survivors (freeze.py).

    research/.venv/bin/python research/benchmark/make_exposed.py
"""
import collections
import json
import random
import re
from pathlib import Path

import bench

SEED = 20260930
HERE = Path(__file__).parent


def main():
    rows = [json.loads(l) for l in (bench.TALEMA / "data" / "sentences.jsonl").read_text().splitlines()]
    seen_text, seen_family, by_book = set(), set(), collections.defaultdict(list)
    for r in rows:
        text, en = r["talema"].strip(), r["en"].strip()
        if not text.endswith(" .") or text.count(" . ") or not re.fullmatch(r"[A-Z][^:\"]*[.?!]", en):
            continue
        words = text.split()[:-1]
        if not bench.in_domain(text) or not 3 <= len(words) <= 12:
            continue
        try:
            native = bench.decode(text[:-1].strip())
        except Exception:
            continue
        roots = []

        def walk(t):
            roots.append(t[0])
            for k in t[1:]:
                walk(k)
        walk(native)
        content = [x for x in roots if bench.LEX.roots.get(x, ("",))[0] in bench.CONTENT]
        family = bench.family_key(roots[0], content)
        if text in seen_text or family in seen_family:
            continue
        seen_text.add(text); seen_family.add(family)
        by_book[r["book"]].append({"source_id": r["id"], "english": en, "talema": text, "native_tree": native,
                                   "family": family, "n_words": len(words), "book": r["book"]})
    rnd = random.Random(SEED)
    total = sum(len(v) for v in by_book.values())
    for name, n in (("test", 250), ("dev", 100)):
        picked = []
        for book, items in sorted(by_book.items()):
            rnd.shuffle(items)
            take = max(1, round(n * len(items) / total))
            picked += [dict(it, id=f"exp-{name}-{len(picked) + i + 1:04d}", set=name) for i, it in enumerate(items[:take])]
            del items[:take]                                   # dev and test are disjoint
        rnd.shuffle(picked)
        picked = picked[:n]
        for i, it in enumerate(picked, 1):
            it["id"] = f"exp-{name}-{i:04d}"
        (HERE / "pool" / f"exposed_{name}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in picked))
        print(name, len(picked), dict(collections.Counter(x["book"] for x in picked)))


if __name__ == "__main__":
    main()
