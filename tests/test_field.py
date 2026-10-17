# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM LSET/RSET store (field.asm lrset_store), no emulator.

FIELD/GET/PUT's *runtime* moves disk sectors (fat_rand_*), which is Tier-3 (needs
the FDC/disk-controller model) and stays in the openMSX probes (disk_probe_field.py,
disk_probe_getput.py). One piece of the FIELD layer is pure in-RAM logic, fully
testable here:

  * lrset_store — LSET/RSET's core: space-fill a field then copy min(srclen,width)
    bytes left- (LSET) or right-justified (RSET), truncating an over-long source.

🗑️ D-FLDDESC (2026-10-17): THE FIELD SIDE-TABLE HALF OF THIS FILE IS GONE WITH THE
TABLE. It drove fld_add / fld_find over FLD_TAB; FIELD now writes each variable's
own descriptor [w][block+9+offset] (field_item, a disk.rom call-back that needs the
evaluator and the sub-ROM's fch_ctx_addr, so it is the emulator rows' --
scratchpad/flddesc_probe.py r1-r9, fldary / fldwidth / lrvar acceptance). The
running-offset contract it pinned (consecutive from offset 0) is field_item's
FLD_CUROFF arithmetic now. And a FIELDed LSET is the non-FIELDed store: the
destination is the target's own body, which for a FIELDed variable IS its slice
of the record, so the "record" cases below point at a stand-in block's +9.

Oracle basis (independently derivable, never the ROM's own output):
  * LSET/RSET justification + space-fill + right-truncation: the documented
    MSX-BASIC LSET/RSET semantics, cited in field.asm's lrset_store header.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
BASIC_BASE = 0x2781

ROM = tp("zb_field.rom")
SYM = tp("zb_field.sym")
SBUF  = 0xC300          # scratch [len][ptr] descriptor for lrset_store
SBODY = 0xC340          # the body that descriptor points at


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    s = m.sym
    fails = 0

    def report(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:34} -> "
              f"{got!r}" + ("" if ok else f"   want {want!r}"))

    # -----------------------------------------------------------------------
    # lrset_store: copy STRPTR's [len][ptr] into (LRSET_DEST), width LRSET_W,
    # justify LRSET_JUST (0=LSET left, 1=RSET right). The destination is first
    # space-filled, then min(srclen,width) bytes copied; an over-long source
    # truncates from the right.
    # Oracle: documented LSET/RSET semantics (field.asm lrset_store header) plus,
    # since D-LRVAR, the CF-3300 readings in docs/spec-basic-lrvar.md §1.
    #
    # ⚠️ D-LRVAR: the cell holds the destination ADDRESS, not the field OFFSET it
    # held while FSECTOR_BUF was the only possible destination. `off` below is
    # an offset into a record for the FIELDed cases -- the test does the addition
    # FIELD's descriptor already holds -- and the two non-FIELDed cases at the end
    # point it somewhere else entirely, which is the whole claim the
    # generalisation makes.
    # D-FLDDESC: the record is a channel block's +9 (FCH_HDRSZ), not FSECTOR_BUF;
    # FBUF stands in for one.
    # -----------------------------------------------------------------------
    FBUF = 0xC400 + s["FCH_HDRSZ"]

    def lrset_case(label, text, width, off, just, want):
        # ⚠️ THE DESCRIPTOR IS [len][ptr], NOT [len][bytes].
        # The lean build stored a string value's bytes INLINE after the length;
        # the shipped str-engine build stores a POINTER to a heap body, and
        # pu_deref_body (str-engine.asm) is what every reader goes through. This
        # test seeded the lean shape and ran on the lean build until S3
        # (docs/spec-lean-retire-s3-gates.md §5, F-U), so it never saw the
        # difference. Body goes in its own buffer; the descriptor points at it.
        src = text.encode("ascii")
        m.mem[SBODY:SBODY + len(src)] = src
        m.mem[SBUF] = len(src)
        m.poke_w(SBUF + 1, SBODY)
        m.poke_w(s["STRPTR"], SBUF)
        m.poke(s["LRSET_W"], width)
        m.poke_w(s["LRSET_DEST"], FBUF + off)
        m.poke(s["LRSET_JUST"], just)
        # poison the field region so space-fill is observable
        m.mem[FBUF + off:FBUF + off + width] = b"\xee" * width
        m.call("lrset_store")
        got = bytes(m.mem[FBUF + off:FBUF + off + width])
        report(label, got, want)

    # LSET (left-justify, space-pad on the right)
    lrset_case("LSET w5 'HI'   ", "HI",    5, 0,  0, b"HI   ")
    lrset_case("LSET w5 'HELLO'", "HELLO", 5, 0,  0, b"HELLO")
    lrset_case("LSET w3 'HELLO'", "HELLO", 3, 0,  0, b"HEL")   # truncate right
    lrset_case("LSET w4 ''     ", "",      4, 0,  0, b"    ")   # all spaces
    # RSET (right-justify, space-pad on the left)
    lrset_case("RSET w5 'HI'   ", "HI",    5, 0,  1, b"   HI")
    lrset_case("RSET w3 'HELLO'", "HELLO", 3, 0,  1, b"HEL")   # truncate right
    # offset placement: write into the middle of the record buffer
    lrset_case("LSET w4 'AB' @off8", "AB",  4, 8,  0, b"AB  ")

    # -----------------------------------------------------------------------
    # D-LRVAR: the non-FIELDed arm. Two claims the FIELDed cases above cannot
    # make, because every one of them lands inside the record (FSECTOR_BUF
    # until D-FLDDESC).
    # -----------------------------------------------------------------------
    # 1. THE DESTINATION IS AN ADDRESS, not an offset into the record buffer.
    #    DBUF is a scratch buffer nowhere near the record, standing in for a
    #    string-heap body; the store must land there and nowhere else.
    DBUF = SBODY + 0x40
    m.mem[DBUF:DBUF + 8] = b"\xee" * 8
    src = b"HI"
    m.mem[SBODY:SBODY + len(src)] = src
    m.mem[SBUF] = len(src)
    m.poke_w(SBUF + 1, SBODY)
    m.poke_w(s["STRPTR"], SBUF)
    m.poke(s["LRSET_W"], 5)
    m.poke_w(s["LRSET_DEST"], DBUF)
    m.poke(s["LRSET_JUST"], 0)
    m.call("lrset_store")
    report("LSET w5 'HI' -> a non-FSECTOR_BUF address",
           bytes(m.mem[DBUF:DBUF + 6]), b"HI   \xee")

    # 2. WIDTH 0 IS A NO-OP AND THE POINTER IS NEVER FOLLOWED (spec §4.3). This
    #    is what makes `LSET A$="HI"` on a NEVER-ASSIGNED A$ safe: such a target
    #    resolves to a [0][garbage] descriptor, so the store must return before
    #    it dereferences anything. The destination is deliberately poisoned and
    #    must come back untouched -- measured on the CF-3300 as a no-op
    #    (n.unset / n.empty), not as an assignment and not as an error.
    m.mem[DBUF:DBUF + 8] = b"\xee" * 8
    m.poke(s["LRSET_W"], 0)
    m.poke_w(s["LRSET_DEST"], DBUF)
    m.call("lrset_store")
    report("LSET w0 'HI' -> nothing written (unset target)",
           bytes(m.mem[DBUF:DBUF + 4]), b"\xee\xee\xee\xee")

    print()
    print("ALL PASS — LSET/RSET store matches the documented contract"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
