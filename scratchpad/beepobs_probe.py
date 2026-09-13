#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWBREADTH batch 7 — is BEEP's effect observable through the PSG?

`beep`'s row prints a CONSTANT MARKER `[6]`, so it scores that the word RAN and
nothing about what it DID. Batch 6 showed the PSG HAS a readback path
(`OUT &HA0,<reg>` selects, `INP(&HA2)` reads) and that turned SOUND's and OUT's
markers into values -- after I had asserted no such path existed. So BEEP is
MEASURED here rather than written off the same way.

BEEP clicks through the PSG. If it leaves a register changed from a known
pre-state, that change is a reading; if it restores everything, the marker is the
honest limit and that is the finding.

⚠️ REUSES `basic_probe_kwsweep`'s OWN MACH_BOOT/MACH_RESET_PRE VALUES. The first
DELETE probe invented its own, so the CF-3300 booted into SCREEN 1 and every
capture was the pattern generator table read as text.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import omsx_repl                                                    # noqa: E402

CASES = {
    # amplitude A: zero it, BEEP, read it back
    "amp":  ['10 SOUND 8,0', '20 BEEP', '30 OUT&HA0,8',
             '40 PRINT"[A";INP(&HA2);"]"', 'RUN'],
    # mixer: set all-off (255), BEEP, read it back
    "mix":  ['10 SOUND 7,255', '20 BEEP', '30 OUT&HA0,7',
             '40 PRINT"[M";INP(&HA2);"]"', 'RUN'],
    # 🔴 THE CONTROL MUST READ THE REGISTER THE CHANGE APPEARS IN. The first run of
    # this probe read register 8 while the change showed up in register 7, so
    # `mix` reading 184 after SOUND 7,255 had NO no-beep reading to be compared
    # against -- and 184 is exactly what the BIOS interrupt handler rewriting the
    # mixer every frame would also produce. A case that agrees can agree for the
    # wrong reason, and a control aimed at the wrong cell excludes nothing.
    "ctl8": ['10 SOUND 8,0', '30 OUT&HA0,8',
             '40 PRINT"[C";INP(&HA2);"]"', 'RUN'],
    "ctl7": ['10 SOUND 7,255', '30 OUT&HA0,7',
             '40 PRINT"[D";INP(&HA2);"]"', 'RUN'],
    # and one more: is 184 simply what reg 7 reads at rest, with no SOUND at all?
    "rest7": ['10 OUT&HA0,7', '20 PRINT"[E";INP(&HA2);"]"', 'RUN'],
}

MACHINES = [("Philips_VG_8020", 8.0, ("NEW", "CLS")),
            ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW", "CLS")),
            ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ("NEW", "CLS"))]

for machine, boot, reset in MACHINES:
    print(f"=== {machine} ===", flush=True)
    for key, lines in CASES.items():
        caps = omsx_repl.run_cases(
            machine, [(key, list(reset) + lines)],
            batch=False, boot=boot, step=3.0, cap_gap=8.0, timeout=300.0)
        text = " ".join(str(caps[0]).split())
        print(f"  {key:4} {text[-90:]!r}", flush=True)
