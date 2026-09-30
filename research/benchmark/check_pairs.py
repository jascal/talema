"""Validate authored English-tree pairs and build the item pool (P5).

Authored files: research/benchmark/authored/<set>_*.tsv, one item per line:  id <TAB> english <TAB> tree
(`#` lines and blanks ignored). For every pair the checker
  - requires the id to exist in specs/<set>.tsv (dev or test),
  - compiles the tree strictly (an ambiguous concept must carry /CLASS or be =root; no literals or numbers),
  - keeps only items inside validate_speech's domain and 2-16 words,
  - drops an item whose Talema text, native tree or FAMILY KEY is in the corpus (not novel), or whose family key is
    already used by another item in dev or test (families are disjoint and unique),
and writes the accepted items to pool/<set>.jsonl. Rerun freely: the pool is rebuilt from the authored files.

    research/.venv/bin/python research/benchmark/check_pairs.py [--parse]
"""
import argparse
import json
from pathlib import Path

import bench

HERE = Path(__file__).parent


def read_specs(name):
    rows = (HERE / "specs" / f"{name}.tsv").read_text().splitlines()[1:]
    return {r.split("\t")[0]: r.split("\t") for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parse", action="store_true", help="also run every accepted text through the exact node parser")
    args = ap.parse_args()
    corpus = bench.corpus_screen()
    specs = {"dev": read_specs("dev"), "test": read_specs("test")}
    seen_family: dict[str, str] = {}
    problems, accepted = [], {"dev": {}, "test": {}}
    for name in ("dev", "test"):
        for path in sorted((HERE / "authored").glob(f"{name}_*.tsv")):
            for n, line in enumerate(path.read_text().splitlines(), 1):
                if not line.strip() or line.startswith("#"):
                    continue
                cols = line.split("\t")
                where = f"{path.name}:{n}"
                if len(cols) != 3 or not all(c.strip() for c in cols):
                    problems.append((where, "expected id<TAB>english<TAB>tree")); continue
                item_id, english, tree = (c.strip() for c in cols)
                if item_id not in specs[name]:
                    problems.append((where, f"{item_id} is not a {name} spec")); continue
                try:
                    c = bench.compile_tree(tree)
                except bench.ItemError as exc:
                    problems.append((where, f"{item_id}: {exc}")); continue
                words = c["talema"].split()[:-1]
                if not bench.in_domain(c["talema"]) or not 2 <= len(words) <= 16:
                    problems.append((where, f"{item_id}: outside the domain or length ({len(words)} words)")); continue
                if c["talema"] in corpus["texts"] or repr(c["native"]) in corpus["trees"] or c["family"] in corpus["families"]:
                    problems.append((where, f"{item_id}: not novel (its text, tree or family is in the corpus)")); continue
                if c["family"] in seen_family and seen_family[c["family"]] != item_id:
                    problems.append((where, f"{item_id}: same family as {seen_family[c['family']]} ({c['family']})")); continue
                seen_family[c["family"]] = item_id
                spec = specs[name][item_id]
                accepted[name][item_id] = {"id": item_id, "set": name, "frame": spec[1], "seeds": spec[2],
                                           "english": english, "concept_tree": tree, "talema": c["talema"],
                                           "native_tree": c["native"], "family": c["family"], "n_words": len(words),
                                           "unseen_roots": [r for r in set(c["content_roots"]) if r not in corpus["roots"]]}
    if args.parse:
        items = [it for name in accepted for it in accepted[name].values()]
        verdicts = bench.parse_with_node([it["talema"] for it in items])
        for it, v in zip(items, verdicts):
            if not v["ok"] or v.get("unknown"):
                problems.append((it["id"], f"exact parser: {v.get('error') or 'unknown roots ' + str(v['unknown'])}"))
                accepted[it["set"]].pop(it["id"], None)
    for name in accepted:
        out = HERE / "pool" / f"{name}.jsonl"
        out.write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in accepted[name].values()))
        print(f"{name}: {len(accepted[name])} accepted of {len(specs[name])} specs")
    for where, msg in problems:
        print("  ", where, msg)
    print(f"{len(problems)} problem(s)")


if __name__ == "__main__":
    main()
