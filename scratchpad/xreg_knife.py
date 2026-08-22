#!/usr/bin/env python3
"""K-XR1 — the one knife D-XREG needed, and the draft that taught nothing.

docs/spec-basic-dupspan2.md §6 filed a suspicion: check_tenant_closure.py may be
BLIND to a cross-region `equ` alias, because D-PINDATA's rule filters `equ` names
as VALUES rather than LOCATIONS. If that were true, 46 B of this carve would be
ungated and the slice could not stand.

So: alias the ONE label scratchpad/crossreg_probe.py calls FATAL -- `affn_found`,
a basic/float-arith.asm exit moved into page 1, where a page-1 tenant has main
page 1 switched OUT -- and require `make basic-reloc` to go RED.

🔴 DRAFT 1 WENT RED AND TAUGHT NOTHING, and that is why the widening below is
part of the knife. `jr nz,affn_found` cannot reach $6760 from $33xx, so PASMO
stopped the build on a relative-jump range error before the gate ever ran. Red
read as success and the subject was untouched. **A knife that reddens through a
different mechanism than the one under test has not been run.** Widening the
caller is also what a real carve does, so the knife is now the carve plus the
hazard rather than the hazard alone.

Draft 2's answer, which is the slice's licence to ship the other ten aliases:

    FAIL: page-1 escapes in the tenant's resident closure ...
    affn_found = 6739  <- called

⚠️ RESTORE BY WRITING THE BYTES BACK, never shutil.copy2 (it preserves mtime and
make then rebuilds nothing), and assert the restore landed. The final
`git diff --stat` makes "the source came back" a READING.
"""
import re, subprocess, sys, os
S = os.environ.get("S", ".")      # where the make log lands
P = "basic/float-arith.asm"
ORIG = open(P).read()
# ⚠️ DRAFT 1 OF THIS KNIFE WENT RED FOR THE WRONG REASON AND TAUGHT NOTHING.
# `jr nz,affn_found` cannot reach $6760 from $33xx, so pasmo stopped the build
# before check_tenant_closure.py ever ran -- red, and not a word about the gate.
# The widening is part of the knife because it is part of the CARVE: a real
# cross-region alias has to assemble before anything else can judge it.
OLD = """                jr      nz,affn_found
                inc     hl
                inc     b
                ld      a,b
                cp      15
                jr      nz,affn_lp
                scf
                ret
affn_found:
                ld      a,b
                or      a
                ret"""
NEW = """                jp      nz,affn_found
                inc     hl
                inc     b
                ld      a,b
                cp      15
                jr      nz,affn_lp
                scf
                ret
; K-XR1 KNIFE (not for shipping): a LOW label aliased onto a PAGE-1 address.
; A page-1 tenant runs with main page 1 switched OUT, so any tenant that reaches
; here now jumps into bytes that are not mapped.  scratchpad/crossreg_probe.py
; says this one IS reached; the closure gate must say so too.
affn_found      equ     cal_srv_ret"""
assert OLD in ORIG
try:
    open(P, "w").write(ORIG.replace(OLD, NEW))
    subprocess.run(["rm", "-rf", "build"], check=True)
    r = subprocess.run(["make", "basic-reloc"], capture_output=True, text=True)
    open(f"{S}/knife_cross.out", "w").write(r.stdout + r.stderr)
    print(f"  make basic-reloc rc={r.returncode}")
    for line in (r.stdout + r.stderr).split("\n"):
        if any(k in line for k in ("FAIL", "ESCAPE", "affn_found", "closure",
                                   "OK:", "tenant")):
            print("   ", line.strip()[:150])
finally:
    open(P, "w").write(ORIG)                 # WRITE THE BYTES BACK, never copy2
    assert open(P).read() == ORIG
    subprocess.run(["rm", "-rf", "build"], check=True)
print("  source restored:",
      subprocess.run(["git", "diff", "--stat", "--", P],
                     capture_output=True, text=True).stdout.strip() or "CLEAN")
