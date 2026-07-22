#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G8 characterization round 3 (Philips VG-8020): the full state delta.

Round 2 asked one register per case and got a confusing picture (a SCREEN-2
name-base change appeared to leave R2 at an unrelated value).  Single-register
questions are the wrong instrument: round 3 DUMPS THE WHOLE STATE around each
case -- the 20-word BASE table in the work area AND the eight VDP write shadows
-- so "which cell moved" is read off directly instead of inferred.

  E1 statedelta -- baseline state per SCREEN mode, then the state after one
                   BASE(n)= / VDP(n)= write (diff printed cell by cell)
  E2 hwreach    -- does VDP(n)= reach the chip? (R1 IE bit off => TIME freezes);
                   run with a LONG step, the round-2 attempt just timed out

Work-area addresses are published MSX contracts (no disassembly): the per-mode
table-base words live at $F3B3.. and the VDP R0..R7 write shadows at $F3DF..,
with the ISR's status copy at $F3E7.
"""
from __future__ import annotations
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
BASETAB = 0xF3B3          # 20 words: BASE(0)..BASE(19)
RGSAV = 0xF3DF            # R0..R7 write shadows, then STATFL at $F3E7
RES = 0xD100              # liveness marker: 7 once the case body has run
CAP = ("mem_abs", [(BASETAB, 40), (RGSAV, 9), (RES, 1)])

SLOTNAME = ["name", "colr", "patt", "satr", "spat"]


def decode(raw: str | None) -> tuple[list[int], list[int]] | None:
    if not raw:
        return None
    b = bytes.fromhex(raw)
    base = [b[2 * i] | (b[2 * i + 1] << 8) for i in range(20)]
    regs = list(b[40:49])
    if b[49] != 7:            # body never reached the hold loop
        return None
    return base, regs


def show_diff(before, after) -> str:
    if before is None or after is None:
        return "<no capture>"
    bb, br = before
    ab, ar = after
    parts = []
    for i, (x, y) in enumerate(zip(bb, ab)):
        if x != y:
            parts.append(f"BASE({i},{SLOTNAME[i % 5]}) {x:#06x}->{y:#06x}")
    for i, (x, y) in enumerate(zip(br, ar)):
        if x != y:
            nm = f"R{i}" if i < 8 else "STATFL"
            parts.append(f"{nm} {x:#04x}->{y:#04x}")
    return ", ".join(parts) if parts else "(no change)"


def prog(lines: list[str]) -> tuple[str, list[str]]:
    """A stored program that NEVER returns to the prompt.

    Round 3 attempt 1 read every case back as "(no change)" because the program
    ended: falling back to the READY prompt re-selects SCREEN 0 and reprograms
    the VDP from scratch, erasing the very delta under test.  So the case ends
    in a self-GOTO and is captured mid-hold (the G3 bitmap probes' trick).
    """
    body = list(lines) + [f"POKE&H{RES:04X},7"]
    hold = (len(body) + 1) * 10
    return ("stored", body + [f"GOTO {hold}"])


# ---- E1: state delta --------------------------------------------------------
E1_CASES = [
    # (label, mode, statement under test)
    ("s0_base0",   "SCREEN0", "BASE(0)=&H0400"),
    ("s0_base2",   "SCREEN0", "BASE(2)=&H1000"),
    ("s1_base5",   "SCREEN1", "BASE(5)=&H1C00"),
    ("s1_base6",   "SCREEN1", "BASE(6)=&H2000"),
    ("s1_base7",   "SCREEN1", "BASE(7)=&H0800"),
    ("s1_base8",   "SCREEN1", "BASE(8)=&H1F00"),
    ("s1_base9",   "SCREEN1", "BASE(9)=&H3000"),
    ("s2_base10",  "SCREEN2", "BASE(10)=&H1C00"),
    ("s2_base12",  "SCREEN2", "BASE(12)=&H2000"),
    ("s2_base13",  "SCREEN2", "BASE(13)=&H1F00"),
    ("s2_base14",  "SCREEN2", "BASE(14)=&H3000"),
    ("s2_base0",   "SCREEN2", "BASE(0)=&H0400"),   # other mode's slot
    ("s0_base10",  "SCREEN0", "BASE(10)=&H1C00"),  # other mode's slot
    ("s2_vdp2",    "SCREEN2", "VDP(2)=7"),         # raw register write
    ("s2_vdp7",    "SCREEN2", "VDP(7)=&H4F"),
    ("noop",       "SCREEN2", "A=0"),              # control
]


def e1_state_delta():
    print("=== E1  state delta (BASE table + R0..R7 shadows) ===")
    progs = []
    for lab, mode, stmt in E1_CASES:
        progs.append(prog([mode]))              # baseline
        progs.append(prog([mode, stmt]))        # after
    outs = omsx_repl.run_cases(REF, progs, batch=False, capture=CAP,
                               step=6.0, cart=None)
    for i, (lab, mode, stmt) in enumerate(E1_CASES):
        before, after = decode(outs[2 * i]), decode(outs[2 * i + 1])
        print(f"  {lab:10s} {mode:8s} {stmt:18s} -> {show_diff(before, after)}")
    # also print one raw baseline per mode for the record
    for i, (lab, mode, stmt) in enumerate(E1_CASES):
        if lab in ("s0_base0", "s1_base5", "s2_base10"):
            d = decode(outs[2 * i])
            if d:
                print(f"  [baseline {mode}] BASE={[hex(x) for x in d[0]]}")
                print(f"  [baseline {mode}] REGS={[hex(x) for x in d[1]]}")


# ---- E2: hardware reach -----------------------------------------------------
E2_CASES = [
    ("ie_off",  "VDP(1)=VDP(1)AND223"),
    ("control", "A=0"),
]

def e2_hw_reach():
    print("\n=== E2  does VDP(n)= reach the chip? (TIME delta; 0 => yes) ===")
    progs = []
    for lab, stmt in E2_CASES:
        progs.append(("stored", [
            f"POKE&H{RES:04X},255",
            f"SCREEN0:{stmt}",
            "T=TIME:FORI=1TO800:NEXT:D=TIME-T",
            "VDP(1)=VDP(1)OR32",
            f"POKE&H{RES+1:04X},D-INT(D/256)*256:POKE&H{RES+2:04X},INT(D/256):"
            f"POKE&H{RES:04X},0:END",
        ]))
    outs = omsx_repl.run_cases(REF, progs, batch=False,
                               capture=("mem_abs", [(RES, 4)]),
                               step=25.0, cart=None)
    for (lab, stmt), o in zip(E2_CASES, outs):
        if not o:
            print(f"  {lab:8s} {stmt:22s} -> <no capture>")
            continue
        b = bytes.fromhex(o)
        st = "<not reached>" if b[0] == 255 else f"TIME delta = {b[1] | (b[2] << 8)}"
        print(f"  {lab:8s} {stmt:22s} -> {st}")


def main() -> int:
    which = sys.argv[1:] or ["e1", "e2"]
    if "e1" in which: e1_state_delta()
    if "e2" in which: e2_hw_reach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
