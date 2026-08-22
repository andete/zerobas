#!/usr/bin/env python3
"""D-SEEDHOLE2 falsification for the RESIDENT-ABI seed set (fix 6).

K1/K2 knife the new ABI arm itself (its own floor/resolve asserts must catch each).
K3..K7 knife the SWEEP with a planted dead span in basic/poke.asm.

🔴 K4 IS THE DISCRIMINATOR and it is the real-world shape: the same name, called
from sub/ CODE, WITH a sub-local definition -- exactly how sub/fatprim.asm's
`call fat_read_fat_sector` kept main's callerless shim alive. K6/K7 are the green
controls that say the fix removed the sub/ scrape and NOTHING else: a tools/
string lookup still seeds, and the ABI arm really does seed.

⚠️ No ROM is built. The sweep reads SOURCES; the .sym files only decorate a
finding with an address. Restore is by WRITING THE BYTES BACK (never cp/copy2).
"""
import os, subprocess, sys

TOOL = 'tools/check_dead_code.py'
POKE = 'basic/poke.asm'
BEEP = 'sub/beep.asm'
ABI  = 'sub/basic-resident-abi.inc'
TOOLPY = 'tools/gen_math_coeffs.py'
SYMS = ['build/basic-reloc.sym', 'build/sub.sym']

PLANT = """
; --- zz_seedhole_plant: D-SEEDHOLE2 falsification plant, never shipped ------
zz_seedhole_plant:
                ld      a,1
                ret
"""
FILES = (TOOL, POKE, BEEP, ABI, TOOLPY)
originals = {p: open(p).read() for p in FILES}


def restore():
    for p, txt in originals.items():
        open(p, 'w').write(txt)          # WRITE THE BYTES, never cp/copy2


def run():
    r = subprocess.run([sys.executable, TOOL, *SYMS], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


NEW_SEEDS = """    abi = resident_abi_seeds(m)
    _assert_sub_resolves_locally(m, s, abi)
    m_seeds = {'init'} | abi | (set(m.nodes) & external_names(['tools']))"""
OLD_SEEDS = """    m_seeds = {'init'} | (set(m.nodes) & external_names(['sub', 'tools']))"""


def old_scrape():
    """Put back the PRE-slice seed set (scrape sub/ as well, no escape guard)."""
    s = originals[TOOL]
    assert s.count(NEW_SEEDS) == 1, s.count(NEW_SEEDS)
    open(TOOL, 'w').write(s.replace(NEW_SEEDS, OLD_SEEDS))


rows, fails = [], 0


def row(name, want, got, note=""):
    global fails
    ok = want == got
    fails += not ok
    rows.append((name, want, got, ok, note))
    print(f"{'EXACT' if ok else 'MISS '}  {name:38s} want={want:22s} got={got:22s} {note}")


def plant_seen(out):
    """A finding in the MAIN build only -- the sub build may carry its own noise."""
    return '[main] zz_seedhole_plant' in out


def both_scrapers(setup, label, want, note):
    restore(); setup()
    _, out_new = run()
    new = plant_seen(out_new)
    old_scrape(); setup_again = setup
    _, out_old = run()
    old = plant_seen(out_old)
    row(label, want, f"new={'YES' if new else 'NO '} old={'YES' if old else 'NO '}", note)


# ---- K1: the ABI import loses its equates ---------------------------------
restore()
open(ABI, 'w').write("; every equate removed by K1\n")
rc, out = run()
row("K1 ABI import emptied", "rc=1 floored",
    f"rc={rc} {'floored' if 'floor' in out or 'imports' in out else 'NOT CAUGHT'}",
    "an ABI arm gutted to nothing must not read as `no seeds needed`")

# ---- K2: an ABI name that is not a main label -----------------------------
restore()
open(ABI, 'w').write(originals[ABI].replace('fp_add equ', 'zz_not_a_label equ'))
rc, out = run()
row("K2 ABI names a non-label", "rc=1 unresolved",
    f"rc={rc} {'unresolved' if 'does not resolve' in out else 'NOT CAUGHT'}",
    "a renamed resident routine must fail loudly, not shrink the seed set")

# ---- K3: a planted dead span, no mention anywhere -------------------------
both_scrapers(lambda: open(POKE, 'w').write(originals[POKE] + PLANT),
              "K3 plant, no mention", "new=YES old=YES",
              "the plant is genuinely dead under BOTH -- this is what makes K4 readable")

# ---- K4: THE DISCRIMINATOR -- sub CODE call + a SUB-LOCAL definition -------
def _k4():
    open(POKE, 'w').write(originals[POKE] + PLANT)
    open(BEEP, 'w').write(originals[BEEP] +
                          "\n                call    zz_seedhole_plant\n"
                          "zz_seedhole_plant:\n                ret\n")
both_scrapers(_k4, "K4 sub CODE + sub-local def", "new=YES old=NO ",
              "<- the whole slice: the sub call resolves SUB-LOCALLY and no longer seeds main")

# ---- K5: sub CODE call with NO sub-local definition -> the escape guard ----
restore()
open(POKE, 'w').write(originals[POKE] + PLANT)
open(BEEP, 'w').write(originals[BEEP] + "\n                call    zz_seedhole_plant\n")
rc, out = run()
row("K5 sub CODE, NOT sub-resolvable", "rc=1 escape",
    f"rc={rc} {'escape' if 'resolves to neither' in out else 'NOT CAUGHT'}",
    "the standing control: dropping the sub/ scrape is only safe while this holds")

# ---- K6: green control -- a tools/ STRING lookup still seeds ---------------
def _k6():
    open(POKE, 'w').write(originals[POKE] + PLANT)
    open(TOOLPY, 'w').write(originals[TOOLPY] + "\nZZ = 'zz_seedhole_plant'\n")
both_scrapers(_k6, "K6 tools/ string lookup (control)", "new=NO  old=NO ",
              "tools/ still seeds -- the fix removed sub/ and nothing else")

# ---- K7: green control -- the ABI arm really seeds ------------------------
def _k7():
    open(POKE, 'w').write(originals[POKE] + PLANT)
    open(ABI, 'w').write(originals[ABI] + "zz_seedhole_plant equ 07FFFH\n")
both_scrapers(_k7, "K7 named in the ABI import (control)", "new=NO  old=NO ",
              "without this, `we dropped sub/` is indistinguishable from `we seed nothing`")

restore()
rc, out = run()
print()
print(f"restored: gate rc={rc}, {'clean' if rc == 0 else 'NOT CLEAN'}")
for p in originals:
    assert open(p).read() == originals[p], f"{p} not restored!"
print(f"all {len(originals)} files byte-identical to their originals")
print(f"\n{len(rows)-fails}/{len(rows)} knife rows EXACT")
sys.exit(1 if fails else 0)
