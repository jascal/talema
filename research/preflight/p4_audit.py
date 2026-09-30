"""Read-only fieldrun inventory. Run: python p4_audit.py; writes per-candidate evidence logs."""
from common import *
import hashlib, subprocess
repo=Path('/home/allans/code/fieldrun')
files=[repo/'AGENTS.md',repo/'README.md',repo/'scripts/validate_all.sh',*sorted((repo/'scripts').glob('*_ref.py'))]
# Preserve the exact inspected reference sources and hashes in a raw evidence log.
with (ROOT/'logs/P4-reference-sources.log').open('w') as f:
    for p in files:
        f.write(f'\nFILE {p}\nSHA256 {hashlib.sha256(p.read_bytes()).hexdigest()}\n'+p.read_text())
bundles=[]
for root in [repo/'bundles',Path.home()/'.cache/fieldrun/bundles']:
    for p in root.rglob('*.fieldrun.json'):
        j=json.loads(p.read_text()); blob=p.with_name(p.name.replace('.json','.bin'))
        bundles.append({'path':str(p),'arch':j['arch'],'blob_exists':blob.is_file(),'blob_bytes':blob.stat().st_size if blob.is_file() else None,'dtypes':sorted({x['dtype'] for x in j['arrays']})})
arches=['rope','rope','gemma3','gemma','gemma4']; keys=['llama-3.2-1b','qwen2.5-1.5b','gemma-3-1b','gemma-2-2b','gemma-4-e4b']
out={}
for m,arch,key in zip(MODELS,arches,keys):
    src=(repo/f'src/{arch}.rs').read_text()
    b=[x for x in bundles if key in x['path'].lower()]
    out[m]={'arch':arch,'bundles':b,'explain':'fn explain(' in src,'predict_ablated':'fn predict_ablated(' in src,'predict_ablated_blocks':'fn predict_ablated_blocks(' in src,'head_sweep':'fn predict_ablated(' in src,'full_checkpoint_documented_arch':arch in ['rope','gemma'],'candidate_full_checkpoint_check_script_found':False,'tiny_fixture':arch in ['gemma3','gemma4']}
    with (ROOT/('logs/P4-'+slug(m)+'-audit.log')).open('w') as f:
        f.write(json.dumps(out[m],indent=2)+'\n')
        for rel,needles in [(f'src/{arch}.rs',['fn explain(', 'fn predict_ablated', 'fn predict_ablated_blocks']),('src/model.rs',['fn predict_ablated']),('src/main.rs',['--head-sweep','has no predict_ablated','predict_ablated(&ids']),('README.md',['0/32','0/18','tiny random-init'])]:
            for i,line in enumerate((repo/rel).read_text().splitlines(),1):
                if any(s in line for s in needles): f.write(f'{rel}:{i}: {line}\n')
save('P4-audit.json',out)
