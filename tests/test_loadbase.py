# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host test for D-LOADBASE: the three tokenised loaders read a program whatever
text base it was SAVEd from.

A tokenised file's link words are absolute addresses on the SAVING machine. The
loaders take each line's length from the difference of two links, which needs
nothing else -- except for the first line, whose length was taken against an
assumed base of $8001. The CF-3300 LOADs a program SAVEd with TXTTAB at $C001
and lists it; zerobas loaded garbage (scratchpad/txttab_saveload.out). The first
line is now scanned for its $00, passing over each constant's bytes, which may
themselves be $00 (`256` is $1C $00 $01; scratchpad/txttab_saveload2.out).

Rows, each on images SAVEd from $8001 and from $C001:
  * tok_payload against the format table, all 256 byte values (the tape
    reader's copy, zerobas-sub2 page 0);
  * CLOAD / LOAD's tape loop (sub2/tapeprog.asm ctp_line), TAPIN served by the test;
  * the disk LOAD (disk/kernel.asm hk_dpload), on test_hk_dpbload's FAT12 model;
  * the tape file skip (basic/casmatch-body.inc csd_tok, zerobas-sub): it must
    consume exactly the image, or the search loses its place on the tape.
"""

import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, _build_sub2rom  # noqa: E402
import test_hk_dpbload as D  # noqa: E402  (the FAT12 model and the disk build)

BASIC_BASE = 0x2781
MAIN_ROM, MAIN_SYM = tp("zb_loadbase_main.rom"), tp("zb_loadbase_main.sym")
SUB_ROM, SUB_SYM = tp("zb_loadbase_sub.rom"), tp("zb_loadbase_sub.sym")
TXTBASE = 0x8001
TAPIN, TAPION, TAPIOF = 0x00E4, 0x00E1, 0x00E7

PAYLOAD = {0x0B: 2, 0x0C: 2, 0x0D: 2, 0x0E: 2, 0x0F: 1, 0x1C: 2, 0x1D: 4, 0x1F: 8}

# (line number, body without its $00) -- line 1 carries constants holding $00
LINES = [
    (10, b"A%\xef\x1c\x00\x01:B%\xef\x0c\x00\x01:\x89\x0e\x1e\x00:X\xef\x1f\x41\x00\x00\x00\x00\x00\x00\x00"
         b":Y\xef\x1d\x41\x00\x00\x00:Z\xef\x0f\x00"),
    (20, b'\x91 "BB"'),
    (30, b"\x91 \x1c\x00\x01"),
]


def image(base):
    """The tokenised SAVE image after the $FF marker: lines linked as on a machine
    whose text starts at `base`, then the $0000 end link."""
    out, addr = bytearray(), base
    for num, body in LINES:
        rec = num.to_bytes(2, "little") + body + b"\x00"
        nxt = addr + 2 + len(rec)
        out += nxt.to_bytes(2, "little") + rec
        addr = nxt
    return bytes(out) + b"\x00\x00"


def stored(base):
    """What the loader leaves at TXTBASE before the commit: every line record with
    its saved link (relink fixes those later), no end link."""
    return image(base)[:-2]


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), MAIN_ROM, MAIN_SYM],
                   check=True, capture_output=True, cwd=ROOT)
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)
    D.build()


def feeder(m, data):
    q = list(data)
    used = []

    def tapin(mach):
        if q:
            mach.cpu.a = q.pop(0)
            used.append(1)
            mach.cpu.f &= ~1
        else:
            mach.cpu.f |= 1
    m.trap(TAPIN, tapin)
    m.trap(TAPION, lambda mach: setattr(mach.cpu, "f", mach.cpu.f & ~1))
    m.trap(TAPIOF, lambda mach: None)
    return used


def sub2_call(m, label, **regs):
    """Run a zerobas-sub2 PAGE-0 routine from main machine `m`, as main reaches it:
    through subrom2_call, which msxtest bridges into sub2 (with p0cb back into main
    -- so main's TAPIN / TAPIOF traps serve the tape) once SUBSLOT2 says the ROM is
    there. D-P0CB's tape-loop slice moved the reader (and its tok_payload) there."""
    m.mem[m.sym["SUBSLOT2"]] = 0x8F         # slot 3-3, as the boot records it
    return m.call("subrom2_call", ix=SUB2_SYM[label], **regs)


def run():
    build()
    global SUB2_SYM
    SUB2_SYM = _build_sub2rom()[1]
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    def guarded(fn, label):
        """A loader that runs away (a wrong length walks into the error funnel)
        is a FAIL row, not a crash that hides the rows after it."""
        try:
            fn()
            return True
        except Exception as e:      # StackLost / runaway
            check(False, f"{label}: the loader ran away ({type(e).__name__})")
            return False

    # --- tok_payload, all 256 values (the tape reader's copy, sub2 page 0) -----
    m = Machine(MAIN_ROM, MAIN_SYM, rom_base=BASIC_BASE)
    bad = [b for b in range(256) if sub2_call(m, "tok_payload", a=b).a != PAYLOAD.get(b, 0)]
    check(not bad, f"tok_payload matches the format table for all 256 bytes (wrong: {bad[:8]})")

    TXTTAB_CELL = 0xF676
    for base, at in ((TXTBASE, TXTBASE), (0xC001, TXTBASE), (0x9000, TXTBASE),
                     (TXTBASE, 0xC001)):
        want = stored(base)
        tag = f"SAVEd from ${base:04X}" + (f", TXTTAB moved to ${at:04X}" if at != TXTBASE else "")

        # --- CLOAD / LOAD: ctp_line (sub2/tapeprog.asm) -----------------------
        # The read ends at ctp_done, whose tail is main's load_commit_prog
        # through p0cb: trapped there, so CLPTR is what the loop left.
        m = Machine(MAIN_ROM, MAIN_SYM, rom_base=BASIC_BASE)
        s = m.sym
        m.trap("load_commit_prog", lambda mach: None)
        m.poke_w(TXTTAB_CELL, at)           # as the cold start (or a POKE) left it
        feeder(m, image(base))
        m.poke(s["CAS_VERIFY"], b"\x00")
        m.poke_w(s["CLINK"], TXTBASE)       # stale: the loader's own start must set it
        if guarded(lambda: sub2_call(m, "ctp_begin"), f"CLOAD {tag}"):
            end = m.mem[s["CLPTR"]] | m.mem[s["CLPTR"] + 1] << 8
            check(bytes(m.mem[at:end]) == want,
                  f"CLOAD {tag}: {end - at} B stored at ${at:04X} (want {len(want)}, the same bytes)")

        # --- disk LOAD: hk_dpload ----------------------------------------------
        d = D.Disk()
        d.add_file("P.BAS", b"\xff" + image(base))
        dm = D.machine(d)
        ds = dm.sym
        dm.poke(ds["DISK_FCB_NAME"], D.name83("P.BAS"))
        dm.poke(ds["FOPEN_SEL"], ds["FOPEN_SEL_LOAD"])
        dm.poke_w(TXTTAB_CELL, at)
        if guarded(lambda: dm.call("hk_dpload"), f"disk LOAD {tag}"):
            end = dm.mem[ds["CLPTR"]] | dm.mem[ds["CLPTR"] + 1] << 8
            check(dm.mem[ds["DISKOP_STATUS"]] == 0 and bytes(dm.mem[at:end]) == want,
                  f"disk LOAD {tag}: status {dm.mem[ds['DISKOP_STATUS']]}, {end - at} B at "
                  f"${at:04X} (want 0, {len(want)} B, the same bytes)")

        # --- the tape file skip: csd_tok (zerobas-sub) ----------------------------
        sm = Machine(SUB_ROM, SUB_SYM, rom_base=0x0000)
        tail = b"\x99" * 4                  # the next file's bytes: must stay unread
        used = feeder(sm, image(base) + tail)
        res = []
        if guarded(lambda: res.append(sm.call("csd_tok")), f"tape skip {tag}"):
            check(not res[0].f & 1 and len(used) == len(image(base)),
                  f"tape skip {tag}: {len(used)} B consumed (want {len(image(base))}, CF clear)")

    # --- D-TXTTAB part 2: NEW keeps a moved TXTTAB ------------------------------
    m = Machine(MAIN_ROM, MAIN_SYM, rom_base=BASIC_BASE)
    s = m.sym
    m.poke_w(TXTTAB_CELL, 0xC001)
    m.poke(0xC001, b"\x55\x55")
    m.call("new_prog_quiet")
    prgend = m.mem[s["PRGEND"]] | m.mem[s["PRGEND"] + 1] << 8
    tt = m.mem[TXTTAB_CELL] | m.mem[TXTTAB_CELL + 1] << 8
    check(tt == 0xC001 and prgend == 0xC001 and m.peek(0xC001, 2) == b"\x00\x00",
          f"NEW with TXTTAB $C001: TXTTAB ${tt:04X}, PRGEND ${prgend:04X}, end link "
          f"{m.peek(0xC001, 2).hex()} (want $C001, $C001, 0000 -- the CF-3300 keeps it)")
    return fails


if __name__ == "__main__":
    f = run()
    print(f"{'OK' if not f else 'FAILED'}: {f} failure(s)")
    sys.exit(1 if f else 0)
