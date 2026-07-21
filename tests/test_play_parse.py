# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: the audio Slice-2a MML parser tenant (play_parse_tenant), no emulator.

This is the load-bearing fast layer for Slice 2a (docs/spec-basic-audio-play-
slice2a.md §8): it RUNS the page-1 parser tenant against representative MML and
DECODES the resulting VOICxQ packet bytes back into (pitch, amplitude, frames),
asserting them against the MML via the shared oracle tests/mml_ref.py. A green
assembly proves nothing here -- the arc lesson is that only running the parser
catches register/ordering bugs (memory: error-handling-arc).

The tenant is a pure RAM leaf, so we assemble the whole sub image and CALL the
tenant label directly with the per-voice (ptr,len) + AUDIO_VMASK marshalled into
RAM exactly as the resident ex_play stub would. We also check the Q2 RAM-
faithfulness surface: MUSICF reflects the present voices, and each QUETAB ring
descriptor's byte count / buffer address land at the reference addresses.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402
import mml_ref  # noqa: E402

SUB_ROM = "/tmp/zb_playparse_sub.rom"
SUB_SYM = "/tmp/zb_playparse_sub.sym"

# Work-area addresses (mirror basic/sysvars.inc; the tenant writes these).
QUETAB = 0xF959
VOICAQ = 0xF975
MUSICF = 0xFB3F
PLYCNT = 0xFB40
VCBA = 0xFB41
VCB_STRIDE = 0x25
VCX_VCXLEN = 2
VCX_VCXPTR = 3
VCX_TEMPO = 17
AUDIO_VMASK = 0xE9FB
AUDIO_STATUS = 0xE9FC

QD_STRIDE = 6
QD_PUT, QD_GET, QD_PUTBAK, QD_SIZE, QD_ADDR = 0, 1, 2, 3, 4

OP_NOTE, OP_ENV, OP_END = 0x00, 0x01, 0xFF
SRC = 0x8200  # where we place MML source strings (RAM, visible to a page-1 tenant)


def build():
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", SUB_ROM, SUB_SYM],
                   cwd=ROOT, check=True, capture_output=True)


def decode_queue(m, voice):
    """Walk VOICxQ[voice] as a PLAY_OP_* stream -> list of decoded packets."""
    base = VOICAQ + voice * 128
    p = base
    out = []
    for _ in range(200):  # guard
        op = m.mem[p]
        if op == OP_END:
            out.append(("END",))
            break
        if op == OP_NOTE:
            per = m.mem[p + 1] | (m.mem[p + 2] << 8)
            amp = m.mem[p + 3]
            fr = m.mem[p + 4] | (m.mem[p + 5] << 8)
            out.append(("NOTE", per, amp, fr))
            p += 6
        elif op == OP_ENV:
            shape = m.mem[p + 1]
            period = m.mem[p + 2] | (m.mem[p + 3] << 8)
            out.append(("ENV", shape, period))
            p += 4
        else:
            out.append(("BAD", op))
            break
    return out


def parse(voices, seed=True):
    """Run the tenant on `voices` (list of up-to-3 MML byte strings; None = absent).
    Returns (machine, status). seed=True zeroes the work area so pt_init seeds the
    cold-boot defaults (TEMPOX==0 sentinel)."""
    m = Machine(SUB_ROM, SUB_SYM, rom_base=0x0000)
    if seed:
        for a in range(0xF800, 0xFC00):
            m.mem[a] = 0
    mask = 0
    off = SRC
    for v, s in enumerate(voices):
        if s is None:
            continue
        m.poke(off, s)
        vcb = VCBA + v * VCB_STRIDE
        m.mem[vcb + VCX_VCXLEN] = len(s)
        m.poke_w(vcb + VCX_VCXPTR, off)
        mask |= (1 << v)
        off += len(s) + 1
    m.mem[AUDIO_VMASK] = mask
    m.mem[AUDIO_STATUS] = 0xEE
    m.call("play_parse_tenant")
    return m, m.mem[AUDIO_STATUS]


def run():
    build()
    fails = 0

    def check(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:52} -> {got!r}"
              + ("" if ok else f"\n      want {want!r}"))

    def note(n, tempo=120, length=4, dots=0, amp=8):
        return ("NOTE", mml_ref.note_period(n), amp, mml_ref.note_frames(tempo, length, dots))

    # note numbers: n = (octave-1)*12 + semitone; C=0,D=2,E=4,F=5,G=7,A=9,B=11
    C4, D4, E4, G4, A4 = 3 * 12 + 0, 3 * 12 + 2, 3 * 12 + 4, 3 * 12 + 7, 3 * 12 + 9

    # --- basic notes at the defaults (O4 L4 T120 V8) ---------------------------
    m, st = parse([b"CDE"])
    check("PLAY \"CDE\" status ok", st, 0)
    check("PLAY \"CDE\" queue", decode_queue(m, 0),
          [note(C4), note(D4), note(E4), ("END",)])
    check("PLAY \"CDE\" MUSICF bit0", m.mem[MUSICF] & 1, 1)
    check("PLAY \"CDE\" QUETAB put=byte count", m.mem[QUETAB + QD_PUT], 3 * 6 + 1)
    check("PLAY \"CDE\" QUETAB addr=VOICAQ",
          m.mem[QUETAB + QD_ADDR] | (m.mem[QUETAB + QD_ADDR + 1] << 8), VOICAQ)

    # --- accidentals (# + -) ---------------------------------------------------
    m, st = parse([b"C#C+D-"])
    check("accidentals C# C+ D-", decode_queue(m, 0),
          [note(C4 + 1), note(C4 + 1), note(D4 - 1), ("END",)])

    # --- octave: O, >, < -------------------------------------------------------
    m, st = parse([b"O5C>C<C"])
    check("octave O5 C >C <C", decode_queue(m, 0),
          [note(5 * 12 + 0 - 12), note(6 * 12 + 0 - 12), note(5 * 12 + 0 - 12), ("END",)])
    # (O5 sets octave 5 -> C = note 5-1)*12; >C bumps to 6; <C back to 5)

    # --- explicit length + dots ------------------------------------------------
    m, st = parse([b"C8C4.C2"])
    check("length C8 C4. C2", decode_queue(m, 0),
          [note(C4, length=8), note(C4, length=4, dots=1), note(C4, length=2), ("END",)])

    # --- L default length ------------------------------------------------------
    m, st = parse([b"L8CC"])
    check("L8 sets default length", decode_queue(m, 0),
          [note(C4, length=8), note(C4, length=8), ("END",)])

    # --- T tempo ---------------------------------------------------------------
    m, st = parse([b"T240C"])
    check("T240 tempo", decode_queue(m, 0), [note(C4, tempo=240), ("END",)])

    # --- V volume --------------------------------------------------------------
    m, st = parse([b"V15C"])
    check("V15 volume", decode_queue(m, 0), [note(C4, amp=15), ("END",)])

    # --- R rest = amp 0 --------------------------------------------------------
    m, st = parse([b"CR4C"])
    check("rest R4", decode_queue(m, 0),
          [note(C4), ("NOTE", 0, 0, mml_ref.note_frames(120, 4)), note(C4), ("END",)])

    # --- N note number ---------------------------------------------------------
    m, st = parse([b"N40N0"])
    check("N40 then N0(rest)", decode_queue(m, 0),
          [note(39), ("NOTE", 0, 0, mml_ref.note_frames(120, 4)), ("END",)])

    # --- '&' is not MSX1 MML (VG-8020 raises ERR5) -> our tenant does too -------
    m, st = parse([b"C&C"])
    check("'&' tie unsupported -> ERR 5", st, 5)

    # --- S/M envelope emits OP_ENV; S sets envelope-mode amplitude $10 ----------
    m, st = parse([b"S3M1000C"])
    check("S3 M1000 C -> ENV packets + envelope-mode note", decode_queue(m, 0),
          [("ENV", 3, 0), ("ENV", 3, 1000), ("NOTE", mml_ref.note_period(C4), 0x10,
           mml_ref.note_frames(120, 4)), ("END",)])

    # --- three voices ----------------------------------------------------------
    m, st = parse([b"C", b"E", b"G"])
    check("three voices C/E/G status", st, 0)
    check("voice0 = C", decode_queue(m, 0), [note(C4), ("END",)])
    check("voice1 = E", decode_queue(m, 1), [note(E4), ("END",)])
    check("voice2 = G", decode_queue(m, 2), [note(G4), ("END",)])
    check("MUSICF = all three", m.mem[MUSICF] & 7, 7)

    # --- empty voice (,,) : voice unchanged, bit clear -------------------------
    m, st = parse([None, b"E", None])
    check("PLAY ,E, : only voice1", m.mem[MUSICF] & 7, 2)
    check("PLAY ,E, voice1 = E", decode_queue(m, 1), [note(E4), ("END",)])

    # --- spaces ignored --------------------------------------------------------
    m, st = parse([b"C D E"])
    check("spaces ignored", decode_queue(m, 0),
          [note(C4), note(D4), note(E4), ("END",)])

    # --- error surface ---------------------------------------------------------
    m, st = parse([b"C?"])
    check("bad command '?' -> ERR 5", st, 5)
    m, st = parse([b"O9"])
    check("O9 out of range -> ERR 5", st, 5)
    m, st = parse([b"T10"])
    check("T10 (<32) -> ERR 5", st, 5)
    m, st = parse([b"C" * 40])           # 40 notes * 6 B = 240 > 128 buffer
    check("overflow (40 notes) -> ERR 15 String too long", st, 15)

    # --- persistence across PLAY statements (D4-B) -----------------------------
    m = Machine(SUB_ROM, SUB_SYM, rom_base=0x0000)
    for a in range(0xF800, 0xFC00):
        m.mem[a] = 0

    def play_on(mach, s, voice=0):
        mach.poke(SRC, s)
        vcb = VCBA + voice * VCB_STRIDE
        mach.mem[vcb + VCX_VCXLEN] = len(s)
        mach.poke_w(vcb + VCX_VCXPTR, SRC)
        mach.mem[AUDIO_VMASK] = 1 << voice
        mach.mem[AUDIO_STATUS] = 0xEE
        mach.call("play_parse_tenant")
        return decode_queue(mach, voice)

    play_on(m, b"O6L8C")                  # sets octave 6, length 8
    q = play_on(m, b"C")                  # a bare C should reuse octave 6, length 8
    check("state persists: 2nd PLAY C uses O6 L8",
          q, [note(6 * 12 + 0 - 12, length=8), ("END",)])
    check("PLYCNT counted two PLAYs", m.mem[PLYCNT], 2)

    print("\n" + (f"{fails} FAILED" if fails else
                  "ALL PASS — the MML parser tenant builds the queues correctly"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
