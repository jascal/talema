"""Power for the non-inferiority contrasts in PREREG_TRANSFER_LADDER.md section 7 (P5: fixes the final item counts).

Paired binary outcomes per item (candidate X, comparator Y), items grouped into clusters (authoring frames), so the
interval uses a cluster-robust standard error over clusters. Non-inferiority is declared when the lower bound of
mean(X - Y) is above -margin. True difference is `delta` (0 = the systems are equal; the hard case).

    python research/benchmark/power_sim.py [--sims 4000] [--seed 20260929]

Assumptions are stated, not estimated: no system has been run. `disc` is the fraction of items on which the two systems
disagree; `icc` is the intra-cluster correlation of that disagreement; `cluster` is items per authoring frame.
The z values: 1.96 (two-sided 95%) and 2.576 (99%: the smallest Holm step over five confirmatory contrasts).
"""
import argparse
import numpy as np


def power(n, margin, disc, delta, z, icc, cluster, sims, rng):
    g = max(2, n // cluster)
    sizes = np.full(g, n // g)
    sizes[: n - sizes.sum()] += 1
    # cluster-specific disagreement probability: Beta with mean disc and intra-cluster correlation icc
    conc = (1 - icc) / icc if icc > 0 else 1e9
    a, b = disc * conc, (1 - disc) * conc
    q = rng.beta(a, b, size=(sims, g)) if icc > 0 else np.full((sims, g), disc)
    pi = 0.5 + delta / (2 * disc)                       # P(candidate right | discordant)
    pos = rng.binomial(sizes, np.clip(q * pi, 0, 1))
    neg = rng.binomial(sizes - pos, np.clip(q * (1 - pi) / (1 - q * pi), 0, 1))
    s = pos - neg                                       # per-cluster sum of X - Y
    mean = s.sum(1) / n
    se = np.sqrt(((s - sizes * mean[:, None]) ** 2).sum(1)) / n
    return float(np.mean(mean - z * se > -margin))


def needed(margin, disc, delta, z, icc, cluster, sims, rng, target=0.8):
    lo, hi = 100, 6000
    while lo < hi:
        mid = (lo + hi) // 2 // 10 * 10
        if power(mid, margin, disc, delta, z, icc, cluster, sims, rng) >= target:
            hi = mid
        else:
            lo = mid + 10
    return lo


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=20260929)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    print(f"items needed for 80% power to declare non-inferiority when the systems are truly equal (sims={a.sims}, seed={a.seed})")
    print("cluster=8 items per authoring frame, icc=0.05 unless stated\n")
    print(f"{'margin':>6} {'disc':>5} {'z':>6} {'icc':>5} {'N':>6}")
    for margin in (0.05, 0.06, 0.07, 0.08):
        for disc in (0.10, 0.20, 0.30):
            for z in (1.96, 2.576):
                print(f"{margin*100:>5.0f}% {disc:>5.2f} {z:>6.3f} {0.05:>5.2f} {needed(margin, disc, 0.0, z, 0.05, 8, a.sims, rng):>6}")
    print("\nsensitivity to clustering at margin 6%, disc 0.20, z 2.576:")
    for icc in (0.0, 0.05, 0.10, 0.20):
        print(f"  icc {icc:.2f}: N = {needed(0.06, 0.20, 0.0, 2.576, icc, 8, a.sims, rng)}")
    print("\npower at fixed N for the provisional minimums (margin 5%, disc 0.20, icc 0.05):")
    for n in (300, 640, 900, 1200):
        print(f"  N={n}: z1.96 -> {power(n, 0.05, 0.20, 0.0, 1.96, 0.05, 8, a.sims, rng):.2f}   z2.576 -> {power(n, 0.05, 0.20, 0.0, 2.576, 0.05, 8, a.sims, rng):.2f}")
