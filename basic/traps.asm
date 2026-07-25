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
                ; STOP-handler grace (R1, spec §12.2): the grace lasts one VBLANK. Clear
                ; it here, UNCONDITIONALLY and BEFORE the TRAPENA fast-out — a SERVICING
                ; STOP handler has TRAPENA==0, so gating this on TRAPENA would leave the
                ; grace stuck set and make the handler un-abortable. check_traps re-sets
                ; it each time the STOP trap fires, so the live window is [fire, next VBLANK].
                xor     a
                ld      (STOPGRACE),a
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
                ld      bc,STOPGRACE-ZTRAP  ; bytes after the first = fill through STOPGRACE
                ldir
                ret

; ===========================================================================
; THE DISPATCH HALF (slice T1 = STOP; docs/spec-traps-t1-stop-reslice.md).
; Resident page-1, EI run loop, RAM-only. Reached from the run-loop TRAPPEND gate
; (check_traps) and the ex_return TRAPSVC gate (trap_return_check); both are
; affordable resident here (155 B page-1 free after the build_83_name carve,
; D-T-8c). The shared state helper set_state also arms STOP ON/OFF/STOP.
; ===========================================================================

; ztrap_entry: HL = &ZTRAP[A] (the state byte of entry index A).
;   IN: A = entry index (0..17).  OUT: HL = ZTRAP + A*ZTRAP_ENTSZ.
;   Clobbers DE. A preserved.
ztrap_entry:
                ld      l,a
                ld      h,0
                ld      e,l
                ld      d,h                 ; DE = A
                add     hl,hl               ; 2A
                add     hl,de               ; 3A   (ZTRAP_ENTSZ = 3)
                ld      de,ZTRAP
                add     hl,de               ; ZTRAP + 3A
                ret

; set_state: set a ZTRAP entry's tri-state, maintaining the TRAPENA (# ON) count.
;   IN: HL -> entry state byte;  A = new state (ZTS_OFF / ZTS_ON / ZTS_STOP).
;   OFF also clears PENDING (a disabled trap forgets its latched event); ON/STOP
;   preserve it. TRAPENA += 1 on (old!=ON -> new==ON), -= 1 on (old==ON -> new!=ON).
;   Clobbers A, B, C. Preserves HL, DE.
set_state:
                ld      c,a                 ; C = new state
                ld      a,(hl)
                ld      b,a                 ; B = old byte (holds PENDING)
                and     ZTS_STATE_MASK      ; A = old state
                cp      ZTS_ON
                jr      z,ss_wason
                ; old != ON: inc TRAPENA only if new == ON
                ld      a,c
                cp      ZTS_ON
                jr      nz,ss_write
                ld      a,(TRAPENA)
                inc     a
                ld      (TRAPENA),a
                jr      ss_write
ss_wason:
                ; old == ON: dec TRAPENA unless new is still ON
                ld      a,c
                cp      ZTS_ON
                jr      z,ss_write
                ld      a,(TRAPENA)
                dec     a
                ld      (TRAPENA),a
ss_write:
                ld      a,c
                or      a                   ; new == OFF?
                jr      z,ss_off
                ld      a,b
                and     ZTS_PENDING         ; keep the latched PENDING bit
                or      c                   ; | new state
                ld      (hl),a
                ret
ss_off:
                ld      (hl),ZTS_OFF        ; OFF: state 0 AND PENDING cleared
                ret

; ct_find: scan ZTRAP for the highest-priority firable entry.
;   OUT: CF=1 -> HL = &entry state byte, C = index, DE = handler link (all set);
;        CF=0 -> none firable.  Firable == state==ON && PENDING && handler!=0.
;   Clobbers A, B, C, DE, HL.
ct_find:
                ld      hl,ZTRAP
                ld      b,ZTRAP_NENT
                ld      c,0
ctf_lp:
                ld      a,(hl)
                bit     7,a                 ; PENDING?
                jr      z,ctf_next
                and     ZTS_STATE_MASK
                cp      ZTS_ON              ; state exactly ON?
                jr      nz,ctf_next
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = handler link
                dec     hl
                dec     hl                  ; HL -> state byte
                ld      a,d
                or      e
                scf
                ret     nz                  ; handler != 0 -> found
ctf_next:
                inc     hl
                inc     hl
                inc     hl                  ; next entry (3 B)
                inc     c
                djnz    ctf_lp
                or      a                   ; CF = 0, none firable
                ret

; check_traps: fire the highest-priority armed+pending trap, if any.
;   IN:  HL = the statement pointer about to run (the RETURN resume point).
;   OUT: CF=1 -> fired: a GOSUB frame was pushed, the entry is SERVICING, a
;                [GSP][idx] service record is on TRAPSTK, and CURLINE points at the
;                handler line's LINK (rp_lp then runs it fresh). HL consumed.
;        CF=0 -> nothing fired; HL/CURLINE unchanged, TRAPPEND cleared.
;   Called from rp_trapchk only when TRAPPEND!=0. Clobbers A, BC, DE.
check_traps:
                push    hl                  ; [S] = resume stmt ptr
                call    ct_find
                jr      nc,ct_none
                ld      a,(TRAPSVC)         ; service-stack depth guard
                cp      TRAPSTK_MAX
                jr      nc,ct_svc_full
                ; --- fire: HL=&state, C=idx, DE=handler ---
                ld      (hl),ZTS_SERVICING  ; clear PENDING + auto-suspend (bit7=0, state=11)
                ld      a,(TRAPENA)
                dec     a
                ld      (TRAPENA),a          ; one fewer ON trap while servicing
                pop     hl                  ; HL = resume ptr
                push    de                  ; save handler link across gosub_push
                call    gosub_push          ; push [CURLINE][resume=HL]; BC(idx) kept; CF=full
                jr      c,ct_gsfull
                ; record service entry [GSP][idx] at TRAPSTK + TRAPSVC*3
                ld      a,(TRAPSVC)
                ld      l,a
                ld      h,0
                ld      e,a
                ld      d,0
                add     hl,hl
                add     hl,de               ; 3*TRAPSVC
                ld      de,TRAPSTK
                add     hl,de               ; HL -> record slot
                ld      de,(GSP)            ; GSP after the push == the RETURN match key
                ld      (hl),e
                inc     hl
                ld      (hl),d
                inc     hl
                ld      (hl),c              ; idx
                ld      hl,TRAPSVC
                inc     (hl)
                ; STOP-trap grace (R1, spec §12.2): the STOP handler is entered while the
                ; triggering Ctrl-STOP may still be held. Grant it a one-VBLANK grace so
                ; rp_break does not immediately re-break it at its own first boundary
                ; (event_poll clears the grace next frame -> a key still held then aborts).
                ; Only the STOP entry cares: the STRIG/KEY/SPRITE handlers are not entered
                ; via Ctrl-STOP, so a Ctrl-STOP during them is a genuine break, ungraced.
                ld      a,c
                cp      ZTI_STOP
                jr      nz,ct_fired
                ld      a,1
                ld      (STOPGRACE),a
ct_fired:
                pop     de                  ; DE = handler link
                ld      (CURLINE),de        ; branch: rp_lp runs the handler line fresh
                scf                         ; (leave TRAPPEND set: a 2nd pending trap
                ret                         ;  fires next boundary; ct_none clears it)
ct_gsfull:
                pop     de                  ; discard handler
                jp      gosub_stk_over      ; control-stack overflow -> ERR 7
ct_svc_full:
                pop     hl                  ; discard resume ptr
                jp      gosub_stk_over      ; too many nested traps -> ERR 7
ct_none:
                pop     hl                  ; restore resume ptr (unchanged)
                xor     a
                ld      (TRAPPEND),a        ; nothing firable -> drop the gate (CF=0)
                ret

; trap_return_check: on RETURN, re-enable the trap whose service record's gsp
; matches the current (pre-pop) GSP. Called from ex_return only when TRAPSVC!=0.
; The top record is at TRAPSTK+(TRAPSVC-1)*3 = [gsp:2][idx:1]. On a gsp match this
; RETURN is the trap frame's own: pop the record, and iff the entry is still
; SERVICING (a handler X OFF/ON/STOP overrides) set it back to ON (+TRAPENA, and
; re-raise TRAPPEND if a fresh PENDING re-latched during the handler). No match ->
; a normal/nested RETURN, leave everything. Clobbers A, BC, DE, HL.
trap_return_check:
                ld      a,(TRAPSVC)
                dec     a
                ld      l,a
                ld      h,0
                ld      e,a
                ld      d,0
                add     hl,hl
                add     hl,de               ; 3*(TRAPSVC-1)
                ld      de,TRAPSTK
                add     hl,de               ; HL -> top record [gsp lo][gsp hi][idx]
                ld      de,(GSP)
                ld      a,(hl)
                cp      e
                ret     nz                  ; gsp lo mismatch -> normal RETURN
                inc     hl
                ld      a,(hl)
                cp      d
                ret     nz                  ; gsp hi mismatch
                inc     hl
                ld      c,(hl)              ; C = trap idx
                ld      hl,TRAPSVC
                dec     (hl)                ; pop the service record
                ld      a,c
                call    ztrap_entry         ; HL = &ZTRAP[idx]
                ld      a,(hl)
                and     ZTS_STATE_MASK
                cp      ZTS_SERVICING
                ret     nz                  ; handler changed the state -> leave it
                ld      a,(hl)
                and     $FC                 ; clear state bits, KEEP PENDING (bit 7)
                or      ZTS_ON              ; SERVICING -> ON (auto-resume)
                ld      (hl),a
                ld      a,(TRAPENA)
                inc     a
                ld      (TRAPENA),a
                ld      a,(hl)
                and     ZTS_PENDING         ; re-latched during the handler?
                ret     z
                ld      a,1
                ld      (TRAPPEND),a         ; yes -> fire again at the next boundary
                ret

    ENDIF
