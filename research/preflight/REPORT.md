# P1–P4 preflight — empirical, no benchmark scoring

Run from `/home/allans/code/talema`. Results describe this session, not an intrinsic model limit. GPU access was blocked **inside the codex sandbox**; the P2 measurements were repeated outside it by the supervising session (`*-gpu.json`), and the corrected P2 table and summary table below use those. No model was trained, no benchmark was built or scored, and no paid API was used.

## Reproduction

The independent environment is `research/.venv`; exact installed pins are in `research/requirements.txt`. Initial installation commands (package downloads only):

```bash
python3 -m venv research/.venv
export TMPDIR="$PWD/research/preflight/tmp"
research/.venv/bin/python -m pip download --no-cache-dir --dest research/preflight/wheels --index-url https://download.pytorch.org/whl/cu130 'torch==2.14.0+cu130'
research/.venv/bin/python -m pip install --no-cache-dir --no-index --find-links research/preflight/wheels 'torch==2.14.0+cu130'
research/.venv/bin/python -m pip install --no-cache-dir 'transformers==5.17.0' peft accelerate datasets bitsandbytes
research/.venv/bin/python -m pip freeze > research/requirements.txt
```

Downloaded torch/dependency wheels were measured, inventoried in `wheel_sizes.json`, then deleted to keep disk use low. For a pinned reinstall use `pip install --extra-index-url https://download.pytorch.org/whl/cu130 -r research/requirements.txt`. Do not install into the tutor environment.

```bash
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
PY=research/.venv/bin/python
$PY research/preflight/inventory.py
$PY research/preflight/p1_check.py
$PY research/preflight/p4_audit.py
for model in meta-llama/Llama-3.2-1B Qwen/Qwen2.5-1.5B unsloth/gemma-3-1b-pt google/gemma-2-2b google/gemma-4-e4b-it; do
  $PY research/preflight/p3_tokenizers.py --model "$model"
  $PY research/preflight/p2_lora.py --model "$model" --seq 1024
  # This session also attempted 512; ordinarily this is the OOM fallback.
  $PY research/preflight/p2_lora.py --model "$model" --seq 512
  $PY research/preflight/p4_parity.py --model "$model"
done
$PY research/preflight/p2_lora.py --model unsloth/gemma-3-1b-pt --tag verification
$PY research/preflight/make_report.py
```

Redirect each invocation’s stdout and stderr to a separate file in `logs/`, as in the delivered `P2-<model>-1024.log`, `P3-<model>.log`, and `P4-<model>-parity.log`. Use fresh P2 tags on successful reruns; adapter directories are never overwritten. The P2 training/lifecycle path was validated by the supervisor's rerun outside the sandbox (see P2). Run it from a normal shell (the codex sandbox has no GPU) with `C_INCLUDE_PATH` pointing at Python 3.12 headers, as described under P2; use tag `gpu` for reruns (adapter directories are never overwritten). `--four-bit` was tried for Gemma-2 and E4B and does not fit either. All model loads use local snapshot paths and `local_files_only=True`.

## P1 — environment and CUDA

| Component | Measured result |
| --- | --- |
| torch | 2.14.0+cu130 |
| transformers | 5.17.0 |
| peft | 0.21.1 |
| accelerate | 1.15.0 |
| datasets | 5.0.1 |
| bitsandbytes | 0.50.2 |
| Python | Python 3.12.3 |
| Dependency consistency | pip check: no broken requirements |
| CUDA build / available | 13.0 / False **inside the codex sandbox**; True from a normal shell (RTX 5050, 7.5 GiB usable) |
| bitsandbytes import | PASS |
| CUDA NF4 128→64 forward/backward | BLOCKED: RuntimeError('No CUDA GPUs are available') |
| 4-bit forward on sm_120, supervisor rerun | The 4-bit gemma-2-2b forward pass through all layers ran on this GPU; the run then hit OOM in the loss (`logits.float()`), so bitsandbytes 4-bit works here (`P2-gemma-2-2b-1024-4bit-gpu.json`) |
| sm_120 execution compatibility | NOT MEASURED — GPU inaccessible |

| Wheel | Measured compressed bytes |
| --- | --- |
| cuda_bindings-13.3.1-cp312-cp312-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl | 6657965 |
| cuda_pathfinder-1.6.0-py3-none-any.whl | 54591 |
| cuda_toolkit-13.0.3.0-py2.py3-none-any.whl | 2512 |
| filelock-3.32.3-py3-none-any.whl | 98901 |
| fsspec-2026.7.0-py3-none-any.whl | 206583 |
| jinja2-3.1.6-py3-none-any.whl | 134899 |
| markupsafe-3.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl | 22947 |
| mpmath-1.3.0-py3-none-any.whl | 536198 |
| networkx-3.6.1-py3-none-any.whl | 2068504 |
| nvidia_cublas-13.1.1.3-py3-none-manylinux_2_27_x86_64.whl | 423138758 |
| nvidia_cuda_cupti-13.0.85-py3-none-manylinux_2_25_x86_64.whl | 10715597 |
| nvidia_cuda_nvrtc-13.0.88-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl | 90215200 |
| nvidia_cuda_runtime-13.0.96-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl | 2243632 |
| nvidia_cudnn_cu13-9.24.0.43-py3-none-manylinux_2_27_x86_64.whl | 553099438 |
| nvidia_cufft-12.0.0.61-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl | 214085489 |
| nvidia_cufile-1.15.1.6-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl | 1223672 |
| nvidia_curand-10.4.0.35-py3-none-manylinux_2_27_x86_64.whl | 59544258 |
| nvidia_cusolver-12.0.4.66-py3-none-manylinux_2_27_x86_64.whl | 200941980 |
| nvidia_cusparse-12.6.3.3-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl | 145942937 |
| nvidia_cusparselt_cu13-0.8.1-py3-none-manylinux2014_x86_64.whl | 170148586 |
| nvidia_nccl_cu13-2.30.7-py3-none-manylinux_2_18_x86_64.whl | 215965170 |
| nvidia_nvjitlink-13.3.33-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl | 40742423 |
| nvidia_nvshmem_cu13-3.4.5-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl | 60412546 |
| nvidia_nvtx-13.0.85-py3-none-manylinux1_x86_64.manylinux_2_5_x86_64.whl | 148047 |
| setuptools-78.1.0-py3-none-any.whl | 1256108 |
| sympy-1.14.0-py3-none-any.whl | 6299353 |
| torch-2.14.0+cu130-cp312-cp312-manylinux_2_28_x86_64.whl | 554622961 |
| triton-3.8.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl | 246842756 |
| typing_extensions-4.16.0-py3-none-any.whl | 45571 |
| TOTAL torch + resolved dependency wheels | 3007417582 |

Wheel sizes above are filesystem sizes before deletion, not installed sizes. Other package download sizes are in `logs/P1-packages-install.log`. Raw setup logs: `P1-torch-download.log`, `P1-torch-install.log`, `P1-packages-install.log`, `P1-pip-check.log`, `P1-cuda-bnb.log`. The tutor environment independently reported torch 2.14.0+cu130 / CUDA 13.0 / unavailable; `nvidia-smi` failed and `/dev/nvidia*` was absent (inventory log). No driver changes were attempted.

## P2 — LoRA memory and lifecycle

Configured test: r=16, alpha=32, PEFT `all-linear` (all supported linear layers except the output head), bf16, batch 1, gradient checkpointing, AdamW lr=1e-4. The first eight real corpus examples are packed/repeated to exactly 1024 or 512 tokens, with prompt labels masked. One full warmup optimizer step precedes three timed full optimizer steps; requested statistic is their median. This is a memory exercise only. Target rendering is described under P3.

| Candidate | Cache weights bytes | 1024 | 512 | GPU allocated / reserved GB | Host RSS GB | Median s/step | Adapter reload / 64-token generation / merged size |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Llama-3.2-1B | 2471645608 | FIT | not run (1024 fit) | 4.33 / 4.77 | 3.27 | 0.622 | PASS / 64 tokens / 2.49 GB |
| Qwen2.5-1.5B | 3087467144 | FIT | not run (1024 fit) | 5.34 / 5.92 | 3.69 | 0.893 | PASS / 64 tokens / 3.10 GB |
| gemma-3-1b-pt | 1999811208 | FIT | not run (1024 fit) | 5.51 / 6.68 | 3.19 | 0.721 | PASS / 64 tokens / 2.03 GB |
| gemma-2-2b | 10457400944 | NOT-FIT (OOM in the loss: fp32 logits, 1000 MiB) | NOT-FIT (500 MiB) | 6.53 / 6.67 at OOM | 10.43 | NOT MEASURED | not reached |
| gemma-4-e4b-it | 15992595884 | NOT-FIT (OOM loading a 5.25 GiB tensor) | NOT-FIT (OOM loading) | 6.79 / 6.79 at OOM | 3.12 | NOT MEASURED | not reached |

**Supervisor rerun (outside the sandbox).** The rows above are from `P2-*-gpu.json` with logs `logs/P2-*-gpu.log`, run with the same `p2_lora.py`. The codex-sandbox attempts (`P2-*-main.json`) all failed at `torch.cuda.init()` with `RuntimeError('No CUDA GPUs are available')`; they are kept as records and are **BLOCKED**, not NOT-FIT. Two environment fixes were needed and neither changes a measurement: torch 2.14 routes the RoPE outer product (`bmm_outer_product`) through a Triton kernel, and Triton compiles a driver stub that needs `Python.h`, which is not installed for the system Python 3.12.3. The matching headers were fetched with `apt download libpython3.12-dev` (extracted, not installed) into `research/.venv/py312-headers` and put on `C_INCLUDE_PATH` (`…/py312-headers`, `…/python3.12`, `…/x86_64-linux-gnu/python3.12`). Adapters were saved, reloaded, generated 64 tokens from, and merged into bf16 base weights for the three models that fit; merged weights were deleted after their size was recorded. **What NOT-FIT means here.** It is the *stock* Hugging Face loss and loader, unmodified: gemma-2-2b (256k vocabulary) fails at 1024 and at 512 in the fp32 upcast of the logits (`ForCausalLMLoss`), and gemma-4-e4b-it fails while materialising one 5.25 GiB tensor on the GPU at load. The same two also fail with 4-bit NF4 weights (`*-4bit-gpu.json`; gemma-2-2b again in the loss after a completed forward, gemma-4-e4b-it again at load, so 4-bit does not remove either bottleneck). Untested mitigations (chunked cross-entropy, keeping the embedding tables on CPU, not upcasting embeddings in `prepare_model_for_kbit_training`) may make them fit; that is **not measured** and the candidates are recorded as failing gate (b) as measured. The card has 7.53 GiB total and ~0.9 GiB is held by another process.

| Explicitly excluded candidate | Status | Observed cache problem |
| --- | --- | --- |
| google/gemma-4-e2b-it | SKIPPED-INCOMPLETE | google/gemma-4-e2b-it: incomplete cache; missing ['model.safetensors', 'tokenizer.json'] |
| Qwen/Qwen2.5-3B | SKIPPED-INCOMPLETE | Qwen/Qwen2.5-3B: incomplete cache; missing ['model-00001-of-00002.safetensors'] |

`inventory.json` records snapshot hashes, exact file sizes and the corpus hash. Gemma-3 has a single `model.safetensors` plus a stale index naming absent shards; the single-file checkpoint takes precedence. The initial conservative inventory incorrectly classified it as incomplete; corrected inventory and corrected P2 attempts are retained alongside the initial error logs.

## P3 — tokenization over every corpus row

All 2,525 rows and 14,780 Talema word occurrences are included. A word is a whitespace-delimited unit containing at least one alphabetic character; standalone `.` is excluded from the denominator but retained in sentence token counts. Special tokens are disabled. Each corpus row is one ‘sentence’ for these statistics.

Trees in `sentences.jsonl` are S-expressions. They are parsed into ordered nested arrays (leaves are strings) and rendered using `json.dumps(..., ensure_ascii=False, separators=(',',':'))`. The one empty tree (`core/06_medium/0109`) renders as `null`; it is included, not imputed or dropped. Example: `["book",["for",["reader","every",["of",["age","every"]]]]]`.

The main per-word measure below is each full sentence’s token count divided by its number of Talema words, then mean/median over rows. JSON uses the **same Talema-word denominator**, making output cost comparable to input cost. Thus punctuation and JSON syntax count toward cost.

| Tokenizer | Talema tokens/word mean / median | Talema tokens/sentence mean / median | JSON tokens/Talema word mean / median | JSON tokens/sentence mean / median |
| --- | --- | --- | --- | --- |
| Llama-3.2-1B | 2.125239 / 1.800000 | 10.453069 / 10.000000 | 3.535504 / 3.250000 | 19.099802 / 18.000000 |
| Qwen2.5-1.5B | 2.139519 / 1.800000 | 10.545743 / 10.000000 | 3.540890 / 3.250000 | 19.131089 / 18.000000 |
| gemma-3-1b-pt | 2.149193 / 1.666667 | 10.031683 / 10.000000 | 3.616280 / 3.222222 | 19.114851 / 18.000000 |
| gemma-2-2b | 2.085692 / 1.625000 | 9.725149 / 9.000000 | 3.278577 / 3.100000 | 18.622178 / 18.000000 |
| gemma-4-e4b-it | 2.149193 / 1.666667 | 10.031683 / 10.000000 | 3.616280 / 3.222222 | 19.114851 / 18.000000 |

Separately, each word is tokenized in isolation with no leading space. Single-token fractions count word occurrences, and the type-based fraction counts unique words. These context-free word statistics differ from sentence costs because tokenizers encode word boundaries and punctuation differently. Vocabulary size is reported both as `vocab_size` and `len(tokenizer)` (includes added tokens).

| Tokenizer | vocab_size / len | Isolated-word tokens mean / median | Single-token occurrences | Single-token types | Corpus tokens / words: Talema / JSON |
| --- | --- | --- | --- | --- | --- |
| Llama-3.2-1B | 128000 / 128256 | 1.614344 / 2.000000 | 46.474966% | 7.489760% | 1.785792 / 3.262991 |
| Qwen2.5-1.5B | 151643 / 151665 | 1.633424 / 2.000000 | 45.696888% | 6.904623% | 1.801624 / 3.268336 |
| gemma-3-1b-pt | 262144 / 262145 | 1.597835 / 1.000000 | 52.408660% | 13.575190% | 1.713802 / 3.265562 |
| gemma-2-2b | 256000 / 256000 | 1.461637 / 1.000000 | 64.377537% | 22.059684% | 1.661434 / 3.181394 |
| gemma-4-e4b-it | 262144 / 262144 | 1.597835 / 1.000000 | 52.408660% | 13.575190% | 1.713802 / 3.265562 |

Raw aggregate output is in `logs/P3-<model>.log`; exact per-row token/word counts are in `P3-<model>-rows.jsonl`. No dataset or model downloads occurred.

## P4 — fieldrun parity and probe surface

Read-only audit of `/home/allans/code/fieldrun`: `AGENTS.md`, `README.md`, `scripts/validate_all.sh`, every `scripts/*_ref.py`, the relevant Rust implementations, and both bundle directories. Exact reference source text and SHA-256 hashes are in `logs/P4-reference-sources.log`; per-model source lines and bundle metadata are in `logs/P4-<model>-audit.log`. The existing release binary was used; no fieldrun files were changed or built.

The README documents historical **architecture-level** full-checkpoint agreement for RoPE (Qwen 32/32) and Gemma-2 (18/18), through sibling numpy/torch references. Those are historical claims, not fresh measurements, and do not establish 59/60 for these candidates. No self-contained candidate-specific full-checkpoint reference script was found in fieldrun. `validate_all.sh` and the Gemma-3/4 references use tiny random fixtures. The new research-only harness reproduces the documented f32 comparison for Llama and Qwen on their actual cached weights.

| Candidate / arch | Existing bundle | Repo full-checkpoint check evidence | Fresh f32 parity | explain | predict_ablated | head-sweep |
| --- | --- | --- | --- | --- | --- | --- |
| Llama-3.2-1B / rope | YES | Documented historical arch check; no candidate script | 60/60 (94.90 s) | YES | YES | YES |
| Qwen2.5-1.5B / rope | YES | Documented historical arch check; no candidate script | 60/60 (84.73 s) | YES | YES | YES |
| gemma-3-1b-pt / gemma3 | NO | NO — tiny fixture only | PENDING: RuntimeError('Only tiny reference exists; no full-checkpoint check in repo') | YES | NO | NO |
| gemma-2-2b / gemma | YES | Documented historical arch check; no candidate script | PENDING: RuntimeError('15 GB new-disk cap: current=6352936960, f32 tensor bytes=10457367552; conversion not attempted') | YES | NO | NO |
| gemma-4-e4b-it / gemma4 | YES | NO — tiny fixture only | PENDING: RuntimeError('Only tiny reference exists; no full-checkpoint check in repo') | YES | NO | NO |

Parity protocol: full cached checkpoint in float32, torch eager attention, 8 CPU threads, identical 16-token sliding contexts at 60 positions from a fixed stream of existing Talema corpus text. Torch and Rust run sequentially to avoid two resident model copies. The comparison checks argmax agreement between implementations; fieldrun’s incidental next-token accuracy line is not used or reported as a benchmark score. A 900-second subprocess deadline applies. Qwen reuses the existing all-f32 bundle; Llama’s temporary f32 conversion is deleted afterwards.

Gemma-2’s existing bundle contains f16/int8 arrays and cannot establish **f32** parity. Its measured f32 tensor requirement exceeds the 15 GB new-disk allowance when added to the environment; conversion was not attempted. Gemma-3/4 remain PENDING because only tiny-model references exist. Gemma-4 does implement `predict_ablated_blocks` (and a head loop through `--causal-dump`), but does not override `predict_ablated`, so the named `--head-sweep` route fails its capability guard. Gemma-2/3 lack both causal-ablation overrides. `explain` alone does not satisfy the full requested probe surface. Probe availability is source inspection, not a run of H5 or a functional probe validation.

| Candidate | Existing bundle path(s) |
| --- | --- |
| Llama-3.2-1B | /home/allans/code/fieldrun/bundles/llama-3.2-1b.fieldrun.json |
| Qwen2.5-1.5B | /home/allans/.cache/fieldrun/bundles/Qwen2.5-1.5B/Qwen2.5-1.5B.fieldrun.json |
| gemma-3-1b-pt | None |
| gemma-2-2b | /home/allans/code/fieldrun/bundles/gemma-2-2b.fieldrun.json |
| gemma-4-e4b-it | /home/allans/code/fieldrun/bundles/gemma-4-e4b.fieldrun.json<br>/home/allans/.cache/fieldrun/bundles/gemma-4-e4b-it-int4/gemma-4-e4b-it-int4.fieldrun.json |

## Problems

- GPU device access was absent **inside the codex sandbox** despite CUDA-enabled torch, which blocked its P2 attempts; the supervisor reran P2 from a normal shell (see the P2 supervisor rerun). That rerun needed `Python.h` for Triton (see P2). A first pass of the rerun failed on the include path and was discarded and repeated; only the passing configuration is recorded.
- One corpus row has no tree. Initial tokenizer runs stopped on it; the explicit `null` convention fixed coverage. Initial errors remain in logs.
- Gemma-3’s stale shard index required correcting the cache checker to prefer its existing single weight file.
- Gemma-3 and Gemma-4 produce identical token counts on this corpus; this is a measured result, not an assumption about all possible text.
- Historical fieldrun architecture claims are not candidate-specific 60-position gates. Gemma-2’s f32 conversion exceeds the disk budget; Gemma-3/4 have only tiny-checkpoint references.

## Verification and disk use

**Reproduction check (supervisor).** Llama-3.2-1B (the smallest candidate that fit) was rerun in a fresh process at sequence 1024, tag `gpuverify`: peak GPU allocated **4,329,998,336 bytes** in both runs, median step **0.622 s** originally and **0.634 s** on the rerun (+1.9%, within the 10% target); loss trajectories agree to three decimals (0.900, 0.828, 0.726, 0.642 vs 0.900, 0.827, 0.726, 0.641). Codex's own attempted verification (Gemma-3-1B, sandbox) could not run for the GPU reason above. Independent checks of codex's other numbers: the tokens-per-word statistic for Llama-3.2-1B, Qwen2.5-1.5B and gemma-2-2b was recomputed from scratch and matches exactly (2.125239, 2.139519, 2.085692); the Llama and Qwen parity logs show 60/60 agreement with no mismatches.

Measured allocated disk at report generation: research total **6,347,563,008 bytes (6.347563 GB)**, of which research/.venv **6,345,695,232 bytes**. This conservatively includes pre-existing research documents. Maximum sampled during the parity disk watch: **11,299,905,536 bytes (11.299906 GB)**; this is a sampled observation, not an assertion of a continuously measured peak. Torch/dependency wheels totaling **3,007,417,582 bytes** were deleted before model conversion. Pip caching was disabled. Only this run’s wheel files and temporary Llama bundle were deleted. New disk stayed below the ~15 GB cap; no model/dataset download, tutor change, fieldrun change, or git write operation was performed.

## Candidate × preflight summary

| Candidate | Fits LoRA at 1024 | Peak GPU GB | s/step | Tokens per Talema word¹ | Bundle exists | Full-checkpoint parity | Probe surface² |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Llama-3.2-1B | FIT | 4.33 | 0.622 | 2.125239 | YES | 60/60 | YES (source) |
| Qwen2.5-1.5B | FIT | 5.34 | 0.893 | 2.139519 | YES | 60/60 | YES (source) |
| gemma-3-1b-pt | FIT | 5.51 | 0.721 | 2.149193 | NO | PENDING | PARTIAL: explain only³ |
| gemma-2-2b | NOT-FIT (stock path) | 6.53 at OOM | NOT MEASURED | 2.085692 | YES | PENDING | PARTIAL: explain only³ |
| gemma-4-e4b-it | NOT-FIT (stock path) | 6.79 at OOM | NOT MEASURED | 2.149193 | YES | PENDING | PARTIAL: explain only³ |

¹ Mean of sentence-level token/word ratios, including sentence punctuation. Isolated-word and corpus-weighted means are separately reported in P3. ² Requires explain + predict_ablated + head-sweep. ³ Gemma-4 additionally has block ablation/causal-dump; the requested named head-sweep is absent. No analysis eligibility is inferred from explain alone.

**Not completed:** Gemma-2 full-checkpoint parity (disk limit: the f32 conversion needs 10.5 GB, more than the 15 GB new-disk allowance with the environment present), Gemma-3/4 full-checkpoint parity (no existing full reference; Gemma-3 also has no bundle), any P2 measurement that fits gemma-2-2b or gemma-4-e4b-it (stock path does not fit; mitigations untested), and P5/P6, benchmarks, SAE work, training.
