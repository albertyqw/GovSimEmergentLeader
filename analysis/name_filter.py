import gzip,json,glob,collections,sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import metrics as M
def content(rc):
    if isinstance(rc,str): rc=json.loads(rc)
    o=rc.get('_sdk_original',rc)
    if isinstance(o,str): o=json.loads(o)
    return o['choices'][0]['message'].get('content') or ''
C=collections.defaultdict(collections.Counter)
for d in sorted(glob.glob('runs/v3/*_N*/seed*')):
    cond=d.split('/')[2]
    try: json.load(open(d+'/run_meta.json'))
    except: continue
    cyc={json.loads(l)['cycle']:json.loads(l) for l in gzip.open(d+'/cycles.jsonl.gz','rt')}
    names={c:[x['identity'] for x in cy['catches']] for c,cy in cyc.items()}
    for l in gzip.open(d+'/calls.jsonl.gz','rt'):
        r=json.loads(l); ct=r['call_type']
        if ct not in('harvest','utterance'): continue
        txt=content(r['raw_completion']); me=r['agent_identity']
        other=M.mentioned_set(txt, names.get(r['cycle'],[]))-{me}
        C[cond][ct+'_n']+=1; C[cond][ct+'_named']+=bool(other)
    for c,cy in cyc.items():
        for me,v in (cy['elicitation'] or {}).items():
            other=M.mentioned_set(v.get('reason') or '',names[c])-{me}
            C[cond]['elic_n']+=1; C[cond]['elic_named']+=bool(other)
tot=collections.Counter()
for k,v in C.items(): print(k,dict(v)); tot.update(v)
for t in ('harvest','utterance','elic'): print(t, tot[t+'_named'],'/',tot[t+'_n'], round(tot[t+'_named']/tot[t+'_n'],3))
