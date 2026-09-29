# PREREG T1 — the Talema transfer ladder: what has to be learned in weights?

**Status:** registered 2026-09-29, **before the benchmark exists and before any student model is trained or any rung is
scored on it.** Every claim below is tagged `proved` / `empirical` / `open` (the workspace rule). Nothing here is
`proved`; the hypotheses are all `open`. Deviations are logged at the end, dated, never applied retroactively.

## 1. Question

Talema is a constructed language with an exact compiler, an exact parser and an exact validity check. A tutor for it
today is a frontier model with a ~100k-token book in every call. How much of the language has to live in **weights**,
how much can live in **retrieval**, and how much is already handled by **exact symbolic tools**? And can a small model
that already knows English, Spanish and German (the three languages Talema's roots are built from) acquire it with far
less data than one that starts from scratch?

## 2. What is already known (so it is not re-argued) — all `empirical`, all from `avatar/experiments/results/`

- The tutor writes valid Talema (2 of 135 turns in the last run failed validation twice, nothing spoken) but **reads
  learner Talema badly**; that was the biggest failure of the Talema-input runs (`ab2*.json`).
- A loosened prompt changes how she sounds: naturalness +1.26 [+0.63, +1.87] with English input, fewer forced
  questions, more small words (`ab4_english*.json`). Adding the play to the books did not measurably help what she
  says; it helped reading more than answering. Pooled play-by-prompt interaction on naturalness −0.57 [−1.09, −0.02].
- **Absolute judge scores drift between runs** (every cell fell between `ab3` and `ab4`, including cells the change
  could not touch). Cross-run comparisons of raw scores are unreliable; §5 builds in an anchor.
- A 135-call run costs 14.0M input tokens (13.9M cached), ~30 s per call at the 200k-TPM limit.

## 3. Constraints (the "constrained circumstances")

| resource | what we have |
|---|---|
| GPU | RTX 5050 Laptop, 8 GB. torch 2.14+cu130 sees it. `peft`, `accelerate`, `datasets`, `trl`, `bitsandbytes` are **not installed** (preflight P1) |
| CPU / RAM | 16 cores, 14 GB. fieldrun runs int8 models on CPU |
| Data | 2,525 sentences (2,109 with English), 6,113 lexicon entries (`data/`) |
| Oracles | compiler `lm-sae/scripts/conlang/author.py`; parser `grammar/parser.mjs` + `parse.dl`; `avatar/dialogue.py` `validate_speech` |
| API | one OpenAI key, ~200k tokens/min, ~30 s between calls carrying the book |
| Models cached locally | Llama-3.2-1B/3B, Qwen2.5-0.5B/1.5B/3B, gemma-2-2b (+ Gemma Scope residual SAEs), gemma-3-1b-pt, gemma-4-e2b/e4b, Pythia 70m–6.9b |
| fieldrun bundles built | Llama-3.2-1B, Qwen2.5-0.5B/1.5B/3B/7B, gemma-2-2b, gemma-4-e4b, Pythia ladder |

## 4. Hypotheses

Each states its prediction and what would falsify it. "Match" always means non-inferior within the margin in §7.

- **H1 — the book is mostly dead weight (`open`).** A retrieved slice of ≤5k tokens per turn matches the full book on R
  and W. *Falsified* if the lower bound of the paired difference is below −δ at every slice size tried (2k, 5k, 20k).
- **H2 — weights can replace the book (`open`).** A LoRA-tuned small model, given no book, matches rung 0 on R and W.
- **H3 — lexical transfer (`open`).** Initialising each root from its en/de/es source words (T1) beats plain
  initialisation (T0) at every training-set size. *Falsified* if T1 ≤ T0 at any size with the interval excluding 0.
- **H4 — warm start (`open`).** A pretrained en/es/de model (T2) beats T0 and T1 at small data, and the gap closes as
  data grows. Prediction: at 250 sentences T2 reaches at least T1 + 10 points on R1.
- **H5 — structural reuse (`open`).** After T2, the structural circuit families Talema needs (copy for names,
  succession for numerals; bracket-matching for arity endings *if that detector is built*) are found on Talema
  stimuli by rosetta's toolkit (detect ≥ 80% **and** causal ≥ 80%, its own threshold), and their head sets overlap the
  base model's heads for the same families more than a permutation null does (observed overlap above the null's 95th
  percentile). *Falsified* if the families appear but with head sets no more overlapping than chance (newly formed,
  not reused), or do not appear.
- **H6 — the endings need not be learned (`open`).** A student that emits concept trees (server derives the endings)
  matches one that emits raw Talema text, at less data. Run only at 1k and 4k sentences.

## 5. Benchmark — built and frozen first

Items are **authored blind to every system**, then compiled and checked by the exact tools. A frontier model writes
novel English sentences using only lexicon concepts; `author.py` compiles them to trees; items are dropped if their
tree **or** Talema text appears in `data/sentences.jsonl`. **Every reference item is read for meaning by a person or
model before the freeze**, as a script, not only through the validator (validator-invisible meaning errors were found
in the corpus before; the validator cannot catch them). Frozen means committed with a hash; no item is changed after
any system is scored.

| task | items | scored how |
|---|---|---|
| **R1** reading, well-formed | 300 (200 novel, 100 seen in the corpus) | Talema → concept tree; exact tree match, plus per-node root accuracy |
| **R2** reading, learner errors | 100 | mechanically perturbed trees (wrong ending, missing particle, swapped order, unknown root); detect yes/no and the token index, against the parser's own diagnostic |
| **W** writing | 150 English intents | emit a tree; validity by `validate_speech`; content by round trip: parse the output with the exact parser and compare to the reference (root-set F1, tree match) — **no LLM judge** |
| **C** conversation | 3 conversations × 9 rounds × learner language {Talema, English} | the existing `conversation_ab.py` harness: blind judge (fit, natural), ends-on-question, small-word share, validity/repair rate |

- The seen-minus-novel gap on R1 is the memorisation control.
- **Anchor for C:** every judging batch re-judges the same 27 rung-0 replies, and all scores are reported as
  differences from the anchor in that batch. This is the response to the drift in §2.
- In-context arms take R and W **10 items per call** to keep cost to ~55 calls (~30 min of pacing); students are
  scored one item per call, and a 40-item subset is run both ways to check the batching changes nothing.
- The seen/novel split and the perturbations are generated by a mechanical rule from a fixed seed, not picked by hand.

## 6. Rungs

Training data are only exact-labelled pairs: (Talema, tree, English), from the corpus plus new trees written by the
current tutor **and accepted only if they pass validation and the round trip**, nested at 250 / 1k / 4k / 16k
sentences, three seeds. Benchmark trees and texts are excluded by exact match.

| rung | setup | varied |
|---|---|---|
| 0 | frontier model, full book in context | baseline, re-scored on R/W/C |
| 1 | frontier model, retrieved slice: lexicon entries for the roots the exact parser finds in the learner message and last k turns, plus the grammar chapter | slice 2k / 5k / 20k tokens |
| T0 | small model from scratch, plain-initialised roots | data size |
| T1 | T0 with roots initialised from their en/de/es source words | data size |
| T2 | LoRA on a pretrained en/es/de model, no book | data size, base model |
| T3 | T2 plus a Talema retrieval store and exact-grammar-constrained decoding | data size |
| T2-raw | T2 emitting raw Talema text instead of trees | 1k, 4k only (H6) |

## 7. Decision rules

- **Non-inferior** = the lower bound of the paired bootstrap 95% interval (over items) of (candidate − comparator) is
  above **−5 points** on R1 tree match and W content F1, **and** W validity is no more than 2 points lower.
- **Primary endpoints are R1, R2 and W** (exact-scored, large n). **C is a gate, not a test:** at 24–54 turns per system
  its intervals are about ±0.5 on the 1–5 scale, so it cannot adjudicate small differences. A student passes C if its
  naturalness is not below the anchored rung-0 value by more than 0.5.
- **Supported / not supported / inconclusive** is reported per hypothesis with the intervals. Negative and inconclusive
  results are reported the same as positive ones.
- Selecting among base models (§8) uses the **dev split only**; the final table is scored once on the frozen items.

## 8. Base models for T2 / T3

Candidates are not chosen in advance. Each must pass gates, then a bake-off picks the base.

**Gates, recorded per candidate in preflight:** (a) officially covers English, German and Spanish; (b) a LoRA at
sequence 1024, batch 1, gradient checkpointing fits in 8 GB — *measured*; (c) fieldrun's full-checkpoint f32 top-1
parity against torch is ≥ 59/60; (d) fieldrun's explain/probe surface exists for that arch. Failing (c) or (d) leaves a
model **trainable and scorable on R/W/C but analysis-ineligible for H5**; that is flagged, not hidden.

| candidate | on disk | fieldrun status (from its own docs) | note |
|---|---|---|---|
| Llama-3.2-1B | yes, bundle built | rope; rosetta toolkit 14/15 families | best-characterised for H5 |
| Qwen2.5-1.5B | yes, bundle built | rope; toolkit measured on the coder variant (12/15) | |
| Gemma-3-1B | yes (`unsloth` pt) | gemma3 arch validated 60/60 | large vocabulary; check tokens per Talema word |
| Gemma-2-2B | yes, bundle built | gemma arch validated | **Gemma Scope SAEs on disk**, so H5 could also be read at feature level; 2.6B is tight on 8 GB (gate b) |
| Gemma-4-E2B / E4B | yes | gemma4 validated | E4B may not fit gate (b) |
| Qwen3 dense (small members) | not cached | rope + QK-norm validated (4B/8B) | needs a download |
| Qwen3.5 dense hybrid (Gated DeltaNet) | MiMo-9B not cached | validated on a **tiny fixture only**; generation recomputes full context; GPU path not wired; 8 GB fit unmeasured; explain surface not stated | analysis-ineligible now; training-eligible only if a small member fits |

**Bake-off:** each gate-passing candidate is trained at 1k sentences (one seed) and scored on the dev split of R1/W.
Best wins; a tie within the §7 margin goes to the analysis-eligible model, then the smaller one. Tokens per Talema
word under each tokenizer is reported as a covariate (measured, not predicted).

## 9. Analysis protocol (H5)

After the T2 model at 4k: merge the LoRA, convert to a fieldrun bundle, and require the fieldrun parity gate on the
merged weights. Run rosetta `py/probe_families.py` on templated Talema stimuli with a foil and a causal perturbation.
Compare the head sets to those found on English stimuli in the unmodified base. For Gemma-2-2B additionally diff the
Gemma Scope features. The bracket-matching detector is listed as unbuilt in rosetta; if it is not built, H5 is scored
on copy and succession only, and that limit is stated in the result.

## 10. Preflight (no scoring)

- **P1** a separate `research/.venv` with `peft`, `accelerate`, `datasets`; do not modify the tutor's `.venv`.
- **P2** measure the LoRA memory fit for each candidate (gate b); note whether `bitsandbytes` works on this GPU
  (Blackwell, cu130) before relying on 4-bit.
- **P3** tokens per Talema word for each tokenizer.
- **P4** fieldrun parity on each candidate's base (gates c, d).
- **P5** freeze the benchmark: author, compile, filter, read, hash, commit.

## 11. Order of work

A. P1–P5, then rungs 0 and 1 on the benchmark (no training, modest API spend).
B. Data pipeline: teacher generation, validation, round-trip filter, nested splits.
C. Bake-off, then T0–T3 and T2-raw.
D. H5 analysis.

A result from A alone (H1) is already worth reporting.

## 12. Limits — what a pass would **not** show

- It would not show "understanding". R and W measure exact behaviour on items of the kinds listed.
- Benchmark items and training trees are written by the same kind of frontier model, so they share its habits; the
  student inherits the teacher's stiffness. The exact tools guard validity, not naturalness.
- Base models differ in more than language coverage (size, data, tokenizer); the bake-off cannot separate those causes.
- One language, one lexicon, one machine. Nothing here says the result generalises to natural low-resource languages.
- Serving form (does a student replace the tutor, or sit behind the sgiandubh path?) is **not** decided here.

## 13. Handoff notes for whoever runs this

- Work in `talema/research/`. The tutor is `avatar/dialogue.py`; the harness and judge are
  `avatar/experiments/conversation_ab.py` (`run`, `judge`, `show`, `compare`). Use `--base-ref aa0b0ca` for
  no-play arms; `main` is no longer a valid baseline.
- Use the `talema/.venv` Python for lm-sae's `author.py` (system `python3` lacks torch).
- Paced API calls: run in the background and poll; one blocking call at ~30 s is fine, a whole run is not.
- lm-sae holds the source of truth for the corpus (`conlang/`); export with `scripts/conlang/export.py --out ../talema`.
  The corpus is squash-merged (talema #12–#14, lm-sae #232).
- Read `rosetta/AGENTS.md`, `rosetta/CROSS_ARCH.md` and `fieldrun/AGENTS.md` before H5.

## Deviations

*(none yet)*
