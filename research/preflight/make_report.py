"""Run after measurements: python research/preflight/make_report.py. Builds REPORT.md from result JSON."""
from common import *
import subprocess
j=lambda name:json.loads((ROOT/name).read_text())
p1=j('P1-check.json'); inventory=j('inventory.json'); audit=j('P4-audit.json'); wheels=j('wheel_sizes.json')
p3={m:j('P3-'+slug(m)+'.json') for m in MODELS}
p4={m:j('P4-'+slug(m)+'-parity.json') for m in MODELS}
lines=[]
def emit(s=''): lines.append(s)
def table(headers,rows):
    emit('| '+' | '.join(headers)+' |');emit('| '+' | '.join(['---']*len(headers))+' |')
    for row in rows: emit('| '+' | '.join(map(str,row))+' |')
    emit()
def pair(x): return f"{x['mean']:.6f} / {x['median']:.6f}"
emit('# P1–P4 preflight — empirical, no benchmark scoring\n')
emit('Run from `/home/allans/code/talema`. Results describe this session, not an intrinsic model limit. GPU access is blocked. No model was trained, no benchmark was built or scored, and no paid API was used.\n')
emit('## Reproduction\n')
emit('The independent environment is `research/.venv`; exact installed pins are in `research/requirements.txt`. Initial installation commands (package downloads only):\n')
emit('''```bash
python3 -m venv research/.venv
export TMPDIR="$PWD/research/preflight/tmp"
research/.venv/bin/python -m pip download --no-cache-dir --dest research/preflight/wheels --index-url https://download.pytorch.org/whl/cu130 'torch==2.14.0+cu130'
research/.venv/bin/python -m pip install --no-cache-dir --no-index --find-links research/preflight/wheels 'torch==2.14.0+cu130'
research/.venv/bin/python -m pip install --no-cache-dir 'transformers==5.17.0' peft accelerate datasets bitsandbytes
research/.venv/bin/python -m pip freeze > research/requirements.txt
```
''')
emit('Downloaded torch/dependency wheels were measured, inventoried in `wheel_sizes.json`, then deleted to keep disk use low. For a pinned reinstall use `pip install --extra-index-url https://download.pytorch.org/whl/cu130 -r research/requirements.txt`. Do not install into the tutor environment.\n')
emit('''```bash
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
''')
emit('Redirect each invocation’s stdout and stderr to a separate file in `logs/`, as in the delivered `P2-<model>-1024.log`, `P3-<model>.log`, and `P4-<model>-parity.log`. Use fresh P2 tags on successful reruns; adapter directories are never overwritten. The supplied P2 training/lifecycle path is runnable but **not validated past CUDA initialization** here. Use `--four-bit` only for Gemma-2/E4B after `p1_check.py` actually passes on CUDA. All model loads use local snapshot paths and `local_files_only=True`.\n')
emit('## P1 — environment and CUDA\n')
table(['Component','Measured result'], [[k,v] for k,v in p1['packages'].items()]+[['Python',subprocess.check_output([str(RESEARCH/'.venv/bin/python'),'--version'],text=True).strip()],['Dependency consistency','pip check: no broken requirements'],['CUDA build / available',f"{p1['cuda_build']} / {p1['cuda_available']}"],['bitsandbytes import',p1['bnb_import']],['CUDA NF4 128→64 forward/backward',p1['bnb_4bit_cuda']+': '+p1['error']],['sm_120 execution compatibility','NOT MEASURED — GPU inaccessible']])
table(['Wheel','Measured compressed bytes'],[[k,v] for k,v in sorted(wheels.items())]+[['TOTAL torch + resolved dependency wheels',sum(wheels.values())]])
emit('Wheel sizes above are filesystem sizes before deletion, not installed sizes. Other package download sizes are in `logs/P1-packages-install.log`. Raw setup logs: `P1-torch-download.log`, `P1-torch-install.log`, `P1-packages-install.log`, `P1-pip-check.log`, `P1-cuda-bnb.log`. The tutor environment independently reported torch 2.14.0+cu130 / CUDA 13.0 / unavailable; `nvidia-smi` failed and `/dev/nvidia*` was absent (inventory log). No driver changes were attempted.\n')
emit('## P2 — LoRA memory and lifecycle\n')
emit('Configured test: r=16, alpha=32, PEFT `all-linear` (all supported linear layers except the output head), bf16, batch 1, gradient checkpointing, AdamW lr=1e-4. The first eight real corpus examples are packed/repeated to exactly 1024 or 512 tokens, with prompt labels masked. One full warmup optimizer step precedes three timed full optimizer steps; requested statistic is their median. This is a memory exercise only. Target rendering is described under P3.\n')
table(['Candidate','Cache weights bytes','1024','512','GPU allocated / reserved GB','Host RSS GB','Median s/step','Adapter reload / 64-token generation / merged size'],[[slug(m),inventory['models'][m]['weights_bytes'],'BLOCKED','BLOCKED','NOT MEASURED','NOT MEASURED','NOT MEASURED','NOT MEASURED'] for m in MODELS])
emit('Every 1024 and 512 invocation failed at `torch.cuda.init()` with `RuntimeError(\'No CUDA GPUs are available\')`. This is **BLOCKED**, not **NOT-FIT** or OOM. No adapter or merged checkpoint was created. No 4-bit training was attempted because the bitsandbytes CUDA test did not run. Peak GPU allocated/reserved memory, training host RSS, optimizer timing and merged size remain NOT MEASURED; import-only RSS is not substituted for training RSS.\n')
table(['Explicitly excluded candidate','Status','Observed cache problem'],[[m,'SKIPPED-INCOMPLETE',inventory['models'][m]['error']] for m in SKIP])
emit('`inventory.json` records snapshot hashes, exact file sizes and the corpus hash. Gemma-3 has a single `model.safetensors` plus a stale index naming absent shards; the single-file checkpoint takes precedence. The initial conservative inventory incorrectly classified it as incomplete; corrected inventory and corrected P2 attempts are retained alongside the initial error logs.\n')
emit('## P3 — tokenization over every corpus row\n')
emit(f"All {inventory['rows']:,} rows and {next(iter(p3.values()))['word_occurrences']:,} Talema word occurrences are included. A word is a whitespace-delimited unit containing at least one alphabetic character; standalone `.` is excluded from the denominator but retained in sentence token counts. Special tokens are disabled. Each corpus row is one ‘sentence’ for these statistics.\n")
emit('Trees in `sentences.jsonl` are S-expressions. They are parsed into ordered nested arrays (leaves are strings) and rendered using `json.dumps(..., ensure_ascii=False, separators=(\',\',\':\'))`. The one empty tree (`core/06_medium/0109`) renders as `null`; it is included, not imputed or dropped. Example: `'+next(iter(p3.values()))['example']['json']+'`.\n')
emit('The main per-word measure below is each full sentence’s token count divided by its number of Talema words, then mean/median over rows. JSON uses the **same Talema-word denominator**, making output cost comparable to input cost. Thus punctuation and JSON syntax count toward cost.\n')
table(['Tokenizer','Talema tokens/word mean / median','Talema tokens/sentence mean / median','JSON tokens/Talema word mean / median','JSON tokens/sentence mean / median'],[[slug(m),pair(d['talema_sentence_tokens_per_talema_word']),pair(d['talema_sentence_tokens']),pair(d['json_sentence_tokens_per_talema_word']),pair(d['json_sentence_tokens'])] for m,d in p3.items()])
emit('Separately, each word is tokenized in isolation with no leading space. Single-token fractions count word occurrences, and the type-based fraction counts unique words. These context-free word statistics differ from sentence costs because tokenizers encode word boundaries and punctuation differently. Vocabulary size is reported both as `vocab_size` and `len(tokenizer)` (includes added tokens).\n')
table(['Tokenizer','vocab_size / len','Isolated-word tokens mean / median','Single-token occurrences','Single-token types','Corpus tokens / words: Talema / JSON'],[[slug(m),f"{d['vocab_size']} / {d['len_tokenizer']}",pair(d['isolated_word_tokens']),f"{d['single_token_word_fraction']:.6%}",f"{d['single_token_unique_word_fraction']:.6%}",f"{d['talema_micro_tokens_per_word']:.6f} / {d['json_micro_tokens_per_word']:.6f}"] for m,d in p3.items()])
emit('Raw aggregate output is in `logs/P3-<model>.log`; exact per-row token/word counts are in `P3-<model>-rows.jsonl`. No dataset or model downloads occurred.\n')
emit('## P4 — fieldrun parity and probe surface\n')
emit('Read-only audit of `/home/allans/code/fieldrun`: `AGENTS.md`, `README.md`, `scripts/validate_all.sh`, every `scripts/*_ref.py`, the relevant Rust implementations, and both bundle directories. Exact reference source text and SHA-256 hashes are in `logs/P4-reference-sources.log`; per-model source lines and bundle metadata are in `logs/P4-<model>-audit.log`. The existing release binary was used; no fieldrun files were changed or built.\n')
emit('The README documents historical **architecture-level** full-checkpoint agreement for RoPE (Qwen 32/32) and Gemma-2 (18/18), through sibling numpy/torch references. Those are historical claims, not fresh measurements, and do not establish 59/60 for these candidates. No self-contained candidate-specific full-checkpoint reference script was found in fieldrun. `validate_all.sh` and the Gemma-3/4 references use tiny random fixtures. The new research-only harness reproduces the documented f32 comparison for Llama and Qwen on their actual cached weights.\n')
def parity(m):
    d=p4[m]
    return f"{d['agreement']}/{d['positions']} ({d['elapsed_s']:.2f} s)" if d['status']=='MEASURED' else 'PENDING: '+d['reason'].replace('|','/')
table(['Candidate / arch','Existing bundle','Repo full-checkpoint check evidence','Fresh f32 parity','explain','predict_ablated','head-sweep'],[[slug(m)+' / '+audit[m]['arch'],'YES' if any(b['blob_exists'] for b in audit[m]['bundles']) else 'NO','Documented historical arch check; no candidate script' if audit[m]['full_checkpoint_documented_arch'] else 'NO — tiny fixture only',parity(m),'YES' if audit[m]['explain'] else 'NO','YES' if audit[m]['predict_ablated'] else 'NO','YES' if audit[m]['head_sweep'] else 'NO'] for m in MODELS])
emit('Parity protocol: full cached checkpoint in float32, torch eager attention, 8 CPU threads, identical 16-token sliding contexts at 60 positions from a fixed stream of existing Talema corpus text. Torch and Rust run sequentially to avoid two resident model copies. The comparison checks argmax agreement between implementations; fieldrun’s incidental next-token accuracy line is not used or reported as a benchmark score. A 900-second subprocess deadline applies. Qwen reuses the existing all-f32 bundle; Llama’s temporary f32 conversion is deleted afterwards.\n')
emit('Gemma-2’s existing bundle contains f16/int8 arrays and cannot establish **f32** parity. Its measured f32 tensor requirement exceeds the 15 GB new-disk allowance when added to the environment; conversion was not attempted. Gemma-3/4 remain PENDING because only tiny-model references exist. Gemma-4 does implement `predict_ablated_blocks` (and a head loop through `--causal-dump`), but does not override `predict_ablated`, so the named `--head-sweep` route fails its capability guard. Gemma-2/3 lack both causal-ablation overrides. `explain` alone does not satisfy the full requested probe surface. Probe availability is source inspection, not a run of H5 or a functional probe validation.\n')
table(['Candidate','Existing bundle path(s)'],[[slug(m),'<br>'.join(b['path'] for b in audit[m]['bundles']) or 'None'] for m in MODELS])
emit('## Problems\n')
emit('- GPU device access is absent in this session despite CUDA-enabled torch. This blocks every requested LoRA performance/lifecycle measurement and the 4-bit CUDA compatibility claim.\n- One corpus row has no tree. Initial tokenizer runs stopped on it; the explicit `null` convention fixed coverage. Initial errors remain in logs.\n- Gemma-3’s stale shard index required correcting the cache checker to prefer its existing single weight file.\n- Gemma-3 and Gemma-4 produce identical token counts on this corpus; this is a measured result, not an assumption about all possible text.\n- Historical fieldrun architecture claims are not candidate-specific 60-position gates. Gemma-2’s f32 conversion exceeds the disk budget; Gemma-3/4 have only tiny-checkpoint references.\n')
emit('## Verification and disk use\n')
verification=j('P2-gemma-3-1b-pt-1024-bf16-verification.json')
emit('The smallest candidate by cached weight size, Gemma-3-1B (1,999,811,208 bytes), was rerun in a **fresh process** at sequence 1024. Both the original and verification attempt stopped at CUDA initialization with `No CUDA GPUs are available`. Original median s/step: **NOT MEASURED**; repeat median s/step: **NOT MEASURED**. Original/repeat peak GPU memory: **NOT MEASURED / NOT MEASURED**. Therefore the requested within-10% numerical reproduction **could not be verified**; repeated failure is not a performance reproduction. See `logs/P2-gemma-3-1b-pt-verification.log`.\n')
used=int(subprocess.check_output(['du','-s','-B1',str(RESEARCH)],text=True).split()[0]); venv=int(subprocess.check_output(['du','-s','-B1',str(RESEARCH/'.venv')],text=True).split()[0])
watch=[json.loads(s)['research_allocated_bytes'] for s in (ROOT/'logs/disk-watch.log').read_text().splitlines()]
emit(f'Measured allocated disk at report generation: research total **{used:,} bytes ({used/1e9:.6f} GB)**, of which research/.venv **{venv:,} bytes**. This conservatively includes pre-existing research documents. Maximum sampled during the parity disk watch: **{max(watch):,} bytes ({max(watch)/1e9:.6f} GB)**; this is a sampled observation, not an assertion of a continuously measured peak. Torch/dependency wheels totaling **{sum(wheels.values()):,} bytes** were deleted before model conversion. Pip caching was disabled. Only this run’s wheel files and temporary Llama bundle were deleted. New disk stayed below the ~15 GB cap; no model/dataset download, tutor change, fieldrun change, or git write operation was performed.\n')
emit('## Candidate × preflight summary\n')
table(['Candidate','Fits LoRA at 1024','Peak GPU GB','s/step','Tokens per Talema word¹','Bundle exists','Full-checkpoint parity','Probe surface²'],[[slug(m),'BLOCKED','NOT MEASURED','NOT MEASURED',f"{p3[m]['talema_sentence_tokens_per_talema_word']['mean']:.6f}",'YES' if audit[m]['bundles'] else 'NO',f"{p4[m]['agreement']}/{p4[m]['positions']}" if p4[m]['status']=='MEASURED' else 'PENDING','YES (source)' if audit[m]['head_sweep'] else 'PARTIAL: explain only³'] for m in MODELS])
emit('¹ Mean of sentence-level token/word ratios, including sentence punctuation. Isolated-word and corpus-weighted means are separately reported in P3. ² Requires explain + predict_ablated + head-sweep. ³ Gemma-4 additionally has block ablation/causal-dump; the requested named head-sweep is absent. No analysis eligibility is inferred from explain alone.\n')
emit('**Not completed:** all successful GPU optimizer steps, GPU/host training memory and timings, 4-bit GPU execution, adapter save/reload/generation/merge, numerical P2 reproduction, Gemma-2 full-checkpoint parity (disk limit), and Gemma-3/4 full-checkpoint parity (no existing full reference). P5/P6, benchmarks, SAE work, training runs and all other plan work were outside this request and were not started.')
(ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')
print('Wrote',ROOT/'REPORT.md')
