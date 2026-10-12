; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; ===========================================================================
; sub2.asm — zerobas-sub2: the SECOND plain 32 KB sub ROM, in slot 3-3 (D-SUB2)
; ===========================================================================
; Ruled by Joost, 2026-10-11 ("Stage 1 now, plain 3-3 later"): when the first
; item the sub walls block reaches the queue, a second sub ROM in the empty
; secondary slot 3-3 -- the SAME shape as zerobas-sub in 3-2 (sub/sub.asm), the
; same CALSLT mechanism, zero extra cost per call, +16 KB on each island. The
; trigger was D-OPENGRP (2026-10-12): `OPEN "GRP:"`'s character logic and
; glyph loop do not fit sub page 1. Plan: scratchpad/subrom_arch_report.md
; Stage 2, steps (a)-(d); TODO.md D-SUB2.
;
; THIS IS STEP (b): THE SKELETON. Two islands, each with its marker, its jp
; table and a PING at index 0, its __MEAS_* wall label and its $FF pad -- and
; nothing main calls yet. `make sub2-acceptance` CALSLTs all four islands
; (3-2 and 3-3, page 0 and page 1) on BOTH repack machines by injection, so the
; ROM is proven present, placed and page-selective before main spends a byte
; on reaching it (step (c)).
;
; LAYOUT -- deliberately identical to sub.rom's, so every rule written for one
; holds for the other:
;   page 0 ($0000-$3FFF): "Z2" at $0000; `jp SUB_INT_RAM` at $0038 (the RAM
;     interrupt trampoline, which since step (a) restores the interrupted
;     tenant's LIVE slot -- so a page-0 tenant here comes back to 3-3, not to
;     3-2); the jp table at SUBROM_ENTRY_BASE_P0 ($0040).
;   page 1 ($4000-$7FFF): "S2" at $4000 (never "AB": the cartridge scan reads
;     $4000 of every subslot and would boot it); the jp table at
;     SUBROM_ENTRY_BASE_P1 ($4010).
; The ROM is chosen by the SLOT the caller CALSLTs ($8F = 3-3), never by the
; address, so the two ROMs share both table bases.
;
; ⚠️ "Z2", NOT "ZB". init_ext_roms discovers zerobas-sub by "ZB" at $0000 of
; every subslot (basic/subrom-boot.asm try_sub_slot) and records the slot it
; finds. A second "ZB" in 3-3 would make discovery depend on scan order --
; whichever it keeps, one ROM would be called as the other.
;
; CLEAN-ROOM: every byte here is own-design (see sub/PROVENANCE.md).
; ===========================================================================

SUB_BUILD       equ     1   ; the shared body .inc files see the sub side
DISK_BUILD      equ     0
                include "equates.inc"
                include "basic/sysvars.inc"

SUB2_PING_P0    equ     $C2 ; written to SUB_PING by the page-0 ping (ROM 1 writes $C0)
SUB2_PING_P1    equ     $C3 ; written to SUB_PING by the page-1 ping (ROM 1 writes $C1)

; ===========================================================================
; PAGE 0 — $0000-$3FFF
; ===========================================================================
                org     $0000
                db      "Z2"                    ; $0000: zerobas sub ROM 2 marker
                dw      0                       ; $0002: INIT -- none (passive callee)
                dw      0,0                     ; $0004-$0007: reserved
                dw      0,0,0,0                 ; $0008-$000F: reserved (RST area)
    IF $ > $0038
                db      SUB2_P0_HEADER_OVERRAN_0038
    ENDIF
                ds      $0038 - $, $FF
                jp      SUB_INT_RAM             ; $0038: -> the RAM trampoline
    IF $ > SUBROM_ENTRY_BASE_P0
                db      SUB2_P0_VECTOR_OVERRAN_THE_TABLE_BASE
    ENDIF
                ds      SUBROM_ENTRY_BASE_P0 - $, $FF

; --- Page-0 entry table (append-only; IX = SUBROM_ENTRY_BASE_P0 + 3*index) --
sub2_p0_table:
                jp      sub2_p0_ping            ; index 0: round-trip ping
                jp      beep_tenant             ; index 1 (SUB2_IDX_BEEP): the BEEP
                                                ;   body (sub/beep.asm), moved from
                                                ;   zerobas-sub page 0 by D-TOKOVF

; --- Page-0 PING: stamp SUB_PING with this island's own tag and return. The
; tag differs from ROM 1's page-0 $C0, so a CALSLT that reached 3-2 instead of
; 3-3 is told apart, not just one that reached nothing.
sub2_p0_ping:
                ld      a,SUB2_PING_P0
                ld      (SUB_PING),a
                ret

; --- BEEP (D-TOKOVF, 2026-10-12): direct PSG port I/O and a busy-wait, no BIOS
; and no sub-local helper, so it runs here unchanged. Its `ei` lands on this
; ROM's own $0038 -> SUB_INT_RAM, which returns to 3-3 (step (a) above).
                include "beep.asm"

; __MEAS_SUB2_P0_END: page-0 free space is $4000 - __MEAS_SUB2_P0_END
; (tools/check_sub_walls.py --sub2, a step of `make basic-reloc`).
__MEAS_SUB2_P0_END:
                ds      $4000 - $, $FF

; ===========================================================================
; PAGE 1 — $4000-$7FFF (the BIOS-visible island; NOT an "AB" header)
; ===========================================================================
                db      "S2"                    ; $4000: page-1 marker (NOT 'A','B')
                dw      0,0,0                   ; $4002-$4007: reserved
                dw      0,0,0,0                 ; $4008-$400F: reserved
    IF $ - SUBROM_ENTRY_BASE_P1
                db      SUB2_P1_TABLE_NOT_AT_4010__HEADER_SIZE_DRIFT
    ENDIF
sub2_p1_table:
                jp      sub2_p1_ping            ; index 0: round-trip ping
                jp      grpprt_tenant           ; index 1 (SUB2_IDX_GRPPRT): one byte
                                                ;   of PRINT # to OPEN "GRP:"
                                                ;   (D-OPENGRP; sub2/grpprt.asm)
                jp      edctrl_tenant           ; index 2 (SUB2_IDX_EDCTRL): the
                                                ;   editor's CTRL-B/E/F/N/U (D-EDCTRL,
                                                ;   moved from main: D-EDCARVE)

sub2_p1_ping:
                ld      a,SUB2_PING_P1
                ld      (SUB_PING),a
                ret

                include "sub2/grpprt.asm"
                include "basic-resident-abi.inc"   ; main-low: rl_vpeek / rl_vpoke / rl_lastrow
                include "sub2/edctrl.asm"

; __MEAS_SUB2_P1_END: page-1 free space is $8000 - __MEAS_SUB2_P1_END.
__MEAS_SUB2_P1_END:
                ds      $8000 - $, $FF
