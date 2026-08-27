#!/usr/bin/env python3
"""SENTINEL-vs-FIXED-TIME differential — the gate the sentinel capture needs.

Capturing when the program says it is done, instead of at a guessed emulated
time, CHANGES WHAT IS MEASURED: today both machines are sampled at the same
emulated instant; with a sentinel each is captured at its own completion. That is
arguably more correct -- final states rather than an arbitrary shared moment --
but *arguably* is not a licence. So: byte-identical or it does not ship.

🔴 THE LOAD-BEARING CONTROL IS "DID THE SENTINEL ACTUALLY FIRE?", NOT THE
AGREEMENT. openMSX drops a callback that errors WITHOUT A WORD. If the watchpoint
body is malformed -- `$::wp_last_value` not being the right variable, `$__f` not
resolving in that scope -- the sentinel never fires, the scheduled FALLBACK
captures instead, and this differential compares the fallback path TO ITSELF and
reports a perfect 100% agreement while measuring nothing at all. Every row
therefore asserts `sentinel.N` was emitted; a row that agrees WITHOUT it is
scored NOT MEASURED, never PASS.
"""
from __future__ import annotations

import os
import sys

ROOT = "/Users/joost/projects/zerobas"
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                   # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW", "CLS")),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW", "CLS")),
    "zb":     dict(machine=ZB, boot=8.0, reset=("NEW", "CLS")),
}

SENT_ADDR, SENT_VAL = 0xE000, 255
BOTH = ("vram_segs", [(0x0000, 0x1800), (0x2000, 0x1800)])

# (label, step, capture, body-without-sentinel). The sentinel POKE is inserted
# just before the final hold/END line, so it fires when the WORK is done.
POKE_LINE = f"POKE&H{SENT_ADDR:X},{SENT_VAL}"

# Lines are EXPLICITLY NUMBERED. 🔴 A first cut auto-numbered them, which
# renumbered `ON ERROR GOTO 900`'s handler to line 40 -- so line 900 did not
# exist, the error aborted with "Undefined line number", and the program never
# reached its POKE. The sentinel then correctly reported NOT MEASURED, which is
# the guard working: it was MY case that was broken, not the mechanism.
# `{P}` marks where the completion POKE goes -- after the work, before the hold.
# ⚠️ `{P:n}` CARRIES ITS OWN LINE NUMBER. A first cut emitted the POKE as line 40
# next to a `40 GOTO40` hold -- the same number twice, so the hold REPLACED the
# POKE and the sentinel could never fire. Caught by reading the built program
# before running it; it would otherwise have surfaced as a mystery NOT MEASURED.
CASES = [
    ("circle", 90.0, BOTH,
     ["10 SCREEN2", "20 CIRCLE(128,96),80,15", "{P:30}", "40 GOTO40"]),
    ("paint",  90.0, BOTH,
     ["10 SCREEN2", "20 CIRCLE(128,96),60,15:PAINT(128,96),15", "{P:30}",
      "40 GOTO40"]),
    ("flood",  90.0, BOTH,
     ["10 SCREEN2", "20 PAINT(128,96),15", "{P:30}", "40 GOTO40"]),
    ("text",   20.0, "screen",
     ["10 ONERRORGOTO900", "15 SCREEN2", "20 CIRCLE(50,50),",
      '30 R=POINT(30,50):SCREEN0:CLS:PRINT"[";ERR;R;"]"', "{P:40}", "50 END",
      '900 R=POINT(30,50):SCREEN0:CLS:PRINT"[";ERR;R;"]"', "{P:910}",
      "920 END"]),
]


def build(body, with_sentinel):
    """Substitute each `{P:n}` with the completion POKE at line n, or drop it on
    the fixed-time side -- so the two programs differ ONLY by that statement."""
    out = []
    for ln in body:
        if ln.startswith("{P:"):
            if with_sentinel:
                out.append(f"{ln[3:-1]} {POKE_LINE}")
        else:
            out.append(ln)
    return out


def run(side, step, cap, body, sentinel):
    cfg = SIDES[side]
    prog = build(body, sentinel)
    spec = ("direct", list(cfg["reset"]) + prog + ["RUN"])
    so: dict = {}
    kw = dict(reset=(), boot=cfg["boot"], step=step, cap_gap=8.0, capture=cap,
              timeout=600.0, verify_delivery=False)
    if sentinel:
        kw["sentinel"] = (SENT_ADDR, SENT_VAL)
        kw["settle_out"] = so
    raw = omsx_repl.run_batch(cfg["machine"], [spec], **kw)[0]
    fired = so.get("sentinel", {}).get(0)
    return raw, fired


def main():
    sides = [a for a in sys.argv[1:] if a in SIDES] or list(SIDES)
    only = [a[5:] for a in sys.argv[1:] if a.startswith("only=")]
    labels = only[0].split(",") if only else None
    print(f"{'case':<8} {'side':<8} {'fixed-time':>11} {'sentinel':>10} "
          f"{'fired@':>9}  verdict")
    npass = nfail = nvac = 0
    for label, step, cap, body in CASES:
        if labels and label not in labels:
            continue
        for side in sides:
            fixed, _ = run(side, step, cap, body, sentinel=False)
            sent, fired = run(side, step, cap, body, sentinel=True)
            same = fixed is not None and fixed == sent
            if fired is None:
                nvac += 1
                v = "🔴 NOT MEASURED — sentinel never fired (callback dropped?)"
            elif same:
                npass += 1
                v = "✅ identical"
            else:
                nfail += 1
                d = (sum(1 for x, y in zip(fixed, sent) if x != y)
                     if fixed and sent and len(fixed) == len(sent) else "?")
                v = f"🔴 DIFFERS ({d} chars)"
            fl = f"{fired:.3f}" if fired is not None else "-"
            print(f"{label:<8} {side:<8} {str(len(fixed) if fixed else None):>11} "
                  f"{str(len(sent) if sent else None):>10} {fl:>9}  {v}")
    print(f"\n{npass} identical, {nfail} differ, {nvac} NOT MEASURED")
    print("A row that agrees WITHOUT its sentinel firing proves nothing: both "
          "sides\nwould be the scheduled fallback, i.e. the old path compared to "
          "itself.")
    return 1 if (nfail or nvac) else 0


if __name__ == "__main__":
    raise SystemExit(main())
