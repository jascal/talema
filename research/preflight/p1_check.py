"""Run: python p1_check.py. Tests import and an actual CUDA NF4 linear forward/backward."""
from common import *
import importlib.metadata, traceback
import torch
out={'torch':torch.__version__,'cuda_build':torch.version.cuda,'cuda_available':torch.cuda.is_available(),'packages':{p:importlib.metadata.version(p) for p in ['torch','transformers','peft','accelerate','datasets','bitsandbytes']}}
try:
    import bitsandbytes as bnb
    out['bnb_import']='PASS'
    layer=bnb.nn.Linear4bit(128,64,bias=False,compute_dtype=torch.bfloat16,quant_type='nf4').to('cuda')
    x=torch.randn(2,128,device='cuda',dtype=torch.bfloat16,requires_grad=True)
    y=layer(x); y.float().square().mean().backward(); torch.cuda.synchronize()
    out.update(bnb_4bit_cuda='PASS',shape=list(y.shape),finite=bool(y.isfinite().all()),gpu=torch.cuda.get_device_name(),capability=torch.cuda.get_device_capability())
except Exception as e:
    traceback.print_exc(); out.update(bnb_4bit_cuda='BLOCKED',error=repr(e))
save('P1-check.json',out)
