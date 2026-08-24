# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-MSGSUB's sub-ROM-hosted error messages say what the MACHINES say.

docs/spec-basic-msgsub.md §7. Fourteen ERR codes that zerobas never RAISES but
must still be able to PRINT live in sub-ROM page 1 (SUBROM_IDX_ERRMSG), keyed on
ERRFLG. `basic_probe_msgexact.py --gate` covers them end-to-end -- but that costs
an openMSX boot; this is the cheap layer, and it covers three things the gate
structurally cannot see:

  * the TABLE's code set, not just the codes someone happened to walk;
  * EM_ROWS vs the actual row count -- one fact in two places, which is exactly
    how err_msgtab's `cp` bound drifted from its table and left ERR 25 dead for a
    whole arc (basic/interp.asm, msgtab-bound-drift);
  * that the fallback string exists and is reachable as a table miss.

⚠️ WHAT MAKES THIS TEST REAL (test_msgenc.py's own rule): it READS THE ROM IMAGE
and compares against strings typed out INDEPENDENTLY below. It does not re-derive
the expected text from the `db` lines that produced it. The strings are the
verbatim readings in docs/msgexact-msx1-characterization.md §1/§2 -- measured on
the two reference machines, never transcribed from a published MSX-BASIC
reference, which D-MSGEXACT proved unreliable about exactly this (that reference
says ERR 17 is `Can't continue`; the machines say `Can't CONTINUE`).

FALSIFIED, 2026-08-02: change one letter of any string in sub/errmsg.asm and that
row fails; drop a table row without touching EM_ROWS and the count check fails;
add a fifteenth code and the exact-set check fails. All three verified by doing
them.
"""

import os
from _tmp import tp
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ROM = tp("zb_msgsub_sub.rom")
SYM = tp("zb_msgsub_sub.sym")

# The sub-ROM is a flat $0000-based 32 KB image spanning BOTH pages, so a symbol
# address IS its file offset -- no relocation base, unlike test_msgenc's LOW.

# ERR code -> the text BOTH references print, except 60..64 which are CF-3300
# only (the diskless VG-8020 answers `Unprintable error` across that span, so it
# is not an oracle there). zerobas ships Disk BASIC in the main ROM and is a disk
# machine, so the CF-3300 is its oracle for those four -- signed off 2026-08-02,
# spec §9 Q3, and the one place this slice makes zerobas differ from a reference
# on purpose.
EXPECT = {
    12: "Illegal direct",
    15: "String too long",
    18: "Undefined user function",
    19: "Device I/O error",
    50: "FIELD overflow",
    51: "Internal error",
    53: "File not found",
    54: "File already open",
    56: "Bad file name",
    57: "Direct statement in file",
    60: "Bad FAT",             # CF-3300 only, from here down
    62: "Bad drive name",
    63: "Bad sector number",
    64: "File still open",

    # --- D-MSGMIGRATE: the sixteen that MOVED here from main page 1 ----------
    # ⚠️ THESE ARRIVED BY HAND-OFF, AND THE HAND-OFF IS THE HAZARD. Each one was
    # deleted from tests/test_msgenc.py's EXPECT dict in the same edit that
    # deleted its string from main. Had they only been deleted, this tree's whole
    # error vocabulary would have gone UNPINNED while every gate stayed green --
    # a readout losing its subject without going red. Typed out here
    # independently, exactly as the rule above requires: these are the verbatim
    # readings in docs/msgexact-msx1-characterization.md §1/§2, not a re-derivation
    # of the `db` lines in sub/errmsg.asm.
    1:  "NEXT without FOR",
    3:  "RETURN without GOSUB",
    4:  "Out of DATA",
    6:  "Overflow",
    8:  "Undefined line number",
    11: "Division by zero",
    13: "Type mismatch",
    17: "Can't CONTINUE",       # ⚠️ capital CONTINUE -- measured. The published
                                # table says `Can't continue` and is WRONG.
    22: "RESUME without error",
    24: "Missing operand",
    25: "Line buffer overflow", # lowercase tail; ERR 6 above is capital `Overflow`.
                                # They CANNOT share storage -- one blob cannot spell
                                # a letter two ways. This pair carries the overlap
                                # control that used to live in test_msgenc.py.
    52: "Bad file number",
    55: "Input past end",
    58: "Sequential I/O only",
    59: "File not OPEN",
    61: "Bad file mode",
}

# What a code the tenant does NOT know must print. Main routes EVERY out-of-dense
# code here (rerr_unprintable -> err_subhosted), so 26..49 and 65..255 land on
# this string -- and `ERROR 26` is the standing gate control that rides it.
# ⚠️ It duplicates main's own err_unprintable ON PURPOSE. The tenant cannot say
# "not my code" (A is not preserved across CALSLT, and subrom_call's CF means
# "absent"), so it must answer every input; that duplication is what buys the
# whole out-of-dense range a zero-byte main-side routing.
EXPECT_FALLBACK = "Unprintable error"


def build():
    r = subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", ROM, SYM],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("pasmo failed")
    return open(ROM, "rb").read(), load_syms(SYM)


def load_syms(path):
    syms = {}
    for ln in open(path):
        m = re.match(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", ln)
        if m:
            syms[m.group(1)] = int(m.group(2), 16)
    return syms


def cstr(rom, addr):
    end = rom.index(b"\0", addr)
    return rom[addr:end].decode("latin-1")


def main():
    rom, syms = build()

    for need in ("em_table", "EM_ROWS", "em_unprintable", "errmsg_tenant"):
        if need not in syms:
            print(f"{need}: absent from the sym file")
            return 1

    # ⚠️ THE ROW COUNT COMES FROM THE ROM, NOT FROM EM_ROWS. Reading EM_ROWS rows
    # and then checking EM_ROWS would be a readout agreeing with itself. The
    # table is bounded by the first string it points at -- every entry's target
    # is at a HIGHER address than the table, and em_ill_direct is the lowest, so
    # the table ends where the first target begins.
    at = syms["em_table"]
    first_target = syms["em_ill_direct"]
    span = first_target - at
    if span <= 0 or span % 3:
        print(f"em_table span {span} is not a whole number of 3-byte rows "
              f"(${at:04X}..${first_target:04X}) -- the layout assumption this "
              f"test reads the table with no longer holds")
        return 1
    nrows = span // 3

    fails = []
    if nrows != syms["EM_ROWS"]:
        fails.append(f"EM_ROWS is {syms['EM_ROWS']} but the table holds {nrows} "
                     f"rows. The scan is `ld b,EM_ROWS` + `djnz`, so the extra "
                     f"rows are DEAD or the scan reads PAST the table -- the "
                     f"same one-fact-in-two-places drift that left err_msgtab's "
                     f"ERR 25 entry dead for a whole arc.")

    got = {}
    for i in range(nrows):
        code = rom[at + 3 * i]
        ptr = rom[at + 3 * i + 1] | (rom[at + 3 * i + 2] << 8)
        if code in got:
            fails.append(f"code {code} appears twice in em_table (row {i}); the "
                         f"scan is linear, so the second copy is unreachable")
        got[code] = cstr(rom, ptr)

    # The DENOMINATOR, both directions. A missing code is a hole that reopened; a
    # surplus one is a code nobody measured against a reference.
    if set(got) != set(EXPECT):
        missing = sorted(set(EXPECT) - set(got))
        surplus = sorted(set(got) - set(EXPECT))
        if missing:
            fails.append(f"em_table is MISSING codes {missing} -- those holes "
                         f"reopened and `ERROR n` prints the fallback again")
        if surplus:
            fails.append(f"em_table carries UNMEASURED codes {surplus} -- add "
                         f"them to docs/msgexact-msx1-characterization.md with a "
                         f"reference reading first, or drop them")

    for code in sorted(set(EXPECT) & set(got)):
        ok = got[code] == EXPECT[code]
        print(f"{'PASS' if ok else 'FAIL'}  ERR {code:<3} {got[code]!r}")
        if not ok:
            fails.append(f"ERR {code}: got {got[code]!r}, want {EXPECT[code]!r}")

    fb = cstr(rom, syms["em_unprintable"])
    if fb == EXPECT_FALLBACK:
        print(f"PASS  fallback  {fb!r}")
    else:
        fails.append(f"em_unprintable: got {fb!r}, want {EXPECT_FALLBACK!r}")

    # The fallback must NOT be one of the table's own targets: if it were, a real
    # code would be answering with the out-of-table text and this test's per-code
    # rows would still all pass.
    if syms["em_unprintable"] in {rom[at + 3 * i + 1] | (rom[at + 3 * i + 2] << 8)
                                  for i in range(nrows)}:
        fails.append("em_unprintable is a TABLE TARGET -- some real code is "
                     "wired to the out-of-table string")

    if fails:
        print("\n" + "\n".join(fails))
        return 1
    print(f"\nALL {len(EXPECT)} sub-hosted messages + the fallback match the "
          f"measured reference text ({nrows} table rows, EM_ROWS agrees)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
