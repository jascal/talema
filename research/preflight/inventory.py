"""Run: research/.venv/bin/python research/preflight/inventory.py"""
from common import *
import hashlib, subprocess
out={'corpus_sha256':hashlib.sha256(DATA.read_bytes()).hexdigest(),'rows':len(rows()),'models':{}}
for m in MODELS+SKIP:
    try:
        p=snapshot(m)
        weights=list(p.glob('*.safetensors'))
        out['models'][m]={'status':'COMPLETE','snapshot':str(p),'weights_bytes':sum(f.stat().st_size for f in weights),'files':[{ 'name':f.name,'bytes':f.stat().st_size} for f in p.iterdir() if f.is_file()]}
    except Exception as e: out['models'][m]={'status':'SKIPPED-INCOMPLETE','error':str(e)}
for cmd in [['nvidia-smi'],['bash','-c','ls -l /dev/nvidia*'],['free','-b'],['df','-B1',str(RESEARCH)]]:
    p=subprocess.run(cmd, capture_output=True,text=True); print('$',cmd,'\n',p.stdout,p.stderr,'exit',p.returncode)
save('inventory.json',out)
