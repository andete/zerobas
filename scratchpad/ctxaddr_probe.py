#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CTXADDR — what does `fch_ctx_addr(1)` actually return?

TODO.md's TXTMAX line-store item is open on one measured oddity: with the fix
built and the machine healthy, `SL_CEIL` read **30119 ($75A7)** after
`CLEAR 300,TXTTAB+1000` -- a MAIN-ROM PAGE-1 ADDRESS, not a RAM ceiling, and
nowhere near `min(HIMEM,TXTMAX) - POOLSIZE - MAXF*FCH_CTXSZ`.

`fch_ctx_addr` (basic/files.asm:1246) is four instructions:

    ld (SH_LEN),a  /  ld a,18  /  ld (SH_OP),a  /  call call_strheap
    ld hl,(SH_PTR) /  ret

So its answer IS `SH_PTR` after op 18. A ROM address in that cell has an obvious
candidate cause: **op 18 never ran and SH_PTR was STALE** -- it is the string
engine's own result cell, so a leftover from an earlier string operation is
exactly the kind of value that looks like $75A7.

This asks the host harness directly, which is cheap and needs no emulator:
poke SH_PTR to a recognisable sentinel, call fch_ctx_addr with A=1, and see
whether the cell CHANGED. If it did not, the call is a no-op in that context and
the published ceiling was never computed.

⚠️ THE HOST HARNESS BRIDGES `subrom_call` (msxtest._install_subrom_bridge) but it
is a BRIDGE, not a real CALSLT. A negative result here is therefore evidence
about the ROUTINE, not proof about the machine -- the emulator reading stands as
the machine's own answer, and this only narrows what to look at next.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from msxtest import Machine                                       # noqa: E402
from _tmp import tp                                              # noqa: E402

ROM, SYM = tp("zb_ctxaddr.rom"), tp("zb_ctxaddr.sym")
BASIC_BASE = 0x2812
SENTINEL = 0xBEEF


def main() -> int:
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"),
                    ROM, SYM], check=True, capture_output=True)
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    s = m.sym

    for name in ("SH_PTR", "SH_OP", "SH_LEN", "MAXF", "HIMEM", "TXTMAX"):
        print(f"  {name:8s} = ${s[name]:04X}" if name in s
              else f"  {name:8s} = <absent>")

    # plausible live state: a machine that has booted and run CLEAR
    m.poke_w(s["SH_PTR"], SENTINEL)
    m.poke(s["MAXF"], 1)
    if "HIMEM" in s:
        m.poke_w(s["HIMEM"], 0x8000 + 0x5000)      # a RAM ceiling
    before = m.peek(s["SH_PTR"], 2)
    print(f"\nSH_PTR before      = ${before[1] << 8 | before[0]:04X}  (sentinel)")

    try:
        m.call("fch_ctx_addr", a=1)
        hl = m.cpu.regs()["hl"] if hasattr(m.cpu, "regs") else None
    except Exception as e:                                        # noqa: BLE001
        print(f"\n🔴 fch_ctx_addr RAISED: {type(e).__name__}: {e}")
        after = m.peek(s["SH_PTR"], 2)
        v = after[1] << 8 | after[0]
        print(f"SH_PTR after       = ${v:04X}"
              + ("   🔴 UNCHANGED — op 18 never wrote it" if v == SENTINEL
                 else "   (changed)"))
        return 2

    after = m.peek(s["SH_PTR"], 2)
    v = after[1] << 8 | after[0]
    print(f"SH_PTR after       = ${v:04X}"
          + ("   🔴 UNCHANGED — op 18 never wrote it, so fch_ctx_addr "
             "returns a STALE cell" if v == SENTINEL else "   (op 18 wrote it)"))
    print(f"SH_OP              = {m.peek(s['SH_OP'])[0]}  (18 = sh_chan_addr)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
