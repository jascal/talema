"""Put the authored trees into the unmarked order (Amendment 4; decisions of the language's owner, 2026-09-30).

Unmarked order: complements (object, indirect object) first, then modifiers, then the subject last; in a noun phrase the
determiner closes the phrase, after any `of` phrase. The change only reorders a head's dependents, so the meaning and the
family key are unchanged. Rewrites research/benchmark/authored/*.tsv in place and prints what moved.

    research/.venv/bin/python research/benchmark/normalize_order.py
"""
import collections
from pathlib import Path

import bench

A = bench.A
HERE = Path(__file__).parent
ROLES = {"SUBJ": "subj", "OBJ": "comp", "DAT": "comp"}
OF_ROOT = "d"


def kind(child):
    head = child[0]
    if head in ROLES:
        return ROLES[head]
    try:
        root = bench.atom_root(head)
    except bench.ItemError:
        return "mod"
    if root == OF_ROOT:
        return "of"
    if root is not None and bench.LEX.roots[root][0] == "DET":
        return "det"
    return "mod"


def normalize(tree, moved):
    head, kids = tree
    kids = [normalize(k, moved) for k in kids]
    before = [k[0] for k in kids]
    comps = [k for k in kids if kind(k) == "comp"]
    subjs = [k for k in kids if kind(k) == "subj"]
    rest = [k for k in kids if kind(k) not in ("comp", "subj")]
    kids = comps + rest + subjs
    if [k[0] for k in kids] != before:
        moved["complements-before-modifiers"] += 1
    last_of = max((i for i, k in enumerate(kids) if kind(k) == "of"), default=None)
    if last_of is not None:
        dets = [k for k in kids[:last_of] if kind(k) == "det"]
        if dets:
            kids = [k for k in kids[:last_of + 1] if kind(k) != "det"] + dets + kids[last_of + 1:]
            moved["determiner-after-of-phrase"] += 1
    return (head, kids)


def show(tree, top=True):
    head, kids = tree
    if not kids:
        return f"({head})" if top else head
    return "(" + " ".join([head] + [show(k, False) for k in kids]) + ")"


def main():
    moved = collections.Counter()
    changed_lines = 0
    for path in sorted((HERE / "authored").glob("*.tsv")):
        out = []
        for line in path.read_text().splitlines():
            cols = line.split("\t")
            if len(cols) == 3 and not line.startswith("#"):
                new = show(normalize(A.parse_trees(cols[2], "n")[0], moved))
                if new != cols[2]:
                    changed_lines += 1
                    cols[2] = new
                line = "\t".join(cols)
            out.append(line)
        path.write_text("\n".join(out) + "\n")
    print("lines changed:", changed_lines, "| node rewrites:", dict(moved))


if __name__ == "__main__":
    main()
