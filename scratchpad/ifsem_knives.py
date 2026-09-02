#!/usr/bin/env python3
r"""D-IFSEM knives — does the new gate actually catch the defect it was written
for, and does it catch a WRONG fix as well as no fix?

🔴 EVERY ARM HASHES build/zerobas-main-eu.rom AND REFUSES IF IT DID NOT MOVE.
[[a-knife-can-be-inert-because-the-build-did-not-happen]]
"""
import hashlib, os, re, subprocess, sys

SRC, ROM = "basic/interp.asm", "build/zerobas-main-eu.rom"

ARMS = {
  # K-IF1: the ORIGINAL flat scan -- stop at the first ELSE, no nesting count.
  "K-IF1": ("""                ld      b,0                 ; nested-IF depth
ifs_lp:
                ld      a,(hl)
                or      a
                ret     z                   ; end of line -> no ELSE for us
                cp      ELSE_TOKEN
                jr      z,ifs_else
                cp      IF_TOKEN
                jr      nz,ifs_step
                inc     b                   ; a nested IF claims the next ELSE
ifs_step:
                call    tok_skip            ; token-aware: quotes/REM/DATA/floats
                jr      ifs_lp
ifs_else:
                ld      a,b
                or      a
                jr      nz,ifs_nested
                ld      a,ELSE_TOKEN        ; the caller tests A -- restore it
                ret
ifs_nested:
                dec     b                   ; this ELSE belongs to a nested IF
                jr      ifs_step
""", """                ld      c,ELSE_TOKEN
                jr      tok_skip_to
""", {"n.dangle", "n.after", "n.outerelse", "n.outerelse2"}),

  # 🎯 K-IF2: THE WRONG FIX. "A false IF ends the LINE" -- fits n.dangle and
  # n.after perfectly and fails only on the rows that separate the two rules.
  # If the gate cannot tell this from the right fix, its row set is too thin.
  "K-IF2": ("""                cp      ELSE_TOKEN
                jr      z,ifs_else
                cp      IF_TOKEN
                jr      nz,ifs_step
                inc     b                   ; a nested IF claims the next ELSE
""", """                cp      ELSE_TOKEN
                jr      z,ifs_else
                cp      IF_TOKEN
                jr      nz,ifs_step
                ret                         ; PLANT: a nested IF ends the line
""", {"n.outerelse", "n.outerelse2", "d.depth2", "d.depth2b", "e.nestelse",
      "e.nestelse2"}),
}

def rom_hash():
    return hashlib.sha1(open(ROM, "rb").read()).hexdigest()[:12] if os.path.exists(ROM) else "ABSENT"

subprocess.run("rm -rf build && make repack-machine > /dev/null 2>&1", shell=True)
base = rom_hash()
print(f"baseline rom={base}")
if base == "ABSENT":
    sys.exit("baseline ROM absent -- guard cannot arm")

for tag, (old, new, expect) in ARMS.items():
    src = open(SRC).read()
    if src.count(old) != 1:
        print(f"{tag}: PLANT SITE NOT UNIQUE ({src.count(old)}) -- ARM NOT RUN"); continue
    open(SRC, "w").write(src.replace(old, new))
    try:
        subprocess.run("rm -rf build", shell=True, check=True)
        b = subprocess.run("make repack-machine", shell=True, capture_output=True, text=True)
        if b.returncode != 0:
            print(f"\n=== {tag}: BUILD FAILED -- arm inert, not a null result")
            print(b.stderr[-400:]); continue
        h = rom_hash()
        if h == base:
            print(f"\n=== {tag}: 🔴 ROM {h} == baseline -- ARM INERT, verdict WITHHELD"); continue
        out = subprocess.run("python3 probes/basic/basic_probe_ifsem.py --gate",
                             shell=True, capture_output=True, text=True,
                             env={**os.environ, "ZEROBAS_REFCACHE": "0"})
        m = re.search(r"^DIFF: \d+/\d+\s+(.*)$", out.stdout, re.M)
        moved = set((m.group(1) if m else "").split())
        ctl = [l for l in out.stdout.splitlines()
               if l.startswith("c.") and l.rstrip().endswith("DIFF")]
        print(f"\n=== {tag}  rom={h}  gate rc={out.returncode}")
        print(f"    moved={sorted(moved)}")
        print(f"    expected={sorted(expect)}  "
              f"{'✅ MATCH' if moved == expect else '⚠️ DIFFERS (superset is fine if it CATCHES)'}")
        print(f"    gate RED: {'✅' if out.returncode else '🔴 NO -- the gate is blind to this'}")
        print(f"    controls still green: {'✅' if not ctl else '🔴 ' + str(ctl)}")
    finally:
        open(SRC, "w").write(src)

subprocess.run("rm -rf build && make repack-machine > /dev/null 2>&1", shell=True)
print(f"\nrestored rom={rom_hash()}  (baseline {base})")
