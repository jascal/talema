"""Full-checkpoint f32 parity, no benchmark scoring. Run: python p4_parity.py --model MODEL.
Sequential subprocesses avoid holding torch and Rust model copies simultaneously.
ctx=16, 60 positions from real Talema text; torch eager attention, 8 CPU threads.
Only runs architectures with documented full-checkpoint checks (rope, gemma).
All subprocesses share a 15 minute limit; generated bundles are removed afterwards.
"""
from common import *
import argparse, subprocess, sys, time, shutil, traceback
p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--reference',action='store_true'); a=p.parse_args()
arch='gemma' if a.model=='google/gemma-2-2b' else 'rope'
work=ROOT/('parity-'+slug(a.model)); work.mkdir(exist_ok=True)
if a.reference:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(8)
    tok=AutoTokenizer.from_pretrained(snapshot(a.model),local_files_only=True)
    ids=tok.encode('\n'.join(r['talema'] for r in rows()[:20]),add_special_tokens=False)[:76]
    assert len(ids)==76
    (work/'ids.json').write_text(json.dumps({'holdout_ids':ids}))
    model=AutoModelForCausalLM.from_pretrained(snapshot(a.model),local_files_only=True,dtype=torch.float32,attn_implementation='eager').eval()
    preds=[]
    with torch.inference_mode():
        for i in range(16,76):
            logits=model(torch.tensor([ids[i-16:i]]),use_cache=False).logits[0,-1]
            preds.append(int(logits.argmax()))
    (work/'torch.json').write_text(json.dumps(preds))
    print('Torch f32 predictions',preds,flush=True)
    sys.exit(0)
start=time.monotonic(); out={'model':a.model,'status':'PENDING','agreement':None,'positions':None}
created=False
try:
    if a.model not in [MODELS[0],MODELS[1],MODELS[3]]: raise RuntimeError('Only tiny reference exists; no full-checkpoint check in repo')
    audit=json.loads((ROOT/'P4-audit.json').read_text())[a.model]
    existing=[b for b in audit['bundles'] if b['blob_exists'] and b['dtypes']==['f32']]
    if existing: stem=Path(existing[0]['path'].replace('.fieldrun.json',''))
    else:
        # Read safetensors headers only to measure actual tensor storage required at f32.
        import struct, math
        count=0
        for f in snapshot(a.model).glob('*.safetensors'):
            with f.open('rb') as stream:
                n=struct.unpack('<Q',stream.read(8))[0]; h=json.loads(stream.read(n))
            count+=sum(math.prod(v['shape']) for k,v in h.items() if k!='__metadata__')
        need=count*4
        used=sum(f.stat().st_blocks*512 for f in RESEARCH.rglob('*') if f.is_file())
        out.update(f32_tensor_bytes=need,current_research_allocated_bytes=used)
        if used+need+100_000_000 > 15_000_000_000: raise RuntimeError(f'15 GB new-disk cap: current={used}, f32 tensor bytes={need}; conversion not attempted')
        available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        out['host_available_bytes']=available
        if need>available: raise RuntimeError(f'f32 tensor bytes {need} exceed measured MemAvailable {available}; CPU <15min feasibility not established without swapping')
        stem=work/'bundle'; created=True
    env=os.environ.copy(); env.update(RAYON_NUM_THREADS='8',OMP_NUM_THREADS='8',MKL_NUM_THREADS='8',PYTHONDONTWRITEBYTECODE='1')
    def run(cmd):
        print('$', ' '.join(map(str,cmd)),flush=True)
        subprocess.run(list(map(str,cmd)),check=True,env=env,cwd=ROOT,timeout=max(1,900-(time.monotonic()-start)))
    run([sys.executable,__file__,'--model',a.model,'--reference'])
    binary='/home/allans/code/fieldrun/target/release/fieldrun'
    if created: run([binary,'convert','--model',snapshot(a.model),'--arch',arch,'--dtype','f32','-o',stem])
    run([binary,'--bundle',stem,'--ids',work/'ids.json','--ctx','16','--n-eval','60','--dump',work/'rust.txt'])
    ref=json.loads((work/'torch.json').read_text()); got=list(map(int,(work/'rust.txt').read_text().split()))
    assert len(ref)==len(got)==60,(len(ref),len(got))
    out.update(status='MEASURED',agreement=sum(x==y for x,y in zip(ref,got)),positions=60,mismatches=[{'position':i,'torch':x,'fieldrun':y} for i,(x,y) in enumerate(zip(ref,got)) if x!=y])
except Exception as e: traceback.print_exc(); out['reason']=repr(e)
finally:
    if created:
        for p in work.glob('bundle*'):
            if p.is_file(): p.unlink()
    out['elapsed_s']=time.monotonic()-start
    save('P4-'+slug(a.model)+'-parity.json',out)
