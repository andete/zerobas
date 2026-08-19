# Repo-wide line-anchor audit. For every `file:LINE` citation in tracked text,
# blame the CITING line to find the commit that wrote it, read the TARGET file at
# that commit to learn what the author actually pointed at, and compare with what
# stands at that line today. No arbitrary baseline: the citation's own birth
# commit is the reference. Companion to scratchpad/anchor_audit.py, which asks
# the same question of one commit window; this one asks it of the whole tree.
import re, subprocess, json, collections, sys

def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

files = run('git','ls-files').split()
tracked = set(files)
text = [f for f in files if f.endswith(('.md','.py','.asm','.inc','.txt'))]
CITE = re.compile(r'((?:\.\./)*[A-Za-z0-9_./-]+\.(?:asm|inc|py|md)):(\d+)')

def resolve(cited, citer):
    """Map a citation string to a tracked repo path, or None."""
    c = cited.lstrip('./')
    while c.startswith('../'): c = c[3:]
    if c in tracked: return c
    base = c.split('/')[-1]
    hits = [t for t in tracked if t.split('/')[-1] == base]
    return hits[0] if len(hits) == 1 else None

# 1. collect citations
cites = []
for f in text:
    try: lines = open(f, encoding='utf-8').read().split('\n')
    except Exception: continue
    for i,l in enumerate(lines,1):
        for m in CITE.finditer(l):
            t = resolve(m.group(1), f)
            if t and t != f: cites.append((f,i,t,int(m.group(2))))
cites = sorted(set(cites))
print("citations resolving to a tracked file: %d" % len(cites), file=sys.stderr)

# 2. one blame per citing file
blame = {}
for f in sorted({c[0] for c in cites}):
    out = run('git','blame','--porcelain','HEAD','--',f)
    if not out: continue
    m = {}; ln = None
    for line in out.split('\n'):
        if re.match(r'^[0-9a-f]{40} \d+ \d+', line):
            p = line.split(); m[int(p[2])] = p[0]
    blame[f] = m

# 3. caches
cache = {}
def at(rev, path):
    k=(rev,path)
    if k not in cache:
        o = run('git','show','%s:%s'%(rev,path))
        cache[k] = o.split('\n') if o is not None else None
    return cache[k]

now = {}
for t in sorted({c[2] for c in cites}):
    now[t] = at('HEAD', t)

rows=[]; tally=collections.Counter()
for f,i,t,n in cites:
    sha = blame.get(f,{}).get(i)
    cur = now.get(t)
    if cur is None: tally['target-unreadable']+=1; continue
    if not sha: tally['no-blame']+=1; continue
    then = at(sha, t)
    if then is None or n > len(then) or n < 1:
        # the anchor pointed past EOF even when it was written, or the target did
        # not exist then -- nothing to recover it from
        if n > len(cur) or n < 1:
            tally['OUT-OF-RANGE-UNRECOVERABLE']+=1
            rows.append([f,i,t,n,'OUT-OF-RANGE','',''])
        else:
            tally['target-absent-at-birth']+=1
        continue
    cited = then[n-1]
    if cited.strip()=='' :
        tally['cited-blank']+=1; continue
    # NOTE: an out-of-range anchor is still repairable if the content it pointed
    # at when written is uniquely locatable today -- so the range test comes AFTER
    # the birth lookup, not before it.
    if n <= len(cur) and cur[n-1] == cited:
        tally['STILL-CORRECT']+=1; continue
    hits=[j+1 for j,x in enumerate(cur) if x==cited]
    if len(hits)==1:
        tally['REPAIRABLE']+=1; rows.append([f,i,t,n,'REPAIRABLE',hits[0],cited.strip()[:60]])
    elif len(hits)==0:
        tally['CONTENT-GONE']+=1; rows.append([f,i,t,n,'CONTENT-GONE','',cited.strip()[:60]])
    else:
        tally['AMBIGUOUS']+=1; rows.append([f,i,t,n,'AMBIGUOUS',len(hits),cited.strip()[:60]])

print("\nREPO-WIDE LINE-ANCHOR AUDIT")
for k in ['STILL-CORRECT','REPAIRABLE','CONTENT-GONE','AMBIGUOUS','OUT-OF-RANGE',
          'OUT-OF-RANGE-UNRECOVERABLE','cited-blank','target-absent-at-birth',
          'no-blame','target-unreadable']:
    if tally[k]: print("  %-24s %5d" % (k, tally[k]))
print("  %-24s %5d" % ('TOTAL', sum(tally.values())))
json.dump(rows, open('scratchpad/anchor_rows_all.json','w'))
