; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; zerobas-disk — disk.asm
; ===========================================================================
; A clean-room MSX1 disk-interface ROM. Standalone 16 KB ROM that lives in an
; internal expansion slot (slot 3-1, page 1, $4000-$7FFF) on a built-in-disk
; MSX1. See README.md and disk/PROVENANCE.md.
;
; CLEAN-ROOM DISCIPLINE: every constant, address, and algorithm here traces to
; an allowed source (MSX2 Technical Handbook, WD2793 datasheet, Microsoft FAT
; spec, ECMA-107, openMSX/C-BIOS sources, or this project's own black-box
; oracle observations). Nothing is derived from any disk-ROM or MSX-BASIC
; disassembly. See disk/PROVENANCE.md.
;
; Runtime model: this is an "AB" disk-interface ROM. At boot the BIOS finds the
; header at $4000 and calls INIT, which installs the H.DSKIO / H.PHYD hooks and
; the SYSTEM (BDOS) vector, then returns to the BIOS boot scan. The BIOS disk
; subsystem reaches the driver through the six fixed-offset entry points at
; $4010..$401F.
;
; STATUS: INIT installs hooks and SYSTEM vector. FDC driver, FAT12 layer, and
; BDOS implementation land in later items; all are gated on the FDC register-map
; oracle probe (still TBD in PROVENANCE.md). GETDPB is a stub pending the
; DSKIO oracle probe that will confirm the exact MSX DPB field encoding.
; ===========================================================================

; --- System addresses (disk/PROVENANCE.md §INIT / §BDOS) -------------------
; Sources: MSX2 Technical Handbook, work area / hook table.
H_PHYD          equ     $FF3E   ; H.PHYD: physical disk I/O hook (5 bytes)
H_DSKIO         equ     $FF4B   ; H.DSKIO: disk-BASIC disk I/O hook (5 bytes)
SYSTEM          equ     $F37D   ; SYSTEM sysvar: BDOS entry-point word

; --- Disk scratch RAM (disk/PROVENANCE.md §Scratch RAM) --------------------
DPB_AREA        equ     $E288   ; DPB work area (DPB_SIZE bytes)
DPB_SIZE        equ     18      ; DPB is 18 bytes (MSX2 TH, DPB layout)

; --- ROM skeleton -----------------------------------------------------------
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

; --- INIT -------------------------------------------------------------------
; Called by the BIOS boot scan. Installs H.PHYD and H.DSKIO hooks in the system
; hook RAM (5-byte slots at $FF3E and $FF4B), and writes the BDOS entry-point
; address into the SYSTEM sysvar ($F37D). Then returns cleanly so the BIOS
; continues its boot sequence.
;
; Hook slot layout (MSX2 TH, hook table): a 5-byte slot patched with
; JP nn ($C3, addr_lo, addr_hi) + 2 padding bytes. The BIOS calls the slot with
; CALL; our JP redirects to the handler, and the handler's RET returns to the
; original CALL site (the BIOS's own return address is already on the stack).
;
; Source: H.PHYD $FF3E, H.DSKIO $FF4B — MSX2 TH, work area / hook table.
;         SYSTEM $F37D — MSX2 TH, work area; C-BIOS systemvars.asm.
;         JP opcode $C3, hook slot 5 bytes — MSX2 TH (all H.* hooks are 5-byte).
init:
                ld      hl, H_PHYD
                ld      de, phyd_handler
                call    install_hook
                ld      hl, H_DSKIO
                ld      de, dskio
                call    install_hook
                ld      hl, bdos_entry
                ld      (SYSTEM), hl
                ret

; install_hook: write a JP instruction into a 5-byte hook slot.
; in:  HL = hook address in page-3 RAM, DE = target handler address
; out: (HL)..(HL+4) = $C3, target_lo, target_hi, $00, $00
; trashes: A, HL
install_hook:
                ld      (hl), $C3       ; Z80 JP opcode
                inc     hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (hl), $00       ; padding (hook slots are 5 bytes)
                inc     hl
                ld      (hl), $00
                ret

; --- Disk entry-point handlers ---------------------------------------------

; dskio — physical sector read/write (intercepted via H.DSKIO hook).
; FDC driver not yet implemented: fail with carry set (MSX2 TH, disk interface).
; Gated on: FDC register map oracle (TBD in PROVENANCE.md §FDC).
dskio:
                scf
                ret

; dskchg — disk-change status inquiry.
; Fail with carry set until FDC driver lands.
dskchg:
                scf
                ret

; getdpb — build the Drive Parameter Block from the BPB.
; Called by the BIOS after reading the boot sector; HL points to the BPB.
; Must fill the 18-byte DPB at DPB_AREA and return with HL = DPB_AREA.
;
; STUB: DPB field encoding (directory mask, directory shift, total-clusters
; encoding) needs the MSX2 TH DPB layout chapter and the DSKIO oracle probe
; (see disk/PROVENANCE.md §Oracle probes, probe 2) before the BPB-to-DPB
; computation can be written correctly. Returns carry set (error) for now.
getdpb:
                scf
                ret

; choice — format-choice string (CHOICE entry point).
; Return HL = 0 (no format-choice string): we support only one fixed 720 KB
; geometry (MSX2 TH, disk ROM interface: HL = 0 means no choices offered).
choice:
                ld      hl, 0
                ret

; dskfmt — format disk (write support deferred indefinitely; not a loader need).
dskfmt:
                scf
                ret

; mtoff — turn off disk motor(s).
; No FDC yet, so this is a no-op; return without carry (not an error).
; MSX2 TH: MTOFF has no error-return convention; the BIOS ignores the return state.
mtoff:
                ret

; phyd_handler — physical disk I/O (behind the H.PHYD hook).
; Intercepted from the BIOS PHYDIO entry. FDC driver not yet implemented.
phyd_handler:
                scf
                ret

; bdos_entry — BDOS entry point (written into SYSTEM sysvar by INIT).
; FAT12 / FCB layer not yet implemented. BDOS Open ($0F) returns A=$FF (error)
; per MSX2 TH BDOS conventions; used here as a general "not supported" stub.
bdos_entry:
                ld      a, $FF
                ret

; --- pad to a full 16 KB page ($4000-$7FFF) --------------------------------
                ds      $8000 - $, $00
