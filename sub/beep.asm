; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; beep.asm -- BEEP as a PAGE-0 sub-ROM tenant (SUBROM_IDX_BEEP).
; docs/spec-basic-input-devices.md §7 (the I1 funding carve).
;
; WHY THIS ONE. Input-devices slice I1 needed 44 B of page-1 tail that did not
; exist (6 B free at the arc's start, and the ev_f_ff dispatch golf recovered only
; part of it). scratchpad/g7_carve_scout.py shortlisted ex_beep at 71 B: the only
; candidate in that size class that is BOTH a single-entry page-0-clean carve AND
; free of interrupt context. (The two larger clean carves it also found, psv_fetch
; and psv_env at 130 B each, are PLAY-servicer halves that run from H.TIMI --
; evicting those would put a CALSLT inside the VBLANK handler, which is not a
; trade worth making for 44 B.)
;
; PAGE-0 CLEAN, transitively: the body is direct PSG port I/O plus a counted
; busy-wait. No BIOS, no page-0 low region (no float pack, no eval), no CALSLT of
; its own -- exactly the closure rule a page-0 tenant must satisfy.
;
; It is also a good fit on two counts beyond size:
;   * COLD -- BEEP is a user-visible ~33 ms tone, so one CALSLT round trip
;     (~100 T) is far below anything observable, and the standing beep-acceptance
;     PSG-trace gate is +-1 frame tolerant by construction.
;   * The `ei` across the delay (reference-faithful: the reference times its tone
;     with interrupts live) is SAFE in a page-0 tenant precisely because the
;     sub-ROM owns its own page-0 $0038 trampoline -- the mechanism the graphics
;     arc built so a long draw can keep interrupts live. This carve is only
;     possible because that exists.
;
; The body below is the resident routine MOVED VERBATIM, with two edits: the
; leading `inc hl` (past the BEEP token) and the trailing `jp exec_stmt` stay
; RESIDENT in the stub -- a tenant neither owns the token cursor nor performs the
; statement tail. Nothing rides back: BEEP has no result and cannot fail.

BEEP_DELAY_ITERS equ    $1200               ; 4608 -> ~33 ms nominal, ~2 VBLANK
                                            ; frames at 3.58 MHz. Calibrated so the
                                            ; psgtrace gate sees the beep span >= 1
                                            ; sampled frame (duration is not
                                            ; black-box-pinnable finer than ~1 frame).
PSG_ADDR        equ     $A0                 ; PSG register-latch port (write reg number)
PSG_DATW        equ     $A1                 ; PSG data-write port
PSG_DATR        equ     $A2                 ; PSG data-read port

; beep_tenant -- one short tone-A blip, then silence + the mixer wiped to default.
; Entry: nothing. Exit: nothing (no result, no failure mode). Clobbers AF/BC/DE.
; docs/spec-basic-audio-beep.md holds the pinned VG-8020 contract this reproduces.
beep_tenant:
                di                          ; --- program the beep (atomic vs play_service) ---
                ld      a,7
                out     (PSG_ADDR),a        ; latch R7
                in      a,(PSG_DATR)        ; A = current R7 -- ONLY the two I/O-direction bits
                                            ; (6-7) read back reliably; the low 6 mixer bits
                                            ; read as 0 (same as SOUND's R7 handling), so the
                                            ; mixer is RECONSTRUCTED below, not saved/restored.
                and     $C0                 ; keep only the two I/O-direction bits
                ld      e,a                 ; E = preserved I/O bits (survives beep_delay,
                                            ; which clobbers BC -- used to reconstruct the
                                            ; restore mixer in the tail)
                or      $3E                 ; + tone A on, tones B/C off, all noise off
                ld      b,a                 ; B = beep mixer byte = ioBits | $3E  ($be)
                xor     a
                out     (PSG_ADDR),a        ; latch R0 (tone A fine)
                ld      a,$55
                out     (PSG_DATW),a        ; R0 = $55  (period low)
                ld      a,1
                out     (PSG_ADDR),a        ; latch R1 (tone A coarse)
                xor     a
                out     (PSG_DATW),a        ; R1 = $00  (period high) -> period $0055
                ld      a,7
                out     (PSG_ADDR),a        ; latch R7 (mixer)
                ld      a,b
                out     (PSG_DATW),a        ; R7 = (curR7 & $C0) | $3E
                ld      a,8
                out     (PSG_ADDR),a        ; latch R8 (channel A amplitude)
                ld      a,7
                out     (PSG_DATW),a        ; R8 = 7  (fixed volume, no envelope)
                ei                          ; delay with interrupts live (reference-faithful;
                                            ; safe here -- the sub-ROM owns its page-0 $0038)
                call    beep_delay          ; ~2 VBLANK frames
                di                          ; --- silence + restore (atomic vs play_service) ---
                ld      a,8
                out     (PSG_ADDR),a        ; latch R8
                xor     a
                out     (PSG_DATW),a        ; R8 = 0  (silence channel A)
                ld      a,7
                out     (PSG_ADDR),a        ; latch R7
                ld      a,e                 ; E = preserved I/O bits (beep_delay kept it)
                or      $38                 ; + all tones on, all noise off (the default mixer)
                out     (PSG_DATW),a        ; R7 = ioBits | $38  ($b8) -- BEEP wipes the mixer
                                            ; back to default; it does NOT restore a prior SOUND 7
                                            ; value (VG-8020: `sound 7,190:beep` leaves R7=$b8).
                ei
                ret                          ; (resident stub performs the statement tail)

; beep_delay -- a plain counted busy-wait, ~2 VBLANK frames (~33 ms) at 3.58 MHz.
; A software delay, exactly as the reference BEEP times its tone (not a JIFFY read --
; self-contained, no dependence on the timer hook). BC-only; AF clobbered; DE kept
; (the mixer's preserved I/O bits ride in E across it).
beep_delay:
                ld      bc,BEEP_DELAY_ITERS
bd_loop:
                dec     bc
                ld      a,b
                or      c
                jr      nz,bd_loop
                ret
