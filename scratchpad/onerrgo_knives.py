#!/usr/bin/env python3
r"""D-ONERRGO knives — FALSIFY BY PLANTING.

Four arms. Each reverts one piece of the fix, rebuilds CLEAN, and re-runs the
eight o.* rows plus `o.gotoctl` (which must stay GREEN in every arm: it is the
leak detector for req_lineno's other three callers).

🔴 THE ROM HASH GUARD IS ARMED, NOT DECORATIVE. D-LSETTM's first runner hashed a
ROM this build never produces, printed `rom=ABSENT` three times and carried on.
An arm whose ROM did not move from the baseline is INERT and its verdict is
withheld. [[a-knife-can-be-inert-because-the-build-did-not-happen]]
"""
import hashlib, os, re, subprocess, sys

ROWS = "o.badop,o.badstr,o.badoperl,o.bare,o.barecol,o.barerun,o.bareinh,o.gotoctl"
PROG = "basic/program.asm"
ROM  = "build/zerobas-main-eu.rom"

ARMS = {
  # (a) remove the NO-OPERAND route -> the four bare-form rows must move
  "K-OG1": ("""                or      a
                jr      z,oe_disable        ; `ON ERROR GOTO` <eol>  == GOTO 0
                cp      COLON
                jr      z,oe_disable        ; `ON ERROR GOTO :`      == GOTO 0
""", "", {"o.bare", "o.barecol", "o.barerun", "o.bareinh"}),
  # (b) remove the NOT-A-LINENO route -> the three untrapped rows must move
  "K-OG2": ("""                cp      LINENO_TOKEN
                jp      nz,oe_badop         ; present, not a line number
""", "", {"o.badop", "o.badstr", "o.badoperl"}),
  # (c) 🎯 THE SHARPEST ARM. Drop record_errline. If o.badoperl is doing real
  # work, it moves ALONE -- every other row stays green, because the message
  # and the untrapped-ness are unaffected and only ERR/ERL change.
  "K-OG3": ("                call    record_errline      ; ERRLIN := this line (ERL reads 30)\n",
            "", {"o.badoperl"}),
  # (d) abort -> trap decision: proves it is ra_abort, not raise_error_hl,
  # that makes the raise untrapped.
  "K-OG4": ("jp      ra_abort            ; PAST raise_error_hl -> never traps",
            "jp      raise_error_hl", {"o.badop", "o.badstr", "o.badoperl"}),
}

def rom_hash():
    return hashlib.sha1(open(ROM, "rb").read()).hexdigest()[:12] if os.path.exists(ROM) else "ABSENT"

subprocess.run("rm -rf build && make repack-machine > /dev/null 2>&1", shell=True)
base = rom_hash()
print(f"baseline rom={base}")
if base == "ABSENT":
    sys.exit("baseline ROM absent -- cannot arm the guard")

for tag, (old, new, expect) in ARMS.items():
    src = open(PROG).read()
    if src.count(old) != 1:
        print(f"{tag}: PLANT SITE NOT UNIQUE ({src.count(old)}) -- arm NOT run"); continue
    open(PROG, "w").write(src.replace(old, new))
    try:
        subprocess.run("rm -rf build", shell=True, check=True)
        b = subprocess.run("make repack-machine", shell=True, capture_output=True, text=True)
        if b.returncode != 0:
            print(f"\n=== {tag}: BUILD FAILED -- arm inert, NOT a null result")
            print(b.stderr[-500:]); continue
        h = rom_hash()
        if h == base:
            print(f"\n=== {tag}: 🔴 ROM {h} == baseline. ARM INERT, verdict WITHHELD.")
            continue
        out = subprocess.run(
            f"python3 probes/basic/basic_probe_onerr0.py --only {ROWS} --sides cf3300,zb",
            shell=True, capture_output=True, text=True,
            env={**os.environ, "ZEROBAS_REFCACHE": "0"})
        moved = {m.group(1) for m in re.finditer(r"^DIFF\s+(\S+)", out.stdout, re.M)}
        ctl_ok = re.search(r"^ok\s+o\.gotoctl", out.stdout, re.M) is not None
        print(f"\n=== {tag}  rom={h}  moved={sorted(moved)}")
        print(f"    expected={sorted(expect)}  {'✅ MATCH' if moved == expect else '🔴 MISMATCH'}")
        print(f"    o.gotoctl green (req_lineno not leaked): {'✅' if ctl_ok else '🔴 NO'}")
    finally:
        open(PROG, "w").write(src)

subprocess.run("rm -rf build && make repack-machine > /dev/null 2>&1", shell=True)
print(f"\nrestored rom={rom_hash()}  (baseline {base})")
