#!/usr/bin/env python3
r"""D-LSETTM knives — FALSIFY BY PLANTING.

Three arms. Each reverts one half of the fix (or blinds the probe), rebuilds
CLEAN, and re-runs the six d.* rows plus `n.ctl` (a POSITIVE CONTROL that must
stay green in every arm -- if it moves, the arm broke the build, not the rule).

🔴 EVERY ARM HASHES build/basic.rom AND REFUSES IF IT DID NOT MOVE. A knife that
reports "moved 0 rows" because the build never happened is indistinguishable
from an arm that legitimately found nothing.
[[a-knife-can-be-inert-because-the-build-did-not-happen]]
"""
import hashlib, os, re, subprocess, sys

ROWS = "d.miss,d.misscol,d.rmiss,d.num,d.rnum,d.numvar,n.ctl"
FIELD, LRVAR = "basic/field.asm", "probes/basic/basic_probe_lrvar.py"
ROM = "build/zerobas-main-eu.rom"   # the artifact the machine actually boots

ARMS = {
  # revert the RETARGET only -> the three TYPE rows must move, the miss rows must not
  "K-LT1": (FIELD, "jp      nc,type_mismatch_error", "jp      nc,stmt_error",
            {"d.num", "d.rnum", "d.numvar"}),
  # remove req_operand -> the three MISSING rows must move, the type rows must not
  "K-LT2": (FIELD, "                call    req_operand         ; `LSET A$=` / `= :` -> ERR 24\n",
            "", {"d.miss", "d.misscol", "d.rmiss"}),
  # blind the PROBE's alphabet -> the three miss rows must go RED AND LOUD,
  # i.e. `[PROBE CANNOT READ THIS SCREEN...]`, NOT the old silent `....`.
  "K-LT3": (LRVAR, '"Missing operand", ', "",
            {"d.miss", "d.misscol", "d.rmiss"}),
}

def rom_hash():
    return hashlib.sha1(open(ROM, "rb").read()).hexdigest()[:12] if os.path.exists(ROM) else "ABSENT"

def run(tag, path, old, new, expect):
    global base_hash
    src = open(path).read()
    if src.count(old) != 1:
        print(f"{tag}: PLANT SITE NOT UNIQUE ({src.count(old)}) -- arm not run"); return
    open(path, "w").write(src.replace(old, new))
    try:
        subprocess.run("rm -rf build", shell=True, check=True)
        b = subprocess.run("make repack-machine", shell=True,
                           capture_output=True, text=True)
        if b.returncode != 0:
            print(f"{tag}: BUILD FAILED -- arm inert, not a null result")
            print(b.stderr[-600:]); return
        h = rom_hash()
        # 🔴 ARMED, NOT DECORATIVE. The first cut of this runner named a ROM that
        # does not exist, printed `rom=ABSENT` three times and carried on -- the
        # exact "inert knife" this guard is for, rebuilt as a guard that cannot
        # fire. An arm whose ROM is absent or unmoved is NOT a null result.
        # ⚠️ THE EXPECTATION IS PER-ARM. K-LT1/K-LT2 patch the ASSEMBLY, so a
        # ROM equal to the baseline means the build did not happen -> INERT.
        # K-LT3 patches the PROBE, so its ROM *must* be unchanged; demanding
        # movement there would fire on a correct arm -- a guard that reddens a
        # good run is worse than no guard.
        rom_moved = (h != base_hash)
        if h == "ABSENT" or rom_moved != (path != LRVAR):
            print(f"{tag}: 🔴 ROM {h} vs baseline {base_hash} "
                  f"(moved={rom_moved}, expected moved={path != LRVAR}). "
                  f"ARM INERT, verdict WITHHELD.")
            return
        out = subprocess.run(
            f"python3 probes/basic/basic_probe_lrvar.py --only {ROWS} --sides cf3300,zb",
            shell=True, capture_output=True, text=True, env={**os.environ, "ZEROBAS_REFCACHE": "0"})
        txt = out.stdout
        moved = {m.group(1) for m in re.finditer(r"^DIFF\s+(\S+)", txt, re.M)}
        loud  = "PROBE CANNOT READ THIS SCREEN" in txt
        ctl_ok = re.search(r"^ok\s+n\.ctl", txt, re.M) is not None
        print(f"\n=== {tag}  rom={h}  moved={sorted(moved)}")
        print(f"    expected={sorted(expect)}  "
              f"{'✅ MATCH' if moved == expect else '🔴 MISMATCH'}")
        print(f"    n.ctl green: {'✅' if ctl_ok else '🔴 NO -- arm broke the build'}")
        if tag == "K-LT3":
            print(f"    loud refusal fired: {'✅' if loud else '🔴 NO -- silent drop is back'}")
    finally:
        open(path, "w").write(src)

subprocess.run("rm -rf build && make repack-machine > /dev/null 2>&1", shell=True)
base_hash = rom_hash()
print(f"baseline rom={base_hash}")
if base_hash == "ABSENT":
    sys.exit("baseline ROM absent -- cannot arm the build-happened guard")
for tag, (path, old, new, expect) in ARMS.items():
    run(tag, path, old, new, expect)
subprocess.run("rm -rf build && make repack-machine > /dev/null 2>&1", shell=True)
print(f"\nrestored rom={rom_hash()}")
