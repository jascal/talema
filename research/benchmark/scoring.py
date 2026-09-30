"""Scoring helpers for the order-insensitive W metric and the unmarked-order check (Amendment 4).

Talema's dependents are free in order (R2) and the unmarked order is: complements (object, indirect object), then
modifiers, then the subject last. Decision of the language's owner (2026-09-30), for a noun phrase with an `of` phrase:
the `of` phrase comes before the determiner ("X of Y the"), so the determiner closes the phrase.

  unordered_key(tree)   the tree with every head's dependents sorted: equal keys mean the same tree up to dependent order
  tree_match(a, b)      order-insensitive by default (the W primary); ordered=True compares exactly
  violations(tree)      the ways a tree departs from the unmarked order ([] = unmarked)
  is_unmarked(tree)

Trees are native-root tuples or lists: (root, child, child, ...), as conlang.decode returns.
"""
import bench

SUBJ = bench.LEX.resolve("SUBJ", "scoring")[0]
OBJ = bench.LEX.resolve("OBJ", "scoring")[0]
DAT = bench.LEX.resolve("DAT", "scoring")[0]
OF = "d"                                             # the root of the adposition "of"
COMPLEMENTS = {OBJ, DAT}


def _t(tree):
    return (tree[0],) + tuple(_t(k) for k in tree[1:])


def unordered_key(tree):
    kids = sorted((unordered_key(k) for k in tree[1:]), key=repr)
    return (tree[0],) + tuple(kids)


def tree_match(a, b, ordered=False):
    return _t(a) == _t(b) if ordered else unordered_key(a) == unordered_key(b)


def _cls(root):
    return bench.LEX.roots.get(root, ("?",))[0]


def violations(tree, path="root"):
    out = []
    roots = [k[0] for k in tree[1:]]
    if SUBJ in roots and roots[-1] != SUBJ:
        out.append(f"{path}: the subject is not last")
    first_comp = next((i for i, r in enumerate(roots) if r in COMPLEMENTS), None)
    if first_comp is not None and any(r not in COMPLEMENTS and r != SUBJ for r in roots[:first_comp]):
        out.append(f"{path}: a modifier comes before a complement")
    for i, r in enumerate(roots):
        if _cls(r) == "DET" and any(x == OF for x in roots[i + 1:]):
            out.append(f"{path}: the determiner comes before an 'of' phrase")
    for n, k in enumerate(tree[1:]):
        out += violations(k, f"{path}/{tree[0]}[{n}]")
    return out


def is_unmarked(tree):
    return not violations(tree)
