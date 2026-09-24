#!/usr/bin/env python3
r"""D-PLAYBACK (2026-09-24) — what does MUSICF read on the statement right after PLAY?

TODO's D-PLAYWIN item measured the SHAPE of the reference's PLAY(n) start-up
transient but left its rule "still unnamed". This reads the documented
work-area cell MUSICF (`PEEK(&HFB3F)`, clean-room readable) alongside
`PLAY(0)`, on the very next statement, in both orders.

Measured twice, byte-identical, refcache OFF:

  case                           vg8020       zb
  empty: PEEK then PLAY(0)       7 -1         0 0
  empty: PLAY(0) then PEEK       7 -1         0 0
  empty: PLAY(0..3) then PEEK    0 -1 -1      0 0 0
  note: PEEK then PLAY(0)        7 -1         1 -1
  nothing: PEEK then PLAY(0)     0 0          0 0

-> the reference marks ALL THREE voices at every PLAY, even `PLAY""`, and its
interrupt clears the idle ones within a statement or two (the third row reads
later and has already cleared). zerobas marks only the voices it was given.
The `nothing` row is the control: the resting state is a shared real zero.

Informational, one row per case, per-side values -- NO-VERDICT by design; the
rows it characterises are pinned through playfn_fixture_probe.
"""
import os, re, sys
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "probes", "lib"))
sys.path.insert(0, os.path.join(_R, "probes", "basic"))
import omsx_repl

REF = "Philips_VG_8020"
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
CASES = [
    ("empty: PEEK then PLAY(0)", 'PLAY""', 'A=PEEK(&HFB3F):B=PLAY(0)', 'A;B'),
    ("empty: PLAY(0) then PEEK", 'PLAY""', 'B=PLAY(0):A=PEEK(&HFB3F)', 'A;B'),
    ("empty: PLAY(0..3) then PEEK", 'PLAY""', 'B=PLAY(0):C=PLAY(1):A=PEEK(&HFB3F)', 'A;B;C'),
    ("note: PEEK then PLAY(0)", 'PLAY"L1C"', 'A=PEEK(&HFB3F):B=PLAY(0)', 'A;B'),
    ("nothing: PEEK then PLAY(0)", '', 'A=PEEK(&HFB3F):B=PLAY(0)', 'A;B'),
]


def run(machine, setup, capture, show):
    prog = ["10 ON ERROR GOTO 100"]
    line = (setup + ":" if setup else "") + capture
    prog += [f"20 {line}", f"30 PRINTCHR$(35);{show};CHR$(35):END",
             "100 PRINTCHR$(35);CHR$(69);ERR;CHR$(35)", "RUN"]
    raw = omsx_repl.run_case(machine, "direct", prog) or ""
    f = re.findall(r"#([^#]*)#", raw)
    return " ".join(f[-1].split()) if f else "<NO OUTPUT>"


print(f"{'case':30} {'vg8020':12} {'zb':12}")
for name, s, c, show in CASES:
    r = run(REF, s, c, show)
    z = run(ZB, s, c, show)
    print(f"{name:30} {r:12} {z:12}", flush=True)
