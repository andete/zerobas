#!/usr/bin/env python3
"""D-STEP7DATE ROM half: route the two non-DOS boot exits through boot_date.

  init.asm   boot_disk's no-signature `ret nz`   -> `jp nz, bd_nosig`
             the data-disk return after dos_handoff -> `jp bd_step7`
  kernel.asm bd_step7 / bd_nosig after br5_end (the pre-$41FD region is pad-packed)

Refuses unless every anchor occurs exactly once. `git checkout disk/init.asm
disk/kernel.asm` reverts it.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sub(path, old, new):
    p = os.path.join(ROOT, path)
    s = open(p).read()
    if s.count(old) != 1:
        sys.exit(f"REFUSED {path}: anchor occurs {s.count(old)}x: {old.splitlines()[0]!r}")
    open(p, "w").write(s.replace(old, new))


sub("disk/init.asm",
    "                cp      $E9\n"
    "                ret     nz              ; not a boot disk -> BASIC\n",
    "                cp      $E9\n"
    "                jp      nz, bd_nosig    ; not a boot disk -> the date, then BASIC\n")
sub("disk/init.asm",
    "                call    page0_ram_out   ; data disk returned: BIOS ROM back in page 0\n"
    "                ei\n"
    "                ret                     ; -> BIOS boot scan -> BASIC\n",
    "                call    page0_ram_out   ; data disk returned: BIOS ROM back in page 0\n"
    "                jp      bd_step7        ; D-STEP7DATE: the date, then the scan -> BASIC\n")
sub("disk/kernel.asm", "br5_end:\n", """br5_end:
; bd_step7 / bd_nosig (D-STEP7DATE, 2026-10-23) -- a disk in the drive that did not start
; MSX-DOS: its boot code RETURNED from step 7 (a data disk's `RET NC` / `RET` stub), or
; it carries no boot signature at all. Both references then ask the date before BASIC
; (the CF-3300 `Enter date ( - - ):`, the VG-8020 + NMS 1200 `Enter date (M-D-Y):`)
; with our own make_test_dsk.py disk (scratchpad/stepret_plain_cf.out,
; scratchpad/stepret_plain_nms.out), and the CF-3300 for an all-zero image too.
; boot_date is D-BOOTDATE's question (it skips a disk with an AUTOEXEC.BAS, as both
; references do) and returns with interrupts masked.
bd_step7:
                call    boot_date
                ei                      ; as the step-7 return always did
                ret                     ; -> the BIOS boot scan -> BASIC
bd_nosig:
                jp      boot_date       ; the scan's masked state kept, as before
""")
sub("disk/fat.asm", "BD_LINL40       equ     $F3AE   ; MSX2 TH work area: LINL40, SCREEN 0's width (1 B)\n",
    "BD_LINL40       equ     $F3AE   ; MSX2 TH work area: LINL40, SCREEN 0's width (1 B)\n"
    "BD_SCNCNT       equ     $F3F6   ; MSX work area: SCNCNT, the key-scan countdown (1 B)\n")
sub("disk/fat.asm", "                ld      (BD_LINL40), a\n", """                ld      (BD_LINL40), a
                ; The keyboard answers the prompt at once: C-BIOS leaves the key-scan
                ; countdown SCNCNT at its power-on $FF, so the interrupt took no key for
                ; ~5 s after power-on; main INIT's D-BOOTSCAN store comes after this
                ; question. The VG-8020's start-up clears the cell within 1 s
                ; (scratchpad/keycells_vg.out); measured here in scratchpad/step7b_scncnt.out.
                ld      a, 1                ; 1 = scan at the next interrupt
                ld      (BD_SCNCNT), a
""")
print("applied")
