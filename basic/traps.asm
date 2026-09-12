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
; is entered DI (it's the ISR), stays DI, and is register-transparent — it saves
; every register it touches, and since T2's GTTRIG call is documented "Registers:
; All", that set is AF/BC/DE/HL/IX/IY (play_service's exact list). It never reads
; JIFFY and never touches the BIOS key buffer. It runs BEFORE the PLAY drain each
; frame, so it must leave every register exactly as found.
;
; Event sources so far: STOP (T1) is NOT polled here — it rides the run loop's
; existing BREAKX detection (spec-traps-t1-stop-reslice.md §6); STRIG 0..4 (T2)
; IS polled, via the published page-0 BIOS GTTRIG (a plain call, never CALSLT —
; the VBLANK ban stands). INTERVAL (T5) is polled here too — a pure frame
; down-counter, no I/O at all.
;
; ⚠️ THIS PARAGRAPH USED TO END "KEY/SPRITE sources arrive with T3/T4; event_poll
; grows one stanza per slice", and BOTH ARRIVED (corrected 2026-09-03,
; D-DEFERSWEEP) — but NOT as event_poll stanzas, which is why the stale line
; survived: KEY (T3) is a C-BIOS keyboard-scan hook in `basic/keytrap.asm`
; because no published ISR seam runs after the scan, and SPRITE (T4) is sampled
; in `basic/sprtrap-body.inc` from `basic/subromcall.asm` ahead of the slot test
; (D-T4-2). §"the shadow" below already named "T2 STRIG, T3 KEY and now T1 STOP"
; — two sections of one file disagreeing on the load-bearing list, which is a
; class this project has been bitten by before.
; [[two-sections-of-one-doc-disagreed]]
;
; ⚠️ This header used to say "INTERVAL's counter stanza is retained but inert on
; MSX1 (INTERVAL is an MSX2 statement — out of charter)". That was RETRACTED on
; 2026-07-26: INTERVAL is MSX1, it works on the VG-8020, and it is simply not a
; keyword — a reserved-word compound INT+"ER"+VAL, which is why a crunch-table
; probe could not see it. "Absent from the keyword table" ≠ "absent from the
; language" (docs/spec-basic-interrupt-traps.md §0).
;
; CLEAN-ROOM: own-design table + poll (docs §3, quarantined in PROVENANCE.md).
; The trap MODEL (types, ON/OFF/STOP tri-state + auto-suspend, RETURN re-enable)
; is the published MSX Technical Handbook contract; the RAM layout and the
; TRAPPEND/service-stack mechanism are own-design. No ROM bytes lifted.


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
; run-loop dispatcher wakes. T2: STRIG 0..4 (the only polled source on MSX1).
; --- trap_pend: raise TRAPPEND, at five sites ------------------------------
; `ld a,1` + `ld (TRAPPEND),a` stood at five sites, 5 B each -- the three event
; sources, rp_break's STOP latch and ei_set. Flag-transparent (neither `ld` nor
; `ret` writes F), so every site keeps whatever flags it had, and A is left
; holding 1 exactly as before.
; ⚠️ TWO OF THE FIVE ARE INSIDE `event_poll`, i.e. the H.TIMI ISR path, whose
; contract is REGISTER TRANSPARENCY -- satisfied here because the helper touches
; only A, which event_poll's own entry `push af` has already saved.
trap_pend:
                ld      a,1
                ld      (TRAPPEND),a
                ret

event_poll:
                push    af                  ; register-transparent on ALL paths (the
                                            ; H.TIMI contract) — the fast-out MUST NOT
                                            ; leak the TRAPENA test into A/flags, or it
                                            ; corrupts the timer ISR that called us.
                ; (The STOPGRACE clear that used to sit here is GONE, spec §12.3. The
                ; STOP entry's edge shadow subsumed it: check_traps preserves ZTS_SHADOW
                ; across a fire, so the still-held triggering key cannot re-latch, which
                ; is what the one-VBLANK grace was approximating. Nothing here samples
                ; Ctrl-STOP — STOP still rides the run loop's BREAKX seam, rp_break.)
                ld      a,(TRAPENA)
                or      a
                jr      nz,ep_live
                ; TRAPENA counts only ON traps, and check_traps DECREMENTS it on fire --
                ; so with a single armed trap it is 0 for the whole time that trap's
                ; handler runs. Gating on it alone would switch the device poll off
                ; exactly during SERVICING, and a press inside the handler (which must
                ; latch and fire after RETURN -- oracle case I) would be dropped. So a
                ; live service stack keeps the poll running too. The gate stays two RAM
                ; loads on the common no-trap path.
                ld      a,(TRAPSVC)
                or      a
                jr      nz,ep_live
    IF TRAPS_T5
                ; ...AND a third term, because TRAPENA counts only ON traps.
                ; MEASURED (docs/spec-traps-t5-interval.md §1.4, P_on_reloads):
                ; with INTERVAL the sole trap and it STOPped, TRAPENA and TRAPSVC
                ; are both 0 -- so without this the poll fast-outs, the counter
                ; FREEZES while suspended, and the case reads 1 fire where the
                ; reference gives 2. D-T5-2, signed off: the suspend semantics are
                ; worth one more test per frame on the common no-trap path.
                ;
                ; ⚠️ A-ONLY, DELIBERATELY. The obvious `ld hl,(ZINTVAL) / ld a,h /
                ; or l` is three bytes shorter and BREAKS THE H.TIMI CONTRACT: this
                ; is ahead of ep_live's `push hl`, so it would clobber HL on both
                ; paths -- including the fast-out, which restores only AF. That is
                ; the exact register-transparency hazard the entry comment above
                ; warns about, one instruction after the warning. A is already
                ; saved by the entry `push af`, so testing the two bytes through it
                ; costs a few T-states and cannot leak.
                ld      a,(ZINTVAL)         ; armed at all? (0 = disarmed; ON INTERVAL=0
                or      a                   ; is ERR 5, so an armed ZINTVAL is never 0)
                jr      nz,ep_live
                ld      a,(ZINTVAL+1)
                or      a
                jr      nz,ep_live
    ENDIF
                jr      ep_out              ; nothing ON, nothing servicing, no INTERVAL
ep_live:
                push    hl
                push    de
    IF TRAPS_T5
                ; --- INTERVAL (entry 0): the per-frame down-counter -------------
                ; docs/spec-traps-t5-interval.md §2.1. This stanza was written for
                ; INTERVAL as the ORIGINAL slice T1 (7a91fd1), then deleted in
                ; 00a593a as "provably dead" on the strength of the
                ; "INTERVAL is MSX2" finding -- which was RETRACTED (arc spec §0).
                ; It is restored here, and it is NOT the same code: running it
                ; against the VG-8020 falsified BOTH of its state tests.
                ;
                ; ⚠️ CORRECTION 1 -- the original gated on `cp ZTS_ON` and that is
                ; WRONG. The counter must keep ticking while the trap is STOPped
                ; (P_on_reloads: n=300 over ON 200 fr / STOP 200 fr / ON 200 fr
                ; reads 2 fires; tick-only-while-ON predicts 1) AND while its
                ; handler runs (S3: with a 47-frame handler and n=100 the gap is
                ; exactly 100, not 147 -- the period is counted from the FIRE, not
                ; from RETURN). So: tick whenever armed, and latch PENDING unless
                ; the state is OFF. ZTS_OFF is 0, so the latch guard is one `and`.
                ; That is also one comparison CHEAPER than the version it replaces.
                ;
                ; Latching-but-not-firing while STOPped is what makes STOP remember
                ; exactly ONE elapsed period (G2_stop_release: three periods pass
                ; suspended, one fires on re-enable) while OFF forgets (H2: zero) --
                ; the same family answer as T1-T4, reached with no INTERVAL-specific
                ; state. There is no edge shadow: the event is GENERATED, not
                ; sampled, so there is no level to de-bounce.
                ld      hl,(ZINTVAL)
                ld      a,h
                or      l
                jr      z,ep_ivl_done       ; not armed -> nothing to tick
                ld      hl,(ZINTCNT)
                dec     hl
                ld      (ZINTCNT),hl
                ld      a,h
                or      l
                jr      nz,ep_ivl_done      ; period not elapsed yet
                ld      hl,(ZINTVAL)        ; reload AT THE FIRE (not at RETURN)
                ld      (ZINTCNT),hl
                ld      a,(ZTRAP)           ; ZTRAP+0 = the INTERVAL state byte
                and     ZTS_STATE_MASK
                jr      z,ep_ivl_done       ; OFF (00) -> elapse silently, do not latch
                ld      hl,ZTRAP
                set     7,(hl)              ; PENDING
                call    trap_pend   ; wake the run-loop dispatcher
ep_ivl_done:
    ENDIF
                ; --- STRIG 0..4 (entries ZTI_STRIG0..+4): joystick trigger edges ---
                ; docs/spec-traps-t2-strig.md §4. A trigger is sampled while its entry
                ; is ON *or* SERVICING, and not while it is OFF or STOP. Both sampled
                ; states have bit 0 set (ON=01, SERVICING=11) and neither unsampled one
                ; does (OFF=00, STOP=10), so the whole test is one `bit 0`.
                ; WHY SERVICING COUNTS (VG-8020-measured, §1.1 case I): a press while
                ; the handler runs is LATCHED -- it cannot fire then (state != ON), but
                ; trap_return_check re-raises TRAPPEND when RETURN restores ON, so it
                ; fires exactly once afterwards. Sampling only ON would silently drop it.
                ; Not sampling while OFF/STOP is what makes a press during those windows
                ; forgotten (§1.2, G/H); a press predating an ENABLE is handled instead
                ; by the arming statement seeding the shadow.
                ; GTTRIG is a PUBLISHED page-0 BIOS entry, so this is a plain `call`,
                ; NOT a CALSLT -- the VBLANK CALSLT ban stands. It is documented
                ; "Registers: All", so BC/IX/IY join the saved set (AF/DE/HL are
                ; already guarded above); the H.TIMI contract is total transparency.
                push    bc
                push    ix
                push    iy
                ld      hl,ZTRAP+ZTI_STRIG0*ZTRAP_ENTSZ
                ld      e,0                 ; E = trigger number 0..4
ep_strig_lp:
                bit     0,(hl)              ; state bit 0 = ON or SERVICING (see above)
                jr      z,ep_strig_next     ; OFF / STOP -> not sampled at all
                push    hl
                push    de
                ld      a,e                 ; A = trigger number for GTTRIG
                call    GTTRIG              ; A = $00 released / $FF pressed
                pop     de
                pop     hl
                or      a
                jr      nz,ep_strig_down
                res     6,(hl)              ; released -> the shadow follows the level
                jr      ep_strig_next       ; down, so the NEXT press is an edge
ep_strig_down:
                bit     6,(hl)
                jr      nz,ep_strig_next    ; still held since last frame -> no edge
                set     6,(hl)              ; 0->1 edge: latch the level...
                set     7,(hl)              ; ...and the entry's PENDING
                call    trap_pend   ; wake the run-loop dispatcher
ep_strig_next:
                inc     hl
                inc     hl
                inc     hl                  ; next entry (3 B)
                inc     e
                ld      a,e
                cp      5                   ; STRIG 0..4
                jr      c,ep_strig_lp
                pop     iy
                pop     ix
                pop     bc
                pop     de
                pop     hl
ep_out:
                pop     af
                ret

; trap_init: reset the whole ZTRAP table + all bookkeeping to zero — every trap
; OFF, no handler, no pending, counters/gates clear. Called at cold boot (before
; any statement runs) and at RUN (re-arm), so garbage RAM can never look like a
; phantom armed trap. Zeroes ZTRAP..TRAPPEND ($E1D1..$E21F) in one fill. The edge
; shadow needs no byte of its own -- it is bit 6 of each entry (T2 STRIG, T3 KEY and
; now T1 STOP), so this same fill clears it. Clobbers A, BC, DE, HL.
trap_init:
                ld      hl,ZTRAP
                ld      (hl),0
                ld      de,ZTRAP+1
                ld      bc,TRAPPEND-ZTRAP   ; bytes after the first = fill through TRAPPEND
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
                ld      a,(TRAPENA)         ; 🔴 NOT `ld hl,TRAPENA / inc (hl)`
                inc     a                   ; (D-PEEPHOLE): set_state's header
                ld      (TRAPENA),a         ; promises it PRESERVES HL, and HL
                jr      ss_write            ; is the entry byte ss_write stores to.
ss_wason:
                ; old == ON: dec TRAPENA unless new is still ON
                ld      a,c
                cp      ZTS_ON
                jr      z,ss_write
                ld      a,(TRAPENA)         ; 🔴 NOT `ld hl,TRAPENA / dec (hl)`
                dec     a                   ; (D-PEEPHOLE): set_state PRESERVES HL
                ld      (TRAPENA),a         ; -- see the arm above.
ss_write:
                ld      a,c
                or      a                   ; new == OFF?
                jr      z,ss_off
                ld      a,b
                and     ZTS_PENDING+ZTS_SHADOW  ; keep the latched PENDING bit AND the T2
                                            ; device edge shadow. Preserving bit 6 here is
                                            ; load-bearing: `STRIG(n) ON` on an ALREADY-ON
                                            ; trap takes this path and does not re-seed, so
                                            ; clearing the shadow would let a trigger held
                                            ; across it fake a 0->1 edge on the next frame.
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
                ld      bc,ZTRAP_NENT*256   ; D-PEEPHOLE: b=count, c=0 in one
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
                ; D-CTLPOOL: the TRAPSTK_MAX depth guard is GONE. The service
                ; record comes out of the control pool now, so "too many nested
                ; in-service traps" is the same condition as every other
                ; overflow -- the pool met the variable area -- and ctl_alloc
                ; below is the one place that decides it.
                ; --- fire: HL=&state, C=idx, DE=handler ---
                ld      a,(hl)
                and     ZTS_SHADOW          ; KEEP the T2 device edge shadow (bit 6) --
                or      ZTS_SERVICING       ; dropping it would let a trigger still held
                ld      (hl),a               ; when the handler RETURNs re-fire (oracle Q2).
                                            ; PENDING (bit 7) is cleared, state = SERVICING.
                ld      hl,TRAPENA
                dec     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
                pop     hl                  ; HL = resume ptr
                push    de                  ; save handler link across gosub_push
                call    gosub_push          ; push [CURLINE][resume=HL]; BC(idx) kept; CF=full
                jr      c,ct_gsfull
                ; D-CTLPOOL: the service record goes on the pool, pushed AFTER the
                ; GOSUB frame so it lands at a LOWER address -- newer than the
                ; frame, and therefore freed by the one `CSP := GSP + GOSUB_FRAME`
                ; store in ret_frame. 🎯 AND THE `gsp` KEY IS GONE WITH THE ARRAY:
                ; the record sits immediately below its own frame, so "is this
                ; RETURN the trap's own?" is the pointer identity
                ; TSP + TRAP_FRAME == GSP -- no stored key and no search.
                push    bc                  ; guard the trap index
                ld      hl,TRAP_FRAME
                call    ctl_alloc
                pop     bc
                jr      c,ct_gsfull
                ex      de,hl               ; DE = the record's base
                ld      hl,(TSP)
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a              ; [0..1] prevTSP -- the record chain
                inc     de
                ld      a,c
                ld      (de),a              ; [2] the trap index
                ld      hl,(CSP)
                ld      (TSP),hl
                ; ⚠️ AND FSP MOVES WITH IT. FSP is the FOR run's floor; leaving it
                ; at the GOSUB frame's base would put this 3-byte record INSIDE the
                ; run, where the next NEXT would read it as a FOR frame.
                ld      (FSP),hl
                ld      hl,TRAPSVC
                inc     (hl)
                ; (The STOP-trap STOPGRACE set that used to sit here is GONE, spec §12.3.
                ; The `and ZTS_SHADOW` above already carries the entry's edge shadow into
                ; SERVICING, so the triggering Ctrl-STOP — still held when the handler is
                ; entered — is not a fresh edge and cannot re-latch. That is the whole job
                ; the grace was doing, without its one-frame expiry, which was aborting
                ; handlers the reference never aborts.)
                pop     de                  ; DE = handler link
                ld      (CURLINE),de        ; branch: rp_lp runs the handler line fresh
                scf                         ; (leave TRAPPEND set: a 2nd pending trap
                ret                         ;  fires next boundary; ct_none clears it)
ct_gsfull:
                pop     de                  ; discard handler
                jp      gosub_stk_over      ; control-pool overflow -> ERR 7
                                            ; (ct_svc_full is retired with
                                            ;  TRAPSTK_MAX -- one arm, not two)
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
                ; D-CTLPOOL: the top record is at TSP, and it is the CURRENT
                ; RETURN's own iff it sits immediately below that RETURN's GOSUB
                ; frame. No stored gsp key, no multiply, no array base.
                ld      hl,(TSP)
                ld      de,TRAP_FRAME
                add     hl,de
                ld      de,(GSP)
                or      a
                sbc     hl,de
                ret     nz                  ; a normal or nested RETURN -- leave all
                ld      hl,(TSP)
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = prevTSP
                inc     hl
                ld      c,(hl)              ; C = trap idx
                ld      (TSP),de            ; pop the record (its POOL space is
                                            ; reclaimed by ret_frame's single
                                            ; CSP := GSP + GOSUB_FRAME, below it)
                ld      hl,TRAPSVC
                dec     (hl)
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
                ld      a,(TRAPENA)         ; 🔴 NOT `ld hl,TRAPENA / inc (hl)`
                inc     a                   ; (D-PEEPHOLE): the very next
                ld      (TRAPENA),a         ; instruction READS (hl).
                ld      a,(hl)
                and     ZTS_PENDING         ; re-latched during the handler?
                ret     z
                call    trap_pend   ; yes -> fire again at the next boundary
                ret

