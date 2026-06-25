; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; Part of zerobas-disk, included by disk.asm (build with `pasmo -I disk`).
; free-tail runtime: relocated templates + shared pg0_mainrom_* helpers + conout_body + int_h_body (Interface B)
; CLEAN-ROOM: every constant, address and algorithm here traces to a public source
; or a black-box oracle probe; nothing is derived from disassembly. See disk/PROVENANCE.md.

; --- shared page-0 main-ROM inter-slot helpers (CONOUT M8 + int_h A-2) ----------
; pg0_mainrom_in - save the current $A8 to PG_SV_A8 and page the main BIOS ROM into
; page 0. PORTABLE (no machine-specific hardcode): the main-ROM slot is read at runtime
; from EXPTBL[0] ($FCC1) - the standard cell holding the slot id (bit7=expanded,
; [3:2]=subslot, [1:0]=primary). Sets page-0's $A8 primary to that primary and, if the
; slot is expanded, programs its page-0 SECONDARY subslot too. Only the page-0 (and,
; transiently, page-3) $A8 fields move: page 1 (our disk ROM) keeps running this code
; and page 2 (the stack) survives, so call/ret is safe. Caller MUST be DI and MUST pair
; with pg0_mainrom_out. Clobbers A,B,C,D,E,H,L (callers save what they need).
; CLEAN-ROOM: EXPTBL/$FCC1, SLTTBL/$FCC5, the $A8 primary register and the $FFFF
; secondary protocol are documented MSX BIOS ABI (MSX2 TH ch.2/2.4); no oracle bytes.
; NOTE: on the CF-3300 EXPTBL[0]=$00 (unexpanded), so the primary path is exercised+
; validated; the expanded sub-path is spec-derived and NOT reachable here (review queue).
pg0_mainrom_in:
                in      a, ($A8)
                ld      (PG_SV_A8), a       ; save full primary-slot config (restore key)
                ld      a, (EXPTBL)         ; main-ROM slot id
                ld      c, a                ; C = slot id
                and     $03                 ; A = main-ROM primary
                ld      b, a                ; B = primary
                ld      a, (PG_SV_A8)
                and     $FC                 ; clear page-0 primary field
                or      b                   ; set page-0 primary = main-ROM primary
                out     ($A8), a            ; main-ROM primary now in page 0 (pages 1/2/3 kept)
                bit     7, c                ; main-ROM slot expanded?
                ret     z                   ; unexpanded -> primary switch is enough (CF-3300)
                ; --- expanded: select the page-0 subslot via the $FFFF/SLTTBL protocol ---
                ld      a, c
                rrca
                rrca
                and     $03                 ; A = main-ROM subslot S
                ld      e, a                ; E = S
                ld      hl, SLTTBL
                ld      a, b
                add     a, l                ; SLTTBL aligned, P<4 -> no page crossing
                ld      l, a                ; HL = &SLTTBL[P]
                ld      a, (hl)
                and     $FC                 ; clear page-0 subslot field
                or      e                   ; merge new page-0 subslot S
                ld      (hl), a             ; update the SLTTBL[P] mirror
                ld      e, a                ; E = new secondary value to write to $FFFF
                ld      a, b                ; primary P -> page-3 field
                rlca
                rlca
                rlca
                rlca
                rlca
                rlca                        ; P << 6
                ld      d, a                ; D = P in page-3 field
                ld      a, (PG_SV_A8)
                and     $3C                 ; keep pages 1/2 ; clear page-0 + page-3 fields
                or      b                   ; page-0 primary = P
                or      d                   ; page-3 primary = P (reach P's $FFFF expander)
                out     ($A8), a
                ld      a, e
                ld      ($FFFF), a          ; P's secondary: page-0 subslot = S
                ld      a, (PG_SV_A8)
                and     $FC                 ; restore page-3 (& 1/2) primaries; clear page 0
                or      b                   ; page-0 primary = P (main-ROM, now subslot S)
                out     ($A8), a
                ret

; pg0_mainrom_out - restore page 0 from PG_SV_A8 (the RAM slot's own secondary is never
; touched, so its page-0 subslot is intact). Clobbers A.
pg0_mainrom_out:
                ld      a, (PG_SV_A8)
                out     ($A8), a
                ret

; --- conout_body - the real $5454 CONOUT (M8/8.67) ------------------------------
; Emit the char in A via the main-ROM CHPUT ($00A2). Reached from the $5454 veneer
; (jp conout_body). Pages the main ROM into page 0 (pg0_mainrom_in), calls CHPUT,
; restores (pg0_mainrom_out). DI spans the window; EI on exit.
;   in:  A = char ; out: A = char, BC/DE/HL/IX/IY preserved
conout_body:
                ld      (CONOUT_CHAR), a    ; stash the char (A is needed for slot work)
                push    af                  ; preserve caller AF
                push    bc
                push    de
                push    hl
                di                          ; no interrupt while the BIOS is half-mapped
                call    pg0_mainrom_in
                ld      a, (CONOUT_CHAR)
                call    $00A2               ; CHPUT - emit A; preserves all registers
                call    pg0_mainrom_out     ; restore page 0
                ei
                pop     hl
                pop     de
                pop     bc
                pop     af                  ; restore caller AF
                ld      a, (CONOUT_CHAR)    ; return A = the emitted char
                ret

; --- int_h_body - the real $0038 DOS interrupt handler (A-2/8.70) ----------------
; A bare VDP ack is not enough: the kernel/COMMAND.COM need H.KEYI/H.TIMI/keyboard/
; JIFFY, which only the main-BIOS KEYINT runs. Stock's $0038 handler ($DDAE) inter-slot
; CALSLTs to the main-ROM KEYINT ($0038 entry -> body $0C3C, calling H.KEYI $FD9A +
; H.TIMI $FD9F) - the MSX1 standard, BIOS-agnostic. We do the same via pg0_mainrom_in:
; page the main ROM in, call $0038 (KEYINT does its own VDP ack), restore, return.
; KEYINT ends with its own EI; the di after the call closes that window before we
; un-map the main ROM. The interrupt arrives with SP in page 2/3 (interrupts are only
; live once DOS is up), so mapping the main ROM into page 0 leaves the stack intact -
; no private-stack switch needed (harden later if a probe shows SP in page 0).
int_h_body:
                push    af
                push    bc
                push    de
                push    hl
                di
                call    pg0_mainrom_in      ; main BIOS ROM -> page 0 (portable, EXPTBL[0])
                call    $0038               ; main-ROM KEYINT: ack + H.KEYI + H.TIMI + kb + JIFFY
                di                          ; close KEYINT's internal EI before un-mapping
                call    pg0_mainrom_out     ; restore page 0 = RAM
                pop     hl
                pop     de
                pop     bc
                pop     af
                ei
                ret

; --- pad to a full 16 KB page ($4000-$7FFF) --------------------------------
                ds      $8000 - $, $00
