import re, subprocess, json, sys

TARGETS = ['basic/interp.asm','basic/kwtable.inc','basic/sysvars.inc',
           'basic/usr.asm','sub/deftype.asm']
BASE = '7aadd36^'

def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

def show(rev, path):
    o = run('git','show','%s:%s' % (rev,path))
    return o.split('\n') if o is not None else None

base = {t: show(BASE,t) for t in TARGETS}
head = {t: show('HEAD',t) for t in TARGETS}

files = run('git','ls-files').split()
text = [f for f in files if f.endswith(('.md','.py','.asm','.inc','.txt'))]
pat = re.compile(r'([A-Za-z0-9_./-]*(?:interp\.asm|kwtable\.inc|sysvars\.inc|usr\.asm|deftype\.asm)):(\d+)')

def canon(c):
    b = c.split('/')[-1]
    for t in TARGETS:
        if t.split('/')[-1] == b: return t
    return None

# collect the drifted set (content at line N differs BASE vs HEAD)
drift = []
seen = set()
for f in text:
    try: lines = open(f, encoding='utf-8').read().split('\n')
    except Exception: continue
    for i,l in enumerate(lines,1):
        for m in pat.finditer(l):
            t = canon(m.group(1)); n = int(m.group(2))
            if not t: continue
            k=(f,i,t,n)
            if k in seen: continue
            seen.add(k)
            b,h = base[t], head[t]
            if n>len(b) or n>len(h): continue
            if b[n-1] != h[n-1]:
                drift.append((f,i,t,n))

print("drifted anchors under audit: %d\n" % len(drift))

# blame the CITING line -> commit that wrote the citation
CORRECT_WHEN_WRITTEN=0; NEVER_CORRECT=0; UNDECIDABLE=0
repairable=0
rows=[]
for f,i,t,n in drift:
    bl = run('git','blame','-L','%d,%d'%(i,i),'--porcelain','HEAD','--',f)
    if not bl: UNDECIDABLE+=1; rows.append((f,i,t,n,'UNDECIDABLE','blame failed','')); continue
    sha = bl.split('\n')[0].split()[0]
    at = show(sha, t)
    if at is None or n>len(at):
        UNDECIDABLE+=1; rows.append((f,i,t,n,'UNDECIDABLE','target absent at cite-commit','')); continue
    cited_then = at[n-1]
    now = head[t]
    # where did that content go in HEAD?
    hits = [j+1 for j,x in enumerate(now) if x == cited_then]
    if cited_then.strip()=='' :
        UNDECIDABLE+=1; rows.append((f,i,t,n,'UNDECIDABLE','cited a blank line','')); continue
    if len(hits)==1 and hits[0]!=n:
        CORRECT_WHEN_WRITTEN+=1; repairable+=1
        rows.append((f,i,t,n,'DRIFTED','->%d'%hits[0], cited_then.strip()[:46]))
    elif len(hits)==1 and hits[0]==n:
        rows.append((f,i,t,n,'STILL-OK','', cited_then.strip()[:46]))
    elif len(hits)==0:
        NEVER_CORRECT+=1
        rows.append((f,i,t,n,'CONTENT-GONE','line deleted since', cited_then.strip()[:46]))
    else:
        UNDECIDABLE+=1
        rows.append((f,i,t,n,'AMBIGUOUS','%d matches'%len(hits), cited_then.strip()[:46]))

print("SPLIT OF THE DRIFTED SET, decided by blaming the CITING line:")
print("  correct when written, content still present -> MECHANICALLY REPAIRABLE : %d" % CORRECT_WHEN_WRITTEN)
print("  content deleted since the citation was written                        : %d" % NEVER_CORRECT)
print("  undecidable (blank/ambiguous/absent)                                  : %d" % UNDECIDABLE)
print("  cited line unchanged since the citing commit (false positive earlier)  : %d"
      % sum(1 for r in rows if r[4]=='STILL-OK'))
json.dump(rows, open('/tmp/claude-501/-Users-joost-projects-zerobas/caf279e5-e405-446f-b919-bce8acf752f8/scratchpad/anchor_rows.json','w'))
