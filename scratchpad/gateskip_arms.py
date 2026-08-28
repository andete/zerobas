#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-GATESKIP falsification — a skip that cannot REFUSE is worthless.

`make gates` skips 23 emulator targets when it can prove they cannot move. The
whole value of that proof is the cases where it says NO, so each arm below
PLANTS a reason to refuse and requires the refusal.

🎯 THESE CALL `run_gates.inert_against_last_green()` ITSELF, not a copy of its
rule. A re-implementation that agreed with a broken original would be worse than
no arm at all. Arm A1 additionally runs the REAL `make gates` end to end, so the
wiring between that function and main() is covered too.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit.
"""
import atexit, importlib.util, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
spec = importlib.util.spec_from_file_location("rg", "tools/run_gates.py")
RG = importlib.util.module_from_spec(spec)
sys.argv = ["run_gates.py"]
spec.loader.exec_module(RG)

fails = []


def arm(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
    if not cond:
        fails.append(name)


def decide():
    ok, why = RG.inert_against_last_green()
    return ok, why


# --- A0 GREEN CONTROL: nothing changed -> it DOES skip ---------------------
ok, why = decide()
arm("A0 unchanged tree -> SKIP (green control; every refusal below needs this)",
    ok, why)
if not ok:
    print("\n🔴 the control failed, so no refusal below is a reading. "
          "Run `make gates-full` first to record a green baseline.")
    raise SystemExit(2)

# --- A1 the real `make gates`, end to end ---------------------------------
p = subprocess.run(["make", "gates"], capture_output=True, text=True)
out = p.stdout
arm("A1 the REAL `make gates` skipped and SAID SO",
    "EMULATOR TARGET(S) NOT RUN" in out and "STATIC TIER ONLY" in out,
    f"rc={p.returncode}")
arm("A1b ...and did NOT print a full-battery green line",
    "GATES: 44/44 green\n" not in out)

# --- A2 one byte of a probe source ----------------------------------------
VICTIM = "probes/lib/omsx_repl.py"
orig = open(VICTIM, "rb").read()
restore = lambda: open(VICTIM, "wb").write(orig)
atexit.register(restore)
try:
    open(VICTIM, "wb").write(orig + b"\n# gateskip arm (restored on exit)\n")
    ok, why = decide()
    arm("A2 one comment added to a probe source -> REFUSE", not ok, why)
finally:
    restore()
    atexit.unregister(restore)
arm("A2b restoring the source restores the skip (control)", decide()[0])

# --- A3 one byte of a ROM the battery fingerprints -------------------------
# build/disk.rom in particular: it was NOT in IMAGES until this slice, so this
# arm is the one that says the hole is actually closed.
for VROM in ("build/disk.rom", "build/zerobas-main-eu.rom"):
    rom = open(VROM, "rb").read()
    rrestore = lambda r=rom, v=VROM: open(v, "wb").write(r)
    atexit.register(rrestore)
    try:
        open(VROM, "wb").write(rom[:-1] + bytes([rom[-1] ^ 0xFF]))
        ok, why = decide()
        arm(f"A3 one byte of {VROM} -> REFUSE", not ok, why)
    finally:
        rrestore()
        atexit.unregister(rrestore)
    arm(f"A3b restoring {VROM} restores the skip (control)", decide()[0])

# --- A4 no baseline on record ----------------------------------------------
rec = RG.LAST_GREEN
saved = open(rec, "rb").read()
r4 = lambda: open(rec, "wb").write(saved)
atexit.register(r4)
try:
    os.unlink(rec)
    ok, why = decide()
    arm("A4 no green battery on record -> REFUSE", not ok, why)
    # and a record from a DIFFERENT tree must not vouch for this one
    with open(rec, "w") as fh:
        json.dump({"images": ["deadbeef"] * 4, "sources": "0" * 16,
                   "when": "1970-01-01"}, fh)
    ok, why = decide()
    arm("A4b a baseline from another tree -> REFUSE", not ok, why)
finally:
    r4()
    atexit.unregister(r4)
arm("A4c restoring the record restores the skip (control)", decide()[0])

print()
print("ALL PASS — the skip refuses whenever it must" if not fails
      else f"🔴 {len(fails)} ARM(S) FAILED: {fails}")
raise SystemExit(1 if fails else 0)
