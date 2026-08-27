import re, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
files = [p for p in ROOT.rglob('*.asm') if 'build' not in p.parts]

def norm(line):
    # strip comment and label, lowercase, collapse whitespace
    l = line.split(';')[0]
    l = re.sub(r'^\s*[A-Za-z_][A-Za-z0-9_]*:', '', l)
    return re.sub(r'[\s]+', ' ', l.strip().lower())

PATTERNS = {
 # name: list of regexes matching consecutive non-blank normalised instrs
 'NEG16-cpl'      : [r'ld a,h', r'cpl', r'ld h,a', r'ld a,l', r'cpl', r'ld l,a', r'inc hl'],
 'NEG16-sub-hl'   : [r'xor a', r'sub l', r'ld l,a', r'sbc a,a', r'sub h', r'ld h,a'],
 'NEG16-sub-bc'   : [r'xor a', r'sub c', r'ld c,a', r'sbc a,a', r'sub b', r'ld b,a'],
 'NEG16-sub-de'   : [r'xor a', r'sub e', r'ld e,a', r'sbc a,a', r'sub d', r'ld d,a'],
 'NEG16-sub-hl2de': [r'xor a', r'sub l', r'ld e,a', r'ld a,0', r'sbc a,h', r'ld d,a'],
 'NEG16-zero-de'  : [r'ld hl,0', r'(or a|and a|scf ccf)?', r'sbc hl,de'],
 'NEG16-zero-bc'  : [r'ld hl,0', r'(or a|and a)?', r'sbc hl,bc'],
 'SHR16-srl-h'    : [r'srl h', r'rr l'],
 'SHR16-sra-h'    : [r'sra h', r'rr l'],
 'SHR16-srl-d'    : [r'srl d', r'rr e'],
 'SHR16-srl-b'    : [r'srl b', r'rr c'],
 'NEG8-neg'       : [r'neg'],
}

hits = {k: [] for k in PATTERNS}
for f in files:
    raw = f.read_text().splitlines()
    ins = [(i+1, norm(l)) for i, l in enumerate(raw)]
    ins = [(n, t) for n, t in ins if t]
    for name, pats in PATTERNS.items():
        for i in range(len(ins)):
            j, k, ok = i, 0, True
            while k < len(pats):
                p = pats[k]
                opt = p.endswith('?')
                body = p[:-1] if opt else p
                if j < len(ins) and re.fullmatch(body.strip('()') if opt else body, ins[j][1]):
                    j += 1; k += 1
                elif opt:
                    k += 1
                else:
                    ok = False; break
            if ok:
                hits[name].append((str(f.relative_to(ROOT)), ins[i][0]))

for name in PATTERNS:
    print(f'--- {name}: {len(hits[name])} ---')
    for f, n in hits[name]:
        print(f'    {f}:{n}')
