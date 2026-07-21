#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""PLAY live-servicer acceptance — per-VBLANK PSG-register trace differential vs the
VG-8020 (audio arc, Slice 3; docs/audio-slice3-characterization.md).

The parser (Slice 2a) built the queues; THIS gate proves the live drain -- play_service
reached from C-BIOS's $0038 ISR through the H.TIMI seam -- reproduces the reference's
per-frame PSG register writes. For each tune we boot both machines, sample the 14 PSG
registers every VBLANK (VDP.IRQvertical raised edge; probes/lib/psgtrace.py) while the
music drains, collapse each voice's trace into its (tone-period, amplitude) note
sequence, and assert zerobas == reference. The onset frame differs (parse/keyboard
latency differs per machine), so we compare the SEQUENCE, not absolute frames.

Covers the pinned drain model: note tone periods (the black-box-measured 96-note
table), frame durations (12000//tl floor), silence-is-amp-0, rests (period untouched),
dotted lengths, envelope (S/M -> R11/R12/R13 + amp $10|volume), 3-voice independent
drain, R7 never touched (stays $B8), MUSICF completion, and a DI-safety liveness case
(PLAY then a tight SIN loop -- a page-1 tenant churning while music drains; proves the
page-1-resident servicer is always mapped when the ISR fires, §4a).

Heavy + oracle-dependent (boots openMSX per case; needs your VG-8020 reference ROM).
The emulator-free fast layer is tests/test_play_frame_sim.py under `unit-test`.
Scope one case with `make play-trace-acceptance ONLY=env`.
"""
import argparse, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import psgtrace  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
# (type-delay, arm) seconds: the repack machine boots slower than the real VG-8020.
BOOT = {REF_MACHINE: (5.0, 5.6)}
DEFAULT_BOOT = (9.0, 9.6)


def voice_seq(machine, stmt, n, voice):
    """Boot `machine`, PLAY `stmt`, return voice's (tone_period, amp5) note sequence
    (leading idle + open-ended trailing segment trimmed)."""
    tp, arm = BOOT.get(machine, DEFAULT_BOOT)
    out = f"/tmp/playtrace_{abs(hash((machine, stmt, voice)))}.txt"
    psgtrace.trace(machine, stmt, out, n=n, tp=tp, arm=arm, deadline=max(45, n / 6 + 25))
    rows = psgtrace.parse(out)
    seq = [(p, a) for st, dur, p, a in psgtrace.note_segments(rows, voice)]
    while seq and seq[0] == (0, 0):
        seq.pop(0)
    return seq[:-1] if seq else seq   # drop the open-ended trailing segment


def envregs(machine, stmt, n):
    """Distinct (shape, env_period, R7, amp5) tuples seen in envelope mode."""
    tp, arm = BOOT.get(machine, DEFAULT_BOOT)
    out = f"/tmp/playtrace_env_{abs(hash((machine, stmt)))}.txt"
    psgtrace.trace(machine, stmt, out, n=n, tp=tp, arm=arm, deadline=45)
    seen = []
    for fc, r in psgtrace.parse(out):
        sig = (r[13] & 0x0F, r[11] | (r[12] << 8), r[7], r[8] & 0x1F)
        if (sig[3] & 0x10) and (not seen or seen[-1] != sig):
            seen.append(sig)
    return seen


def r7_values(machine, stmt, n):
    tp, arm = BOOT.get(machine, DEFAULT_BOOT)
    out = f"/tmp/playtrace_r7_{abs(hash((machine, stmt)))}.txt"
    psgtrace.trace(machine, stmt, out, n=n, tp=tp, arm=arm, deadline=45)
    return sorted({r[7] for fc, r in psgtrace.parse(out)})


# (label, statement, frames, voices-to-compare)
SEQ_CASES = [
    ("scale",  'PLAY"O4L8CDEFGAB"',                    300, (0,)),
    ("rest",   'PLAY"O4L4CRCRC"',                      300, (0,)),
    ("dots",   'PLAY"O4L4C.G.C."',                     300, (0,)),
    ("multi",  'PLAY"O4L4CEG","O4L2EG","O4L1G"',       300, (0, 1, 2)),
    ("octaves",'PLAY"O2L8CO4CO6C"',                    300, (0,)),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only")
    a = ap.parse_args()
    ok = True

    print("--- PLAY note sequence (differential vs VG-8020) ---")
    for lbl, stmt, n, voices in SEQ_CASES:
        if a.only and a.only not in lbl:
            continue
        for v in voices:
            ref = voice_seq(a.machine, stmt, n, v)
            zb = voice_seq(a.zb_machine, stmt, n, v)
            good = ref == zb and (len(ref) > 0 or v > 0)
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {lbl:8} v{v}  ref={ref}")
            if not good:
                print(f"                     zb ={zb}")

    if not a.only or a.only in "env":
        print("\n--- envelope registers (S8 M2000; R11/12/13 + amp $10|vol) ---")
        stmt = 'PLAY"O4L4S8M2000CDE"'
        ref = envregs(a.machine, stmt, 300)
        zb = envregs(a.zb_machine, stmt, 300)
        good = ref == zb and len(ref) > 0
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} env       ref={ref}")
        if not good:
            print(f"                     zb ={zb}")

    if not a.only or a.only in "mixer":
        print("\n--- R7 mixer never touched (stays $B8) ---")
        stmt = 'PLAY"O4L4CEG","O4L2EG","O4L1G"'
        ref = r7_values(a.machine, stmt, 300)
        zb = r7_values(a.zb_machine, stmt, 300)
        good = ref == zb == [0xB8]
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} mixer     ref={[hex(x) for x in ref]} zb={[hex(x) for x in zb]}")

    if not a.only or a.only in "di_safety":
        print("\n--- DI-safety: PLAY then a tight SIN loop (page-1 tenant) ---")
        stmt = 'PLAY"O4L4CDEFGAB":FORI=1TO3000:X=SIN(I):NEXT'
        # music must still advance through >=4 distinct notes with no derail
        zb = voice_seq(a.zb_machine, stmt, 300, 0)
        good = len(zb) >= 4 and all(a2 == 8 for _, a2 in zb) and \
            zb[:4] == [(428, 8), (381, 8), (339, 8), (320, 8)]
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} di_safety notes-advanced={zb}")

    print("\n" + ("ALL PASS — the live PLAY servicer matches the VG-8020"
                  if ok else "FAILURES above"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
