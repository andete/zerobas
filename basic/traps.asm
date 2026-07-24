; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; traps.asm — the resident half of the interrupt-trap machinery (arc slice T1).
; ===========================================================================
; docs/spec-basic-interrupt-traps.md. Only the interrupt-path code lives here:
; the per-frame event poll (event_poll), reached from C-BIOS's $0038 timer ISR
; through the H.TIMI ($FD9F) hook ahead of the PLAY servicer; the H.TIMI
; trampoline that chains the two; and trap_init (cold-boot / RUN reset of the
; ZTRAP table). The DISPATCH half (check_traps + the RETURN re-enable) is NOT
; here — it runs in the EI run loop, touches only RAM, and lives in a sub-ROM
; page-1 tenant reached by subrom_call, gated by the resident TRAPPEND byte
; event_poll raises (D-T-2a): the per-statement cost is one RAM load, and the
; expensive tenant call fires ~once per trap event, never per statement.
;
; INTERRUPT DISCIPLINE (inherited from play_service, playsvc.asm §): event_poll
; is entered DI (it's the ISR), stays DI, is register-transparent (saves every
; register it touches), and reads/writes only its own RAM (ZTRAP/ZINTCNT/ZINTVAL/
; TRAPPEND) — never JIFFY, never the keyboard, no PSG. It runs BEFORE the PLAY
; drain each frame, so it must leave AF/DE/HL exactly as found.
;
; T1 scope: only the INTERVAL trap (entry 0) has an event source — a pure frame
; down-counter, zero device I/O. STOP/STRIG/KEY/SPRITE sources are added by
; T2..T4; event_poll grows a stanza per slice.
;
; Repack-only (IF ROM_BASE < $4000), like playsvc.asm: the H.TIMI seam and the
; trap table only exist in the repacked page-1 window. The lean 16 KB ROM is
; byte-identical (nothing here is assembled into it).
;
; CLEAN-ROOM: own-design table + poll (docs §3, quarantined in PROVENANCE.md).
; The trap MODEL (types, ON/OFF/STOP tri-state + auto-suspend, RETURN re-enable)
; is the published MSX Technical Handbook contract; the RAM layout and the
; TRAPPEND/service-stack mechanism are own-design. No ROM bytes lifted.

    IF ROM_BASE < $4000

; htimi_service: the H.TIMI seam target (installed by play_install, playsvc.asm).
; Poll the traps, then fall into the PLAY drain (its own MUSICF==0 fast-out keeps
; the always-installed seam cheap). jp (not call) so play_service's ret returns
; straight to the $0038 ISR.
htimi_service:
                call    event_poll
                jp      play_service

; event_poll: one frame of trap event detection. Called from htimi_service every
; VBLANK, DI, register-transparent. Fast-out when no trap is ON (the common case).
; For each armed event source, set the entry's PENDING bit + raise TRAPPEND so the
; run-loop dispatcher wakes. T1: INTERVAL only.
event_poll:
                push    af                  ; register-transparent on ALL paths (the
                                            ; H.TIMI contract) — the fast-out MUST NOT
                                            ; leak the TRAPENA test into A/flags, or it
                                            ; corrupts the timer ISR that called us.
                ld      a,(TRAPENA)
                or      a
                jr      z,ep_out            ; no ON traps -> fast out (common path)
                push    hl
                push    de
                ; --- INTERVAL (entry 0): tick only while its state is exactly ON ---
                ld      a,(ZTRAP)           ; ZTRAP+0 = INTERVAL entry state byte
                and     ZTS_STATE_MASK
                cp      ZTS_ON
                jr      nz,ep_done          ; OFF / STOP / SERVICING -> do not tick
                ld      hl,(ZINTCNT)
                dec     hl
                ld      (ZINTCNT),hl
                ld      a,h
                or      l
                jr      nz,ep_done          ; period not elapsed yet
                ld      hl,(ZINTVAL)        ; reload the period
                ld      (ZINTCNT),hl
                ld      hl,ZTRAP            ; latch PENDING on the INTERVAL entry
                set     7,(hl)
                ld      a,1
                ld      (TRAPPEND),a        ; wake the run-loop dispatcher
ep_done:
                pop     de
                pop     hl
ep_out:
                pop     af
                ret

; trap_init: reset the whole ZTRAP table + all bookkeeping to zero — every trap
; OFF, no handler, no pending, counters/gates clear. Called at cold boot (before
; any statement runs) and at RUN (re-arm), so garbage RAM can never look like a
; phantom armed trap. Zeroes ZTRAP..TRAPPEND ($E1D1..$E21F) in one fill.
; Clobbers A, BC, DE, HL.
trap_init:
                ld      hl,ZTRAP
                ld      (hl),0
                ld      de,ZTRAP+1
                ld      bc,TRAPPEND-ZTRAP   ; bytes after the first = fill the rest
                ldir
                ret

    ENDIF
