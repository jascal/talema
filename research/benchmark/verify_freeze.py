"""Independent checks on the frozen benchmark files (P5). Exits non-zero on any failure.

  - ids are unique; dev and test share no Talema text and no family hash; no novel family is in the corpus
  - every R1 input passes avatar/dialogue.py validate_speech (the real function, not the mirror); every R2 input is inside
    its character/length domain, and validate_speech accepts exactly the valid and meaning-change items (the structural
    and unknown-root ones are broken on purpose, so it must reject them)
  - every R1 text parses with the exact node parser, no unknown roots, and its tree equals the stored native tree
  - every R2 input's exact-parser verdict equals its gold verdict; locations are within range
  - the input files carry no answer fields
  - every novel item is in the unmarked order (scoring.violations)
"""
import json
import sys
from pathlib import Path

import bench

sys.path.insert(0, str(bench.TALEMA / "avatar"))
import dialogue  # noqa: E402

FROZEN = Path(__file__).parent / "frozen"


def load(p):
    return [json.loads(l) for l in p.read_text().splitlines()]


def main():
    failures = []
    corpus = bench.corpus_screen()
    texts, hashes = {}, {}
    for name in ("dev", "test"):
        ans = load(FROZEN / name / "answers.jsonl")
        r1w = [a for a in ans if a["task"] == "r1_w"]
        r2 = [a for a in ans if a["task"] == "r2"]
        ids = [a["id"] for a in ans]
        if len(set(ids)) != len(ids):
            failures.append(f"{name}: duplicate ids")
        for fname, key in (("r1_inputs.jsonl", "text"), ("w_inputs.jsonl", "english"), ("r2_inputs.jsonl", "text")):
            for row in load(FROZEN / name / fname):
                if set(row) != {"id", key}:
                    failures.append(f"{name}/{fname}: {row['id']} carries extra fields {set(row) - {'id', key}}")
        for a in r1w:
            try:
                dialogue.validate_speech(a["talema"])
            except ValueError as exc:
                failures.append(f"{name}: {a['id']} fails validate_speech: {exc}")
            if a["stratum"] == "novel":
                texts.setdefault(a["talema"], set()).add(name)
                hashes.setdefault(a["family_hash"], set()).add(name)
        # R1 texts through the exact parser, tree equality
        verdicts = bench.parse_with_node([a["talema"] for a in r1w])
        for a, v in zip(r1w, verdicts):
            if not v["ok"] or v.get("unknown"):
                failures.append(f"{name}: {a['id']} exact parser: {v.get('error') or v.get('unknown')}")
            elif bench.decode(a["talema"][:-1].strip()) != tuple_of(a["native_tree"]):
                failures.append(f"{name}: {a['id']} stored tree differs from the decoded text")
        # R2 verdicts
        verdicts = bench.parse_with_node([e["text"] for e in r2])
        for e, v in zip(r2, verdicts):
            g = e["gold"]["verdict"]
            got = "error" if not v["ok"] else ("warning" if v.get("unknown") else "valid")
            if got != g:
                failures.append(f"{name}: {e['id']} gold {g} but parser says {got}")
            n_tokens = len(e["text"].split())
            if any(not 0 <= t < n_tokens for t in e["gold"].get("accepted_tokens", [])):
                failures.append(f"{name}: {e['id']} accepted token out of range")
            if not bench.in_domain(e["text"]):
                failures.append(f"{name}: {e['id']} R2 text is outside the character/length domain")
            # the tutor's own validator: well-formed items pass, and the deliberately broken ones must fail
            try:
                dialogue.validate_speech(e["text"])
                accepted = True
            except ValueError:
                accepted = False
            if accepted != (e["category"] in ("valid", "meaning-change")):
                failures.append(f"{name}: {e['id']} ({e['category']}) validate_speech verdict {accepted} disagrees with its category")
        # the unmarked order (Amendment 4)
        import scoring
        for a in r1w:
            if a["stratum"] == "novel" and scoring.violations(a["native_tree"]):
                failures.append(f"{name}: {a['id']} departs from the unmarked order: {scoring.violations(a['native_tree'])[0]}")
        # novelty against the corpus
        for a in r1w:
            if a["stratum"] == "novel" and (a["talema"] in corpus["texts"]):
                failures.append(f"{name}: {a['id']} novel text is in the corpus")
    clash = [t for t, s in texts.items() if len(s) > 1]
    if clash:
        failures.append(f"dev and test share {len(clash)} Talema text(s)")
    clash = [h for h, s in hashes.items() if len(s) > 1]
    if clash:
        failures.append(f"dev and test share {len(clash)} family hash(es)")
    for f in failures[:40]:
        print("FAIL", f)
    print("verify_freeze:", "OK" if not failures else f"{len(failures)} failure(s)")
    sys.exit(1 if failures else 0)


def tuple_of(t):
    return tuple([t[0]] + [tuple_of(k) for k in t[1:]])


if __name__ == "__main__":
    main()
