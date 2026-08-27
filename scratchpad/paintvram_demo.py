#!/usr/bin/env python3
"""D-PAINTVRAM closing demo -- real MSX BASIC, all three machines.

The program a user could actually type. It PAINTs, then reads the stored bytes
back with VPEEK (a BASIC statement, which is the whole point), then draws ONE
more pixel into the painted cell and asks POINT what happened to its NEIGHBOURS.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                   # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "Philips VG-8020 ": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW", "CLS")),
    "National CF-3300": dict(machine="National_CF-3300", boot=14.0,
                             reset=("", "SCREEN 0", "NEW", "CLS")),
    "zerobas         ": dict(machine=ZB, boot=8.0, reset=("NEW", "CLS")),
}

# pattern byte for (128,96) = (96\8)*256 + (128\8)*8 + (96 AND 7) = 3200 = &H0C80
# ⚠️ DIRECT mode with EXPLICIT line numbers, then RUN -- the shape
# vram_fidelity.py already uses for these three machines. "stored" mode numbers
# the lines itself (pre-numbering them made the machine store 1010/2020/... and
# the delivery guard refused the run, correctly), and the CF-3300's longer boot
# needs its reset lines injected as part of the case rather than as `reset=`.
BODY = [
    "SCREEN2",
    "PAINT(128,96),15",
    "P=VPEEK(&H0C80):C=VPEEK(&H2C80)",
    "PSET(128,96),6",
    "A=POINT(128,96):B=POINT(129,96):D=POINT(135,96)",
    'SCREEN0:PRINT"PAT=";P;"COL=";C',
    'PRINT"PSET=";A;"NEXT=";B;"LAST=";D',
    "END",
]
PROG = [f"{10 * (i + 1)} {ln}" for i, ln in enumerate(BODY)]

print("10 SCREEN2                                 ' a blank SCREEN 2")
print("20 PAINT(128,96),15                        ' flood it white")
print("30 P=VPEEK(&H0C80):C=VPEEK(&H2C80)         ' the STORED bytes for that cell")
print("40 PSET(128,96),6                          ' one more pixel, colour 6")
print("50 A=POINT(128,96):B=POINT(129,96):D=POINT(135,96)")
print("60/70 PRINT them\n")
for label, cfg in SIDES.items():
    spec = ("direct", list(cfg["reset"]) + PROG + ["RUN"])
    raw = omsx_repl.run_batch(cfg["machine"], [spec], reset=(), boot=cfg["boot"],
                              step=2.5, run_gap=90.0, cap_gap=10.0, timeout=900.0,
                              verify_delivery=False)[0]
    txt = " ".join("".join(raw).split()) if raw else "<NO OUTPUT>"
    i = txt.find("PAT=")
    print(f"  {label}  {txt[i:i + 52] if i >= 0 else txt}")
