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

; --- conout_body - the real $5454 CONOUT (M8/8.67; char-reg fix M10/§8.80) ------
; Emit the char (in E) via the main-ROM CHPUT ($00A2). Reached from the $5454 veneer
; (jp conout_body). Pages the main ROM into page 0 (pg0_mainrom_in), calls CHPUT,
; restores (pg0_mainrom_out). DI spans the window; EI on exit.
;   in:  E = char ; out: A = char, BC/DE/HL/IX/IY preserved
; CHAR REGISTER = E (not A). The $5454 CONOUT contract passes the char in E: the
; relocated MSX-DOS kernel's per-char console output (caller $D88A) loads E=char and
; leaves A=0, so reading A emitted $00/garbage for ALL COMMAND.COM-phase + A>-prompt
; output (banner/date/prompt rendered as constant tiles). The early MSXDOS.SYS sign-on
; (caller $0320) happens to pass the char in BOTH A and E, so the old A-read worked
; there and HID the bug -- the exact "early works, COMMAND fails" discriminator. E is
; the register common to BOTH callers. Black-box proven: $7922-entry callseq shows E
; spelling "MSX-DOS version 1.03" (early) and "Sun 84-01-01"/"A>" (kernel), A=0.
; CLEAN-ROOM: E=char is the MSX-DOS BDOS CONOUT (func 2) ABI convention; no oracle bytes.
conout_body:
                ld      a, e                ; char arrives in E ($5454 CONOUT contract)
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

; --- int_h_body - the OLD page-1 $0038 handler (A-2/A-2b) — SUPERSEDED by A-3 -------
; DEAD as of A-3: $0038 no longer points here (it points at INT_H_HIRAM). Kept in place
; (net-zero, no address shift) pending removal; the live handler is int_h_hiram_tmpl
; below, relocated into always-mapped high RAM because page 1 is reclaimed for the TPA.
; A bare VDP ack is not enough: the kernel/COMMAND.COM need H.KEYI/H.TIMI/keyboard/
; JIFFY, which only the main-BIOS KEYINT runs. Stock's $0038 handler ($DDAE) inter-slot
; CALSLTs to the main-ROM KEYINT ($0038 entry -> body $0C3C, calling H.KEYI $FD9A +
; H.TIMI $FD9F) - the MSX1 standard, BIOS-agnostic. We do the same via pg0_mainrom_in:
; page the main ROM in, call $0038 (KEYINT does its own VDP ack), restore, return.
int_h_body:
                ld      (INT_SP_SAVE), sp   ; A-2b: save caller SP (no stack touch) ...
                ld      sp, INT_STK_TOP     ; ... and run on our private interrupt stack,
                                            ; so a corrupt caller SP is never marched (§8.75)
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
                ld      sp, (INT_SP_SAVE)   ; A-2b: restore caller SP, then the single EI
                ei
                ret

; --- int_h_hiram_tmpl - the LIVE $0038 handler, A-3 + A-5 (tier2-a5-spec.md) ------
; Relocated by a plain LDIR into INT_H_HIRAM ($DDAE) page-3 high RAM during init, so it
; survives COMMAND.COM reclaiming page 1 (wa_seg_ram). RELOCATABLE: straight-line, ONLY a
; PC-relative jr + the FIXED call $0038 (no template-relative call/jp, same rule as
; res_print_tmpl). pg0_mainrom_in/out are INLINED (their `ret z` early-out becomes `jr z`);
; all data refs ($A8/$FFFF, EXPTBL/SLTTBL, PG_SV_A8, $0038) are absolute fixed addresses that
; survive relocation. Pages the main ROM into PAGE 0 only (page 1 = the TPA is never touched),
; calls the main-BIOS KEYINT, restores, EI, RET. BIOS-agnostic (EXPTBL[0]); the expanded-slot
; path is spec-derived (CF-3300 is unexpanded). CLEAN-ROOM: our own code/address; $DDAE is an
; oracle WHERE, never stock's bytes.
;
; A-5 (tier2-a5-spec.md): runs on the CALLER's (interrupted code's) stack — the standard MSX
; interrupt convention — NOT a private stack. The A-2b private stack was a guard against an
; interrupt firing with a corrupt caller SP (the primary derail); A-3 fixed that derail, so
; the caller SP is always valid here. The 48-byte private stack was in fact TOO SMALL for the
; main-ROM KEYINT (~60 B, unbounded via H.TIMI/H.KEYI hooks): KEYINT overflowed it DOWNWARD
; into the WA_SEG trampoline laid out just below it ($E795+), corrupting the $F368/$F36B
; segment switch and hanging the COMMAND.COM handoff (harness, 2026-06-26). Caller stacks
; here (kernel $DBFA, COMMAND.COM $F513…) have ample room, so this is both correct and safe.
int_h_hiram_tmpl:
                push    af
                push    bc
                push    de
                push    hl
                di
                ; --- inlined pg0_mainrom_in (main BIOS ROM -> page 0; EXPTBL[0]) ---
                in      a, ($A8)
                ld      (PG_SV_A8), a       ; save full primary-slot config (restore key)
                ld      a, (EXPTBL)         ; main-ROM slot id
                ld      c, a
                and     $03                 ; A = main-ROM primary
                ld      b, a
                ld      a, (PG_SV_A8)
                and     $FC                 ; clear page-0 primary field
                or      b
                out     ($A8), a            ; main-ROM primary now in page 0 (pages 1/2/3 kept)
                bit     7, c                ; main-ROM slot expanded?
                jr      z, ihh_keyint       ; unexpanded (CF-3300) -> primary switch is enough
                ; --- expanded: select page-0 subslot via the $FFFF/SLTTBL protocol ---
                ld      a, c
                rrca
                rrca
                and     $03                 ; A = main-ROM subslot S
                ld      e, a
                ld      hl, SLTTBL
                ld      a, b
                add     a, l                ; SLTTBL aligned, P<4 -> no page crossing
                ld      l, a                ; HL = &SLTTBL[P]
                ld      a, (hl)
                and     $FC                 ; clear page-0 subslot field
                or      e
                ld      (hl), a             ; update the SLTTBL[P] mirror
                ld      e, a                ; E = new secondary value for $FFFF
                ld      a, b
                rlca
                rlca
                rlca
                rlca
                rlca
                rlca                        ; P << 6
                ld      d, a
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
ihh_keyint:
                call    $0038               ; main-ROM KEYINT: ack + H.KEYI + H.TIMI + kb + JIFFY
                di                          ; close KEYINT's internal EI before un-mapping
                ; --- inlined pg0_mainrom_out (restore page 0 from PG_SV_A8) ---
                ld      a, (PG_SV_A8)
                out     ($A8), a
                pop     hl
                pop     de
                pop     bc
                pop     af
                ei
                ret
int_h_hiram_end:

; --- dos_handoff — DOS-only $F338 default + the step-7 "load the system" call ---
; COMMAND.COM's startup branches on $F338 (`ld a,($F338); and a; jr nz` @ $C26B):
; 0 = "no AUTOEXEC -> prompt", nonzero -> the wrong path (SELDSK/loop). Stock's disk
; ROM clears $F338 at boot; ours never did. We default it to 0 just before handing to
; the boot sector's step-7 entry. $F338 is dual-purpose (a $C9 RET BASIC hook stub on
; C-BIOS vs $00 for DOS), so we SAVE the host value and RESTORE it if the call returns --
; which only a non-system / data disk does (a real DOS disk JPs into MSXDOS.SYS and never
; returns, so the 0 persists to COMMAND.COM's read). The save uses the stack: on the
; no-return DOS path the push is simply abandoned (MSXDOS.SYS resets SP). Called from
; boot_sig_ok with IX=$F195 and the page-0 env laid; replaces the inline `scf; call
; BOOT_ENTRY` there -- net-zero in that $41FD-pad-packed region. (tier2-f338-default-spec.md)
; Also defaults the date-format config cells $F30D/$F30E (M9 date slice): COMMAND.COM
; reads $F30E at $CDA7 (`ld a,($F30E)`) to format the boot date; ours leaves them $FF
; (uninit) so the date prints malformed and the prompt loops. Stock's disk ROM defaults
; them to $F30D=01 / $F30E=00 at boot (observed black-box; clean-room, no stock bytes).
; Same DOS-only save/restore discipline as $F338, so a returning data disk leaves the
; host's cells untouched (BIOS-agnostic). (tier2-gdate-spec.md)
dos_handoff:
                ld      a, ($F338)          ; save host $F338 (BASIC hook stub on C-BIOS)
                push    af
                ld      hl, ($F30D)         ; save host $F30D/$F30E (date-format config)
                push    hl
                xor     a
                ld      ($F338), a          ; DOS default: $F338 = 0
                ld      hl, $0001
                ld      ($F30D), hl         ; DOS default: $F30D=01, $F30E=00 (date format)
                scf                         ; Cy = 1 -> step-7 "load the system" entry
                call    BOOT_ENTRY          ; DOS disk JPs into MSXDOS.SYS (no return)
                pop     hl                  ; data disk returned: recover host values
                ld      ($F30D), hl
                pop     af                  ; recover host $F338
                ld      ($F338), a          ; restore the dual-purpose stub for BASIC
                ret

; --- pad to a full 16 KB page ($4000-$7FFF) --------------------------------
                ds      $8000 - $, $00
