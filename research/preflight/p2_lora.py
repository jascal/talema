"""Offline GPU preflight; python p2_lora.py --model MODEL [--seq 1024] [--four-bit] [--tag rerun].
One warmup optimizer step + three timed full steps; batch 1, packed real examples.
Adapter lifecycle runs only after steps fit. Deletes only its own merged directory.
"""
from common import *
import argparse, gc, resource, statistics, time, traceback, shutil
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, PeftModel, prepare_model_for_kbit_training
p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--seq',type=int,default=1024); p.add_argument('--four-bit',action='store_true'); p.add_argument('--tag',default='main'); a=p.parse_args()
name=f'P2-{slug(a.model)}-{a.seq}-{ "4bit" if a.four_bit else "bf16"}-{a.tag}'
out={'model':a.model,'sequence_length':a.seq,'batch_size':1,'r':16,'alpha':32,'target_modules':'all-linear (PEFT excludes output head)','dtype':'4-bit NF4, bf16 compute' if a.four_bit else 'bf16','seed':20260929,'status':'BLOCKED','peak_allocated_bytes':None,'peak_reserved_bytes':None,'peak_host_rss_bytes':None,'median_step_s':None}
try:
    path=snapshot(a.model)
    # Force an actual CUDA initialization, preserving the exact driver error.
    torch.cuda.init()
    torch.manual_seed(20260929); torch.set_num_threads(8)
    tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
    examples=rows()[:8]; ids=[]; labels=[]
    for row in examples:
        prompt=tok.encode(row['talema']+'\n',add_special_tokens=False)
        target=tok.encode(tree_json(row['tree']),add_special_tokens=False)+[tok.eos_token_id]
        ids+=prompt+target; labels += [-100]*len(prompt)+target
    repeat=(a.seq+len(ids)-1)//len(ids)
    ids=torch.tensor([(ids*repeat)[:a.seq]],device='cuda'); labels=torch.tensor([(labels*repeat)[:a.seq]],device='cuda')
    kwargs={'local_files_only':True,'dtype':torch.bfloat16,'device_map':{'':'cuda'},'attn_implementation':'sdpa'}
    if a.four_bit: kwargs['quantization_config']=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.bfloat16)
    torch.cuda.reset_peak_memory_stats()
    model=AutoModelForCausalLM.from_pretrained(path,**kwargs)
    model.config.use_cache=False
    if a.four_bit: model=prepare_model_for_kbit_training(model,use_gradient_checkpointing=True)
    model=get_peft_model(model,LoraConfig(r=16,lora_alpha=32,target_modules='all-linear',lora_dropout=0.0,task_type='CAUSAL_LM'))
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False}); model.enable_input_require_grads(); model.train()
    out['trainable_parameters']=sum(p.numel() for p in model.parameters() if p.requires_grad)
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=1e-4)
    times=[]; losses=[]
    for i in range(4):
        opt.zero_grad(set_to_none=True); torch.cuda.synchronize(); start=time.perf_counter()
        loss=model(input_ids=ids,labels=labels,use_cache=False).loss
        if not torch.isfinite(loss): raise RuntimeError('Nonfinite training loss')
        loss.backward(); opt.step(); torch.cuda.synchronize()
        elapsed=time.perf_counter()-start; losses.append(loss.item())
        print(json.dumps({'step':i,'warmup':i==0,'seconds':elapsed,'loss':loss.item()}),flush=True)
        if i: times.append(elapsed)
    out.update(status='FIT',step_times_s=times,losses=losses,median_step_s=statistics.median(times),peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),peak_host_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    adapter=ROOT/'adapters'/name; adapter.mkdir(parents=True,exist_ok=False); model.save_pretrained(adapter)
    del model,opt,loss; gc.collect(); torch.cuda.empty_cache()
    base=AutoModelForCausalLM.from_pretrained(path,**kwargs)
    model=PeftModel.from_pretrained(base,adapter,local_files_only=True).eval()
    prompt=tok(examples[0]['talema']+'\n',return_tensors='pt').to('cuda')
    with torch.no_grad(): generated=model.generate(**prompt,min_new_tokens=64,max_new_tokens=64,do_sample=False,pad_token_id=tok.eos_token_id)
    out['generation_ids']=generated[0].tolist(); out['generated_tokens']=generated.shape[1]-prompt['input_ids'].shape[1]; out['adapter_reload']='PASS'
    del model,base; gc.collect(); torch.cuda.empty_cache()
    # Reload bf16 base on CPU for a non-quantized merge, also for QLoRA.
    base=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,dtype=torch.bfloat16,device_map={'':'cpu'})
    merged=PeftModel.from_pretrained(base,adapter,local_files_only=True).merge_and_unload()
    dest=ROOT/'merged'/name; dest.mkdir(parents=True,exist_ok=False)
    try:
        used=sum(p.stat().st_blocks*512 for p in RESEARCH.rglob('*') if p.is_file())
        weight_bytes=sum(p.numel()*p.element_size() for p in merged.parameters())
        if used+weight_bytes+100_000_000 > 15_000_000_000: raise RuntimeError('15 GB new-disk budget prevents merged save')
        merged.save_pretrained(dest,max_shard_size='1GB'); tok.save_pretrained(dest)
        out['merged_bytes']=sum(p.stat().st_size for p in dest.rglob('*') if p.is_file()); out['merge']='PASS'
    finally: shutil.rmtree(dest)
except Exception as e:
    traceback.print_exc(); out['error']=repr(e)
    if isinstance(e,torch.cuda.OutOfMemoryError): out['status']='NOT-FIT'
    elif out['status']=='FIT': out['lifecycle_status']='FAILED'
    if torch.cuda.is_initialized():
        out.update(peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),peak_host_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
save(name+'.json',out)
