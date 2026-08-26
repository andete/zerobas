#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 4 — the two rows that could not share a batch,
plus the clause an error-scrape could not see.

* `WAIT` BLOCKS on a port condition. In tranche 1 it hung both references and
  voided every case AFTER it, which came back reading as "the references printed
  nothing". One boot per case here, so a hang costs ONE row.
* `FILES"<bad 8.3>"` — the item's second clause is *"and FILES LISTS ANYWAY"*,
  which an error scrape is structurally blind to. This one DRAWS THE SCREEN.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DSK = os.path.join(ROOT, "disk", "test720.dsk")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, diska=True),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=8.0, diska=True),
}
COLS, ROWS = 40, 24


def draw(side, scr, note=""):
    print(f"  --- {side}{note}")
    if scr is None:
        print("      <NO CAPTURE>"); return
    for r in range(ROWS):
        t = scr[r * COLS:(r + 1) * COLS].rstrip()
        if t:
            print(f"      r{r:02d} |{t}|")


def one(side, lines, step, disk):
    cfg = SIDES[side]
    return omsx_repl.run_case(cfg["machine"], "direct", lines,
                              boot=cfg["boot"], step=step,
                              diska=DSK if (disk and cfg["diska"]) else None)


def main():
    print("=== WAIT (isolated; a hang costs ONE row, not the batch) ===")
    for side in SIDES:
        # A short step: if WAIT blocks, this case alone times out.
        # 🔴 `WAIT` MUST BE THE LAST LINE. The first draft put a PRINT after it
        # and the harness's echo guard ABORTED the whole run: the reference was
        # still inside WAIT when the next line was injected, so 12 leading
        # characters were swallowed and it refused to report a reading at all.
        # That refusal IS the evidence that WAIT blocks -- but it costs every
        # later case, so the reading is taken from what follows WAIT on screen
        # (an `Ok` prompt, or nothing) rather than from a line typed after it.
        scr = one(side, ['PRINT"[BEFORE]"', "WAIT 1,0"], step=8.0, disk=False)
        draw(side, scr)
    print("\n=== WAIT control: the same fixture with no WAIT ===")
    for side in SIDES:
        draw(side, one(side, ['PRINT"[BEFORE]"'], step=8.0, disk=False))

    print("\n=== FILES with a malformed 8.3 name -- DOES IT LIST ANYWAY? ===")
    for side in ("cf3300", "zb"):
        draw(side, one(side, ['FILES"TOOLONGNAME.EXTRA"', 'PRINT"[END]"'],
                       step=8.0, disk=True))
    print("\n=== FILES control: a bare FILES, to see what a real listing is ===")
    for side in ("cf3300", "zb"):
        draw(side, one(side, ['FILES', 'PRINT"[END]"'], step=8.0, disk=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
