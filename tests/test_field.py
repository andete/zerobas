# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM FIELD side-table + LSET/RSET store (field.asm), no emulator.

FIELD/GET/PUT's *runtime* moves disk sectors (fat_rand_*), which is Tier-3 (needs
the FDC/disk-controller model) and stays in the openMSX probes (disk_probe_field.py,
disk_probe_getput.py). But two pieces of FIELD are pure in-RAM logic, fully testable
here:

  * the field side-table — fld_add appends [chan,key,offset,width] with the running
    record offset, fld_find looks an entry up by variable key. This is what maps a
    fielded variable to its slice of the record buffer.
  * lrset_store — LSET/RSET's core: space-fill a field then copy min(srclen,width)
    bytes left- (LSET) or right-justified (RSET), truncating an over-long source.

Oracle basis (independently derivable, never the ROM's own output):
  * field offsets are the running sum of preceding widths (the documented FIELD
    contract: fields are laid out consecutively from offset 0) — field.asm fld_add.
  * LSET/RSET justification + space-fill + right-truncation: the documented
    MSX-BASIC LSET/RSET semantics, cited in field.asm's lrset_store header.
"""

import os
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
BASIC_BASE = 0x2812

ROM = "/tmp/zb_field.rom"
SYM = "/tmp/zb_field.sym"
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
    # Field side-table: FIELD #1, 5 AS A$, 10 AS B$, 2 AS C$
    # fld_add(BC=key, E=width) reads FLD_CHAN + the running FLD_CUROFF, appends an
    # entry and advances FLD_CUROFF by the width. The three fields must therefore
    # land at offsets 0, 5, 15 (running sum) with their widths preserved, and
    # fld_find must recover each by key. Keys are arbitrary 2-byte tags here (the
    # real keyer is exercised elsewhere); we only need them distinct.
    # Oracle: consecutive layout from offset 0 (FIELD contract).
    # -----------------------------------------------------------------------
    # start from a clean table + zero running offset, channel #1
    m.mem[s["FLD_TAB"]:s["FLD_TABEND"]] = b"\x00" * (s["FLD_TABEND"] - s["FLD_TAB"])
    m.poke(s["FLD_CHAN"], 1)
    m.poke_w(s["FLD_CUROFF"], 0)

    fields = [(0x4101, 5), (0x4201, 10), (0x4301, 2)]   # (key, width)
    for key, width in fields:
        m.call("fld_add", bc=key, de=width)             # E = width (D ignored)

    # fld_find each key -> entry [chan][k0][k1][off lo][off hi][width]; verify the
    # offset is the running sum and the width round-trips.
    running = 0
    for key, width in fields:
        cpu = m.call("fld_find", bc=key)
        from msxtest import carry
        ent = cpu.hl
        chan = m.mem[ent]
        off = m.mem[ent + 3] | (m.mem[ent + 4] << 8)
        w = m.mem[ent + 5]
        report(f"fld_find {key:#06x} CF", carry(cpu), True)
        report(f"  chan/off/width {key:#06x}", (chan, off, w), (1, running, width))
        running += width

    # a key that was never FIELDed -> CF clear (not found)
    from msxtest import carry
    cpu = m.call("fld_find", bc=0x5A5A)
    report("fld_find missing-key CF", carry(cpu), False)

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
    # still an offset into the record buffer for the FIELDed cases -- the test
    # does the addition the resident FIELDed arm now does -- and the two
    # non-FIELDed cases at the end point it somewhere else entirely, which is the
    # whole claim the generalisation makes.
    # -----------------------------------------------------------------------
    FBUF = s["FSECTOR_BUF"]

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
    # make, because every one of them lands inside FSECTOR_BUF.
    # -----------------------------------------------------------------------
    # 1. THE DESTINATION IS AN ADDRESS, not an offset into the record buffer.
    #    DBUF is a scratch buffer nowhere near FSECTOR_BUF, standing in for a
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
    print("ALL PASS — FIELD layout + LSET/RSET store match the documented contract"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
