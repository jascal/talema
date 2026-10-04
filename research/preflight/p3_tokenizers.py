"""Run once per model: python p3_tokenizers.py --model MODEL (offline; all corpus rows)."""
from common import *
import argparse, statistics, time
from transformers import AutoTokenizer
p=argparse.ArgumentParser(); p.add_argument('--model',required=True); a=p.parse_args()
t=time.perf_counter(); tok=AutoTokenizer.from_pretrained(snapshot(a.model),local_files_only=True)
r=rows(); wordlists=[words(x['talema']) for x in r]
assert all(wordlists)
texts=[x['talema'] for x in r]; trees=[tree_json(x['tree']) for x in r]
def counts(xs): return [len(x) for x in tok(xs,add_special_tokens=False)['input_ids']]
def stat(x): return {'mean':statistics.mean(x),'median':statistics.median(x)}
wc=[len(x) for x in wordlists]; flat=[w for ws in wordlists for w in ws]
wordtokens=counts(flat); tal=counts(texts); js=counts(trees)
out={'model':a.model,'rows':len(r),'word_occurrences':len(flat),'vocab_size':tok.vocab_size,'len_tokenizer':len(tok),'talema_sentence_tokens':stat(tal),'json_sentence_tokens':stat(js),'talema_sentence_tokens_per_talema_word':stat([n/w for n,w in zip(tal,wc)]),'json_sentence_tokens_per_talema_word':stat([n/w for n,w in zip(js,wc)]),'isolated_word_tokens':stat(wordtokens),'single_token_word_fraction':sum(n==1 for n in wordtokens)/len(wordtokens),'single_token_unique_word_fraction':sum(n==1 for n in counts(sorted(set(flat))))/len(set(flat)),'talema_micro_tokens_per_word':sum(tal)/sum(wc),'json_micro_tokens_per_word':sum(js)/sum(wc),'elapsed_s':time.perf_counter()-t,'example':{'talema':texts[1],'json':trees[1]}}
save('P3-'+slug(a.model)+'.json',out)
# Per-row raw counts allow recomputation of every sentence aggregate.
with (ROOT/('P3-'+slug(a.model)+'-rows.jsonl')).open('w') as f:
    for row,w,n,j in zip(r,wc,tal,js): f.write(json.dumps({'id':row['id'],'words':w,'talema_tokens':n,'json_tokens':j})+'\n')
