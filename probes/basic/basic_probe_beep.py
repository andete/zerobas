#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""BEEP acceptance — per-VBLANK PSG-register trace differential vs the VG-8020
(audio arc, close-out; docs/spec-basic-audio-beep.md).

BEEP is a discrete, fire-once tone on PSG channel A. For each case we boot both the
reference (Philips VG-8020) and the zerobas repack build, sample the 14 PSG registers
every VBLANK (VDP.IRQvertical raised edge; probes/lib/psgtrace.py) across the beep, and
collapse the trace into the (R0, R1, R7, R8) transition sequence -- the tone-A period,
the mixer, and the channel-A amplitude, the four registers BEEP touches. The onset frame
differs per machine (keyboard/parse latency), so we compare the SEQUENCE, not absolute
frames.

Pins the black-box contract (spec §2): BEEP on -> R0=$55 R1=$00 (tone A period 85),
R7=(prevR7 & $C0)|$3E (mute B/C + noise, keep tone A + I/O bits), R8=$07 (fixed vol 7);
then off -> R8=$00, R7=(prevR7 & $C0)|$38 (mixer wiped back to the default all-tones-on).
The `sound 7,190:beep` case proves the restore is DYNAMIC (reconstructs from the read-back
I/O bits) not a hardcoded $B8, and that BEEP wipes a prior SOUND 7 mixer. The
`sound 8,10:beep` case proves BEEP zeroes R8 rather than restoring a prior amplitude.

Heavy + oracle-dependent (boots openMSX per case; needs your VG-8020 reference ROM).
The emulator-free fast layer is tests/test_beep.py under `unit-test`. Scope one case
with `make beep-acceptance ONLY=r7dyn`.
"""
import argparse, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import psgtrace  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
# (type-delay, arm) seconds: the repack machine boots slower than the real VG-8020.
BOOT = {REF_MACHINE: (5.0, 5.05)}
DEFAULT_BOOT = (9.0, 9.1)


def beep_transitions(machine, stmt, n=700):
    """Boot `machine`, run `stmt`, return the beep's own (R0, R1, R7, R8) transient:
    the ON state through the following OFF (R8 back to 0), consecutive duplicates
    collapsed. BEEP touches exactly these four registers.

    The onset is anchored on the beep's UNIQUE mixer signature -- tones B and C muted,
    R7 bits 1,2 set ((R7 & $06)==$06) -- with amp on (R8!=0). This deliberately skips
    any prior direct PSG write (e.g. `sound 8,10` sets R8 without touching the mixer),
    so the comparison is the beep transient alone and never races on whether a VBLANK
    happened to sample a pre-beep SOUND state (which the faster VG-8020 trace may miss
    but the slower repack trace may catch)."""
    tp, arm = BOOT.get(machine, DEFAULT_BOOT)
    out = f"/tmp/beeptrace_{abs(hash((machine, stmt)))}.txt"
    psgtrace.trace(machine, stmt, out, n=n, tp=tp, arm=arm, deadline=max(45, tp + 40))
    rows = psgtrace.parse(out)
    on = next((i for i, (fc, r) in enumerate(rows)
               if (r[7] & 0x06) == 0x06 and r[8] != 0), None)
    if on is None:
        return []           # beep never fired -> caller asserts non-empty
    seq, prev = [], None
    for fc, r in rows[on:]:
        sig = (r[0], r[1], r[7], r[8])
        if sig != prev:
            seq.append(sig)
            prev = sig
        if sig[3] == 0:     # reached the OFF (amp silenced) -> transient complete
            break
    return seq


def _h(seq):
    return [tuple(f"{b:02x}" for b in s) for s in seq]


# (label, statement, expected zerobas==reference transition tail).
# Each tail is [prior, ON, OFF]: prior mixer -> beep(tone85/vol7) -> silence+default mixer.
CASES = [
    ("beep",   "beep"),                 # cold: b8 -> be/07 -> b8/00
    ("chain",  "beep:beep"),            # two blips
    ("r7dyn",  "sound 7,190:beep"),     # prior R7=be; restore to b8 (dynamic, wipes SOUND 7)
    ("r8prior", "sound 8,10:beep"),     # prior R8=0a; BEEP zeroes it, not restores
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()

    ok = True
    print("--- BEEP PSG transient (differential vs VG-8020) ---")
    for lbl, stmt in CASES:
        if a.only and a.only not in lbl:
            continue
        ref = beep_transitions(a.machine, stmt)
        zb = beep_transitions(a.zb_machine, stmt)
        # the beep must actually fire on both, and the transient must be byte-identical.
        fired = any(s[3] != 0 for s in ref) and any(s[3] != 0 for s in zb)
        good = fired and ref == zb
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {lbl:8} ref={_h(ref)}")
        if not good:
            print(f"                     zb ={_h(zb)}")

    print("\n" + ("ALL PASS — BEEP matches the VG-8020"
                  if ok else "FAILURES above"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
