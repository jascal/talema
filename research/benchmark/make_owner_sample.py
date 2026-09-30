"""The stratified 10% sample of novel items the repository owner reads (PREREG_TRANSFER_LADDER.md section 5; P5).

Disputed items go in research/benchmark/owner_drops.txt (one id per line); rerun freeze.py and the final freeze is the
same procedure with those ids removed and replacements drawn from the surviving reserve.
    research/.venv/bin/python research/benchmark/make_owner_sample.py
"""
import collections
import json
import random
from pathlib import Path

HERE = Path(__file__).parent
SEED = 20260930


def main():
    reviews = {}
    for f in ("reviews.jsonl", "reviews_whether_v2.jsonl"):
        for l in (HERE / "review" / f).read_text().splitlines():
            r = json.loads(l); reviews[r["id"]] = r
    items = []
    for name in ("dev", "test"):
        items += [a for a in map(json.loads, (HERE / "frozen" / name / "answers.jsonl").read_text().splitlines())
                  if a["task"] == "r1_w" and a["stratum"] == "novel"]
    concept = {}
    for name in ("dev", "test"):
        for l in (HERE / "pool" / f"{name}.jsonl").read_text().splitlines():
            it = json.loads(l); concept[it["id"]] = it["concept_tree"]
    by = collections.defaultdict(list)
    for it in items:
        by[it["frame"]].append(it)
    rnd = random.Random(SEED)
    picked = []
    for frame, v in sorted(by.items()):
        rnd.shuffle(v)
        picked += v[: max(1, round(len(v) * 0.10))]
    picked.sort(key=lambda a: a["id"])
    lines = [f"# Owner review sample: {len(picked)} of {len(items)} novel items (10%, stratified by frame)", "",
             "For each row: does the **English** say the same thing as the **tree**? (The tree is the authored form; the Talema",
             "text is its exact compilation. The blind reader's English is shown for reference.) Put `x` in the last column for",
             "any item that is wrong or that you dispute; write the ids to `owner_drops.txt`, then rerun `freeze.py`.", "",
             "| id | frame | English (intended) | tree | blind reader said | wrong? |", "|---|---|---|---|---|---|"]
    for a in picked:
        r = reviews.get(a["id"], {})
        lines.append(f"| {a['id']} | {a['frame']} | {a['english']} | `{concept[a['id']]}` | {r.get('reader', '')} | |")
    (HERE / "owner_review_sample.md").write_text("\n".join(lines) + "\n")
    print("sample:", len(picked), dict(collections.Counter(a["frame"] for a in picked)))


if __name__ == "__main__":
    main()
