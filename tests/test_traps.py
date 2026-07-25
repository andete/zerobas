# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: the interrupt-trap dispatch state machine (basic/traps.asm), no
emulator paging — a flat host Z80 image of the repack build (rom_base=$2812, so the
repack-only trap code is present).

Slice T1 = STOP (docs/spec-traps-t1-stop-reslice.md). These are the §9.1 host tests:
the tri-state + auto-STOP + PENDING-latch + GSP-match service-stack logic, where the
subtle bugs live. They poke ZTRAP/TRAPENA/TRAPPEND/TRAPSVC/TRAPSTK/GSP directly and
call set_state / ct_find / check_traps / trap_return_check by label, asserting the
RAM result. End-to-end Ctrl-STOP -> handler -> RETURN -> resume is covered by the
openMSX stop-trap-acceptance differential (§9.2), on real hardware.

Oracle: the documented trap semantics (arc spec §3): only state==ON fires; firing
auto-suspends to SERVICING and drops the ON count; OFF clears PENDING; a RETURN whose
GSP matches the service record re-enables the trap to ON.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

RES_ROM = "/tmp/zb_traps_reloc.rom"
RES_SYM = "/tmp/zb_traps_reloc.sym"
RELOC_BASE = 0x2812

# trap state-byte encoding (basic/sysvars.inc)
ZTS_OFF, ZTS_ON, ZTS_STOP, ZTS_SERVICING = 0, 1, 2, 3
ZTS_PENDING = 0x80
ZTI_STOP = 1
ENTSZ = 3


def build():
    subprocess.run(["pasmo", "--bin",
                    os.path.join(ROOT, "basic", "main-reloc.asm"), RES_ROM, RES_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def check(fails, label, got, want):
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got}" + ("" if ok else f"  want {want}"))
    return fails + (not ok)


def stop_entry(m):
    return m.addr("ZTRAP") + ZTI_STOP * ENTSZ


def reset_traps(m):
    """Clear the whole ZTRAP window + bookkeeping (mirror trap_init)."""
    z = m.addr("ZTRAP")
    for a in range(z, m.addr("TRAPPEND") + 1):
        m.poke(a, b"\x00")


def set_entry(m, idx, state, handler=0, pending=False):
    a = m.addr("ZTRAP") + idx * ENTSZ
    sb = state | (ZTS_PENDING if pending else 0)
    m.poke(a, bytes([sb]))
    m.poke_w(a + 1, handler)


# ---------------------------------------------------------------------------

def t_set_state(fails):
    m = Machine(RES_ROM, RES_SYM, rom_base=RELOC_BASE)
    e = stop_entry(m)
    TRAPENA = m.addr("TRAPENA")

    # OFF -> ON: TRAPENA +1, state ON, PENDING preserved
    reset_traps(m)
    m.poke(e, bytes([ZTS_OFF | ZTS_PENDING]))     # OFF but a stale PENDING bit
    m.poke(TRAPENA, b"\x00")
    m.call("set_state", hl=e, a=ZTS_ON)
    fails = check(fails, "set_state OFF->ON state", m.peek(e)[0] & 3, ZTS_ON)
    fails = check(fails, "set_state OFF->ON keeps PENDING", m.peek(e)[0] & 0x80, 0x80)
    fails = check(fails, "set_state OFF->ON TRAPENA", m.peek(TRAPENA)[0], 1)

    # ON -> STOP: TRAPENA -1, PENDING preserved (suspend remembers)
    m.poke(e, bytes([ZTS_ON | ZTS_PENDING]))
    m.poke(TRAPENA, b"\x01")
    m.call("set_state", hl=e, a=ZTS_STOP)
    fails = check(fails, "set_state ON->STOP state", m.peek(e)[0] & 3, ZTS_STOP)
    fails = check(fails, "set_state ON->STOP keeps PENDING", m.peek(e)[0] & 0x80, 0x80)
    fails = check(fails, "set_state ON->STOP TRAPENA", m.peek(TRAPENA)[0], 0)

    # ON -> OFF: TRAPENA -1, PENDING CLEARED (disabled forgets)
    m.poke(e, bytes([ZTS_ON | ZTS_PENDING]))
    m.poke(TRAPENA, b"\x01")
    m.call("set_state", hl=e, a=ZTS_OFF)
    fails = check(fails, "set_state ON->OFF state", m.peek(e)[0] & 3, ZTS_OFF)
    fails = check(fails, "set_state ON->OFF clears PENDING", m.peek(e)[0] & 0x80, 0)
    fails = check(fails, "set_state ON->OFF TRAPENA", m.peek(TRAPENA)[0], 0)

    # STOP -> ON: TRAPENA +1 (a re-enable of a suspended trap)
    m.poke(e, bytes([ZTS_STOP | ZTS_PENDING]))
    m.poke(TRAPENA, b"\x00")
    m.call("set_state", hl=e, a=ZTS_ON)
    fails = check(fails, "set_state STOP->ON TRAPENA", m.peek(TRAPENA)[0], 1)

    # ON -> ON: no TRAPENA change (idempotent re-arm)
    m.poke(e, bytes([ZTS_ON]))
    m.poke(TRAPENA, b"\x01")
    m.call("set_state", hl=e, a=ZTS_ON)
    fails = check(fails, "set_state ON->ON TRAPENA unchanged", m.peek(TRAPENA)[0], 1)
    return fails


def t_check_traps_fire(fails):
    m = Machine(RES_ROM, RES_SYM, rom_base=RELOC_BASE)
    reset_traps(m)
    e = stop_entry(m)
    HANDLER = 0x5AA5          # arbitrary "line link" -- check_traps only stores it
    STMT = 0x9C40            # the resume statement pointer passed in HL
    set_entry(m, ZTI_STOP, ZTS_ON, handler=HANDLER, pending=True)
    m.poke(m.addr("TRAPENA"), b"\x01")
    m.poke(m.addr("TRAPPEND"), b"\x01")
    m.poke(m.addr("TRAPSVC"), b"\x00")
    m.poke_w(m.addr("GSP"), m.addr("GOSUB_STK"))   # empty control stack
    m.poke_w(m.addr("CURLINE"), 0x8000)            # the "current line" saved into the frame

    r = m.call("check_traps", hl=STMT)
    fails = check(fails, "check_traps fired (CF=1)", carry(r), True)
    fails = check(fails, "STOP now SERVICING", m.peek(e)[0] & 3, ZTS_SERVICING)
    fails = check(fails, "STOP PENDING cleared", m.peek(e)[0] & 0x80, 0)
    fails = check(fails, "TRAPENA dropped to 0", m.peek(m.addr("TRAPENA"))[0], 0)
    fails = check(fails, "TRAPSVC bumped to 1", m.peek(m.addr("TRAPSVC"))[0], 1)
    fails = check(fails, "CURLINE = handler", m.peek(m.addr("CURLINE"), 2), bytes([HANDLER & 0xFF, HANDLER >> 8]))
    # GSP advanced by 4 (one frame pushed); the record's gsp == that new GSP
    new_gsp = m.peek(m.addr("GSP"), 2)
    new_gsp = new_gsp[0] | (new_gsp[1] << 8)
    fails = check(fails, "GSP advanced by 4", new_gsp - m.addr("GOSUB_STK"), 4)
    rec = m.peek(m.addr("TRAPSTK"), 3)
    fails = check(fails, "service record gsp", rec[0] | (rec[1] << 8), new_gsp)
    fails = check(fails, "service record idx", rec[2], ZTI_STOP)
    # the pushed GOSUB frame carries resume == STMT (bytes 2-3 of the frame)
    frame = m.peek(m.addr("GOSUB_STK"), 4)
    fails = check(fails, "frame resume ptr = STMT", frame[2] | (frame[3] << 8), STMT)
    return fails


def t_check_traps_nofire(fails):
    m = Machine(RES_ROM, RES_SYM, rom_base=RELOC_BASE)
    HANDLER = 0x5AA5
    for label, state, handler, pending in [
        ("OFF",        ZTS_OFF,       HANDLER, True),
        ("suspended",  ZTS_STOP,      HANDLER, True),
        ("no PENDING", ZTS_ON,        HANDLER, False),
        ("no handler", ZTS_ON,        0,       True),
    ]:
        reset_traps(m)
        set_entry(m, ZTI_STOP, state, handler=handler, pending=pending)
        m.poke(m.addr("TRAPPEND"), b"\x01")
        m.poke_w(m.addr("GSP"), m.addr("GOSUB_STK"))
        e = stop_entry(m)
        before = m.peek(e)[0]
        r = m.call("check_traps", hl=0x9C40)
        fails = check(fails, f"check_traps NO fire ({label}) CF=0", carry(r), False)
        fails = check(fails, f"check_traps NO fire ({label}) entry unchanged", m.peek(e)[0], before)
        fails = check(fails, f"check_traps NO fire ({label}) TRAPPEND cleared", m.peek(m.addr("TRAPPEND"))[0], 0)
    return fails


def t_trap_return_check(fails):
    m = Machine(RES_ROM, RES_SYM, rom_base=RELOC_BASE)
    e = stop_entry(m)

    # gsp MATCH: SERVICING -> ON, TRAPENA +1, TRAPSVC popped to 0
    reset_traps(m)
    GSPV = 0x7B34
    m.poke(e, bytes([ZTS_SERVICING]))
    m.poke(m.addr("TRAPENA"), b"\x00")
    m.poke(m.addr("TRAPSVC"), b"\x01")
    rec = m.addr("TRAPSTK")
    m.poke_w(rec, GSPV)
    m.poke(rec + 2, bytes([ZTI_STOP]))
    m.poke_w(m.addr("GSP"), GSPV)             # this RETURN's GSP == the record
    m.call("trap_return_check")
    fails = check(fails, "return match: SERVICING->ON", m.peek(e)[0] & 3, ZTS_ON)
    fails = check(fails, "return match: TRAPENA +1", m.peek(m.addr("TRAPENA"))[0], 1)
    fails = check(fails, "return match: TRAPSVC popped", m.peek(m.addr("TRAPSVC"))[0], 0)

    # gsp MISMATCH: a normal/nested RETURN -> nothing changes
    reset_traps(m)
    m.poke(e, bytes([ZTS_SERVICING]))
    m.poke(m.addr("TRAPENA"), b"\x00")
    m.poke(m.addr("TRAPSVC"), b"\x01")
    m.poke_w(rec, GSPV)
    m.poke(rec + 2, bytes([ZTI_STOP]))
    m.poke_w(m.addr("GSP"), GSPV + 4)         # nested GOSUB pushed higher -> no match
    m.call("trap_return_check")
    fails = check(fails, "return mismatch: state untouched", m.peek(e)[0] & 3, ZTS_SERVICING)
    fails = check(fails, "return mismatch: TRAPSVC untouched", m.peek(m.addr("TRAPSVC"))[0], 1)

    # handler changed the state (SERVICING overwritten by STOP OFF/ON): leave it,
    # but still pop the record on a gsp match
    reset_traps(m)
    m.poke(e, bytes([ZTS_OFF]))               # handler did STOP OFF
    m.poke(m.addr("TRAPENA"), b"\x00")
    m.poke(m.addr("TRAPSVC"), b"\x01")
    m.poke_w(rec, GSPV)
    m.poke(rec + 2, bytes([ZTI_STOP]))
    m.poke_w(m.addr("GSP"), GSPV)
    m.call("trap_return_check")
    fails = check(fails, "return match, handler-OFF: stays OFF", m.peek(e)[0] & 3, ZTS_OFF)
    fails = check(fails, "return match, handler-OFF: TRAPENA unchanged", m.peek(m.addr("TRAPENA"))[0], 0)
    fails = check(fails, "return match, handler-OFF: record popped", m.peek(m.addr("TRAPSVC"))[0], 0)
    return fails


def main():
    build()
    fails = 0
    fails = t_set_state(fails)
    fails = t_check_traps_fire(fails)
    fails = t_check_traps_nofire(fails)
    fails = t_trap_return_check(fails)
    print()
    print("ALL PASS" if fails == 0 else f"{fails} FAILURE(S)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
