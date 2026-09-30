# PREREG T1 — the Talema transfer ladder: what has to be learned in weights?

**Status:** registered 2026-09-29 (commit `881ce08`), amended twice the same day (Amendment 1 `0b9156b`; Amendment 2 in
this PR, see the end). **Before the benchmark exists and before any student model is trained or any rung is scored on
it.** Every claim is tagged `proved` / `empirical` / `open` (the workspace rule). Nothing here is `proved`; all
hypotheses are `open`. Amendments are dated, list what they change, and are never applied retroactively.

## 1. Question

Talema is a constructed language with an exact compiler, an exact parser and an exact validity check. A tutor for it
today is a frontier model with a ~100k-token book in every call. How much of the language has to live in **weights**,
how much can live in **retrieval**, and how much is already handled by **exact symbolic tools**? And can a small model
that already knows English, Spanish and German (the three languages Talema's roots are built from) acquire it with far
less data than one that starts from scratch?

## 2. What is already known (so it is not re-argued) — `empirical`, from `avatar/experiments/results/`

- The tutor writes valid Talema (2 of 135 turns in the last run failed validation twice and nothing was spoken; the run
  made 150 API calls, the extra 15 being repair retries). Reading learner Talema was the largest failure **seen in
  transcripts** of the Talema-input runs (`ab2*.json`); **no dedicated reading measure existed**, which is one reason R1
  and R2 below exist. Treat "she reads badly, and the play helps reading more than answering" as an observation, not a
  measured effect.
- A loosened prompt changes how she sounds: judge naturalness +1.26 [+0.63, +1.87] with English input (as printed by
  `conversation_ab.py show`, bootstrap seed 7; an independent recomputation gave [+0.65, +1.89]), with fewer forced
  questions and more small words (`ab4_english*.json`). Adding the play did not measurably help what she says. Pooled
  play-by-prompt interaction on naturalness −0.57 [−1.09, −0.02], n=44 (`research/scripts/pooled_interaction.py`,
  seed 5, 5,000 resamples); each run alone includes 0.
- **Absolute judge scores drift between runs**: fit and naturalness fell in every cell between `ab3` and `ab4`,
  including cells the change could not touch. Raw scores are not comparable across runs; §5 builds in an anchor.
- The last run's token totals (14.0M input, 13.9M cached) cover the 135 recorded turns, not failed or retried
  responses. Pacing is ~30 s per call at the 200k-TPM limit.
- The existing three scripted conversations were used while the tutor was being developed. They are **development
  material only** from here on (§5).

## 3. Constraints (the "constrained circumstances")

| resource | what we have |
|---|---|
| GPU | RTX 5050 Laptop, 8 GB. torch 2.14+cu130 sees it. `peft`, `accelerate`, `datasets`, `trl`, `bitsandbytes` are **not installed** (P1) |
| CPU / RAM | 8 cores / 16 threads (Ryzen 7 260), 14 GB. fieldrun runs int8 models on CPU |
| Data | 2,525 sentences (2,109 with English), 6,113 lexicon entries (`data/`) |
| Oracles | compiler `lm-sae/scripts/conlang/author.py` (**takes trees, not English**); parser `grammar/parser.mjs` + `parse.dl`; `avatar/dialogue.py` `validate_speech` |
| API | one OpenAI key, ~200k tokens/min, ~30 s between calls carrying the book |
| Complete on disk (HF cache; file lists checked) | Llama-3.2-1B, Qwen2.5-1.5B, Qwen2.5-3B-Instruct, gemma-2-2b, gemma-3-1b-pt, gemma-4-e4b-it |
| Present, contents **not** checked | Gemma Scope residual SAEs for gemma-2-2b (layers checked in P2), the Pythia ladder |
| **Incomplete** on disk | gemma-4-e2b-it (config only), Qwen2.5-3B base (missing a shard): need a download before use |
| fieldrun bundles | Llama-3.2-1B, gemma-2-2b, gemma-4-e4b (`fieldrun/bundles/`); Qwen2.5-0.5B/1.5B/3B/7B, Qwen3-30B-A3B, Pythia ladder (`~/.cache/fieldrun/bundles/`) |

## 4. Hypotheses

Statements only; the contrast, endpoint, comparator, size and decision rule for each are in the **§7 table**.

- **H1 — the book is mostly dead weight (`open`).** A retrieved slice of at most 5k tokens per turn matches the full book.
- **H2 — weights can replace the book (`open`).** A LoRA-tuned pretrained small model with no book matches rung 0.
- **H3 — lexical transfer (`open`).** Initialising each root from its en/de/es source words beats plain initialisation.
- **H4 — warm start (`open`).** A pretrained en/es/de model beats a from-scratch model at small data, and the gap closes
  as data grows.
- **H5 — structural reuse (`open`, **exploratory**).** After adaptation, the structural circuit families Talema needs
  (copy for names, succession for numerals; bracket-matching for arity endings only if that detector is built) are
  present on Talema stimuli (**H5a**, behavioural), and they run through the same heads as in the base model on the
  corresponding English stimuli (**H5b**, reuse). H5b cannot be tested with the behavioural probe alone (§9).
- **H6 — the endings need not be learned (`open`).** A student that emits concept trees (the server derives the
  endings) at 1k sentences matches one that emits raw Talema text at 4k.
- **H7 — a Datalog dialogue runtime can hold a Talema-input conversation (`open`; Amendment 1, revised by Amendment 2).**
  A runtime with no neural model at serve time (exact parser → dialogue-act rules → reply-frame planner → exact
  compiler, packaged the way sgiandubh serves a rosetta package) stays within 0.5 of rung 0 on both judge scales on
  the C test conversations, and abstains on at most 30% of scheduled turns (a margin chosen now, not derived). T4 has
  no English input path, so H7 is about Talema-input conversations only; an English frontend for T4 would have to be
  frozen and registered first.

## 5. Benchmark — built and frozen first

**Two disjoint sets.** A **development set** (used freely for prompt/slice/base-model choices and debugging) and a
**test set** (used once, at the end, for every system in the same scoring event). Test answers live in a file no
development script loads. **Rung 0 and rung 1 are scored on the dev set during development and on the test set only in
the final scoring event**, so no baseline result on the test set is seen before any system is frozen.

**Authoring.** A frontier model writes **English–tree pairs** (the concept-tree notation `author.py` accepts, with the
English gloss the pair means), using only lexicon concepts. `author.py` then compiles and validates each tree.
A compiler pass shows the tree is well-formed, not that it means what the English says, so **every pair is checked for
meaning by an independent reader**: a second model of a different family reads all pairs (as the Talema text plus a
word-by-word gloss, without seeing the intended English) and flags any whose meaning differs; the repository owner reads
a stratified 10% sample. Flagged or disputed pairs are dropped. Items are authored **blind to every system**.

**Families.** Each item has a family key (head root, multiset of content roots). Dev and test families are disjoint. A
*novel* item is one whose family key appears nowhere in the corpus, the books, or any teacher trace, **and** whose tree
and Talema text are not in `data/sentences.jsonl`. Exact-match screening alone misses paraphrases and templates, hence
the family key. The books and corpus cannot be edited for rung 0, so the screening is on the items.

**Domain.** All R and W items lie inside `validate_speech`'s domain (native lowercase words and periods, at most 350
characters). The parser accepts more (hyphenated literals, up to 2,000 characters and 512 words); those inputs are
outside every task here, and an added stratum for them would be labelled and reported separately.

| task | provisional minimum items | scored how |
|---|---|---|
| **R1** reading, well-formed | 640 novel + 100 *exposed* (corpus sentences) | Talema → concept tree; exact tree match, plus per-node root accuracy |
| **R2** reading, learner errors | 300: 150 valid controls + 150 perturbed (50 each: structural error, unknown-root warning, grammatical meaning change) | error detected yes/no on all items, and the location on perturbed structural errors |
| **W** writing | 300 English intents | emit a tree; validity by `validate_speech`; **primary content score = canonical tree match** against the reference and its pre-declared equivalent references; root-set F1 is secondary |
| **C** conversation | **new** test conversations (≥3, unrelated to the dev ones) × 9 rounds × learner language {Talema, English} | the `conversation_ab.py` harness: blind judge (fit, natural), ends-on-question, small-word share, validity/repair rate |

- **Scoring rules.** Invalid, empty and missing outputs score **zero** on every task (on C: the lowest judge score on
  both scales, and counted as a failure). Compiler-assisted validity (a server that derives endings) is reported
  separately from raw-text validity.
- **R2 details.** Each perturbation's category is verified by the parser before freezing (swapping subtrees can remain
  grammatical; unknown roots produce parser warnings, not errors). The character-offset-to-token mapping and the
  accepted diagnostic locations are frozen. Valid controls prevent an always-"error" system from scoring well.
- **Exposure is reported per item and per system**: is the item's family in this system's training data, its
  retrieved slice, its book, its teacher traces? The *exposed* stratum is corpus sentences, which students **are**
  trained on and rung 0 has in its book; the seen-minus-novel gap on R1 measures memorisation. Exclusion from training
  applies to the novel items only.
- **C anchor.** Every judging batch re-judges the same 27 rung-0 replies; scores are reported as differences from the
  anchor in that batch, and only same-batch comparisons are made. C conclusions are **descriptive** until conversation-level
  precision is justified (§7).
- **Cost.** In-context arms take R and W 10 items per call (~135 calls, ~70 min of pacing); students are scored one item per
  call, and a 40-item subset is run both ways. Cross-format comparisons that cannot use identical batching are
  exploratory.

## 6. Rungs

Training data are only exact-labelled pairs: (Talema, tree, English), from the corpus plus new trees written by the
current tutor **and accepted only if they pass validation and the round trip**, nested at 250 / 1k / 4k / 16k
sentences, three seeds. Novel benchmark items (dev and test) are excluded by family key.

| rung | setup | varied |
|---|---|---|
| 0 | frontier model, full book in context | baseline, re-scored on R/W/C |
| 1 | frontier model, retrieved slice: lexicon entries for the roots the exact parser finds in the learner message and last k turns, plus the grammar chapter | slice 2k / 5k / 20k tokens |
| T0 | small model from scratch, plain-initialised roots | data size |
| T1 | T0 with roots initialised from their en/de/es source words | data size |
| T2 | LoRA on a pretrained en/es/de model, no book | data size, base model |
| T3 | T2 plus a Talema retrieval store and exact-grammar-constrained decoding | data size |
| T2-raw | T2 emitting raw Talema text instead of trees | 1k, 4k only (H6) |
| T4 | Datalog dialogue runtime, no neural model at serve time (H7) | act inventory size |
| T1-SAE | T1 with roots initialised from P6 shared-feature signatures; **optional, reported separately** from T1 | only if P6's admission rule is met |

**Frozen before any training.** For each trained rung, in `research/configs/` with a hash in the freeze commit:
architecture, tokenizer, the root-initialisation mapping, objective, optimizer and schedule, epochs, decoding, stopping
rule and the seed list. **Retrieval and T4 behaviour** for English W intents and malformed R2 inputs is frozen without
access to any reference tree.

**T4 in one paragraph.** Reading is the exact parser; the rules infer a dialogue act from the parsed tree and the
conversation state; a planner picks a reply frame (react, ask a follow-up, offer a topic, correct, and the like) and
fills its slots from the learner's concepts; the exact compiler writes Talema. The act inventory and frames come from
three sources, each recorded per item: the books and the play (documents), tutor replies that passed validation and the
round trip (teacher), and, later, learner sessions (feedback). It abstains when the parse fails or no act matches. The
inventory is frozen **independently of the test conversations**. R1, R2 and W are not T4 tasks (the parser is exact by
construction; there is no English frontend); T4's compiler-derived validity is reported, not tested.

## 7. Decision rules

**Estimation.** Resampling unit: the item **family** (paired across all systems and seeds); a seed-by-item observation
is never treated as independent. Percentile bootstrap, 10,000 resamples, a seed fixed in the freeze commit, 95% intervals
(Holm-adjusted as below). Seed-specific results are reported alongside the pooled ones.

**Endpoints.** Primary: R1 tree match on **novel** items, and W canonical tree match. Secondary: R2, W root-set F1,
validity, the exposed stratum. C is descriptive.

**Definitions.** *Non-inferior*: the lower bound of (candidate − comparator) is above −5 points on both primary
endpoints **and** above −2 points on W validity. *Inferior*: the **upper** bound is below the margin. Otherwise the
result is *inconclusive* (failure to establish non-inferiority is not evidence of inferiority). *Superior*: the lower
bound is above 0.

**Multiplicity.** The confirmatory family is H1, H2, H3, H4, H6 (each with its one primary contrast below), tested with
Holm at 0.05. H5 and H7 are exploratory/descriptive; secondary endpoints and slice/size curves are descriptive. Choices
among searched alternatives (base model, slice size, seeds) are made on the **dev set** by the rules in §8 and §7 and
never by picking a successful seed.

| H | contrast (candidate − comparator) | data size / arm | endpoints | supported if | not supported if |
|---|---|---|---|---|---|
| H1 | dev-selected slice (2k or 5k; the best on dev R1 novel + W by the sum of the two, ties to the smaller) − rung 0 | test, rung 1 vs 0 | R1 novel, W tree match, W validity | non-inferior on all three | inferior on either primary endpoint; the 20k slice is exploratory and cannot support H1 |
| H2 | T2 (bake-off base) − rung 0 | 4k and 16k, no book | as H1 | non-inferior on all three at 16k | inferior at 16k |
| H3 | T1 − T0 | 1k (primary); 250/4k/16k descriptive | R1 novel | superior | upper bound < 0 |
| H4 | T2 − T1 | 250 | R1 novel | superior **and** point estimate ≥ +10 | upper bound < +10 |
| H6 | T2 (tree) at 1k − T2-raw at 4k | as stated | W tree match | non-inferior | inferior |
| H7 | T4 − rung 0, same-batch anchor | test conversations, Talema input | judge fit and natural (0.5 margin, descriptive); abstention rate | both within 0.5 and abstention ≤ 30% | either fails |

**Power comes first.** The item counts in §5 are *provisional minimums*. Before the freeze, a simulation over plausible
paired discordance (0.10–0.30), W variance, family clustering and seed variation, with Holm at five contrasts and 80%
power for the −5-point margin, fixes the final counts. (For scale: at 20% paired discordance, n=300 gives about 49%
power to declare non-inferiority when the systems are truly equal; about 640 items reach 80% without multiplicity.) If
the required R1-novel count exceeds ~1,000, the margin is widened **before any system is scored** and the change is
logged as an amendment.

**C.** At tens of turns per system its intervals are about ±0.5 on the 1–5 scale. C results are descriptive; the H7
"within 0.5" is a screening check, not a hypothesis test, and it needs **both** fit and naturalness (naturalness alone
rewards fluent replies that ignore the learner). Every scheduled turn is scored (failures and abstentions per §5).

**Reporting.** Negative and inconclusive results are reported the same as positive ones.

## 8. Base models for T2 / T3

Candidates are not chosen in advance. Each must pass gates, then a bake-off on the **dev set** picks the base.

**Gates, recorded per candidate in preflight:** (a) officially covers English, German and Spanish; (b) a LoRA at
sequence 1024, batch 1, gradient checkpointing fits in 8 GB — *measured*, with peak host memory and throughput; (c)
fieldrun's **full-checkpoint** f32 top-1 parity against torch ≥ 59/60; (d) fieldrun's explain/probe/ablation surface
exists for that arch. Failing (c) or (d) leaves a model **trainable and scorable on R/W/C but analysis-ineligible for
H5**; that is flagged, not hidden.

| candidate | complete on disk | fieldrun status (from its own docs) | note |
|---|---|---|---|
| Llama-3.2-1B | yes; bundle built | rope path validated on Qwen2.5 (0/32 vs torch); rosetta toolkit 14/15 families on this model | best-characterised for H5 |
| Qwen2.5-1.5B | yes; bundle built | same rope path; toolkit measured on the **coder** variant (12/15) | |
| Gemma-3-1B | yes (`unsloth` pt) | gemma3 validated on a **tiny random-init fixture** only; no full-checkpoint parity yet (gate c pending) | large vocabulary; check tokens per Talema word |
| Gemma-2-2B | yes; bundle built | gemma-2-2b 0/18 vs torch (full checkpoint) | **Gemma Scope SAEs on disk**; 2.6B is tight on 8 GB (gate b) |
| Gemma-4-E4B | yes | gemma4 on a tiny fixture only | may not fit gate (b) |
| Gemma-4-E2B | **no** (config only) | as gemma4 | download needed |
| Qwen3 dense (small members) | not cached | rope + QK-norm on a tiny fixture | download needed |
| Qwen3.5 dense hybrid (Gated DeltaNet) | not cached | tiny fixture only; generation recomputes full context; GPU path not wired; 8 GB fit unmeasured | analysis-ineligible now |

**Bake-off.** Each gate-passing candidate is trained at 1k sentences (one seed) and scored on the **dev** split of R1 novel
and W. The base is the one with the highest sum of the two; a tie within the §7 margin goes to the analysis-eligible
model, then the smaller one. Tokens per Talema word under each tokenizer is reported as a covariate.

## 9. Analysis protocol (H5, exploratory)

`py/probe_families.py` in rosetta **changes input operands** (for example swapping the repeated name in an IOI prompt) and
reads the behavioural effect. It does not localise heads or intervene on them, so it alone can support only **H5a**
(the family is present, at rosetta's own thresholds of detect ≥ 80% and causal ≥ 80%). **H5b** (same heads) needs head
localisation and activation interventions, for which fieldrun's explain, `predict_ablated` and head-sweep surface
exists for the rope archs and is checked per candidate in P4. Before H5b is run, freeze: the head-selection procedure,
the overlap statistic, the head-count- and layer-preserving permutation null, and the family-wise correction. Until
they are frozen H5b is not run and no reuse claim is made. Pipeline: merge the LoRA, convert to a fieldrun bundle, require
the parity gate on the merged weights, then measure the base and the adapted model on **both** English and Talema
stimuli. The bracket-matching detector is unbuilt; without it H5 covers copy and succession only, and that limit is stated.

## 10. Preflight (no scoring)

- **P1** a separate `research/.venv` with `peft`, `accelerate`, `datasets`; do not modify the tutor's `.venv`.
- **P2** per candidate, a **complete optimizer step**, checkpoint reload, representative generation, SAE extraction
  (where relevant) and merged-weight conversion, with peak GPU and host memory and throughput; note whether
  `bitsandbytes` works on this GPU (Blackwell, cu130); check which Gemma Scope layers are on disk. Then a **compute
  budget** for every seed, size, generation retry and bake-off run.
- **P3** tokens per Talema word for each tokenizer.
- **P4** fieldrun full-checkpoint parity and the explain/ablation surface on each candidate (gates c, d).
- **P5** freeze the benchmark: author, compile, independent meaning review, family partition, power simulation, hash,
  commit. Dev and test are frozen in the same commit; test answers are stored apart.
- **P6** shared-feature signatures (Amendment 1, revised by Amendment 2), on **development material only**, completed
  before the T1-SAE treatment is frozen. For each lexicon concept with en, es and de source words, run gemma-2-2b on
  fixed carrier sentences, read the residual at a Gemma Scope layer, and take each word's SAE features. **Freeze first:**
  k, the handling of positive activations, token pooling, the carriers, the layers tried, and the choice of word sense.
  **Test:** overlap for the concept's true en/es/de words against **matched within-language permutations** (a word
  swapped for another word of the same language and frequency band), with a **global test that accounts for the
  search over layers**. Cognates, tokenisation and carrier features can inflate two-language overlap, so an association
  does not show usefulness. **Admission rule for T1-SAE:** signatures are used as an initialisation only if, on held-out
  **dev** material, they beat both plain gloss initialisation and shuffled signatures. The old "fraction above the
  95th percentile, ≤10% means unusable" rule is **withdrawn**: a null here does not establish that shared features are
  unusable, and 10% is not a calibrated threshold. The fraction is reported as descriptive `empirical`.

## 11. Order of work

A. P1–P6 and the dev-set benchmark; rungs 0 and 1 on **dev** (slice selection for H1).
B. Data pipeline: teacher generation, validation, round-trip filter, nested splits; T4's act inventory.
C. Bake-off on dev, then T0–T3, T2-raw and T4 built and frozen. P6 completes before T1-SAE is frozen.
D. **One final scoring event on the test set for every system**, including rungs 0 and 1.
E. H5 analysis, exploratory.

A result from A alone (H1 on dev) is worth reporting as development evidence, not as a confirmatory test.

## 12. Limits — what a pass would **not** show

- It would not show "understanding". R and W measure exact behaviour on items of the kinds listed.
- Benchmark items and training trees are written by the same kind of frontier model, so they share its habits; the
  student inherits the teacher's stiffness. The exact tools guard validity, and the independent meaning review guards
  semantics only as far as its reader does. The parser both labels training data and scores the output, so agreement
  with it proves consistency, not correctness.
- Base models differ in more than language coverage (size, data, tokenizer); the bake-off cannot separate the causes.
- One language, one lexicon, one machine. Nothing here says the result generalises to natural low-resource languages.
- Serving form (does a student replace the tutor, or sit behind the sgiandubh path?) is **not** decided here.
- T4's naturalness ceiling is set by the acts and frames its authors give it. rosetta has so far extracted retrieval and
  narrow circuits from small local models — n-gram, induction and succession (`IDIOM_LEARNER.md`, measured on
  llama-3.2-1b) — and not dialogue policy. Its reasoning tier came up empty for the riscv distillation
  (`REASONING.md`). The J-Lens hook was a clean null on `llama32_1b` and marginal/inconclusive on `qwen25coder15b`
  (`JLENS_BRIDGE.md`), tagged `open`, not a hard null. So T4's policy is expected to come from documents, teacher traces
  and feedback rather than model extraction; that expectation is `open`.

## 13. Handoff notes for whoever runs this

- Work in `talema/research/`. The tutor is `avatar/dialogue.py`; the harness and judge are
  `avatar/experiments/conversation_ab.py` (`run`, `judge`, `show`, `compare`). Use `--base-ref aa0b0ca` for no-play
  arms; `main` is no longer a valid baseline. The three existing conversations are **dev only**.
- Use the `talema/.venv` Python for lm-sae's `author.py` (system `python3` lacks torch).
- Paced API calls: run in the background and poll.
- lm-sae holds the source of truth for the corpus (`conlang/`); export with `scripts/conlang/export.py --out ../talema`.
  The corpus is squash-merged (talema #12–#14, lm-sae #232).
- Read `rosetta/AGENTS.md`, `rosetta/CROSS_ARCH.md` and `fieldrun/AGENTS.md` before H5.
- The raw review that led to Amendment 2 is `research/reviews/2026-09-29_astra_review_of_prereg.md`.

## Amendments and deviations

Each entry is dated, states what it changes, and states whether any result could have informed it.

- **Amendment 1 — 2026-09-29, before the benchmark exists and before any scoring.** Added rung T4, hypothesis H7,
  preflight P6, the T4 paragraph in §6, and a limit in §12. Motivation: a proposal to use a Datalog chat runtime (the
  sgiandubh form) with shared en/es/de features. No benchmark result existed, so none informed it.
- **Amendment 2 — 2026-09-29, before the benchmark exists and before any scoring.** Revises the document after an
  independent read-only review by codex (`gpt-6-astra`, reasoning effort raised to high; raw text in
  `research/reviews/`). A first review by a Fable agent was attempted and did not run (monthly spend limit, HTTP 429), so
  it contributed nothing. Evidence inspected: the review text, and the files it cites (each factual claim was checked
  against the file). **No benchmark or student result existed or was inspected.**
  *Changes:* (1) H1 given a non-inferiority/inferiority/inconclusive rule and a dev-selected slice; the 20k arm made
  exploratory. (2) Item counts made provisional minimums, raised (R1 novel 640, R2 300, W 300), with a power simulation
  required before the freeze; the 49%-power illustration was recomputed analytically (paired binary outcomes, two-sided 95% bound) and matches. (3) Hypothesis-to-contrast table,
  multiplicity (Holm over five confirmatory contrasts), family-level resampling, a dev ranking for choices. (4) A dev/test
  split; baselines scored on test only in the final event; family-key screening; the "exposed" stratum redefined;
  C test conversations to be newly authored. (5) `author.py` takes trees, not English: authoring is English–tree pairs with
  independent meaning review; W primary score is canonical tree match, root-set F1 secondary; zero for invalid/missing.
  (6) R2 gets valid controls, labelled categories and frozen location rules; the parser's and validator's domains are
  reconciled. (7) H7 restricted to Talema-input conversations, both judge scales, failures scored; W removed from H7.
  (8) H5 split into H5a (behavioural) and H5b (reuse, exploratory), with the head-level tooling and null frozen first.
  (9) P6's 5%/10% rule withdrawn; replaced by frozen parameters, matched permutations, a layer-search-aware test and a
  dev-utility admission rule; T1-SAE added as a separate optional treatment. (10) Configurations to be frozen; P2 expanded
  to a full optimizer step and a compute budget. (11) Amendment 1's "H1–H6 unchanged" no longer holds and is superseded by this list.
  *Facts corrected:* the run was 135 turns and 150 API calls; the CPU is 8 cores / 16 threads; gemma-4-e2b-it and
  Qwen2.5-3B base are incomplete on disk; Gemma-3/4 parity is on tiny fixtures only, so gate (c) is pending for them; the
  rosetta limit in §12 now cites succession, the Llama-null and Qwen-inconclusive J-Lens results and `REASONING.md`;
  the pooled-interaction script is now in the repo.
  *Not adopted:* the review's claim that only a Qwen2.5-Coder bundle exists. `~/.cache/fieldrun/bundles/Qwen2.5-1.5B`
  holds a Qwen2.5-1.5B bundle.
- **Amendment 3 — 2026-09-29, at the P5 candidate freeze, before any system was scored.** Records the operational choices P5 made
  where this document left them open; the details, counts and hashes are in `research/benchmark/FREEZE.md`. (1) Final counts, fixed
  by the power simulation: 930 novel test items and 300 novel dev items, plus 100 and 50 exposed corpus items, and 300 and 101 R2
  items; W uses the same items as R1 in separate calls (so W has 1,030 test items, not 300). (2) The blind reader was shown each
  item's indented tree with word glosses, not a linear gloss, because a linear gloss hides attachment. (3) The reader's first pass
  rendered a top-level `whether` as a clause and so judged 115 of 119 yes-no items different; that was a rubric omission, fixed by
  one added sentence and one added example, and only those 119 items were re-read (both result files are kept). (4) R2 gold is the
  exact parser's verdict; locations are token indexes. (5) Survivors of the review are items a small reader reads correctly, which
  biases the benchmark towards easier reading, and the *number or quantity* frame is under-represented; both are stated as limits.
  (6) "No development script loads the test answers" is read as: training, prompting and selection scripts; the benchmark's own
  build and verification tools do read them. The owner's 10% sample read is still pending, so the final freeze follows it. No
  benchmark result of any kind existed when these choices were made.
