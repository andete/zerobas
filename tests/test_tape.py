# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Unit test: zerobas-tape cassette BIOS routines (tape/tape.asm), no emulator.

tape.asm is a self-contained C-BIOS page-0 patch: the seven cassette jump
vectors at `org $00E1` and the routine bodies at `org FREE_ORG` ($3A72). pasmo
emits a flat image whose first byte IS address $00E1, so we load it at
rom_base=0x00E1 and the (absolute) symbols line up directly.

The routines are entirely port-I/O (PSG/PPI) plus FSK half-period timing. The
embedded Z80 core models IN/OUT via cpu.io_in / cpu.io_out, and — crucially —
the FSK "half-period count" the reader measures is just *the number of io_in
polls until the sampled level flips*, which the test controls exactly. So the
whole surface is reachable without an emulator and without any wall-clock timing.

Oracle basis (every expected value is independent of the ROM's own output):
  - STMOTR convention: A=0 stop / A=$FF toggle / else start; motor = i8255 PPI
    Port C bit 4 driven via the BSR control register (MSX2 TH / MSX Assembly
    Page). The BSR command bytes (MOTOR_ON/OFF, CASW_0/1) and ports come from
    tape.asm's own EQUs, pulled from the symbol file.
  - cas_baud: the documented work-area comparison — active LOW word ($F406)
    equal to the CS240 reference ($F401) means 2400, anything else (incl. CS120,
    garbage, or a blank area) defaults to 1200 (tape.asm cas_baud).
  - cas_short/long: the FSK-derived half-period constants CAS_HHALF/LHALF (1200)
    and CAS_HHALF24/LHALF24 (2400), selected by the cached CASBAUD byte.
  - cas_islong: the documented threshold — long iff B*4 >= LOWLIM.
  - Write frame (tapout): the documented FSK frame — start bit '0' (low/long
    tone), 8 data bits LSB-first ('0'=one low/long cycle, '1'=two high/short
    cycles), 2 stop bits '1' (four high/short cycles). Asserted two ways: the
    ordered cas_long/cas_short tone-selection sequence, and the cas_cycle count.
  - Read path (tapin): the inverse frame. A synthetic waveform is built to the
    SAME documented FSK spec (start = 2 long halves, '0' = 2 long halves, '1' =
    4 short halves, LSB-first) and fed via io_in; tapin must decode the byte.
    This is spec-conformance, not a copy of the decoder's logic; it cross-checks
    the write-framing test from the opposite direction.
  - Header / flush lengths: CAS_SHORTLEN / CAS_LONGLEN / CAS_FLUSHLEN from the
    symbol file.

CLEAN-ROOM: tape.asm is this project's own code; no reference-BIOS disassembly
is consulted. The FSK frame and tuning constants are documented in tape.asm /
PROVENANCE.md as black-box-oracle-derived, not copied from any ROM listing.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry, zero  # noqa: E402

ROM = "/tmp/zb_tape.rom"
SYM = "/tmp/zb_tape.sym"
ROM_BASE = 0x00E1          # tape.asm's first org -> the flat image starts here


def build():
    src = os.path.join(ROOT, "tape", "tape.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def machine():
    return Machine(ROM, SYM, rom_base=ROM_BASE)


# ---------------------------------------------------------------------------
# A scripted CAS-in sample stream for the reader. cas_half polls IN (PSG_STAT)
# and counts until bit 7 flips; we hand it exactly the samples we want.
# ---------------------------------------------------------------------------
class Samples:
    def __init__(self, seq):
        self.seq = list(seq)
        self.i = 0

    def __call__(self, port):
        if self.i < len(self.seq):
            v = self.seq[self.i]
            self.i += 1
            return v
        # Over-read (shouldn't happen for a well-formed frame): hold last level.
        return self.seq[-1] if self.seq else 0x00


def set_baud_area(m, baud1200=True):
    """Lay down the cassette write-timing work area cas_baud compares against.

    Reference LOW words observed on a real VG-8020 (tape.asm comment): 1200 baud
    leaves the active LOW word = CS120 (53 5c); 2400 sets it = CS240 (25 2d)."""
    s = m.sym
    cs120 = bytes([0x53, 0x5C])
    cs240 = bytes([0x25, 0x2D])
    m.poke(s["CS120_LOW"], cs120)
    m.poke(s["CS240_LOW"], cs240)
    m.poke(s["ACT_LOW"], cs120 if baud1200 else cs240)


# ===========================================================================
# Tier 1 — pure RAM (no I/O)
# ===========================================================================

def test_cas_baud(m, fails):
    """cas_baud: Z set => 1200, Z clear => 2400 (defaults to 1200)."""
    s = m.sym
    cs120 = bytes([0x53, 0x5C])
    cs240 = bytes([0x25, 0x2D])
    m.poke(s["CS120_LOW"], cs120)
    m.poke(s["CS240_LOW"], cs240)

    cases = [
        ("active == CS120 -> 1200", cs120,            True),
        ("active == CS240 -> 2400", cs240,            False),
        ("garbage active -> default 1200", b"\x99\x88", True),
        ("blank active (00 00) -> 1200", b"\x00\x00",  True),
    ]
    # Note: the blank case requires CS120 != 0; the real area is never blank, but
    # the documented default still resolves to 1200 for any non-CS240 value.
    for desc, act, want_1200 in cases:
        m.poke(s["ACT_LOW"], act)
        cpu = m.call("cas_baud")
        got_1200 = zero(cpu)            # Z set => 1200
        ok = got_1200 == want_1200
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  cas_baud: {desc} "
              f"(Z={int(got_1200)}, want 1200={int(want_1200)})")
    return fails


def test_cas_short_long(m, fails):
    """cas_short/cas_long load C with the active-baud half-period count."""
    s = m.sym
    cases = [
        # CASBAUD, routine,      expected C constant
        (0x00, "cas_short", s["CAS_HHALF"]),    # 1200: high tone half
        (0x00, "cas_long",  s["CAS_LHALF"]),    # 1200: low tone half
        (0xFF, "cas_short", s["CAS_HHALF24"]),  # 2400: high tone half
        (0xFF, "cas_long",  s["CAS_LHALF24"]),  # 2400: low tone half
    ]
    for casbaud, routine, want_c in cases:
        m.poke(s["CASBAUD"], casbaud)
        cpu = m.call(routine)
        got = cpu.c
        ok = got == want_c
        fails += not ok
        baud = "2400" if casbaud else "1200"
        print(f"{'PASS' if ok else 'FAIL'}  {routine} @ {baud} -> C={got} "
              f"(want {want_c})")
    return fails


def test_cas_islong(m, fails):
    """cas_islong: CF=1 (long) iff B*4 >= LOWLIM, else CF=0 (short)."""
    s = m.sym
    LOWLIM = 20
    m.poke(s["LOWLIM"], LOWLIM)
    cases = [
        # B,  expected long?  (B*4 vs 20)
        (4, False),   # 16 < 20 -> short
        (5, True),    # 20 >= 20 -> long (boundary)
        (6, True),    # 24 >= 20 -> long
        (3, False),   # 12 < 20 -> short
    ]
    for b, want_long in cases:
        cpu = m.call("cas_islong", b=b)
        got_long = carry(cpu)
        ok = got_long == want_long
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  cas_islong: B={b} (B*4={b*4} vs "
              f"LOWLIM={LOWLIM}) -> long={int(got_long)} (want {int(want_long)})")

    # Fast-baud near-margin: this is WHY LOWLIM is kept in quarter-count units.
    # A fast leader of short halves ~3 counts derives LOWLIM = 7*3 = 21 (see
    # tapion). The 1.5x leader->data transition artifact then measures ~5 counts.
    # cas_islong must reject it as SHORT: 5*4 = 20 < 21. An integer threshold of
    # floor(1.75*3) = 5 would misclassify B=5 as LONG (5 >= 5) — the bug the
    # B*4 fractional precision exists to prevent. A real 2x long (B=6) is LONG:
    # 6*4 = 24 >= 21. (tape.asm cas_islong / tapion_haveavg.)
    m.poke(s["LOWLIM"], 21)
    for b, want_long, note in [
        (3, False, "short carrier"),
        (5, False, "1.5x transition artifact (integer thresh would mis-flag)"),
        (6, True,  "2x real long"),
    ]:
        cpu = m.call("cas_islong", b=b)
        got_long = carry(cpu)
        ok = got_long == want_long
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  cas_islong near-margin: B={b} "
              f"(B*4={b*4} vs 21) -> long={int(got_long)} (want {int(want_long)}; "
              f"{note})")
    return fails


# ===========================================================================
# Tier 2 — port I/O
# ===========================================================================

def test_stmotr(m, fails):
    """stmotr: A=0 stop, A=start (nonzero, not $FF) start, A=$FF toggle.

    Motor = PPI BSR command out to PPI_REGS ($AB): MOTOR_ON / MOTOR_OFF.
    Toggle reads PPI_PORTC bit 4 (0 = motor currently on)."""
    s = m.sym
    PPI = s["PPI_REGS"]
    ON, OFF = s["MOTOR_ON"], s["MOTOR_OFF"]

    # A=0 -> stop
    out = m.record_out()
    m.call("stmotr", a=0)
    ok = out == [(PPI, OFF)]
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  stmotr(A=0) stop -> OUT {out} "
          f"(want [({PPI:#x},{OFF:#x})])")

    # A=1 -> start
    out = m.record_out()
    m.call("stmotr", a=1)
    ok = out == [(PPI, ON)]
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  stmotr(A=1) start -> OUT {out} "
          f"(want [({PPI:#x},{ON:#x})])")

    # A=$FF toggle, motor currently ON (PortC bit4 = 0) -> turn OFF
    m.cpu.io_in = lambda port: 0x00          # bit 4 clear = motor on
    out = m.record_out()
    m.call("stmotr", a=0xFF)
    ok = out == [(PPI, OFF)]
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  stmotr(A=$FF) toggle when ON -> OUT {out} "
          f"(want [({PPI:#x},{OFF:#x})])")

    # A=$FF toggle, motor currently OFF (PortC bit4 = 1) -> turn ON
    m.cpu.io_in = lambda port: 0x10          # bit 4 set = motor off
    out = m.record_out()
    m.call("stmotr", a=0xFF)
    ok = out == [(PPI, ON)]
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  stmotr(A=$FF) toggle when OFF -> OUT {out} "
          f"(want [({PPI:#x},{ON:#x})])")
    return fails


def test_cas_latch(m, fails):
    """cas_latch: select PSG R14 so IN (PSG_STAT) returns CAS-in."""
    s = m.sym
    out = m.record_out()
    m.call("cas_latch")
    want = [(s["PSG_REGS"], s["CASIN_R14"])]
    ok = out == want
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  cas_latch -> OUT {out} (want {want})")
    return fails


def test_cas_cycle(m, fails):
    """cas_cycle: one square-wave cycle = CASW_1 then CASW_0 to PPI_REGS."""
    s = m.sym
    PPI = s["PPI_REGS"]
    out = m.record_out()
    m.call("cas_cycle", bc=0x000A)           # C=10: short djnz, value irrelevant
    want = [(PPI, s["CASW_1"]), (PPI, s["CASW_0"])]
    ok = out == want
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  cas_cycle -> OUT {out} (want {want})")
    return fails


def test_tapiof(m, fails):
    """tapiof: motor off (+ EI, not observable)."""
    s = m.sym
    out = m.record_out()
    m.call("tapiof")
    want = [(s["PPI_REGS"], s["MOTOR_OFF"])]
    ok = out == want
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  tapiof -> OUT {out} (want {want})")
    return fails


def test_tapout_tone_sequence(m, fails):
    """tapout: the ordered tone-selection (cas_long='0'/low, cas_short='1'/high)
    must spell start + 8 data bits LSB-first + stop, per the documented frame."""
    for byte in (0x00, 0xFF, 0x01, 0x80, 0xA5):
        seq = []
        m.trap("cas_long",  lambda mm, seq=seq: seq.append("L"))
        m.trap("cas_short", lambda mm, seq=seq: seq.append("S"))
        m.trap("cas_cycle", lambda mm: None)
        m.call("tapout", a=byte)
        bits_lsb = [(byte >> i) & 1 for i in range(8)]
        want = ["L"] + ["S" if b else "L" for b in bits_lsb] + ["S"]
        ok = seq == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  tapout({byte:#04x}) tones "
              f"{''.join(seq)} (want {''.join(want)})")
    return fails


def test_tapout_cycle_count(m, fails):
    """tapout cycle count = 1 (start) + sum(2 if bit else 1) + 4 (stop)
    = 13 + popcount(byte) — verifies '0'=1 cycle, '1'=2 cycles, 2-stop framing."""
    s = m.sym
    m.poke(s["CASBAUD"], 0x00)                # 1200 (only affects djnz length)
    for byte in (0x00, 0xFF, 0x01, 0xA5, 0x41):
        count = [0]
        m.trap("cas_cycle", lambda mm, count=count: count.__setitem__(0, count[0] + 1))
        m.call("tapout", a=byte)
        want = 13 + bin(byte).count("1")
        ok = count[0] == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  tapout({byte:#04x}) cycles={count[0]} "
              f"(want 13+popcount={want})")
    return fails


def test_tapoon_header(m, fails):
    """tapoon: emit a header carrier — CAS_SHORTLEN cycles (A=0) or CAS_LONGLEN
    (A!=0) — and turn the motor on first."""
    s = m.sym
    for sel, want_len, label in [
        (0x00, s["CAS_SHORTLEN"], "short"),
        (0x01, s["CAS_LONGLEN"],  "long"),
    ]:
        set_baud_area(m, baud1200=True)      # cas_baud resolves deterministically
        count = [0]
        m.trap("cas_cycle", lambda mm, count=count: count.__setitem__(0, count[0] + 1))
        out = m.record_out()
        m.call("tapoon", a=sel)
        motor_on = (s["PPI_REGS"], s["MOTOR_ON"]) in out
        ok = count[0] == want_len and motor_on
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  tapoon({label}) cycles={count[0]} "
              f"(want {want_len}), motor_on={motor_on}")
    return fails


def test_tapoof_flush(m, fails):
    """tapoof: flush CAS_FLUSHLEN trailing carrier cycles, then motor off."""
    s = m.sym
    m.poke(s["CASBAUD"], 0x00)
    count = [0]
    m.trap("cas_cycle", lambda mm, count=count: count.__setitem__(0, count[0] + 1))
    out = m.record_out()
    m.call("tapoof")
    motor_off = (s["PPI_REGS"], s["MOTOR_OFF"]) in out
    ok = count[0] == s["CAS_FLUSHLEN"] and motor_off
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  tapoof flush cycles={count[0]} "
          f"(want {s['CAS_FLUSHLEN']}), motor_off={motor_off}")
    return fails


# --- Read path: drive a synthetic FSK waveform through tapin -----------------

# Discrimination geometry: a "short" half is SHORT samples, a "long" half is
# LONG samples, with SHORT*4 < LOWLIM_RD <= LONG*4 so cas_islong splits them.
SHORT, LONG, LOWLIM_RD = 2, 4, 12   # 8 < 12 <= 16


def _halves_to_samples(halves, level0=0x00):
    """Render half-period durations to an alternating-level CAS-in sample stream
    (prefixed with the level byte the reader's first `in a` reads). cas_half
    returns a half of duration d when it sees (d-1) same-level samples then 1
    flipped sample; the level alternates every half."""
    samples = [level0]
    cur = level0
    for d in halves:
        samples += [cur] * (d - 1) + [cur ^ 0x80]
        cur ^= 0x80
    samples += [cur] * 8                        # a little tail padding (unused)
    return samples


def encode_byte(byte, short=SHORT, long_=LONG, level0=0x00):
    """Build a CAS-in sample stream that the reader must decode to `byte`.

    Documented FSK frame (tape.asm header): start bit '0' = 1 low cycle = 2 long
    halves; data bit '0' = 2 long halves, '1' = 2 high cycles = 4 short halves;
    bits LSB-first. tapin reads the start bit (hunt half + 2nd half) then 8 data
    bits.
    """
    bits_lsb = [(byte >> i) & 1 for i in range(8)]
    halves = [long_, long_]                     # start bit (2 long halves)
    for b in bits_lsb:
        halves += [short] * 4 if b else [long_, long_]
    return _halves_to_samples(halves, level0)


def leader(short, n_halves=80, level0=0x00):
    """A pure carrier leader: n_halves short (high-freq) halves — the tone
    TAPION locks onto and measures to derive LOWLIM."""
    return _halves_to_samples([short] * n_halves, level0)


def test_tapion_lock_and_calibrate(m, fails):
    """tapion locks onto a clean leader and derives LOWLIM = 7 * short-half.

    Oracle (tape.asm tapion_haveavg): it sums CAS_RUNLEN (16) leader halves of
    count H, so sum = 16*H, and stores LOWLIM = (7*sum) >> 4 = 7*H (1.75x the
    average short half, in quarter-count units). On success CF = 0.
    """
    s = m.sym
    H = 4
    m.cpu.io_in = Samples(leader(H))
    cpu = m.call("tapion")
    lowlim = m.mem[s["LOWLIM"]]
    ok = (not carry(cpu)) and lowlim == 7 * H
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  tapion clean leader: CF={int(carry(cpu))} "
          f"(want 0), LOWLIM={lowlim} (want 7*{H}={7*H})")

    # The motor must be switched on (PPI BSR MOTOR_ON -> PPI_REGS).
    m2 = machine()
    out = m2.record_out()
    m2.cpu.io_in = Samples(leader(H))
    m2.call("tapion")
    motor_on = (s["PPI_REGS"], s["MOTOR_ON"]) in out
    fails += not motor_on
    print(f"{'PASS' if motor_on else 'FAIL'}  tapion turns motor on (={motor_on})")

    # A slow leader (large half-period) makes the 16-half running sum exceed 255,
    # so the high-byte carry propagation (INC H in tapion_meas) is exercised.
    # LOWLIM = (7*sum)>>4 = 7*H still: H=20 -> sum=320 -> 7*320/16 = 140.
    H2 = 20
    m3 = machine()
    m3.cpu.io_in = Samples(leader(H2))
    cpu = m3.call("tapion")
    lowlim2 = m3.mem[s["LOWLIM"]]
    ok = (not carry(cpu)) and lowlim2 == (7 * H2) & 0xFF
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  tapion slow leader (H={H2}, sum>255): "
          f"CF={int(carry(cpu))}, LOWLIM={lowlim2} (want 0, {(7 * H2) & 0xFF})")
    return fails


def test_tapion_silence_and_dead(m, fails):
    """tapion tolerates leading silence (the openMSX .cas LONG_SILENCE) but a
    genuinely dead/flat tape exhausts CAS_FLATMAX and fails (CF=1).

    Oracle (tape.asm tapion_wait): WAIT for the first real edge, counting flat
    cas_half timeouts against the 16-bit CAS_FLATMAX budget; silence before the
    carrier is skipped, a flat that never breaks fails.
    """
    H = 4
    # ~256 flat samples (one cas_half timeout of silence) then a clean leader.
    m.cpu.io_in = Samples([0x00] * 256 + leader(H))
    cpu = m.call("tapion")
    ok = not carry(cpu)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  tapion leading-silence then leader: "
          f"CF={int(carry(cpu))} (want 0 = locked)")

    # Dead tape: the level never flips, so every cas_half times out until the
    # CAS_FLATMAX budget is exhausted -> failure.
    m2 = machine()
    m2.cpu.io_in = lambda port: 0x00
    cpu = m2.call("tapion", max_steps=5_000_000)
    ok = carry(cpu)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  tapion dead/flat tape: "
          f"CF={int(carry(cpu))} (want 1 = fail)")
    return fails


def test_tapin_self_calibrated(m, fails):
    """End-to-end read: tapion DERIVES LOWLIM from the leader, then tapin decodes
    bytes against that derived threshold — no hand-set LOWLIM.

    This is the coupling the higher-speed openMSX waveform stressed: the
    discrimination threshold tapin uses is the one tapion measured, not a value
    the test chose. Frame tones use short=H, long=2H, so a data '0' half (2H*4)
    lands above LOWLIM=7H and a '1' carrier half (H*4) below it.
    """
    s = m.sym
    H = 4
    m.cpu.io_in = Samples(leader(H))
    cpu = m.call("tapion")
    assert not carry(cpu), "leader should lock"
    derived = m.mem[s["LOWLIM"]]
    print(f"      (tapion derived LOWLIM={derived} from an H={H} leader)")
    for byte in (0x00, 0xFF, 0xA5, 0x41):
        m.cpu.io_in = Samples(encode_byte(byte, short=H, long_=2 * H))
        cpu = m.call("tapin")
        ok = cpu.a == byte and not carry(cpu)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  tapin (self-calibrated, LOWLIM="
              f"{derived}) decodes {byte:#04x} -> A={cpu.a:#04x}, "
              f"CF={int(carry(cpu))}")
    return fails


def test_tapin_no_start(m, fails):
    """tapin with a carrier but NO start bit (all short halves) exhausts the
    16-bit start-bit hunt and fails (CF=1).

    Oracle (tape.asm tapin_hunt): the hunt classifies each half; a short half is
    not a start bit, so it decrements the 16-bit HL budget and retries; when HL
    reaches 0 with no long (start) half seen, it sets CF and returns. Exercises
    the dec-hl loop + the scf/ret no-start path.
    """
    s = m.sym
    m.poke(s["LOWLIM"], LOWLIM_RD)           # SHORT(2)*4=8 < 12 -> always "short"
    # >65535 short halves so the full HL countdown runs without any cas_half
    # timing out (each short half has an edge within 2 polls).
    m.cpu.io_in = Samples(_halves_to_samples([SHORT] * 65540))
    cpu = m.call("tapin", max_steps=4_000_000)
    ok = carry(cpu)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  tapin no-start-bit (all short) -> "
          f"hunt timeout CF={int(carry(cpu))} (want 1)")
    return fails


def test_tapin_decode(m, fails):
    """tapin decodes a synthetic FSK frame back to the original byte."""
    s = m.sym
    m.poke(s["LOWLIM"], LOWLIM_RD)
    for byte in (0x00, 0xFF, 0xA5, 0x41):
        m.cpu.io_in = Samples(encode_byte(byte))
        cpu = m.call("tapin")
        ok = cpu.a == byte and not carry(cpu)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  tapin decodes {byte:#04x} -> "
              f"A={cpu.a:#04x}, CF={int(carry(cpu))} (want CF=0)")
    return fails


def test_cas_half_counts(m, fails):
    """cas_half: B = same-level polls to the edge (incl. the flip), D = new
    level, CF set on timeout (level never flips within 256 polls)."""
    # Low start, flips on the 3rd sample.
    m.cpu.io_in = Samples([0x00, 0x00, 0x80])
    cpu = m.call("cas_half", d=0x00)
    ok = cpu.b == 3 and cpu.d == 0x80 and not carry(cpu)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  cas_half low->high: B={cpu.b}, "
          f"D={cpu.d:#04x}, CF={int(carry(cpu))} (want B=3, D=0x80, CF=0)")

    # High start, flips on the 3rd sample.
    m.cpu.io_in = Samples([0x80, 0x80, 0x00])
    cpu = m.call("cas_half", d=0x80)
    ok = cpu.b == 3 and cpu.d == 0x00 and not carry(cpu)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  cas_half high->low: B={cpu.b}, "
          f"D={cpu.d:#04x}, CF={int(carry(cpu))} (want B=3, D=0x00, CF=0)")

    # No edge for >256 polls -> timeout (CF set), low branch (cas_half_lo).
    m.cpu.io_in = lambda port: 0x00          # forever low
    cpu = m.call("cas_half", d=0x00)
    ok = carry(cpu)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  cas_half flat-low -> timeout "
          f"CF={int(carry(cpu))} (want CF=1)")

    # Same, but starting high: exercises the cas_half_hi timeout (SCF/RET).
    m.cpu.io_in = lambda port: 0x80          # forever high
    cpu = m.call("cas_half", d=0x80)
    ok = carry(cpu)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  cas_half flat-high -> timeout "
          f"CF={int(carry(cpu))} (want CF=1)")
    return fails


# ===========================================================================
# Runner
# ===========================================================================

def run():
    build()
    fails = 0
    groups = [
        ("Tier 1: cas_baud",          test_cas_baud),
        ("Tier 1: cas_short/cas_long", test_cas_short_long),
        ("Tier 1: cas_islong",        test_cas_islong),
        ("Tier 2: stmotr",            test_stmotr),
        ("Tier 2: cas_latch",         test_cas_latch),
        ("Tier 2: cas_cycle",         test_cas_cycle),
        ("Tier 2: tapiof",            test_tapiof),
        ("Tier 2: tapout tone frame", test_tapout_tone_sequence),
        ("Tier 2: tapout cycle count", test_tapout_cycle_count),
        ("Tier 2: tapoon header",     test_tapoon_header),
        ("Tier 2: tapoof flush",      test_tapoof_flush),
        ("Tier 2: cas_half",          test_cas_half_counts),
        ("Tier 2: tapion lock + LOWLIM calibration", test_tapion_lock_and_calibrate),
        ("Tier 2: tapion silence tolerance + dead-tape fail", test_tapion_silence_and_dead),
        ("Tier 2: tapin self-calibrated (tapion-derived LOWLIM)", test_tapin_self_calibrated),
        ("Tier 2: tapin no-start-bit timeout", test_tapin_no_start),
        ("Tier 2: tapin decode (hand-set LOWLIM)", test_tapin_decode),
    ]
    for title, fn in groups:
        print(f"=== {title} ===")
        fails = fn(machine(), fails)
        print()

    if not fails:
        print("ALL PASS — tape BIOS routines match the documented FSK frame + "
              "motor/PPI/PSG contracts")
    else:
        print(f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
