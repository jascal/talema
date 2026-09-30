"""Build and hash the frozen benchmark (PREREG_TRANSFER_LADDER.md section 5; P5).

Deterministic given the pool, the review results, the owner's drops and the seeds: rerun it after the owner has read
the sample and listed disputed ids in owner_drops.txt, and the final freeze is the same procedure minus those items.

  survivors  = items the blind reviewer judged "same" (and not in owner_drops.txt)
  novel sets = survivors, stratified by frame in the shares of make_specs.FRAMES, seeded: 930 test, 300 dev
  exposed    = corpus sentences that survived review: 100 test, 50 dev
  R1 / W     = the novel + exposed items (reading Talema -> tree; writing English -> tree), separate calls
  R2         = valid controls and verified perturbations of novel items (r2.py): 300 test, ~100 dev
  C          = c_test.json (four new conversations); the three in conversation_ab.py are development only

Test ANSWERS live in frozen/test/answers.jsonl, apart from the test INPUTS; no development script loads it.

    research/.venv/bin/python research/benchmark/freeze.py [--dry-run]
"""
import argparse
import collections
import hashlib
import json
import random
from pathlib import Path

import bench
import make_specs
import power_sim
import r2

HERE = Path(__file__).parent
SEED = 20260930
FINAL = {"test": {"novel": 930, "exposed": 100, "r2_valid": 150, "r2_each": 50},
         "dev": {"novel": 300, "exposed": 50, "r2_valid": 50, "r2_each": 17}}


def load(path):
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def stratified(items, n, rnd):
    """n items, proportional to make_specs.FRAMES shares, shortfalls filled from the rest, all in a seeded order."""
    by = collections.defaultdict(list)
    for it in items:
        by[it["frame"]].append(it)
    for v in by.values():
        rnd.shuffle(v)
    picked = []
    for frame, (share, _) in make_specs.FRAMES.items():
        picked += by[frame][: round(n * share)]
    have = {it["id"] for it in picked}
    rest = [it for v in by.values() for it in v if it["id"] not in have]
    rnd.shuffle(rest)
    picked += rest[: max(0, n - len(picked))]
    return picked[:n]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    reviews = {r["id"]: r for r in load(HERE / "review" / "reviews.jsonl")}
    reviews.update({r["id"]: r for r in load(HERE / "review" / "reviews_whether_v2.jsonl")})   # corrected rubric for `whether` items
    drops = set((HERE / "owner_drops.txt").read_text().split()) if (HERE / "owner_drops.txt").exists() else set()

    def survivors(items):
        return [it for it in items if reviews.get(it["id"], {}).get("same") is True and it["id"] not in drops]

    out = {}
    report = {"review": {}, "counts": {}}
    for name in ("dev", "test"):
        rnd = random.Random(f"{SEED}-{name}")
        pool = load(HERE / "pool" / f"{name}.jsonl")
        exposed_pool = load(HERE / "pool" / f"exposed_{name}.jsonl")
        report["review"][name] = {"novel_authored": len(pool), "novel_same": len(survivors(pool)),
                                  "exposed_candidates": len(exposed_pool), "exposed_same": len(survivors(exposed_pool))}
        cfg = FINAL[name]
        novel = stratified(survivors(pool), cfg["novel"], rnd)
        exposed = survivors(exposed_pool)
        rnd.shuffle(exposed)
        exposed = exposed[: cfg["exposed"]]
        for it in novel:
            it["stratum"] = "novel"
        for it in exposed:
            it["stratum"] = "exposed"; it["frame"] = "corpus"
        items = novel + exposed
        rnd.shuffle(items)
        # R2 comes from novel items; perturbations are verified by the exact parser and topped up until the counts hold
        entries, extra = [], 0
        while True:
            built = r2.label(r2.build(list(novel), cfg["r2_valid"], cfg["r2_each"] + extra, random.Random(f"{SEED}-{name}-r2-{extra}")))
            counts = collections.Counter(e["category"] for e in built)
            if counts["valid"] >= cfg["r2_valid"] and all(counts[c] >= cfg["r2_each"] for c in ("structural", "unknown-root", "meaning-change")) or extra > 60:
                break
            extra += 5
        entries = [e for e in built if e["category"] == "valid"][: cfg["r2_valid"]]
        for c in ("structural", "unknown-root", "meaning-change"):
            entries += [e for e in built if e["category"] == c][: cfg["r2_each"]]
        random.Random(f"{SEED}-{name}-r2-order").shuffle(entries)
        for i, e in enumerate(entries, 1):
            e["id"] = f"{name}-r2-{i:04d}"
        report["counts"][name] = {"r1_w_items": len(items), "novel": len(novel), "exposed": len(exposed),
                                  "r2": dict(collections.Counter(e["category"] for e in entries)), "r2_topups": extra}
        out[name] = {"items": items, "r2": entries}

    if args.dry_run:
        print(json.dumps(report, indent=1))
        return

    root = HERE / "frozen"
    for name, d in out.items():
        base = root / name
        write(base / "r1_inputs.jsonl", [{"id": it["id"], "text": it["talema"]} for it in d["items"]])
        write(base / "w_inputs.jsonl", [{"id": it["id"], "english": it["english"]} for it in d["items"]])
        write(base / "r2_inputs.jsonl", [{"id": e["id"], "text": e["text"]} for e in d["r2"]])
        answers = [{"task": "r1_w", "id": it["id"], "stratum": it["stratum"], "frame": it["frame"], "english": it["english"],
                    "talema": it["talema"], "native_tree": it["native_tree"], "family_hash": bench.family_hash(it["family"]),
                    "n_words": it["n_words"], "unseen_roots": it.get("unseen_roots", []), "seeds": it.get("seeds", "")}
                   for it in d["items"]]
        answers += [{"task": "r2", **e} for e in d["r2"]]
        write(base / "answers.jsonl", answers)
        (root / f"{name}_family_hashes.txt").write_text("\n".join(sorted({bench.family_hash(it["family"]) for it in d["items"] if it["stratum"] == "novel"})) + "\n")
    (root / "c_test.json").write_text((HERE / "c_test.json").read_text())

    # power at the final novel N, for the record
    n = report["counts"]["test"]["novel"]
    rng = __import__("numpy").random.default_rng(SEED)
    report["power_at_final_n"] = {f"disc={d}": {f"z={z}": round(power_sim.power(n, 0.05, d, 0.0, z, 0.0, 1, 4000, rng), 3)
                                             for z in (1.96, 2.576)} for d in (0.10, 0.20, 0.30)}
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "MANIFEST.json")
    tools = ["bench.py", "make_specs.py", "check_pairs.py", "review.py", "r2.py", "freeze.py", "power_sim.py", "c_test.py", "make_exposed.py", "parse_batch.mjs"]
    report["sha256"] = {str(p.relative_to(HERE)): sha(p) for p in files}
    report["tools_sha256"] = {t: sha(HERE / t) for t in tools}
    report["review_sha256"] = {f: sha(HERE / "review" / f) for f in ("reviews.jsonl", "reviews_whether_v2.jsonl")}
    report["owner_drops"] = sorted(drops)
    (HERE / "frozen" / "MANIFEST.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("review", "counts", "power_at_final_n")}, indent=1))


if __name__ == "__main__":
    main()
