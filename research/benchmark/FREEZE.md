# P5 — benchmark freeze record

**Status: candidate freeze, 2026-09-29.** Test items, test answers and the dev set are built, verified and hashed. The
final freeze waits for one preregistered step that only the repository owner can do: read the 10% sample in
`owner_review_sample.md`, list disputed ids in `owner_drops.txt`, then rerun `freeze.py` and `verify_freeze.py` and
commit the new manifest. **No system has been run on any item.**

## What is frozen (`frozen/`, hashes in `frozen/MANIFEST.json`)

| set | R1 (read) and W (write) items | of which novel / exposed | R2 items |
|---|---|---|---|
| dev | 350 | 300 / 50 | 101 (50 valid, 17 structural, 17 unknown-root, 17 meaning-change) |
| test | 1030 | 930 / 100 | 300 (150 valid, 50 structural, 50 unknown-root, 50 meaning-change) |

R1 and W use the **same** items in separate calls (read Talema to tree; write English to tree). C is `c_test.json`: four new
conversations of eight learner turns each. The three conversations in `conversation_ab.py` are development only.
Test inputs (`frozen/test/*_inputs.jsonl`) carry only an id and the text or English; test **answers** are in
`frozen/test/answers.jsonl`. Training and prompting scripts must not load it; they screen candidate training trees against
`frozen/test_family_hashes.txt` (hashes of the test families) instead.

## How the items were made

1. `make_specs.py`: a seeded spec per item, an authoring frame (12 fixed strata) and three random seed concepts, 60% from
   roots the corpus uses and 40% from the heavier half of roots it never uses, weighted toward ordinary words. The author does not
   choose the topic. 345 dev and 1,070 test specs.
2. Authoring: a Claude model wrote each English-tree pair, using at least two seeds per item, with no system output in view.
   The tree is the notation `author.py` accepts. The reviewer (`gpt-5.4-mini`) and the tutor (`gpt-6-luna`) are OpenAI models, so the
   items were not written by the tutor's family; the reviewer is a different family from the author.
3. `check_pairs.py`: strict compile (an ambiguous concept must carry `/CLASS`; no literals or numbers), inside the
   `validate_speech` character and length domain, 2 to 16 words, its Talema text, native tree and family key **not** in the
   corpus, family unique across dev and test, and the exact node parser accepts it with no unknown root.
4. `review.py`: the blind meaning review below.
5. `freeze.py`: seeded, frame-stratified selection of the survivors; exposed items; R2 (`r2.py`); hashing.

## Independent meaning review

A different-family model (`gpt-5.4-mini`, low reasoning effort) saw only each item's tree (every word with its class and English
meaning, dependents indented under their head) and wrote the English it expresses, with four corpus examples (five in the corrected pass). A second call,
without the tree, compared that reading with the intended English. Only "same" survives; nothing is repaired.

| set | authored | judged same (v1 rubric) | judged same (after the fix below) | selected |
|---|---|---|---|---|
| dev novel | 345 | 307 | 332 | 300 |
| test novel | 1070 | 930 | 1010 | 930 |
| dev exposed candidates | 73 | | 59 | 50 |
| test exposed candidates | 248 | | 180 | 100 |

**A fault in my own rubric, and its fix.** The first pass judged only 4 of the 119 `whether`-rooted items "same": the reader wrote
"whether you ..." instead of a question, because the rubric never said that a top-level `whether` marks a yes/no question. That is
a reading-instruction bug, not an item fault. The 119 items were re-read with one added sentence ("a sentence whose top word is
'whether' is a yes/no question: write it as a direct question") and one added corpus example (`Do you want a story?`); 113 were
then judged same. Both result files are kept (`review/reviews.jsonl`, `review/reviews_whether_v2.jsonl`), the fix was made
before any system was scored, and only `whether`-rooted items were re-read.

| frame | authored | same, v1 | same, after fix |
|---|---|---|---|
| coordination | 85 | 82 | 82 |
| copular | 169 | 159 | 159 |
| declarative | 241 | 238 | 238 |
| modal or tense | 127 | 124 | 124 |
| negation | 114 | 108 | 108 |
| number or quantity | 42 | 24 | 24 |
| place or time | 141 | 139 | 140 |
| possession | 42 | 39 | 39 |
| request | 99 | 95 | 95 |
| subordination | 114 | 112 | 112 |
| wh question | 127 | 113 | 113 |
| yes-no question | 114 | 4 | 108 |

**Selection bias to keep in mind.** An item survives only if a small model reads it correctly from its tree. Items that model
misreads (numeral phrases and plurals in particular: the *number or quantity* frame loses the most) are dropped, including some
that are correct, so the benchmark is somewhat easier for reading than the full space, and the number frame is under-represented
(the shortfall was filled from other frames). Every system is scored on the same items, so comparisons are unaffected, but absolute
reading accuracy should not be read as a claim about all Talema.

## Power at the final counts

Non-inferiority margin 5 points, true difference 0, items as independent (frames are fixed strata, families are unique),
simulated with `power_sim.py` at the final novel count:

| paired disagreement | power, 95% interval | power, 99% interval (Holm's smallest step over five contrasts) |
|---|---|---|
| 0.1 | 0.997 | 0.989 |
| 0.2 | 0.923 | 0.794 |
| 0.3 | 0.799 | 0.586 |

This meets the 80% target at 20% disagreement with the 95% interval, is at the edge of it with the 99% interval, and falls
short at 30% disagreement. The preregistration's rule (widen the margin before scoring if the required count exceeds about
1,000) was not triggered: at 20% disagreement and the 99% interval about 940 items are needed (`power_sim.py needed`).

## Operational choices the preregistration left open

- **W shares R1's items.** The preregistration listed 300 W intents; the power simulation needs the same N for W's tree match as
  for R1's, so W uses all R1 items (separate calls). Dev is 300 novel + 50 exposed.
- **The reader saw a tree, not a linear gloss.** The preregistration said "Talema text plus word-by-word gloss"; a linear gloss
  hides which word attaches where, so the reader was given the indented tree with each word's gloss.
- **R2 gold is the exact parser's verdict.** `valid` and `meaning-change` items are accepted by the parser (the latter is
  grammatical but says something else); `structural` items are rejected (arity ending changed, a word deleted or inserted);
  `unknown-root` items are accepted with an `UNKNOWN_ROOT` warning at the edited word. Locations are 0-based token indexes over
  the whitespace-separated words, the final `.` included; the accepted locations for a structural error are the edited token and
  the token the parser's offset falls in. `validate_speech` accepts exactly the valid and meaning-change items.
- **W scoring** is strict canonical tree match (native roots); root-set F1 is secondary; no alternative trees were declared.
- **Family key** is the head root plus the sorted content-word roots (nouns, verbs, adjectives, adverbs, numerals), hashed to
  16 hex characters in `frozen/*_family_hashes.txt`.
- **Exposed items** are corpus sentences (a complete English sentence, a single tree, 3 to 12 words, in the domain, distinct text
  and family), stratified by book. Students are trained on them and rung 0 has them in its book; the exposed-minus-novel gap
  is the memorisation control. Dev and test exposed sets are disjoint.
- **Vocabulary is seeded and often odd.** Random seed words produce sentences that are grammatical and meaningful but sometimes
  unnatural ("The temperature is yellow"). The benchmark tests reading and writing Talema, not conversational fitness.

## Files and hashes

| file | sha256 |
|---|---|
| `frozen/c_test.json` | `52c1c81f802ea48f…` |
| `frozen/dev/answers.jsonl` | `5aed6413907cd784…` |
| `frozen/dev/r1_inputs.jsonl` | `82b3a88ef7254361…` |
| `frozen/dev/r2_inputs.jsonl` | `4fd25faac846cc97…` |
| `frozen/dev/w_inputs.jsonl` | `db31d17be4070ff0…` |
| `frozen/dev_family_hashes.txt` | `6572fddba88829ba…` |
| `frozen/test/answers.jsonl` | `7eccff2d2e09b5be…` |
| `frozen/test/r1_inputs.jsonl` | `69d3571a5d0d353f…` |
| `frozen/test/r2_inputs.jsonl` | `5f39e011ef996220…` |
| `frozen/test/w_inputs.jsonl` | `f8c8a5bbbace9029…` |
| `frozen/test_family_hashes.txt` | `5500d1e778be548f…` |

Tool hashes, review-file hashes and the owner drops (none yet) are in `frozen/MANIFEST.json`.

## Before the final freeze

1. The owner reads `owner_review_sample.md` and lists disputed ids in `owner_drops.txt`.
2. `research/.venv/bin/python research/benchmark/freeze.py` then `verify_freeze.py`; commit the new manifest and hashes.
3. The power table above is regenerated by `freeze.py`; if drops bring the test novel count below 930, it changes with it.

## Reproduce

```bash
PY=research/.venv/bin/python
$PY research/benchmark/make_specs.py && $PY research/benchmark/make_exposed.py && $PY research/benchmark/c_test.py
$PY research/benchmark/check_pairs.py --parse
$PY research/benchmark/review.py --workers 8 && $PY research/benchmark/review.py --whether-v2 --workers 8   # spends on the OpenAI key
$PY research/benchmark/freeze.py && $PY research/benchmark/verify_freeze.py && $PY research/benchmark/make_owner_sample.py
$PY research/benchmark/write_freeze_md.py
```
