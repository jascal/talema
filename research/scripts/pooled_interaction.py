"""Play-by-prompt interaction on judge naturalness/fit, per run and pooled over runs.

interaction = (D - C) - (B - A) per (conversation, round), where each cell's score is the mean over judge passes;
bootstrapped over (conversation, round) pairs. Cells: A/B current prompt without/with the play, C/D loosened prompt
without/with the play (see avatar/experiments/conversation_ab.py).

    python research/scripts/pooled_interaction.py avatar/experiments/results/ab3_english.judged.json \
                                                  avatar/experiments/results/ab4_english.judged.json
"""
import json
import random
import statistics as st
import sys
from collections import defaultdict

SEED, RESAMPLES = 5, 5000


def rows_for(path, quality):
    scores = defaultdict(list)
    for r in json.load(open(path)):
        scores[(r["conv"], r["round"], r["cell"])].append(r[quality])
    s = {k: st.mean(v) for k, v in scores.items()}
    keys = sorted({(c, r) for c, r, _ in s})
    return [(s[(c, r, "D")] - s[(c, r, "C")]) - (s[(c, r, "B")] - s[(c, r, "A")])
            for c, r in keys if all((c, r, x) in s for x in "ABCD")]


def interval(values):
    rnd = random.Random(SEED)
    means = sorted(st.mean(rnd.choices(values, k=len(values))) for _ in range(RESAMPLES))
    return st.mean(values), means[int(0.025 * RESAMPLES)], means[int(0.975 * RESAMPLES) - 1]


if __name__ == "__main__":
    paths = sys.argv[1:]
    for quality in ("natural", "fit"):
        for path in paths:
            m, lo, hi = interval(rows_for(path, quality))
            print(f"{path.split('/')[-1]:<28} {quality:<8} {m:+.2f} [{lo:+.2f}, {hi:+.2f}]")
        pooled = [v for path in paths for v in rows_for(path, quality)]
        m, lo, hi = interval(pooled)
        print(f"{'pooled':<28} {quality:<8} {m:+.2f} [{lo:+.2f}, {hi:+.2f}]  n={len(pooled)}")
