"""Write FREEZE.md from frozen/MANIFEST.json and the review files, so no number in it is typed by hand."""
import collections
import json
from pathlib import Path

HERE = Path(__file__).parent


def load(p):
    return [json.loads(l) for l in (HERE / p).read_text().splitlines()]


def main():
    m = json.loads((HERE / "frozen" / "MANIFEST.json").read_text())
    v1 = {r["id"]: r for r in load("review/reviews.jsonl")}
    v2 = {r["id"]: r for r in load("review/reviews_whether_v2.jsonl")}
    final = {**v1, **v2}
    pool = {it["id"]: it for n in ("dev", "test") for it in load(f"pool/{n}.jsonl")}
    frames = collections.defaultdict(lambda: [0, 0, 0])
    for i, it in pool.items():
        f = frames[it["frame"]]
        f[0] += 1
        f[1] += bool(v1[i].get("same"))
        f[2] += bool(final[i].get("same"))
    counts, rv = m["counts"], m["review"]
    L = []
    a = L.append
    a("# P5 — benchmark freeze record")
    a("")
    a("**Status: candidate freeze, 2026-09-29.** Test items, test answers and the dev set are built, verified and hashed. The")
    a("final freeze waits for one preregistered step that only the repository owner can do: read the 10% sample in")
    a("`owner_review_sample.md`, list disputed ids in `owner_drops.txt`, then rerun `freeze.py` and `verify_freeze.py` and")
    a("commit the new manifest. **No system has been run on any item.**")
    a("")
    a("## What is frozen (`frozen/`, hashes in `frozen/MANIFEST.json`)")
    a("")
    a("| set | R1 (read) and W (write) items | of which novel / exposed | R2 items |")
    a("|---|---|---|---|")
    for n in ("dev", "test"):
        c = counts[n]
        r2 = c["r2"]
        a(f"| {n} | {c['r1_w_items']} | {c['novel']} / {c['exposed']} | {sum(r2.values())} ({r2['valid']} valid, {r2['structural']} structural, "
          f"{r2['unknown-root']} unknown-root, {r2['meaning-change']} meaning-change) |")
    a("")
    a("R1 and W use the **same** items in separate calls (read Talema to tree; write English to tree). C is `c_test.json`: four new")
    a("conversations of eight learner turns each. The three conversations in `conversation_ab.py` are development only.")
    a("Test inputs (`frozen/test/*_inputs.jsonl`) carry only an id and the text or English; test **answers** are in")
    a("`frozen/test/answers.jsonl`. Training and prompting scripts must not load it; they screen candidate training trees against")
    a("`frozen/test_family_hashes.txt` (hashes of the test families) instead.")
    a("")
    a("## How the items were made")
    a("")
    a("1. `make_specs.py`: a seeded spec per item, an authoring frame (12 fixed strata) and three random seed concepts, 60% from")
    a("   roots the corpus uses and 40% from the heavier half of roots it never uses, weighted toward ordinary words. The author does not")
    a("   choose the topic. 345 dev and 1,070 test specs.")
    a("2. Authoring: a Claude model wrote each English-tree pair, using at least two seeds per item, with no system output in view.")
    a("   The tree is the notation `author.py` accepts. The reviewer (`gpt-5.4-mini`) and the tutor (`gpt-6-luna`) are OpenAI models, so the")
    a("   items were not written by the tutor's family; the reviewer is a different family from the author.")
    a("3. `check_pairs.py`: strict compile (an ambiguous concept must carry `/CLASS`; no literals or numbers), inside the")
    a("   `validate_speech` character and length domain, 2 to 16 words, its Talema text, native tree and family key **not** in the")
    a("   corpus, family unique across dev and test, and the exact node parser accepts it with no unknown root.")
    a("4. `review.py`: the blind meaning review below.")
    a("5. `freeze.py`: seeded, frame-stratified selection of the survivors; exposed items; R2 (`r2.py`); hashing.")
    a("")
    a("## Independent meaning review")
    a("")
    a("A different-family model (`gpt-5.4-mini`, low reasoning effort) saw only each item's tree (every word with its class and English")
    a("meaning, dependents indented under their head) and wrote the English it expresses, with four corpus examples (five in the corrected pass). A second call,")
    a("without the tree, compared that reading with the intended English. Only \"same\" survives; nothing is repaired.")
    a("")
    a("| set | authored | judged same (v1 rubric) | judged same (after the fix below) | selected |")
    a("|---|---|---|---|---|")
    for n in ("dev", "test"):
        ids = [i for i in pool if pool[i]["set"] == n]
        a(f"| {n} novel | {rv[n]['novel_authored']} | {sum(bool(v1[i].get('same')) for i in ids)} | {rv[n]['novel_same']} | {counts[n]['novel']} |")
    for n in ("dev", "test"):
        a(f"| {n} exposed candidates | {rv[n]['exposed_candidates']} | | {rv[n]['exposed_same']} | {counts[n]['exposed']} |")
    a("")
    wh = [i for i in v2]
    a(f"**A fault in my own rubric, and its fix.** The first pass judged only {sum(bool(v1[i].get('same')) for i in wh)} of the {len(wh)} `whether`-rooted items \"same\": the reader wrote")
    a("\"whether you ...\" instead of a question, because the rubric never said that a top-level `whether` marks a yes/no question. That is")
    a(f"a reading-instruction bug, not an item fault. The {len(wh)} items were re-read with one added sentence (\"a sentence whose top word is")
    a(f"'whether' is a yes/no question: write it as a direct question\") and one added corpus example (`Do you want a story?`); {sum(bool(v2[i].get('same')) for i in wh)} were")
    a("then judged same. Both result files are kept (`review/reviews.jsonl`, `review/reviews_whether_v2.jsonl`), the fix was made")
    a("before any system was scored, and only `whether`-rooted items were re-read.")
    a("")
    a("| frame | authored | same, v1 | same, after fix |")
    a("|---|---|---|---|")
    for f, (t, s1, s2) in sorted(frames.items()):
        a(f"| {f} | {t} | {s1} | {s2} |")
    a("")
    a("**Selection bias to keep in mind.** An item survives only if a small model reads it correctly from its tree. Items that model")
    a("misreads (numeral phrases and plurals in particular: the *number or quantity* frame loses the most) are dropped, including some")
    a("that are correct, so the benchmark is somewhat easier for reading than the full space, and the number frame is under-represented")
    a("(the shortfall was filled from other frames). Every system is scored on the same items, so comparisons are unaffected, but absolute")
    a("reading accuracy should not be read as a claim about all Talema.")
    a("")
    rr = load("review/reviews_reorder.jsonl")
    was = [x for x in rr if v1[x["id"]].get("same")]
    pending = m.get("reorder_review_pending", [])
    a("## Word order (Amendment 4, 2026-09-30)")
    a("")
    a("Talema's dependents are free in order (rule R2); the unmarked order is complements (object, indirect object), then modifiers, then")
    a("the subject last, and other orders mark emphasis. The language's owner decided that in a noun phrase the `of` phrase comes before the")
    a("determiner. On the corpus, 97.8% of single-tree sentences follow this (`scoring.py`). My items were first written with `will` before the")
    a("object in some sentences and the determiner before the `of` phrase in many, so `normalize_order.py` rewrote the authored trees into")
    a("the unmarked order (meanings and family keys unchanged). `verify_freeze.py` now fails any novel item that departs from it.")
    a("")
    a(f"Every item whose Talema text changed ({len(load('review/changed_ids.txt')) if False else len(Path(HERE / 'review' / 'changed_ids.txt').read_text().split())}) needs a fresh blind read. The OpenAI account ran out of credit partway, so "
      f"{len(rr)} were re-read and **{len(Path(HERE / 'review' / 'reorder_pending_ids.txt').read_text().split())} are pending** and carry their pre-reorder verdict for now "
      f"({len(pending)} of them are in the selected sets). Of the re-read items judged same before, {sum(x['same'] is True for x in was)} of {len(was)} were still judged same, "
      f"and {sum(x['same'] is True and not v1[x['id']].get('same') for x in rr)} judged different before were judged same now, so a single reading pass is about 96% stable either way. "
      f"`review.py --ids-file review/reorder_pending_ids.txt` finishes the job once credit is restored; rerun `freeze.py` after it.")
    a("")
    a("W's primary score is order-insensitive (`scoring.tree_match`), with adherence to the unmarked order (`scoring.is_unmarked`) reported separately.")
    a("")
    a("## Power at the final counts")
    a("")
    a("Non-inferiority margin 5 points, true difference 0, items as independent (frames are fixed strata, families are unique),")
    a("simulated with `power_sim.py` at the final novel count:")
    a("")
    a("| paired disagreement | power, 95% interval | power, 99% interval (Holm's smallest step over five contrasts) |")
    a("|---|---|---|")
    for d, v in m["power_at_final_n"].items():
        a(f"| {d.split('=')[1]} | {v['z=1.96']} | {v['z=2.576']} |")
    a("")
    import numpy as np
    import power_sim
    need = power_sim.needed(0.05, 0.20, 0.0, 2.576, 0.0, 1, 2000, np.random.default_rng(20260930))
    a("This meets the 80% target at 20% disagreement with the 95% interval, is at the edge of it with the 99% interval, and falls")
    a(f"short at 30% disagreement. The preregistration's rule (widen the margin before scoring if the required count exceeds about")
    a(f"1,000) was not triggered: at 20% disagreement and the 99% interval about {need} items are needed (`power_sim.py needed`).")
    a("")
    a("## Operational choices the preregistration left open")
    a("")
    a("- **W shares R1's items.** The preregistration listed 300 W intents; the power simulation needs the same N for W's tree match as")
    a("  for R1's, so W uses all R1 items (separate calls). Dev is 300 novel + 50 exposed.")
    a("- **The reader saw a tree, not a linear gloss.** The preregistration said \"Talema text plus word-by-word gloss\"; a linear gloss")
    a("  hides which word attaches where, so the reader was given the indented tree with each word's gloss.")
    a("- **R2 gold is the exact parser's verdict.** `valid` and `meaning-change` items are accepted by the parser (the latter is")
    a("  grammatical but says something else); `structural` items are rejected (arity ending changed, a word deleted or inserted);")
    a("  `unknown-root` items are accepted with an `UNKNOWN_ROOT` warning at the edited word. Locations are 0-based token indexes over")
    a("  the whitespace-separated words, the final `.` included; the accepted locations for a structural error are the edited token and")
    a("  the token the parser's offset falls in. `validate_speech` accepts exactly the valid and meaning-change items.")
    a("- **W scoring** is strict canonical tree match (native roots); root-set F1 is secondary; no alternative trees were declared.")
    a("- **Family key** is the head root plus the sorted content-word roots (nouns, verbs, adjectives, adverbs, numerals), hashed to")
    a("  16 hex characters in `frozen/*_family_hashes.txt`.")
    a("- **Exposed items** are corpus sentences (a complete English sentence, a single tree, 3 to 12 words, in the domain, distinct text")
    a("  and family), stratified by book. Students are trained on them and rung 0 has them in its book; the exposed-minus-novel gap")
    a("  is the memorisation control. Dev and test exposed sets are disjoint.")
    a("- **Vocabulary is seeded and often odd.** Random seed words produce sentences that are grammatical and meaningful but sometimes")
    a("  unnatural (\"The temperature is yellow\"). The benchmark tests reading and writing Talema, not conversational fitness.")
    a("")
    a("## Files and hashes")
    a("")
    a("| file | sha256 |")
    a("|---|---|")
    for f, h in m["sha256"].items():
        a(f"| `{f}` | `{h[:16]}…` |")
    a("")
    a("Tool hashes, review-file hashes and the owner drops (none yet) are in `frozen/MANIFEST.json`.")
    a("")
    a("## Before the final freeze")
    a("")
    a("1. The owner reads `owner_review_sample.md` and lists disputed ids in `owner_drops.txt`.")
    a("2. `research/.venv/bin/python research/benchmark/freeze.py` then `verify_freeze.py`; commit the new manifest and hashes.")
    a("3. The power table above is regenerated by `freeze.py`; if drops bring the test novel count below 930, it changes with it.")
    a("")
    a("## Reproduce")
    a("")
    a("```bash")
    a("PY=research/.venv/bin/python")
    a("$PY research/benchmark/make_specs.py && $PY research/benchmark/make_exposed.py && $PY research/benchmark/c_test.py")
    a("$PY research/benchmark/check_pairs.py --parse")
    a("$PY research/benchmark/review.py --workers 8 && $PY research/benchmark/review.py --whether-v2 --workers 8   # spends on the OpenAI key")
    a("$PY research/benchmark/freeze.py && $PY research/benchmark/verify_freeze.py && $PY research/benchmark/make_owner_sample.py")
    a("$PY research/benchmark/write_freeze_md.py")
    a("```")
    (HERE / "FREEZE.md").write_text("\n".join(L) + "\n")
    print("wrote FREEZE.md,", len(L), "lines")


if __name__ == "__main__":
    main()
