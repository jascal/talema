"""Shared library for building the Talema benchmark (PREREG_TRANSFER_LADDER.md section 5, P5).

An item is an English-tree pair: the English gloss the author means, and a tree of concepts in the notation
lm-sae's author.py accepts (the same notation as the `tree` field of data/sentences.jsonl). Everything else is derived
by the exact tools: the Talema text (author.py's spelling), the native-root tree (conlang.decode), the parser's
verdict (grammar/parser.mjs), and the family key.

Run with research/.venv/bin/python (lm-sae's author imports torch). LM_SAE overrides the lm-sae checkout.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TALEMA = HERE.parents[1]
LM_SAE = Path(os.environ.get("LM_SAE", Path.home() / "code" / "lm-sae"))
sys.path.insert(0, str(LM_SAE / "scripts" / "conlang"))
import author as A  # noqa: E402
from conlang import decode, numeral  # noqa: E402,F401

CONTENT = {"NOUN", "VERB", "ADJ", "ADV", "NUM"}     # classes whose roots count towards the family key
LEX = A.Lex()
ROLE_ATOMS = {"SUBJ", "OBJ", "DAT"}


class ItemError(Exception):
    pass


def atom_root(atom: str) -> str | None:
    """The root an atom stands for, strictly: an atom that could mean several roots is an error, not a guess."""
    if atom in ROLE_ATOMS or atom.startswith('"') or re.fullmatch(r"-?\d+([.,]\d+)?", atom):
        return None
    if atom.startswith("="):
        if atom[1:] not in LEX.roots:
            raise ItemError(f"{atom} is not a root")
        return atom[1:]
    base, _, cls = atom.partition("/")
    hits = LEX.key.get(base.lower() + ("/" + cls if cls else ""))
    if not hits:
        raise ItemError(f"no concept '{atom}'")
    roots = list(dict.fromkeys(r for r, _ in hits))
    if len(roots) > 1:
        options = "; ".join(f"{base}/{LEX.roots[r][0]}=" + r for r in roots[:5])
        raise ItemError(f"'{atom}' is ambiguous (write word/CLASS or =root): {options}")
    return roots[0]


def compile_tree(tree_text: str) -> dict:
    """Concept tree text -> {talema, native, roots, content_roots, family}. Raises ItemError."""
    try:
        trees = A.parse_trees(tree_text, "item")
    except (SystemExit, IndexError) as exc:
        raise ItemError(f"unparseable tree: {exc}")
    if len(trees) != 1:
        raise ItemError(f"expected one tree, found {len(trees)}")
    roots: list[str] = []
    errors: list[str] = []

    def walk(t):
        head, kids = t
        try:
            r = atom_root(head)
        except ItemError as exc:
            errors.append(str(exc)); r = "?"
        if r is None and not (head in ROLE_ATOMS):
            errors.append(f"literals and numbers are outside the benchmark domain: {head}")
        roots.append(r if r is not None else (LEX.resolve(head, "item")[0] if head in ROLE_ATOMS else "?"))
        for k in kids:
            walk(k)
    walk(trees[0])
    if errors:
        raise ItemError(" | ".join(dict.fromkeys(errors)))
    try:
        words = A.spell(LEX, trees[0], "item")
    except SystemExit as exc:
        raise ItemError(str(exc))
    talema = " ".join(words) + " ."
    native = decode(" ".join(words))
    content = sorted(r for r in roots if LEX.roots.get(r, ("",))[0] in CONTENT)
    return {"talema": talema, "native": native, "roots": roots, "content_roots": content,
            "family": family_key(roots[0], content)}


def family_key(head_root: str, content_roots: list[str]) -> str:
    return f"{head_root}|{','.join(sorted(content_roots))}"


def family_hash(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def in_domain(talema: str) -> bool:
    """Mirror of avatar/dialogue.py validate_speech (checked against it at freeze time)."""
    return bool(talema.strip()) and len(talema) <= 350 and re.fullmatch(r"[a-z\s.]+", talema) is not None


def corpus_screen() -> dict:
    """Texts, native trees and family keys of every corpus sentence that is a single tree."""
    texts, trees, families, roots_seen = set(), set(), set(), set()
    for line in (TALEMA / "data" / "sentences.jsonl").read_text().splitlines():
        row = json.loads(line)
        text = row["talema"].strip()
        body = text[:-1].strip() if text.endswith(".") else text
        texts.add(text)
        try:
            tree = decode(body)
        except Exception:
            continue
        trees.add(repr(tree))

        def walk(t, acc):
            acc.append(t[0])
            for k in t[1:]:
                walk(k, acc)
        acc: list[str] = []
        walk(tree, acc)
        roots_seen.update(acc)
        content = [r for r in acc if LEX.roots.get(r, ("",))[0] in CONTENT]
        families.add(family_key(acc[0], content))
    return {"texts": texts, "trees": trees, "families": families, "roots": roots_seen}


def parse_with_node(texts: list[str]) -> list[dict]:
    """The exact parser's verdict for each text: {ok, unknown_roots, error, tree_roots_ok}."""
    payload = "\n".join(json.dumps({"i": i, "text": t}) for i, t in enumerate(texts))
    proc = subprocess.run(["node", str(HERE / "parse_batch.mjs")], input=payload, capture_output=True, text=True,
                          cwd=str(TALEMA / "grammar"), check=True)
    return [json.loads(line) for line in proc.stdout.splitlines()]
