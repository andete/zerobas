# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: the interrupt-trap dispatch state machine (basic/traps.asm), no
emulator paging — a flat host Z80 image of the repack build (rom_base=$2812, so the
repack-only trap code is present).

Slice T1 = STOP (docs/spec-traps-t1-stop-reslice.md). These are the §9.1 host tests:
the tri-state + auto-STOP + PENDING-latch + GSP-match service-stack logic, where the
subtle bugs live. They poke ZTRAP/TRAPENA/TRAPPEND/TRAPSVC and the control pool
directly and
call set_state / ct_find / check_traps / trap_return_check by label, asserting the
RAM result. End-to-end Ctrl-STOP -> handler -> RETURN -> resume is covered by the
openMSX stop-trap-acceptance differential (§9.2), on real hardware.

Oracle: the documented trap semantics (arc spec §3): only state==ON fires; firing
auto-suspends to SERVICING and drops the ON count; OFF clears PENDING; a RETURN whose
GSP matches the service record re-enables the trap to ON.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

RES_ROM = tp("zb_traps_reloc.rom")
RES_SYM = tp("zb_traps_reloc.sym")
RELOC_BASE = 0x2765

# trap state-byte encoding (basic/sysvars.inc)
ZTS_OFF, ZTS_ON, ZTS_STOP, ZTS_SERVICING = 0, 1, 2, 3
ZTS_PENDING = 0x80
ZTS_SHADOW = 0x40         # traps T2: the per-entry device edge shadow
ZTI_STOP = 1
ZTI_STRIG0 = 3            # STRIG n -> entry 3 + n
ENTSZ = 3


def build():
    subprocess.run(["pasmo", "--bin",
                    os.path.join(ROOT, "basic", "main.asm"), RES_ROM, RES_SYM],
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


# D-CTLPOOL: the control frames live in one descending pool whose top the
# sub-ROM tenant derives; there is no sub ROM here, so the harness seeds it. The
# addresses are arbitrary -- what matters is CTLLIM < CTLTOP with room between.
POOL_TOP, POOL_FLOOR = 0xD000, 0x9000


def seed_pool(m, top=POOL_TOP):
    """An EMPTY pool: every pointer at the top, the collision floor well below."""
    for cell in ("CTLTOP", "CSP", "GSP", "FSP", "TSP"):
        m.poke_w(m.addr(cell), top)
    m.poke_w(m.addr("CTLLIM"), POOL_FLOOR)


def seed_record(m, idx, rec=0x7B00, prev=POOL_TOP):
    """One live service record at `rec`, with the GOSUB frame it belongs to
    directly above it -- which is the whole match key now: the record carries no
    gsp, and `TSP + TRAP_FRAME == GSP` is what says "this RETURN is the trap's".
    -> the GSP value that MATCHES it."""
    m.poke_w(m.addr("TSP"), rec)
    m.poke_w(rec, prev)                       # prevTSP -- the record chain
    m.poke(rec + 2, bytes([idx]))
    gsp = rec + m.addr("TRAP_FRAME")
    m.poke_w(m.addr("GSP"), gsp)
    return gsp


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
    # D-CTLPOOL: the frames come out of one descending pool now, and the harness
    # stands in for the sub-ROM tenant that would size it (see the module note).
    # 🎯 GSP AND FSP ARE SEEDED APART ON PURPOSE. They mean different things --
    # GSP is the innermost GOSUB frame, FSP is the FOR run's floor -- and seeding
    # both to CTLTOP would let a fix that confused them pass. FSP is parked one
    # FOR frame BELOW the top, so the value the frame records is one this test
    # could not get by accident from a zeroed cell.
    POOL_TOP, POOL_FLOOR = 0xD000, 0x9000
    for cell in ("CTLTOP", "CSP", "GSP", "TSP"):
        m.poke_w(m.addr(cell), POOL_TOP)
    m.poke_w(m.addr("CTLLIM"), POOL_FLOOR)
    m.poke_w(m.addr("CURLINE"), 0x8000)            # the "current line" saved into the frame
    seeded_fsp = POOL_TOP - m.addr("FOR_FRAME")
    m.poke_w(m.addr("FSP"), seeded_fsp)

    r = m.call("check_traps", hl=STMT)
    fails = check(fails, "check_traps fired (CF=1)", carry(r), True)
    fails = check(fails, "STOP now SERVICING", m.peek(e)[0] & 3, ZTS_SERVICING)
    fails = check(fails, "STOP PENDING cleared", m.peek(e)[0] & 0x80, 0)
    fails = check(fails, "TRAPENA dropped to 0", m.peek(m.addr("TRAPENA"))[0], 0)
    fails = check(fails, "TRAPSVC bumped to 1", m.peek(m.addr("TRAPSVC"))[0], 1)
    fails = check(fails, "CURLINE = handler", m.peek(m.addr("CURLINE"), 2), bytes([HANDLER & 0xFF, HANDLER >> 8]))
    # GSP advanced by one frame; the record's gsp == that new GSP.
    # 🔴 THE WIDTH IS READ FROM THE SYMBOL, NOT SPELT AGAIN HERE. It was written
    # as a literal 4 and D-FORRET widened the frame to 6 -- this assertion went
    # red and was RIGHT to, but a test that restates a constant can only ever
    # rot into agreement with whatever it was last edited to match.
    # 🔴 THE WIDTHS ARE READ FROM THE SYMBOLS, NOT SPELT AGAIN HERE -- see above.
    gframe = m.addr("GOSUB_FRAME")
    tframe = m.addr("TRAP_FRAME")
    new_gsp = m.peek(m.addr("GSP"), 2)
    new_gsp = new_gsp[0] | (new_gsp[1] << 8)
    # The pool DESCENDS, so a push LOWERS the pointer by exactly one frame.
    fails = check(fails, "GSP descended by one GOSUB_FRAME", POOL_TOP - new_gsp, gframe)
    # D-CTLPOOL: the service record sits immediately BELOW its own GOSUB frame,
    # so no gsp key is stored -- the pointer identity IS the match. Assert the
    # geometry that replaced the key.
    tsp = m.peek(m.addr("TSP"), 2)
    tsp = tsp[0] | (tsp[1] << 8)
    fails = check(fails, "service record sits under its frame", tsp + tframe, new_gsp)
    rec = m.peek(tsp, tframe)
    fails = check(fails, "service record prevTSP", rec[0] | (rec[1] << 8), POOL_TOP)
    fails = check(fails, "service record idx", rec[2], ZTI_STOP)
    # ⚠️ AND FSP MOVES TO THE RECORD, not to the frame: the FOR run is [CSP,FSP),
    # so leaving FSP at the frame base would put the record inside the run and the
    # next NEXT would read it as a FOR frame.
    new_fsp = m.peek(m.addr("FSP"), 2)
    fails = check(fails, "FSP excludes the service record",
                  new_fsp[0] | (new_fsp[1] << 8), tsp)
    # the pushed GOSUB frame carries resume == STMT (bytes 2-3 of the frame)
    frame = m.peek(new_gsp, gframe)
    fails = check(fails, "frame resume ptr = STMT", frame[2] | (frame[3] << 8), STMT)
    # D-FORRET under its new name: bytes 6-7 carry the FOR run's floor at push
    # time, so the handler's RETURN discards whatever FOR frames it opened.
    fails = check(fails, "frame records prevGSP", frame[4] | (frame[5] << 8), POOL_TOP)
    fails = check(fails, "frame records prevFSP", frame[6] | (frame[7] << 8), seeded_fsp)
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
        seed_pool(m)
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
    m.poke(e, bytes([ZTS_SERVICING]))
    m.poke(m.addr("TRAPENA"), b"\x00")
    m.poke(m.addr("TRAPSVC"), b"\x01")
    seed_pool(m)
    GSPV = seed_record(m, ZTI_STOP)             # this RETURN's GSP == the record
    m.call("trap_return_check")
    fails = check(fails, "return match: SERVICING->ON", m.peek(e)[0] & 3, ZTS_ON)
    fails = check(fails, "return match: TRAPENA +1", m.peek(m.addr("TRAPENA"))[0], 1)
    fails = check(fails, "return match: TRAPSVC popped", m.peek(m.addr("TRAPSVC"))[0], 0)

    # gsp MISMATCH: a normal/nested RETURN -> nothing changes
    reset_traps(m)
    m.poke(e, bytes([ZTS_SERVICING]))
    m.poke(m.addr("TRAPENA"), b"\x00")
    m.poke(m.addr("TRAPSVC"), b"\x01")
    seed_record(m, ZTI_STOP)
    # A NESTED GOSUB inside the handler: the pool descends, so a further frame
    # puts GSP one GOSUB_FRAME BELOW the record's own -- no match, nothing moves.
    # 🔴 THE DIRECTION IS THE POINT AND IT INVERTED WITH THE POOL. Read from the
    # symbol rather than spelt as a literal: this line kept passing when
    # D-FORRET widened the frame, because ANY non-equal value satisfies it, so
    # the number was never load-bearing -- but the comment claiming "a nested
    # GOSUB" was, and only the sign makes it true.
    m.poke_w(m.addr("GSP"), GSPV - m.addr("GOSUB_FRAME"))
    m.call("trap_return_check")
    fails = check(fails, "return mismatch: state untouched", m.peek(e)[0] & 3, ZTS_SERVICING)
    fails = check(fails, "return mismatch: TRAPSVC untouched", m.peek(m.addr("TRAPSVC"))[0], 1)

    # handler changed the state (SERVICING overwritten by STOP OFF/ON): leave it,
    # but still pop the record on a gsp match
    reset_traps(m)
    m.poke(e, bytes([ZTS_OFF]))               # handler did STOP OFF
    m.poke(m.addr("TRAPENA"), b"\x00")
    m.poke(m.addr("TRAPSVC"), b"\x01")
    seed_record(m, ZTI_STOP)
    m.call("trap_return_check")
    fails = check(fails, "return match, handler-OFF: stays OFF", m.peek(e)[0] & 3, ZTS_OFF)
    fails = check(fails, "return match, handler-OFF: TRAPENA unchanged", m.peek(m.addr("TRAPENA"))[0], 0)
    fails = check(fails, "return match, handler-OFF: record popped", m.peek(m.addr("TRAPSVC"))[0], 0)
    return fails


def t_strig_shadow(fails):
    """Slice T2 (docs/spec-traps-t2-strig.md §3): the device EDGE SHADOW, bit 6 of
    the entry byte. It must survive every state write that is not an explicit
    re-seed, because it is what stops a trigger HELD across a fire/RETURN (or across
    a redundant `STRIG(n) ON`) from faking a fresh 0->1 press. The VG-8020 says a
    3 s hold fires exactly once (oracle Q2); each assertion below is one way that
    could silently become "fires every frame"."""
    m = Machine(RES_ROM, RES_SYM, rom_base=RELOC_BASE)
    e0 = m.addr("ZTRAP") + ZTI_STRIG0 * ENTSZ
    HANDLER = 0x5AA5

    # 1. check_traps' ON -> SERVICING write must PRESERVE bit 6 (and still clear
    #    PENDING). A plain `ld (hl),ZTS_SERVICING` -- the T1 code -- fails this.
    reset_traps(m)
    m.poke(e0, bytes([ZTS_ON | ZTS_PENDING | ZTS_SHADOW]))
    m.poke_w(e0 + 1, HANDLER)
    m.poke(m.addr("TRAPENA"), b"\x01")
    m.poke(m.addr("TRAPPEND"), b"\x01")
    m.poke(m.addr("TRAPSVC"), b"\x00")
    seed_pool(m)
    m.poke_w(m.addr("CURLINE"), 0x8000)
    r = m.call("check_traps", hl=0x9C40)
    fails = check(fails, "STRIG fire: CF=1", carry(r), True)
    fails = check(fails, "STRIG fire: state SERVICING", m.peek(e0)[0] & 3, ZTS_SERVICING)
    fails = check(fails, "STRIG fire: PENDING cleared", m.peek(e0)[0] & 0x80, 0)
    fails = check(fails, "STRIG fire: SHADOW PRESERVED", m.peek(e0)[0] & ZTS_SHADOW,
                  ZTS_SHADOW)

    # 2. trap_return_check's SERVICING -> ON must also keep bit 6, so a trigger
    #    still held when the handler RETURNs does not immediately re-fire.
    reset_traps(m)
    m.poke(e0, bytes([ZTS_SERVICING | ZTS_SHADOW]))
    m.poke(m.addr("TRAPSVC"), b"\x01")
    seed_pool(m)
    GSPV = seed_record(m, ZTI_STRIG0)
    m.call("trap_return_check")
    fails = check(fails, "STRIG return: SERVICING->ON", m.peek(e0)[0] & 3, ZTS_ON)
    fails = check(fails, "STRIG return: SHADOW PRESERVED", m.peek(e0)[0] & ZTS_SHADOW,
                  ZTS_SHADOW)

    # 3. set_state must carry bit 6 through a state change. The load-bearing case is
    #    ON -> ON (a redundant `STRIG(n) ON`, which deliberately does NOT re-seed):
    #    if that dropped the shadow, a held trigger would fire on the next frame.
    for label, old, new in (("ON->ON", ZTS_ON, ZTS_ON),
                            ("ON->STOP", ZTS_ON, ZTS_STOP),
                            ("STOP->ON", ZTS_STOP, ZTS_ON)):
        reset_traps(m)
        m.poke(e0, bytes([old | ZTS_SHADOW]))
        m.poke(m.addr("TRAPENA"), bytes([1 if old == ZTS_ON else 0]))
        m.call("set_state", hl=e0, a=new)
        fails = check(fails, f"set_state {label}: state", m.peek(e0)[0] & 3, new)
        fails = check(fails, f"set_state {label}: SHADOW kept",
                      m.peek(e0)[0] & ZTS_SHADOW, ZTS_SHADOW)

    # 4. OFF forgets PENDING and KEEPS THE DEVICE EDGE SHADOW.
    #    🔴 THIS USED TO ASSERT THE WHOLE BYTE CLEARED, on the reasoning that OFF
    #    is "the single forget-it-all reset" and is "safe because the next enable
    #    re-seeds (spec §3)". BOTH HALVES FAILED against a measurement
    #    (D-STOPEDGE 2026-09-16, scratchpad/ctrlstop_probe.py, a 2 s Ctrl-STOP
    #    against the VG-8020):
    #      * the re-seed argument is about the transition BACK to ON, and the
    #        divergence happens WHILE OFF -- rp_break consults the shadow on a
    #        path that runs in the OFF state, and `STOP OFF` under a still-held
    #        key answered `Break in 50` where the reference answers `< 1 >`;
    #      * and STOP HAS NO SEED. strig_flag re-seeds on ON (program.asm), STOP
    #        does not -- so for STOP the preserved shadow is also what stops a key
    #        held across OFF->ON faking a fresh edge.
    #    The shadow is a fact about the DEVICE, not about the trap's state, which
    #    is exactly what the ss_write arm beside it already says in its own words.
    #    Harmless where it is re-seeded (STRIG), necessary where it is not (STOP);
    #    all eight trap suites re-run green.
    reset_traps(m)
    m.poke(e0, bytes([ZTS_ON | ZTS_PENDING | ZTS_SHADOW]))
    m.poke(m.addr("TRAPENA"), b"\x01")
    m.call("set_state", hl=e0, a=ZTS_OFF)
    fails = check(fails, "set_state ON->OFF: state and PENDING cleared",
                  m.peek(e0)[0] & ~ZTS_SHADOW, 0)
    fails = check(fails, "set_state ON->OFF: SHADOW kept",
                  m.peek(e0)[0] & ZTS_SHADOW, ZTS_SHADOW)
    return fails


def t_stop_shadow(fails):
    """Slice T1, RE-SLICED 2026-07-25 (spec §12.3): the STOP entry now rides the SAME
    edge shadow as STRIG/KEY, and that is load-bearing in a way the STRIG cases do not
    cover, because Ctrl-STOP is the ONE event source whose key is still held when its
    own handler is entered.

    This replaced STOPGRACE, a one-VBLANK timer that let rp_break abort a SERVICING
    handler once it expired. The VG-8020 never aborts a handler: while the entry is ON
    or SERVICING, Ctrl-STOP is edge-latched into PENDING and fires once after RETURN
    (oracle 2026-07-25 -- a 100 ms tap and a 3 s hold each give exactly ONE extra
    fire). The shadow is what makes the still-held triggering key not-an-edge, so if
    any of these three writes drops bit 6 on the STOP entry, zerobas goes straight back
    to spurious re-fires -- and this time with no grace timer to mask it.

    The helpers are shared with STRIG, so this is a fence, not new logic: it pins that
    ZTI_STOP is not special-cased out of the discipline by a later edit."""
    m = Machine(RES_ROM, RES_SYM, rom_base=RELOC_BASE)
    e = m.addr("ZTRAP") + ZTI_STOP * ENTSZ
    HANDLER = 0x4C2A

    # 1. the fire itself: ON -> SERVICING must keep bit 6, so the Ctrl-STOP that is
    #    STILL DOWN as the handler starts cannot look like a fresh press.
    reset_traps(m)
    m.poke(e, bytes([ZTS_ON | ZTS_PENDING | ZTS_SHADOW]))
    m.poke_w(e + 1, HANDLER)
    m.poke(m.addr("TRAPENA"), b"\x01")
    m.poke(m.addr("TRAPPEND"), b"\x01")
    m.poke(m.addr("TRAPSVC"), b"\x00")
    seed_pool(m)
    m.poke_w(m.addr("CURLINE"), 0x8000)
    r = m.call("check_traps", hl=0x9C40)
    fails = check(fails, "STOP fire: CF=1", carry(r), True)
    fails = check(fails, "STOP fire: state SERVICING", m.peek(e)[0] & 3, ZTS_SERVICING)
    fails = check(fails, "STOP fire: SHADOW PRESERVED (was STOPGRACE's job)",
                  m.peek(e)[0] & ZTS_SHADOW, ZTS_SHADOW)

    # 2. RETURN: SERVICING -> ON must keep bit 6 too, or a key held across the whole
    #    handler re-fires the instant it returns -- an infinite handler loop.
    reset_traps(m)
    m.poke(e, bytes([ZTS_SERVICING | ZTS_SHADOW]))
    m.poke(m.addr("TRAPSVC"), b"\x01")
    seed_pool(m)
    GSPV = seed_record(m, ZTI_STOP)
    m.call("trap_return_check")
    fails = check(fails, "STOP return: SERVICING->ON", m.peek(e)[0] & 3, ZTS_ON)
    fails = check(fails, "STOP return: SHADOW PRESERVED",
                  m.peek(e)[0] & ZTS_SHADOW, ZTS_SHADOW)

    # 3. `STOP ON` must not DROP the shadow through set_state. Note ex_stop deliberately
    #    does not SEED it either (unlike ex_strig_set) -- the VG-8020 re-fires a
    #    self-re-arming handler under a held key, so a seed there is a divergence.
    reset_traps(m)
    m.poke(e, bytes([ZTS_ON | ZTS_SHADOW]))
    m.poke(m.addr("TRAPENA"), b"\x01")
    m.call("set_state", hl=e, a=ZTS_ON)
    fails = check(fails, "STOP set_state ON->ON: SHADOW kept",
                  m.peek(e)[0] & ZTS_SHADOW, ZTS_SHADOW)
    return fails


def main():
    build()
    fails = 0
    fails = t_set_state(fails)
    fails = t_check_traps_fire(fails)
    fails = t_check_traps_nofire(fails)
    fails = t_trap_return_check(fails)
    fails = t_strig_shadow(fails)
    fails = t_stop_shadow(fails)
    print()
    print("ALL PASS" if fails == 0 else f"{fails} FAILURE(S)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
