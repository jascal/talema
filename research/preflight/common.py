"""Shared offline paths, cache validation, and deterministic corpus rendering."""
import os
from pathlib import Path
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false', PYTHONDONTWRITEBYTECODE='1')
ROOT = Path(__file__).resolve().parent
os.environ['TMPDIR'] = str(ROOT / 'tmp')
import json, re
RESEARCH = ROOT.parent
DATA = RESEARCH.parent / 'data/sentences.jsonl'
MODELS = ['meta-llama/Llama-3.2-1B','Qwen/Qwen2.5-1.5B','unsloth/gemma-3-1b-pt','google/gemma-2-2b','google/gemma-4-e4b-it']
SKIP = ['google/gemma-4-e2b-it','Qwen/Qwen2.5-3B']
def slug(model): return model.split('/')[-1]
def snapshot(model):
    paths = sorted((Path.home()/'.cache/huggingface/hub'/('models--'+model.replace('/','--'))/'snapshots').glob('*'))
    for p in paths:
        idx = p/'model.safetensors.index.json'
        names = {'model.safetensors'} if (p/'model.safetensors').is_file() else (set(json.loads(idx.read_text())['weight_map'].values()) if idx.exists() else {'model.safetensors'})
        missing = [n for n in sorted(names | {'config.json','tokenizer.json'}) if not (p/n).is_file()]
        if not missing: return p
    raise FileNotFoundError(f'{model}: incomplete cache; missing {missing if paths else "snapshot"}')
def tree_json(s):
    # Corpus tree is an S-expression. JSON arrays preserve ordered nodes; leaves are strings.
    if not s.strip(): return 'null'
    toks = re.findall(r'\(|\)|[^\s()]+', s)
    def parse(i):
        if toks[i] != '(': return toks[i], i+1
        out=[]; i+=1
        while toks[i]!=')':
            v,i=parse(i); out.append(v)
        return out,i+1
    tree,n=parse(0)
    assert n == len(toks), s
    return json.dumps(tree, ensure_ascii=False, separators=(',',':'))
def rows():
    return [json.loads(s) for s in DATA.read_text().splitlines() if s.strip()]
def words(text): return [w for w in text.split() if any(c.isalpha() for c in w)]
def save(name,obj):
    (ROOT/name).write_text(json.dumps(obj, indent=2)+'\n')
    print(json.dumps(obj, indent=2), flush=True)
