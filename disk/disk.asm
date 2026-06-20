; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; zerobas-disk — disk.asm
; ===========================================================================
; A clean-room MSX1 disk-interface ROM. Standalone 16 KB ROM that lives in an
; internal expansion slot (slot 3-1, page 1, $4000-$7FFF) on a built-in-disk
; MSX1, exactly as a real machine carries its disk ROM. See README.md and
; disk/PROVENANCE.md.
;
; CLEAN-ROOM DISCIPLINE: every constant, address, and algorithm here traces to
; an allowed source (MSX2 Technical Handbook, WD2793 datasheet, Microsoft FAT
; spec, ECMA-107, openMSX/C-BIOS sources, or this project's own black-box
; oracle observations). Nothing is derived from any disk-ROM or MSX-BASIC
; disassembly. See disk/PROVENANCE.md.
;
; Runtime model: this is an "AB" disk-interface ROM. At boot the BIOS finds the
; header at $4000 and calls INIT (which will install the H.DSKIO / H.PHYD hooks
; and the DPB — see the INIT item). The BIOS disk subsystem reaches the driver
; through the six fixed-offset entry points at $4010..$401F.
;
; STATUS: skeleton only. The header and the entry-point jump table are in place
; at their fixed offsets; every entry is a clean failure stub. The FDC driver,
; FAT12 layer, BDOS hooks, and a real INIT land in later items, each gated on
; the matching PROVENANCE.md section (the FDC register map is still a hard-blocked
; TBD).
; ===========================================================================

                org     $4000

; --- MSX cartridge / disk-ROM header ---------------------------------------
; Standard 16-byte cartridge header (MSX2 TH, cartridge ROM format), identical
; in shape to the main zerobas ROM: ID, INIT, STATEMENT, DEVICE, TEXT, then 6
; reserved bytes. INIT is a *word* at $4002 (the BIOS CALLs through it); the
; header is exactly 16 bytes, so the disk entry-point table begins at $4010.
                db      "AB"            ; ROM signature              ($4000)
                dw      init            ; INIT entry point           ($4002)
                dw      0               ; STATEMENT expansion (none) ($4004)
                dw      0               ; DEVICE expansion (none)    ($4006)
                dw      0               ; TEXT / BASIC program (none)($4008)
                dw      0,0,0           ; reserved                   ($400A-$400F)

; --- Disk-ROM entry-point table (MSX2 TH, disk ROM interface) --------------
; Six JP instructions at fixed offsets from the ROM base. The BIOS disk
; subsystem CALLs these; each is 3 bytes, so they land exactly on the +$10,
; +$13, +$16, +$19, +$1C, +$1F boundaries. The `ds` guard is a compile-time
; assert that the header above is exactly 16 bytes (pasmo errors if $ > $4010).
                ds      $4010 - $, $00
                jp      dskio           ; +$10  sector read/write    ($4010)
                jp      dskchg          ; +$13  disk-change status   ($4013)
                jp      getdpb          ; +$16  build DPB from BPB   ($4016)
                jp      choice          ; +$19  format-choice string ($4019)
                jp      dskfmt          ; +$1C  format disk          ($401C)
                jp      mtoff           ; +$1F  motors off           ($401F)

; --- INIT (cartridge header points here) -----------------------------------
; Real INIT (next item) installs the H.DSKIO / H.PHYD hooks and the DPB, then
; returns to the BIOS boot scan. The skeleton returns cleanly so boot proceeds.
init:
                ret

; --- Entry-point stubs ------------------------------------------------------
; Placeholders until the FDC / FAT12 / BDOS items land. Each signals failure the
; documented way so a premature call fails cleanly instead of running garbage:
; the disk interface reports an error by returning with carry set (MSX2 TH, disk
; ROM interface). CHOICE is the exception — it returns HL = pointer to a
; NUL-terminated format-choice string, or HL = 0 for "no choices", which is the
; correct permanent answer for a single fixed 720 KB geometry.
dskio:
dskchg:
getdpb:
dskfmt:
mtoff:
                scf                     ; carry = operation failed
                ret

choice:
                ld      hl,0            ; no format-choice string
                ret

; --- pad to a full 16 KB page ($4000-$7FFF) --------------------------------
                ds      $8000 - $, $00
