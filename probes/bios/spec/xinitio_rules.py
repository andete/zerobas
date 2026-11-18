#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/INITIO.md's EXECUTABLE RULES (docs/spec-method.md §3a): INITIO ($003B) from five desynced states --
scratchpad/XINITIO_run3.out (probes/bios/spec/xinitio.asm documents the cases and the 105-byte record)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/INITIO.md"
OUTPUTS = {"XI": ["af", "bc", "de", "hl", "ix", "iy", "iff", "psg", "r14", "aa", "nchg", "cells"]}
# psg: R0..R13 then R15 (index 14); R14, the input port, is its own field
# the cases, as xinitio.asm's table: interrupts on, PSG base, step, port $AA's high nibble, entry F
CASES = [(0, 0x40, 0x01, 0x00, 0x00), (0, 0xA0, 0x07, 0xF0, 0xFF), (1, 0xFF, 0x00, 0x50, 0x00),
         (1, 0x00, 0x00, 0xA0, 0xFF), (0, 0x5A, 0x13, 0xC0, 0x00)]
REC = 105


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XINITIO_run3.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        b += bytes(1 + REC * len(CASES) - len(b))
        cs = []
        for i, (ei, base, step, aa, f) in enumerate(CASES):
            r = b[1 + REC * i: 1 + REC * (i + 1)]
            if b[0] != 0xA5 or r[REC - 1] != 0xC3:
                sys.exit("FAIL: an XINITIO record has no sentinel")
            w = [(r[2 * j] << 8) | r[2 * j + 1] for j in range(6)]
            n = r[30] | (r[31] << 8)
            cells = [(r[32 + 3 * j] | (r[33 + 3 * j] << 8), r[34 + 3 * j]) for j in range(min(n, 24))]
            cs.append(NS(src="XI", id=f"XI {i + 1}", ei=ei, base=base, step=step, aa_in=aa, f_in=f,
                         af=w[0], bc=w[1], de=w[2], hl=w[3], ix=w[4], iy=w[5], iff=(r[12] >> 2) & 1,
                         psg=list(r[13:27]) + [r[28]], r14=r[27], aa=r[29], nchg=n, cells=cells))
        out[who] = cs
    return out


def pattern(c, k):
    return (c.base + k * c.step) & 0xFF


# QUETAB's three voice descriptors after INITIO: put, get, backup 0, size $7F, the buffer's address
VOICE_BUF = (0xF975, 0xF9F5, 0xFA75)
RESET = ([(0xF959 + 6 * v + k, x) for v, a in enumerate(VOICE_BUF)
          for k, x in enumerate((0, 0, 0, 0x7F, a & 0xFF, a >> 8))]
         + [(0xFB3F, 0), (0xFB40, 0)])


def seeded(c):
    return c.ei == 0                              # the probe seeds PLAY's cells only with interrupts staying off


def play_ok(c):
    """the changed cells are exactly those of RESET that the seed made different (the seed is $5A.. in QUETAB /
    QUEBAK, $A5 in MUSICF / PLYCNT)"""
    seed = {0xF959 + k: (0x5A + k) & 0xFF for k in range(28)}
    seed.update({0xFB3F: 0xA5, 0xFB40: 0xA5})
    want = [(a, v) for a, v in RESET if seed[a] != v]
    return c.nchg == len(want) and c.cells == want


S1 = "1. INITIO ($003B)"

RULES = [
    Rule("R-IO-PSG", S1, "The PSG: R7 := $B8 (the mixer bits are active-low: tone ENABLED on A / B / C, noise disabled, port A input, "
         "port B output -- the silence comes from the amplitudes), "
         "R8 / R9 / R10 := 0 (the three amplitudes), R11 := $0B, R15 := $CF; R0-R6, R12 and R13 are left as found -- "
         "for five patterns, all $00 and all $FF included.", lambda c: True,
         lambda c: (c.psg[7], c.psg[8], c.psg[9], c.psg[10], c.psg[11], c.psg[14]) == (0xB8, 0, 0, 0, 0x0B, 0xCF)
         and all(c.psg[k] == pattern(c, k) for k in (0, 1, 2, 3, 4, 5, 6, 12, 13))),
    Rule("R-IO-AA", S1, "Port $AA's high nibble (the PPI's port C: the CAPS lamp, the click, the cassette motor and "
         "output) is left as found -- 0, 5, A, C and F. (Its low nibble, the keyboard row, is the interrupt's: it "
         "may run an interrupt between the return and the read; R-IO-AA4 closes that window.)",
         lambda c: True,
         lambda c: c.aa >> 4 == c.aa_in >> 4),
    Rule("R-IO-PLAY", S1, "PLAY's state is reset: the three voice queues' descriptors -- in the table QUEUES points to, $F959-$F96A "
         "as the boot leaves it (R-IO-QUEUES) -- to put / get / backup 0, "
         "size $7F and their buffers $F975, $F9F5, $FA75; MUSICF ($FB3F) and PLYCNT ($FB40) to 0. The fourth (RS-232) "
         "queue's descriptor and QUEBAK ($F96B-$F974) are left, from garbage; no other cell of the work area "
         "$F380-$FFFF changes (cells not seeded held what the boot or the previous case left: R-IO-SEED seeds "
         "more).", seeded, play_ok),
    Rule("R-IO-QUIET", S1, "A second call, from the state the previous INITIO left (PLAY idle), changes nothing in "
         "the work area (R-IO-BOOT: the first call after boot).",
         lambda c: not seeded(c), lambda c: c.nchg == 0 and c.cells == []),
    Rule("R-IO-REGS", S1, "On return A = $FF and F = $54 whatever the flags on entry ($00 / $FF); D is kept and E is "
         "$0B; BC, HL, IX and IY are kept.", lambda c: True,
         lambda c: (c.af, c.de, c.bc, c.hl, c.ix, c.iy) == (0xFF54, 0x9B0B, 0x1357, 0x2468, 0x4321, 0x8765)),
    Rule("R-IO-EI", S1, "It returns with interrupts ENABLED, also when entered with them disabled.", lambda c: True,
         lambda c: c.iff == 1),
]

UNREAD = {f"XI {i + 1}": (["r14"], "R14 is the PSG's INPUT port A: it reads the joystick lines, not "
                                       "anything INITIO writes")
          for i in range(len(CASES))}


# ---- round 2: XINITIO2 (probes/bios/spec/xinitio2.asm; scratchpad/XINITIO2_run2.out), after the first review ----
OUTPUTS["XI2"] = ["af", "bc", "de", "hl", "ix", "iy", "afx", "bcx", "dex", "hlx", "iff", "psg", "r14", "aa", "nchg",
                  "cells", "vcb"]
# interrupts on, PSG base, step, port $AA's high nibble, entry F, the register set, the seed mode
CASES2 = [(0, 0x40, 0x01, 0x00, 0x00, 0, 1), (1, 0xA0, 0x07, 0xF0, 0xFF, 0, 2), (1, 0x5A, 0x13, 0x50, 0x00, 1, 2),
          (0, 0xFF, 0x00, 0xA0, 0xFF, 1, 1), (0, 0x00, 0x00, 0xC0, 0x00, 1, 0)]
REC2 = 224
# each register set: entry A, then BC DE HL IX IY, then AF' BC' DE' HL'
SETS = [(0xA7, 0x1357, 0x9BDF, 0x2468, 0x4321, 0x8765, 0xC35A, 0x1111, 0x2222, 0x3333),
        (0x00, 0xECA8, 0x6420, 0xDB97, 0xBCDE, 0x789A, 0x3CA5, 0x8642, 0x0FE1, 0x7531)]
_cases1 = cases


def cases():                                     # noqa: F811
    out = _cases1()
    t = open(os.path.join(ROOT, "scratchpad", "XINITIO2_run2.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        b += bytes(1 + REC2 * len(CASES2) - len(b))
        for i, (ei, base, step, aa, f, rs, seed) in enumerate(CASES2):
            r = b[1 + REC2 * i: 1 + REC2 * (i + 1)]
            if b[0] != 0xA5 or r[REC2 - 1] != 0xC3:
                sys.exit("FAIL: an XINITIO2 record has no sentinel")
            w = [(r[2 * j] << 8) | r[2 * j + 1] for j in range(10)]
            n = r[38] | (r[39] << 8)
            out[who].append(NS(src="XI2", id=f"XI2 {i + 1}", ei=ei, base=base, step=step, aa_in=aa, f_in=f, rs=rs,
                               seed=seed, afx=w[0], bcx=w[1], dex=w[2], hlx=w[3], af=w[4], bc=w[5], de=w[6], hl=w[7],
                               ix=w[8], iy=w[9], iff=(r[20] >> 2) & 1, psg=list(r[21:35]) + [r[36]], r14=r[35],
                               aa=r[37], nchg=n,
                               cells=[(r[40 + 3 * j] | (r[41 + 3 * j] << 8), r[42 + 3 * j]) for j in range(min(n, 24))],
                               vcb=list(r[112:223])))
    return out


for _r in RULES:
    _r.select = (lambda s: (lambda c: c.src == "XI" and s(c)))(_r.select)

VCB_RESET = [0] * 15 + [0x04, 0x04, 0x78, 0x88, 0xFF] + [0] * 17      # one voice's 37 B after INITIO


def seed_cells(seed):
    """the cells the probe's seed mode set, with the value it set"""
    if seed == 0:
        return {}
    d = {0xF959 + k: (0x5A + k) & 0xFF for k in range(28)}
    if seed == 1:
        d.update({0xFB3F: 0xA5, 0xFB40: 0xA5})
        d.update({0xFB41 + k: (0x33 + k) & 0xFF for k in range(111)})
    return d


def reset_changes(seed):
    """(address, value after INITIO) for each seeded cell the reset gives another value, in address order"""
    reset = dict(RESET)
    reset.update({0xFB41 + 37 * v + k: x for v in range(3) for k, x in enumerate(VCB_RESET)})
    return sorted((a, reset[a]) for a, v in seed_cells(seed).items() if a in reset and reset[a] != v)


def changed_by_reset(seed):
    """the number of seeded cells the reset gives another value"""
    return len(reset_changes(seed))


S2 = "2. Round 2: a second register set and the shadow registers; the reset with interrupts ON; the voice control blocks (XINITIO2)"

RULES += [
    Rule("R-IO-REGS2", S2, "Whatever A was on entry ($A7 or $00), A = $FF and F = $54 on return; D is kept ($9B and "
         "$64 measured) and E is $0B; BC, HL, IX, IY and the shadow registers AF' / BC' / DE' / HL' are kept -- two "
         "full sets of entry values.", lambda c: c.src == "XI2",
         lambda c: (c.af, c.de >> 8, c.de & 0xFF) == (0xFF54, SETS[c.rs][2] >> 8, 0x0B)
         and (c.bc, c.hl, c.ix, c.iy, c.afx, c.bcx, c.dex, c.hlx) == SETS[c.rs][1:2] + SETS[c.rs][3:]),
    Rule("R-IO-PSG2", S2, "R-IO-PSG and R-IO-AA hold here too, with interrupts on and off and both register sets.",
         lambda c: c.src == "XI2",
         lambda c: (c.psg[7], c.psg[8], c.psg[9], c.psg[10], c.psg[11], c.psg[14]) == (0xB8, 0, 0, 0, 0x0B, 0xCF)
         and all(c.psg[k] == pattern(c, k) for k in (0, 1, 2, 3, 4, 5, 6, 12, 13)) and c.aa >> 4 == c.aa_in >> 4
         and c.iff == 1),
    Rule("R-IO-PLAYEI", S2, "Entered with interrupts ON (MUSICF 0, so the interrupt plays nothing), INITIO resets "
         "the three voice descriptors (QUEUES at $F959) the same way, from garbage; the RS-232 descriptor and QUEBAK "
         "stay.",
         lambda c: c.src == "XI2" and c.seed == 2,
         lambda c: c.nchg == changed_by_reset(2) and c.cells == [(a, v) for a, v in RESET if a < 0xFB00]),
    Rule("R-IO-VCB", S2, "The three voice control blocks (37 B each at $FB41, $FB66, $FB8B) are rewritten: offsets "
         "15-19 = 04 04 78 88 FF, every other byte 0 -- from garbage in XI2 1 / 4; in the other cases the blocks "
         "already held these values.", lambda c: c.src == "XI2", lambda c: c.vcb == VCB_RESET * 3),
    Rule("R-IO-SEED", S2, "With PLAY's state, QUEBAK and the voice control blocks all garbage, exactly the cells "
         "R-IO-PLAY and R-IO-VCB name change, no other; with nothing seeded, nothing changes.",
         lambda c: c.src == "XI2" and c.seed != 2,
         lambda c: c.nchg == changed_by_reset(c.seed) and c.cells == reset_changes(c.seed)[:24]),
]

UNREAD.update({f"XI2 {i + 1}": (["r14"], "R14 is the PSG's INPUT port A: it reads the joystick lines, not "
                                         "anything INITIO writes") for i in range(len(CASES2))})


# ---- round 3: XINITIO3 (probes/bios/spec/xinitio3.asm; scratchpad/XINITIO3_run1.out), after the confirming review ----
OUTPUTS["XI3"] = OUTPUTS["XI2"]
# ei, PSG base, step, port $AA (whole byte), F, register set, desc seed, VCB seed, MUSICF/PLYCNT written, MUSICF, PLYCNT
CASES3 = [(0, 0x40, 0x01, 0x35, 0x00, 0, 0, 0, 0, 0x00, 0x00), (0, 0xA0, 0x07, 0x35, 0xFF, 0, 1, 1, 1, 0x00, 0x5A),
          (1, 0x5A, 0x13, 0xC0, 0x00, 1, 1, 1, 1, 0x00, 0x00), (0, 0xFF, 0x00, 0xA5, 0xFF, 1, 0, 0, 1, 0xFF, 0x00),
          (0, 0x00, 0x00, 0xF0, 0x00, 0, 1, 1, 1, 0x5A, 0xFF), (1, 0x33, 0x05, 0x50, 0xFF, 0, 0, 1, 1, 0x00, 0x33)]
_cases2 = cases


def cases():                                     # noqa: F811
    out = _cases2()
    t = open(os.path.join(ROOT, "scratchpad", "XINITIO3_run1.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        b += bytes(1 + REC2 * len(CASES3) - len(b))
        for i, (ei, base, step, aa, f, rs, desc, vcb, mp, mus, ply) in enumerate(CASES3):
            r = b[1 + REC2 * i: 1 + REC2 * (i + 1)]
            if b[0] != 0xA5 or r[REC2 - 1] != 0xC3:
                sys.exit("FAIL: an XINITIO3 record has no sentinel")
            w = [(r[2 * j] << 8) | r[2 * j + 1] for j in range(10)]
            n = r[38] | (r[39] << 8)
            out[who].append(NS(src="XI3", id=f"XI3 {i + 1}", ei=ei, base=base, step=step, aa_in=aa, f_in=f, rs=rs,
                               desc=desc, vcbseed=vcb, mp=mp, mus=mus, ply=ply,
                               afx=w[0], bcx=w[1], dex=w[2], hlx=w[3], af=w[4], bc=w[5], de=w[6], hl=w[7],
                               ix=w[8], iy=w[9], iff=(r[20] >> 2) & 1, psg=list(r[21:35]) + [r[36]], r14=r[35],
                               aa=r[37], nchg=n,
                               cells=[(r[40 + 3 * j] | (r[41 + 3 * j] << 8), r[42 + 3 * j]) for j in range(min(n, 24))],
                               vcb=list(r[112:223])))
    return out


def seed3(c):
    """the cells XINITIO3's seeds set in case c, with the value set"""
    d = {}
    if c.desc:
        d.update({0xF959 + k: (0x5A + k) & 0xFF for k in range(28)})
    if c.vcbseed:
        d.update({0xFB41 + k: (0x33 + k) & 0xFF for k in range(111)})
    if c.mp:
        d.update({0xFB3F: c.mus, 0xFB40: c.ply})
    return d


def reset3(c):
    reset = dict(RESET)
    reset.update({0xFB41 + 37 * v + k: x for v in range(3) for k, x in enumerate(VCB_RESET)})
    return sorted((a, reset[a]) for a, v in seed3(c).items() if a in reset and reset[a] != v)


S3 = "3. Round 3: each seed independent, MUSICF / PLYCNT values, the first call after boot (XINITIO3)"

RULES += [
    Rule("R-IO-VCB3", S3, "The voice control blocks are rewritten to R-IO-VCB's values whatever else holds: with "
         "interrupts ON and MUSICF 0 (XI3 3), with the blocks seeded and only PLYCNT besides (XI3 6), and already at a "
         "cartridge's INIT during boot (XI3 1, "
         "the first call: nothing to change).", lambda c: c.src == "XI3", lambda c: c.vcb == VCB_RESET * 3),
    Rule("R-IO-MP", S3, "MUSICF and PLYCNT become 0 whatever they held -- 0 / $5A, $FF / 0 (MUSICF alone), $5A / $FF, "
         "0 / $33 (XI3 2 / 4 / 5 / 6; XI3 3 seeds 0 / 0) -- and exactly the seeded cells the reset gives another "
         "value change, no other.",
         lambda c: c.src == "XI3" and c.mp,
         lambda c: c.nchg == len(reset3(c)) and c.cells == reset3(c)[:24]),
    Rule("R-IO-BOOT", S3, "The first call after boot, nothing seeded, changes no cell of the work area: the boot "
         "already left PLAY's state, the voice control blocks included, at INITIO's values.",
         lambda c: c.src == "XI3" and not (c.desc or c.vcbseed or c.mp), lambda c: c.nchg == 0 and c.cells == []),
    Rule("R-IO-REGS3", S3, "R-IO-REGS2 and R-IO-PSG2 hold here too: A $FF, F $54, E $0B, the rest and the shadow "
         "registers kept; the PSG; port $AA's high nibble (CAPS, click, motor, cassette out) as found; interrupts on.",
         lambda c: c.src == "XI3",
         lambda c: (c.af, c.de >> 8, c.de & 0xFF) == (0xFF54, SETS[c.rs][2] >> 8, 0x0B)
         and (c.bc, c.hl, c.ix, c.iy, c.afx, c.bcx, c.dex, c.hlx) == SETS[c.rs][1:2] + SETS[c.rs][3:]
         and (c.psg[7], c.psg[8], c.psg[9], c.psg[10], c.psg[11], c.psg[14]) == (0xB8, 0, 0, 0, 0x0B, 0xCF)
         and all(c.psg[k] == pattern(c, k) for k in (0, 1, 2, 3, 4, 5, 6, 12, 13))
         and c.aa >> 4 == c.aa_in >> 4 and c.iff == 1),
]

UNREAD.update({f"XI3 {i + 1}": (["r14"], "R14 is the PSG's INPUT port A: it reads the joystick lines, not "
                                         "anything INITIO writes") for i in range(len(CASES3))})


# ---- round 4: XINITIO4 (probes/bios/spec/xinitio4.asm; scratchpad/XINITIO4_run1.out), after the third review ----
OUTPUTS["XI4"] = OUTPUTS["XI2"] + ["ireg"]
# XINITIO3's fields, then the parse-cell seed and the I register's value
CASES4 = [(0, 0x40, 0x01, 0x35, 0x00, 0, 0, 0, 0, 0x00, 0x00, 1, 0x5A),
          (1, 0xA0, 0x07, 0xC3, 0xFF, 1, 1, 0, 1, 0x00, 0x00, 1, 0xA5),
          (0, 0x5A, 0x13, 0x96, 0x00, 0, 1, 1, 1, 0x5A, 0xFF, 1, 0x00)]
REC4 = 225
_cases3 = cases


def cases():                                     # noqa: F811
    out = _cases3()
    t = open(os.path.join(ROOT, "scratchpad", "XINITIO4_run1.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        b += bytes(1 + REC4 * len(CASES4) - len(b))
        for i, (ei, base, step, aa, f, rs, desc, vcb, mp, mus, ply, parse, ireg) in enumerate(CASES4):
            r = b[1 + REC4 * i: 1 + REC4 * (i + 1)]
            if b[0] != 0xA5 or r[REC4 - 1] != 0xC3:
                sys.exit("FAIL: an XINITIO4 record has no sentinel")
            w = [(r[2 * j] << 8) | r[2 * j + 1] for j in range(10)]
            n = r[38] | (r[39] << 8)
            out[who].append(NS(src="XI4", id=f"XI4 {i + 1}", ei=ei, base=base, step=step, aa_in=aa, f_in=f, rs=rs,
                               desc=desc, vcbseed=vcb, mp=mp, mus=mus, ply=ply, parse=parse, ireg_in=ireg,
                               afx=w[0], bcx=w[1], dex=w[2], hlx=w[3], af=w[4], bc=w[5], de=w[6], hl=w[7],
                               ix=w[8], iy=w[9], iff=(r[20] >> 2) & 1, psg=list(r[21:35]) + [r[36]], r14=r[35],
                               aa=r[37], nchg=n,
                               cells=[(r[40 + 3 * j] | (r[41 + 3 * j] << 8), r[42 + 3 * j]) for j in range(min(n, 24))],
                               vcb=list(r[112:223]), ireg=r[223]))
    return out


S4 = ("4. Round 4: the parse cells, the I register, and a read window no interrupt can enter (XINITIO4: the VDP status "
      "read just before the call, `di` the first instruction after it)")

RULES += [
    Rule("R-IO-I", S4, "The I register is kept ($5A, $A5, $00).", lambda c: c.src == "XI4", lambda c: c.ireg == c.ireg_in),
    Rule("R-IO-PARSE", S4, "PLAY's parse cells $FB35-$FB3E (VOICEN, MCLPTR, QUEUEN ...) are left, from garbage: the "
         "changed cells are exactly R-IO-PLAY's / R-IO-VCB's / R-IO-MP's.", lambda c: c.src == "XI4",
         lambda c: c.nchg == len(reset3(c)) and c.cells == reset3(c)[:24]),
    Rule("R-IO-AA4", S4, "With interrupts off on entry and no interrupt after the return, port $AA is left WHOLE, the "
         "keyboard-row nibble included ($35, $96); R15 still reads $CF, so INITIO wrote it, not an interrupt.",
         lambda c: c.src == "XI4" and c.ei == 0, lambda c: c.aa == c.aa_in and c.psg[14] == 0xCF),
    Rule("R-IO-REGS4", S4, "R-IO-REGS3's registers, the PSG and port $AA's high nibble hold here too.",
         lambda c: c.src == "XI4",
         lambda c: (c.af, c.de >> 8, c.de & 0xFF) == (0xFF54, SETS[c.rs][2] >> 8, 0x0B)
         and (c.bc, c.hl, c.ix, c.iy, c.afx, c.bcx, c.dex, c.hlx) == SETS[c.rs][1:2] + SETS[c.rs][3:]
         and (c.psg[7], c.psg[8], c.psg[9], c.psg[10], c.psg[11], c.psg[14]) == (0xB8, 0, 0, 0, 0x0B, 0xCF)
         and all(c.psg[k] == pattern(c, k) for k in (0, 1, 2, 3, 4, 5, 6, 12, 13)) and c.aa >> 4 == c.aa_in >> 4),
    Rule("R-IO-VCB4", S4, "R-IO-VCB holds here too.", lambda c: c.src == "XI4", lambda c: c.vcb == VCB_RESET * 3),
]


def seed3(c):                                    # noqa: F811 -- XINITIO4's parse seed joins XINITIO3's
    d = {}
    if c.desc:
        d.update({0xF959 + k: (0x5A + k) & 0xFF for k in range(28)})
    if c.vcbseed:
        d.update({0xFB41 + k: (0x33 + k) & 0xFF for k in range(111)})
    if c.mp:
        d.update({0xFB3F: c.mus, 0xFB40: c.ply})
    if getattr(c, "parse", 0):
        d.update({0xFB35 + k: (0xC1 + k) & 0xFF for k in range(10)})
    return d


UNREAD.update({f"XI4 {i + 1}": (["r14", "iff"], "R14 is the PSG's input port; IFF2 reads the probe's own `di` "
                                                "(the first instruction after the return: round 4's read window)")
               for i in range(len(CASES4))})


# ---- round 5: XINITIO5 (probes/bios/spec/xinitio5.asm; scratchpad/XINITIO5_run4.out), after the fourth / fifth reviews
OUTPUTS["XI5"] = OUTPUTS["XI4"] + ["jifb", "jifa", "quetab1", "q9eb7"]
# XINITIO4's fields, then the QUEUES seed ($9EB7)
CASES5 = [(0, 0x00, 0x00, 0x35, 0x00, 0, 1, 0, 1, 0xFF, 0x00, 0, 0x5A, 1),
          (0, 0xFF, 0x00, 0x96, 0xFF, 1, 0, 1, 1, 0x00, 0x5A, 1, 0xA5, 1),
          (0, 0xA0, 0x07, 0xC3, 0x00, 1, 1, 1, 1, 0x5A, 0xFF, 0, 0x00, 0)]
REC5 = 275
QDESC = [x for a in VOICE_BUF for x in (0, 0, 0, 0x7F, a & 0xFF, a >> 8)]       # the three reset descriptors
_cases4 = cases


def cases():                                     # noqa: F811
    out = _cases4()
    t = open(os.path.join(ROOT, "scratchpad", "XINITIO5_run4.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        b += bytes(1 + REC5 * len(CASES5) - len(b))
        for i, (ei, base, step, aa, f, rs, desc, vcb, mp, mus, ply, parse, ireg, qs) in enumerate(CASES5):
            r = b[1 + REC5 * i: 1 + REC5 * (i + 1)]
            if b[0] != 0xA5 or r[REC5 - 1] != 0xC3:
                sys.exit("FAIL: an XINITIO5 record has no sentinel")
            w = [(r[2 * j] << 8) | r[2 * j + 1] for j in range(10)]
            n = r[38] | (r[39] << 8)
            out[who].append(NS(src="XI5", id=f"XI5 {i + 1}", ei=ei, base=base, step=step, aa_in=aa, f_in=f, rs=rs,
                               desc=desc, vcbseed=vcb, mp=mp, mus=mus, ply=ply, parse=parse, ireg_in=ireg, qseed=qs,
                               afx=w[0], bcx=w[1], dex=w[2], hlx=w[3], af=w[4], bc=w[5], de=w[6], hl=w[7],
                               ix=w[8], iy=w[9], iff=(r[20] >> 2) & 1, psg=list(r[21:35]) + [r[36]], r14=r[35],
                               aa=r[37], nchg=n,
                               cells=[(r[40 + 3 * j] | (r[41 + 3 * j] << 8), r[42 + 3 * j]) for j in range(min(n, 24))],
                               vcb=list(r[112:223]), ireg=r[223], jifb=r[224] | (r[225] << 8),
                               jifa=r[226] | (r[227] << 8), quetab1=list(r[228:256]), q9eb7=list(r[256:274])))
    return out


def mp5_changes(c):
    """round 5's expected changes: the voice control blocks and MUSICF / PLYCNT, NOT the descriptors at $F959 (QUEUES
    points elsewhere, so INITIO writes them there, outside the work area)"""
    return [(a, v) for a, v in reset3(c) if not (0xF959 <= a <= 0xF96A)]


S5 = ("5. Round 5: under the clean window, with JIFFY as the witness; QUEUES moved (XINITIO5: QUEUES ($F3F3) := $9EB7 "
      "in XI5 1 / 2, left so for XI5 3)")

RULES += [
    Rule("R-IO-CLEAN", S5, "No interrupt ran between the VDP status read before the call and the reads after it in "
         "XI5 2 and 3: JIFFY is the same before and after. (In XI5 1 the VG-8020 took one: JIFFY moved by 1.) With "
         "the PSG all $FF (XI5 2) and a pattern (XI5 3) R7 / R8-R10 / R11 / R15 are as R-IO-PSG says, so INITIO wrote "
         "them, not an interrupt.", lambda c: c.src == "XI5" and c.base != 0x00,
         lambda c: c.jifb == c.jifa
         and (c.psg[7], c.psg[8], c.psg[9], c.psg[10], c.psg[11], c.psg[14]) == (0xB8, 0, 0, 0, 0x0B, 0xCF)),
    Rule("R-IO-QUEUES", S5, "INITIO writes the three voice-queue descriptors into the table QUEUES ($F3F3) points to: "
         "with QUEUES = $9EB7 the 18 bytes there become R-IO-PLAY's descriptors (0, 0, 0, $7F, $F975 / $F9F5 / "
         "$FA75), and $F959.. keeps its garbage, as do its bytes +18..+27 (read after one more interrupt). QUEUES itself is left (it is in no case's changed cells). As the boot "
         "leaves QUEUES ($F959), rounds 1-4 saw the reset at $F959.", lambda c: c.src == "XI5",
         lambda c: c.q9eb7 == QDESC and c.quetab1[:18] != QDESC
         and c.quetab1[18:] == [(0x5A + k) & 0xFF for k in range(18, 28)]),
    Rule("R-IO-MP5", S5, "Under the clean window too: MUSICF / PLYCNT become 0 ($FF / 0, 0 / $5A, $5A / $FF), the voice "
         "control blocks R-IO-VCB's values, and exactly those seeded cells change.", lambda c: c.src == "XI5",
         lambda c: c.vcb == VCB_RESET * 3 and c.nchg == len(mp5_changes(c)) and c.cells == mp5_changes(c)[:24]),
    Rule("R-IO-REGS5", S5, "The registers, I and the PSG (all $00, all $FF and a pattern) as R-IO-REGS3 / R-IO-I / "
         "R-IO-PSG say; port $AA WHOLE in the clean cases ($96, $C3), its high nibble in XI5 1, where the interrupt "
         "that slipped in scanned the keyboard ($35 read as $3A).",
         lambda c: c.src == "XI5",
         lambda c: (c.af, c.de >> 8, c.de & 0xFF) == (0xFF54, SETS[c.rs][2] >> 8, 0x0B)
         and (c.bc, c.hl, c.ix, c.iy, c.afx, c.bcx, c.dex, c.hlx) == SETS[c.rs][1:2] + SETS[c.rs][3:]
         and all(c.psg[k] == pattern(c, k) for k in (0, 1, 2, 3, 4, 5, 6, 12, 13))
         and (c.aa >> 4 == c.aa_in >> 4 if c.id == "XI5 1" else c.aa == c.aa_in)
         and c.ireg == c.ireg_in
         and (c.psg[7], c.psg[8], c.psg[9], c.psg[10], c.psg[11], c.psg[14]) == (0xB8, 0, 0, 0, 0x0B, 0xCF)),
]

UNREAD.update({f"XI5 {i + 1}": (["r14", "iff"], "R14 is the PSG's input port; IFF2 reads the probe's own `di` "
                                                "(round 5's read window)") for i in range(len(CASES5))})
UNSTABLE = {"XI5 1": (["jifb", "jifa"], "the read window's witness, not INITIO's output: the VG-8020 itself does "
                     "not reproduce it -- XI5 1 took no interrupt in scratchpad/XINITIO5_run2.out (JIFFY $BD -> $BD) and "
                     "one in scratchpad/XINITIO5_run4.out ($BD -> $BE), so R-IO-CLEAN leaves this case out")}


# ---- round 6: XINITIO6 (probes/bios/spec/xinitio6.asm; scratchpad/XINITIO6_run1.out), after the sixth review ----
OUTPUTS["XI6"] = ["jifb", "jifa", "qb", "qa", "tb", "ta", "fb", "fa", "musicf"]
CASES6 = [(0x0000, 0x00, 0x00, 0), (0x9EB7, 0x40, 0x90, 0), (0xA123, 0xC0, 0x10, 0),   # QUEUES (0 = as found),
          (0xF959, 0x60, 0x60, 0), (0xF959, 0x20, 0x20, 0xFF)]                       # seeds, MUSICF
_cases5 = cases


def cases():                                     # noqa: F811
    out = _cases5()
    t = open(os.path.join(ROOT, "scratchpad", "XINITIO6_run3.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        b += bytes(1 + 125 * len(CASES6) - len(b))
        for i, (q, qs, fs, mus) in enumerate(CASES6):
            r = b[1 + 125 * i: 1 + 125 * (i + 1)]
            if b[0] != 0xA5 or r[124] != 0xC3:
                sys.exit("FAIL: an XINITIO6 record has no sentinel")
            w = lambda o: r[o] | (r[o + 1] << 8)  # noqa: E731
            out[who].append(NS(src="XI6", id=f"XI6 {i + 1}", q_in=q, qs=qs, fs=fs, mus=mus, jifb=w(0), jifa=w(2), qb=w(4),
                               qa=w(6), tb=list(r[8:36]), ta=list(r[36:64]), fb=list(r[64:92]), fa=list(r[92:120]),
                               musicf=r[120]))
    return out


def seeded28(s):
    return [(s + k) & 0xFF for k in range(28)]


S6 = ("6. Round 6: QUEUES and its table read BEFORE any interrupt can run (XINITIO6: the clean window, JIFFY as the "
      "witness, the reads before any `ei`)")

RULES += [
    Rule("R-IO-QBOOT", S6, "At the first call after boot QUEUES is $F959 and its table already holds R-IO-PLAY's "
         "descriptors, the RS-232 descriptor and QUEBAK 0; the call changes none of it, and no interrupt runs.",
         lambda c: c.src == "XI6" and c.q_in == 0,
         lambda c: c.jifb == c.jifa and c.qb == c.qa == 0xF959 and c.tb == c.ta == c.fb == c.fa == QDESC + [0] * 10
         and c.musicf == 0),
    Rule("R-IO-QUEUES6", S6, "INITIO ITSELF writes the descriptors where QUEUES points: with QUEUES $9EB7 or $A123 and its "
         "28-byte table garbage, the table's first 18 bytes become R-IO-PLAY's descriptors (the buffer addresses "
         "$F975 / $F9F5 / $FA75 whatever QUEUES is), its bytes +18..+27 keep their garbage, $F959.. (the fixed "
         "$F96B-$F974 included) keeps its own, and QUEUES is kept -- with JIFFY unchanged: no interrupt ran.",
         lambda c: c.src == "XI6" and c.q_in not in (0, 0xF959),
         lambda c: c.jifb == c.jifa and c.qb == c.qa == c.q_in and c.tb == seeded28(c.qs)
         and c.ta == QDESC + seeded28(c.qs)[18:] and c.fb == c.fa == seeded28(c.fs) and c.musicf == 0),
    Rule("R-IO-QF959", S6, "With QUEUES at the boot's $F959 and that table garbage, the descriptors are written "
         "there: the first 18 bytes become R-IO-PLAY's, bytes +18..+27 keep their garbage. (In this run an interrupt "
         "slipped into the window; XI6 5 shows the same with none: R-IO-MPFF.)",
         lambda c: c.src == "XI6" and c.q_in == 0xF959 and c.mus == 0,
         lambda c: c.qb == c.qa == 0xF959 and c.tb == c.fb == seeded28(c.fs)
         and c.ta == c.fa == QDESC + seeded28(c.fs)[18:] and c.musicf == 0),
    Rule("R-IO-MPFF", S6, "With MUSICF $FF (every bit) and no interrupt in the window (JIFFY unchanged), INITIO itself "
         "clears MUSICF -- and writes the descriptors at $F959 as R-IO-QF959.", lambda c: c.src == "XI6" and c.mus,
         lambda c: c.jifb == c.jifa and c.musicf == 0 and c.qb == c.qa == 0xF959 and c.tb == c.fb == seeded28(c.fs)
         and c.ta == c.fa == QDESC + seeded28(c.fs)[18:]),
]

UNSTABLE["XI6 4"] = (["jifb", "jifa"], "the read window's witness, not INITIO's output: the VG-8020 does not reproduce "
                                       "it -- no interrupt in scratchpad/XINITIO6_run2.out (JIFFY $BD -> $BD), one in "
                                       "scratchpad/XINITIO6_run3.out ($BD -> $BE)")
