#!/usr/bin/env python3
"""D-KWCASOR: the ONE run that separates the two remaining causes for "the VG-8020
does not read the tape fixture".

  (a) the FIXTURE is built to zerobas's reading of the .cas format and a real BIOS
      wants something else  -> a finding about the FORMAT, worth more than the word
  (b) the VG-8020's tape PATH does not work in this rig

Feed the reference a tape ZEROBAS ITSELF WROTE. If it reads that, (a). If it reads
nothing, (b) — and the fixture is exonerated either way.

  step 1  zb records:  cassetteplayer new {wav}, type the program, CSAVE"ZQ"
  step 2  zb re-reads that wav       -- the CONTROL: the tape must be readable AT ALL
  step 3  vg8020 reads the same wav  -- the subject

⚠️ Boot per case with its own mount: the TAPE POSITION survives a case.
"""
import os, re, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides

tmp = tempfile.mkdtemp(prefix="kwcasor_")
wav = os.path.join(tmp, "zbwrote.wav")

def run(side, lines, prologue, gap=60.0):
    cfg = probe_sides.sides(side)[side]
    caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + lines)],
                               batch=False, reset=(), boot=cfg["boot"],
                               step=5.0, cap_gap=gap, timeout=900.0,
                               prologue=prologue)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return " | ".join(r.strip() for r in rows if r.strip())

# step 1 -- zerobas WRITES a tape
scr = run("zb", ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30', 'PRINT"[W9]"'],
          (f"cassetteplayer new {{{wav}}}",), gap=90.0)
size = os.path.getsize(wav) if os.path.exists(wav) else -1
print("step 1  zb CSAVE -> %d WAV bytes" % size)
print("        screen=%s" % scr[-90:])

# step 2 -- zerobas READS it back (the control: is this tape readable at all?)
scr = run("zb", ['NEW', 'CLOAD"ZQ"'], (f"cassetteplayer {{{wav}}}",), gap=90.0)
print("step 2  zb re-reads its own tape")
print("        screen=%s" % scr[-90:])

# step 3 -- the REFERENCE reads the same tape
scr = run("vg8020", ['NEW', 'CLOAD"ZQ"'], (f"cassetteplayer {{{wav}}}",), gap=90.0)
print("step 3  vg8020 reads the SAME tape")
print("        screen=%s" % scr[-90:])
