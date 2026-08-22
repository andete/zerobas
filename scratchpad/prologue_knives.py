#!/usr/bin/env python3
"""D-PROLOGUE falsification for apparatus fix (7).

The claim: a prologue span that EMITS NOTHING cannot fall through into its
file's first label, so that label is no longer live by construction.

⚠️ THE FAILURE DIRECTION HERE IS UNDER-SEEDING -- reporting LIVE code as dead --
which is why K-P4 (a prologue that genuinely emits still confers fallthrough) and
K-P5 (the alternate-entry-point case, which the obvious generalisation breaks)
carry as much weight as the discriminator.

⚠️ No ROM is built: the sweep decides from SOURCES. Restore writes the bytes back.
"""
import os, subprocess, sys

TOOL = 'tools/check_dead_code.py'
POKE = 'basic/poke.asm'
TOOLPY = 'tools/gen_math_coeffs.py'
SYMS = ['build/basic-reloc.sym', 'build/sub.sym']

# a plant that FALLS THROUGH (no terminator), so the file's real first label
# keeps its liveness and only the plant itself is at issue
PLANT_FIRST = "\nzz_prologue_plant:\n                nop\n"
originals = {p: open(p).read() for p in (TOOL, POKE, TOOLPY)}


def restore():
    for p, txt in originals.items():
        open(p, 'w').write(txt)          # WRITE THE BYTES, never copy2


def run():
    r = subprocess.run([sys.executable, TOOL, '--report', *SYMS],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def gate():
    r = subprocess.run([sys.executable, TOOL, *SYMS], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


NEWFIX = """                if a.startswith(PROLOGUE) and not last:
                    continue
"""


def old_model():
    """Put back the pre-slice edge rule (every prologue falls through)."""
    s = originals[TOOL]
    assert s.count(NEWFIX) == 1
    open(TOOL, 'w').write(s.replace(NEWFIX, ""))


def plant_at_top(extra_prologue=""):
    """Insert the plant as poke.asm's FIRST label (its prologue is comments only)."""
    txt = originals[POKE]
    i = txt.index("do_poke:")
    open(POKE, 'w').write(txt[:i] + extra_prologue + PLANT_FIRST.lstrip('\n') + "\n" + txt[i:])


rows, fails = [], 0


def row(name, want, got, note=""):
    global fails
    ok = want == got
    fails += not ok
    rows.append(ok)
    print(f"{'EXACT' if ok else 'MISS '}  {name:44s} want={want:26s} got={got:26s} {note}")


def seen(out):
    return 'zz_prologue_plant' in out


# ---- K-P1: revert the fix -> the fat_io_open allowlist entry stops matching --
restore()
old_model()
rc, out = gate()
row("K-P1 fix reverted, allowlist canary", "rc=1 canary",
    f"rc={rc} {'canary' if 'no longer detected as dead' in out and 'fat_io_open' in out else 'NOT CAUGHT'}",
    "the allowlist IS the detector: an entry that stops matching means the sweep went blind")

# ---- K-P2: THE DISCRIMINATOR -- a dead span as the FIRST LABEL ---------------
restore(); plant_at_top()
_, out_new = run()
new = seen(out_new)
old_model()
_, out_old = run()
old = seen(out_old)
row("K-P2 plant as the FIRST label", "new=YES old=NO ",
    f"new={'YES' if new else 'NO '} old={'YES' if old else 'NO '}",
    "<- the whole slice: an empty prologue no longer keeps a first label alive")

# ---- K-P3: green control -- the same plant NOT first ------------------------
restore()
txt = originals[POKE]
open(POKE, 'w').write(txt + "\n; zz plant, not a first label\nzz_prologue_plant:\n                nop\n")
_, out_new = run()
new = seen(out_new)
old_model()
_, out_old = run()
old = seen(out_old)
row("K-P3 plant NOT first (control)", "new=YES old=YES",
    f"new={'YES' if new else 'NO '} old={'YES' if old else 'NO '}",
    "a plain dead span is reported by BOTH -- this is what makes K-P2 readable")

# ---- K-P4: SAFETY -- a prologue that EMITS still falls through ---------------
restore()
plant_at_top(extra_prologue="                nop                 ; an EMITTING prologue\n")
_, out_new = run()
new = seen(out_new)
old_model()
_, out_old = run()
old = seen(out_old)
row("K-P4 EMITTING prologue (safety)", "new=NO  old=NO ",
    f"new={'YES' if new else 'NO '} old={'YES' if old else 'NO '}",
    "over-cutting would report LIVE code dead -- the fix must not touch this")

# ---- K-P5: SAFETY -- the ALTERNATE ENTRY POINT, which is the 1227-span error -
# 🔴 DRAFT 1 OF THIS ROW WAS WRONG AND THE FIX WAS RIGHT. It put the bare label
# where poke.asm's FIRST label goes -- which is just K-P2 again, and an alias
# nothing references genuinely IS dead there. The property that matters is
# different: a bare label reached from OUTSIDE, with a real routine below it that
# is live ONLY by falling out of it. That is the shape "any empty span cannot
# fall through" destroys, and fix (7) must leave it alone.
restore()
open(POKE, 'w').write(originals[POKE] +
                      "\n; --- zz alias pair: zz_alias is SEEDED from tools/, zz_target is live\n"
                      "; ONLY by falling out of it ---------------------------------------\n"
                      "zz_alias:\n"
                      "zz_target:\n                nop\n                ret\n")
open(TOOLPY, 'w').write(originals[TOOLPY] + "\nZZ_SEED = 'zz_alias'\n")
_, out_new = run()
bad = 'zz_target' in out_new
old_model()
_, out_old = run()
bad_old = 'zz_target' in out_old
row("K-P5 alternate ENTRY POINT (safety)", "new=LIVE old=LIVE",
    f"new={'DEAD' if bad else 'LIVE'} old={'DEAD' if bad_old else 'LIVE'}",
    "zz_target is live ONLY by fallthrough out of a bare label -- the 1227-span error")

restore()
rc, out = gate()
print()
print(f"restored: gate rc={rc}, {'clean' if rc == 0 else 'NOT CLEAN'}")
for p in originals:
    assert open(p).read() == originals[p], f"{p} not restored!"
print(f"all {len(originals)} files byte-identical to their originals")
print(f"\n{len(rows)-fails}/{len(rows)} knife rows EXACT")
sys.exit(1 if fails else 0)
