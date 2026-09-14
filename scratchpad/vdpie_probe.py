#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWBATCH3 — does a `VDP(n)=v` write reach the CHIP, and can zerobas survive it?

🎚️ Joost, 2026-09-14: *"if you choose a clever write, you can see the effects in
the visual appearance of the screen"*. He is right that the effect is reachable,
but not through the kwsweep capture, which scrapes VRAM $0000 and therefore reads
the NAME TABLE rather than the display -- a blanked screen, a changed backdrop and
a moved name-table base all look identical to it. So the chip-side witness has to
be something a PROGRAM can measure, and VDP register 1 bit 5 is one: it is the
FRAME-INTERRUPT ENABLE, so clearing it stops JIFFY and freezes TIME. A handler
that stored the value in the RGnSAV mirror and never reached the port leaves the
interrupt running and TIME advancing.

🔴 WHY THIS PROBE EXISTS RATHER THAN A SWEEP ROW. The sweep row (`vdp_d`) read
`[0l 0 -1 ]` on the VG-8020 -- exactly the designed answer, TIME frozen then
ticking again -- and on zerobas produced NO OUTPUT AT ALL: the capture was the
program listing, so the program never reached its PRINT. A DIVERGENT verdict does
not say which of these it is, and the sweep cannot tell them apart:

  * zerobas never writes the port, so the interrupt stays on (harmless, and the
    row would still have PRINTED, just with a different value) -- RULED OUT by the
    missing output, but only if the output is really missing rather than scraped
    wrong;
  * zerobas writes the port and cannot recover -- the interrupt never comes back,
    so the machine wedges before the PRINT;
  * the program never ran at all (a length or packing fault), which has nothing to
    do with the VDP.

Each case below separates one of those, and each is its own boot so a wedge cannot
contaminate the next reading.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import omsx_repl                                                    # noqa: E402

CASES = {
    # (1) CONTROL: the same program shape with NO VDP write at all. If this reads
    #     nothing either, the fault is the program, not the VDP.
    "control":  ['10 T=TIME:FOR I=1 TO 400:NEXT:A=TIME-T',
                 '20 PRINT"[C";A>0;"]"', 'RUN'],
    # (2) Does the write land in the MIRROR? This is what `vdp_c` already proves,
    #     repeated here so the two halves are measured in one place.
    "mirror":   ['10 V=VDP(1):VDP(1)=V AND 223:A=VDP(1):VDP(1)=V',
                 '20 PRINT"[M";A;V;"]"', 'RUN'],
    # (3) THE CHIP. Clear bit 5, time a loop, restore, time it again.
    "chip":     ['10 V=VDP(1):VDP(1)=V AND 223',
                 '20 T=TIME:FOR I=1 TO 400:NEXT:A=TIME-T',
                 '30 VDP(1)=V',
                 '40 U=TIME:FOR I=1 TO 400:NEXT:B=TIME-U',
                 '50 PRINT"[K";A;B>0;"]"', 'RUN'],
    # (5) ONE loop instead of two. Case (3) times the loop TWICE -- once with the
    #     interrupt off and once with it back on -- and zerobas is 2.5-3.8x slower
    #     than the reference (the open TIER 4 item), so the pair may simply outrun
    #     the capture window. If this shape ANSWERS where (3) did not, the fault
    #     was the apparatus and not the VDP.
    "chip1":    ['10 V=VDP(1):VDP(1)=V AND 223:T=TIME',
                 '20 FOR I=1 TO 400:NEXT:A=TIME-T:VDP(1)=V',
                 '30 PRINT"[1";A;"]"', 'RUN'],
    # (4) Does the machine come back AFTER the write is restored? Same as (3) but
    #     the reading is taken in a SECOND direct-mode line, so it can only print
    #     if the interpreter is still alive and the keyboard still scans.
    "survive":  ['10 V=VDP(1):VDP(1)=V AND 223:FOR I=1 TO 400:NEXT:VDP(1)=V',
                 'RUN', 'PRINT"[S";VDP(1);"]"'],
}

MACHINES = [("Philips_VG_8020", 8.0, ("NEW", "CLS")),
            ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ("NEW", "CLS"))]

for machine, boot, reset in MACHINES:
    print(f"=== {machine} ===", flush=True)
    for key, lines in CASES.items():
        caps = omsx_repl.run_cases(
            machine, [(key, list(reset) + lines)],
            batch=False, boot=boot, step=3.0, cap_gap=8.0, timeout=300.0)
        print(f"  {key:9} {' '.join(str(caps[0]).split())[-78:]!r}", flush=True)
