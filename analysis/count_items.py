import gzip,json,glob,collections
def content(rc):
    try:
        if isinstance(rc,str): rc=json.loads(rc)
        o=rc.get('_sdk_original',rc)
        if isinstance(o,str): o=json.loads(o)
        return o['choices'][0]['message'].get('content') or ''
    except Exception: return None
S=collections.defaultdict(lambda: collections.Counter())
for d in sorted(glob.glob('runs/v3/*_N*/seed*')):
    cond=d.split('/')[2]
    try: json.load(open(d+'/run_meta.json'))
    except: continue
    st=S[cond]; st['runs']+=1
    for l in gzip.open(d+'/calls.jsonl.gz','rt'):
        r=json.loads(l); ct=r['call_type']
        if ct in ('harvest','utterance'):
            c=content(r['raw_completion'])
            if c is None: st['unreadable']+=1; continue
            st[ct+'_n']+=1; st[ct+'_chars']+=len(c)
            if r.get('reasoning_text'): st['reasoning_n']+=1; st['reasoning_chars']+=len(r['reasoning_text'])
            st['out_tok_'+ct]+=r['tokens']['output'] or 0; st['reason_tok_'+ct]+=r['tokens']['reasoning'] or 0
    cyc=[json.loads(l) for l in gzip.open(d+'/cycles.jsonl.gz','rt')]
    turns=[json.loads(l) for l in gzip.open(d+'/utterances.jsonl.gz','rt')]
    for cy in cyc:
        for v in (cy['elicitation'] or {}).values():
            if v.get('reason'): st['elic_n']+=1; st['elic_chars']+=len(v['reason'])
        final={c['identity'] for c in cy['catches'] if c['months_remaining']==1}
        for t in turns:
            if t['cycle']==cy['cycle'] and t['speaker_identity'] in final: st['final_month_utt']+=1
    for t in turns: st['utt_n']+=1; st['utt_chars']+=len(t['text'])
for k,v in S.items(): print(k, dict(v))
