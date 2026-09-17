#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-AKCM scout -- what `AUTO`, `KEY ON/OFF`, `CALL` and `MAX` can be scored ON.

These four are the remaining reachable TIER 1 evidence gaps. Two of them may not
be TIER-1-able AT ALL, and finding that out is the point:

  * `KEY ON`/`KEY OFF` were left uncovered ON PURPOSE (D-KWOSK): the obvious
    instrument, the function-key line in VRAM, has a DIFFERENT LAYOUT on the two
    machines (LINLEN 37 vs 39; the assigned string at name-table offset 922 on
    the reference only), and the first cut scored SUPPORTED on `32` from both --
    an agreement about a blank cell. `CRTCNT` ($F3B1, the documented text-row
    count) is a candidate because a DELTA across `KEY OFF`->`KEY ON` cancels any
    machine difference, exactly as `varptr_b` does for VARPTR. ⚠️ Read as a
    DELTA, never as a value: a row that reads 24 on both sides has measured a
    constant, which is the same mistake in a new cell.
  * `CALL` and `MAX` have ONE agreeing row each and NO authored form list. Before
    writing one: does either have a happy path on a bare MSX1 at all? `CALL` with
    no extension ROM may simply refuse, and `MAX` may exist only inside
    `MAXFILES` -- in which case they belong with `SET`/`IPL`/`CMD` (refused on
    both) or with `GET`/`ON`/`USING` (no bare form), NOT at TIER 0 awaiting rows.
  * `AUTO` needs its prompt read; its hazard is that it leaves the machine in
    LINE-ENTRY MODE and ate 21 following rows once.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")


def prog(*body: str) -> list[str]:
    """🔴 THE TRAP NUMBER IS DERIVED FROM THE FINAL LIST, NOT COUNTED BY HAND.
    The first cut used `10*(len(body)+2)`, which is the `END` line -- one short of
    the handler -- so every trapped case jumped to END and printed NOTHING. Eleven
    cells came back `<no reading>` and looked like two machines refusing, when it
    was this line. [[a-trap-line-pointing-at-the-success-line]]"""
    lines = ["ON ERROR GOTO @T"] + list(body) + ["END", 'PRINT"<E";ERR;">":END']
    lines[0] = "ON ERROR GOTO %d" % (10 * len(lines))   # the LAST line
    for l in lines:
        assert len(l) <= 34, (len(l), l)
        assert "@" not in l, l
    return lines


CASES = [
    # --- KEY ON / OFF: is CRTCNT the observable? -----------------------------
    ("k0_on",    prog("KEY ON", 'PRINT"<";PEEK(&HF3B1);">"')),
    ("k1_off",   prog("KEY OFF", 'PRINT"<";PEEK(&HF3B1);">"')),
    ("k2_delta", prog("KEY OFF", "A=PEEK(&HF3B1)", "KEY ON",
                      'PRINT"<";PEEK(&HF3B1)-A;">"')),
    # a second candidate: does the usable text window move with it?
    ("k3_csr",   prog("KEY OFF", "LOCATE 0,23", 'PRINT"<";CSRLIN;">"')),
    ("k4_csron", prog("KEY ON", "LOCATE 0,23", 'PRINT"<";CSRLIN;">"')),
    # --- CALL: is there a happy path on a bare MSX1? -------------------------
    ("c0_call",  prog("CALL FOO", 'PRINT"<CALLOK>"')),
    ("c1_under", prog("_FOO", 'PRINT"<UNDEROK>"')),
    ("c2_bare",  prog("CALL", 'PRINT"<BAREOK>"')),
    # --- MAX: does it exist outside MAXFILES? --------------------------------
    ("m0_bare",  prog("MAX", 'PRINT"<MAXOK>"')),
    ("m1_print", prog('PRINT"<";MAX;">"')),
    ("m2_files", prog("MAXFILES=2", 'PRINT"<MF";MAXFILES;">"')),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=8.0)
        except Exception as exc:                       # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE on {mach}: "
                  f"{str(exc).splitlines()[0][:150]}", flush=True)
            continue
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            r = txt.rfind("RUN")
            tail = txt[r + 3:] if r >= 0 else txt
            i = tail.find("<")
            j = tail.find(">", i + 1)
            cell = tail[i:j + 1] if i >= 0 and j > i else "<no reading>"
            print(f"  {name:11} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
