#!/usr/bin/env python3
"""D-SUBSIG (Joost 2026-10-11): the zerobas sub ROM carries its own "ZB" marker,
not the MSX2 SUB-ROM's "CD", and boot no longer writes EXBRSA ($FAF8).
Anchored on text; refuses a missing or non-unique anchor."""
import sys

def sub(path, old, new):
    s = open(path).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE {path}: anchor found {n}x: {old[:60]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

sub("sub/sub.asm", """; --- Sub-ROM signature (MSX2 sub-ROM ID; §3c/D-3) --------------------------
; `CD` at $0000 marks a sub-ROM (vs `AB` for a cartridge). init_ext_roms
; (S2b) RDSLT-checks $0000/$0001 for 'C'/'D' to discover and record our slot.
                db      "CD"                    ; $0000: sub-ROM signature
""", """; --- Sub-ROM signature: zerobas's OWN marker (D-SUBSIG) ---------------------
; `ZB` at $0000. It used to be `CD`, the MSX2 SUB-ROM's published ID -- but this
; ROM is zerobas's own invention, and on an MSX2 C-BIOS scans every subslot for
; `CD` and takes the FIRST: ours in a lower subslot would capture EXBRSA and
; break EXTROM (scratchpad/subrom_arch_report.md). Joost, 2026-10-11: own ID,
; `ZB`. Not `AB` either (the BIOS would run it as a cartridge). init_ext_roms
; RDSLT-checks $0000/$0001 for 'Z'/'B' to discover and record our slot.
                db      "ZB"                    ; $0000: zerobas sub-ROM marker
""")
sub("basic/subrom-boot.asm", """; try_sub_slot: if the slot just scanned by try_init_slot (SCAN_SLOT) carries the
; MSX2 sub-ROM signature "CD" at $0000 (page 0), record it.""", """; try_sub_slot: if the slot just scanned by try_init_slot (SCAN_SLOT) carries
; zerobas's own sub-ROM marker "ZB" at $0000 (page 0), record it. (D-SUBSIG,
; 2026-10-11: it was the MSX2 SUB-ROM's "CD", and the slot also went to EXBRSA
; $FAF8 -- which nothing read, and which both MSX1 references leave 0:
; scratchpad/subsig_probe.out.)""")
sub("basic/subrom-boot.asm", """                cp      'C'
                ret     nz
                ld      hl,$0001
                call    rdslt_scan
                cp      'D'
                ret     nz
                ; found: record the slot in the private path AND the MSX2 work area
                ld      a,(SCAN_SLOT)
                ld      (SUBSLOT),a
                ld      (EXBRSA),a          ; convention-compat (D-6); dispatch uses SUBSLOT
                ld      a,1
""", """                cp      'Z'
                ret     nz
                ld      hl,$0001
                call    rdslt_scan
                cp      'B'
                ret     nz
                ; found: record the slot (the private path; EXBRSA stays the MSX1 0)
                ld      a,(SCAN_SLOT)
                ld      (SUBSLOT),a
                ld      a,1
""")
sub("tools/check_sub_walls.py", """ANCHORS = ((P0_BASE, b"CD"), (P1_BASE, b"S1"))""",
    """ANCHORS = ((P0_BASE, b"ZB"), (P1_BASE, b"S1"))   # D-SUBSIG: was b"CD" (the MSX2 SUB-ROM's)""")
sub("tools/check_sub_walls.py", """    print(f"OK: sub ROM {len(image)} B, 'CD' @ $0000,""",
    """    print(f"OK: sub ROM {len(image)} B, 'ZB' @ $0000,""")
