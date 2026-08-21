#!/usr/bin/env python3
"""D-SEEDPROSE falsification for the CODE-COLUMN seed scrape.

Rows K1..K3 knife the STRIPPER (its own self-test must catch each).
Rows K4..K6 knife the SWEEP with a planted dead span, and the pair K5/K6 is the
discriminator: the SAME text under sub/, once as a comment and once as code.

⚠️ No ROM is built. These knives only change SOURCES, and the sweep reads
sources -- the .sym files decorate findings with an address, they do not decide
them. Restoring is done by WRITING THE BYTES BACK (never cp/copy2).
"""
import os, subprocess, sys

TOOL = 'tools/check_dead_code.py'
POKE = 'basic/poke.asm'
BEEP = 'sub/beep.asm'
SYMS = ['build/basic-reloc.sym', 'build/sub.sym']

PLANT = """
; --- zz_seedprose_plant: D-SEEDPROSE falsification plant, never shipped -----
zz_seedprose_plant:
                ld      a,1
                ret
"""
originals = {p: open(p).read() for p in (TOOL, POKE, BEEP)}


def restore():
    for p, txt in originals.items():
        open(p, 'w').write(txt)          # WRITE THE BYTES, never cp/copy2


def run(argv=()):
    r = subprocess.run([sys.executable, TOOL, *argv, *SYMS],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def old_scrape():
    """Put back the PRE-slice scraper (whole file, prose included)."""
    s = originals[TOOL]
    old = """                out.update(m.group(0)
                           for m in IDENT.finditer(_code_column(path, txt)))"""
    new = """                out.update(m.group(0) for m in IDENT.finditer(txt))"""
    assert s.count(old) == 1
    open(TOOL, 'w').write(s.replace(old, new))


rows, fails = [], 0


def row(name, want, got, note=""):
    global fails
    ok = want == got
    fails += not ok
    rows.append((name, want, got, ok, note))
    print(f"{'EXACT' if ok else 'MISS '}  {name:34s} want={want:24s} got={got:24s} {note}")


# ---- K1: gut the self-test table ------------------------------------------
restore()
s = originals[TOOL]
i = s.index('_CC_VECTORS = [')
j = s.index('\n]\n', i) + 3
open(TOOL, 'w').write(s[:i] + '_CC_VECTORS = []\n' + s[j:])
rc, out = run()
row("K1 self-test table gutted to []", "rc=1 floored",
    f"rc={rc} {'floored' if '_CC_VECTORS has 0 rows' in out else 'NOT CAUGHT'}")

# ---- K2: the stripper stops stripping (the pre-slice behaviour) ------------
restore()
s = originals[TOOL]
old = """    if path.endswith('.py'):
        return _py_code_column(txt, path)
    return "\\n".join(ln.split(';', 1)[0] for ln in txt.splitlines())"""
assert s.count(old) == 1, s.count(old)
open(TOOL, 'w').write(s.replace(old, "    return txt"))
rc, out = run()
row("K2 _code_column returns txt", "rc=1 kept-prose",
    f"rc={rc} {'kept-prose' if 'which is PROSE' in out else 'NOT CAUGHT'}")

# ---- K3: the stripper strips everything -----------------------------------
restore()
open(TOOL, 'w').write(s.replace(old, '    return ""'))
rc, out = run()
row("K3 _code_column returns ''", "rc=1 dropped-ref",
    f"rc={rc} {'dropped-ref' if 'which is a REFERENCE' in out else 'NOT CAUGHT'}")

# ---- K4: a planted dead span, no mention anywhere -------------------------
restore()
open(POKE, 'w').write(originals[POKE] + PLANT)
rc, out = run()
seen_new = 'zz_seedprose_plant' in out
old_scrape()
rc_old, out_old = run()
seen_old = 'zz_seedprose_plant' in out_old
row("K4 plant, no mention", "new=YES old=YES",
    f"new={'YES' if seen_new else 'NO '} old={'YES' if seen_old else 'NO '}",
    "the plant is genuinely dead in both scrapers")

# ---- K5: THE DISCRIMINATOR -- the same name, in a COMMENT under sub/ ------
restore()
open(POKE, 'w').write(originals[POKE] + PLANT)
open(BEEP, 'w').write(originals[BEEP] +
                      "\n; zz_seedprose_plant was removed from the sub copy.\n")
rc, out = run()
seen_new = 'zz_seedprose_plant' in out
old_scrape()
rc_old, out_old = run()
seen_old = 'zz_seedprose_plant' in out_old
row("K5 plant + sub COMMENT", "new=YES old=NO ",
    f"new={'YES' if seen_new else 'NO '} old={'YES' if seen_old else 'NO '}",
    "<- the whole slice: prose seeded it, and no longer does")

# ---- K6: green control -- the SAME text as CODE, one `; ` less ------------
restore()
open(POKE, 'w').write(originals[POKE] + PLANT)
open(BEEP, 'w').write(originals[BEEP] +
                      "\n                call    zz_seedprose_plant\n")
rc, out = run()
seen_new = 'zz_seedprose_plant' in out
old_scrape()
rc_old, out_old = run()
seen_old = 'zz_seedprose_plant' in out_old
row("K6 plant + sub CODE (control)", "new=NO  old=NO ",
    f"new={'YES' if seen_new else 'NO '} old={'YES' if seen_old else 'NO '}",
    "a real reference still seeds -- the `;` is the only difference from K5")

restore()
rc, out = run()
print()
print(f"restored: gate rc={rc}, {'clean' if rc == 0 else 'NOT CLEAN'}")
for p in originals:
    assert open(p).read() == originals[p], f"{p} not restored!"
print("all three files byte-identical to their originals")
print(f"\n{len(rows)-fails}/{len(rows)} knife rows EXACT")
sys.exit(1 if fails else 0)
