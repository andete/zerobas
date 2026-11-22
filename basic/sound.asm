; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; sound.asm — the SOUND statement handler (audio arc, Slice 1).
;
;   SOUND register, value    write one byte to a PSG register
;
; SOUND is a synchronous single register write — no interrupt, no queue, no
; sub-ROM tenant (spec-basic-audio-play.md §3.D). C-BIOS's own boot GICINI leaves
; the PSG quiet (amplitudes 0), so a fresh SOUND still needs no init of ours.
;
; ⚠️ THIS PARAGRAPH USED TO DEFER A GICINI-EQUIVALENT TO "Slice 2", on the
; grounds that "there are no PLAY queues / MUSICF to zero yet". They shipped
; (basic/play.asm, basic/playsvc.asm) and the deferral was never revisited —
; D-DEFERSWEEP's whole point. Corrected 2026-09-03: what was missing is
; `psg_silence` below, a TEARDOWN rather than the init the deferral named, and it
; was a real 6-row divergence (docs/spec-basic-gicini.md).
;
; Faithful contract — every boundary black-box-captured from the Philips VG-8020
; reference (scratchpad spikes, 2026-07-21), NOT taken from the draft spec:
;   * register: 0..13 valid. 14..255 -> Illegal function call (ERR 5); the spec
;     draft's "registers 14/15 are silently masked" was WRONG — the reference
;     RAISES on them (SOUND 14,0 -> ERR5, SOUND 16,0 -> ERR5).
;   * register / value coercion: >int16 -> Overflow (ERR 6); in-int16 but >255 or
;     negative -> Illegal function call (ERR 5). Same D-F2-2 byte-arg leaf
;     (get_byte_arg) STRING$/SPACE$/ON/WIDTH use (docs/spec-basic-df2-2-intarg-
;     coercion.md; [memory: df2-2-intarg-coercion-arc]).
;   * value: byte 0..255, written whole to registers 0..6, 8..13.
;   * register 7 (mixer): the top two bits are the PSG I/O-direction bits the BIOS
;     configured (port A input / port B output, "10"); SOUND must NOT change them.
;     Confirmed: SOUND 7,192 -> R7=$80, SOUND 7,255 -> R7=$bf (top 2 bits stay the
;     current R7's; low 6 come from the value). So R7' = (curR7 & $C0) | (val & $3F).
;
; PSG access is direct port I/O (sign-off Q4): latch the register number on port
; $A0, write the data on $A1 (read-back for R7 via the data-read port $A2). The
; PSG ports are slot-independent (spec §2.3, MSX BIOS list map.grauw.nl). No DI/EI
; guard — matches the reference WRTPSG/RDPSG, and C-BIOS's timer ISR does not
; touch the PSG latch, so the latch survives across the read-modify-write.
;
; Clean-room: original code, modelled on vdpio.asm's arg-parse. SOUND *semantics*
; + the register/value ranges + the R7 mask are from the public MSX-BASIC language
; reference / MSX Wiki AND the black-box VG-8020 captures above; the PSG port
; protocol is from the MSX Assembly Page BIOS list (see PROVENANCE.md). No
; disassembly.
;
; Entry: ex_sound, HL on the SOUND token. On success continue the statement loop
; (jp exec_stmt) so the verbs chain on one `:`-separated line.
PSG_ADDR        equ     $A0                 ; PSG register-latch port (write reg number)
PSG_DATW        equ     $A1                 ; PSG data-write port
PSG_DATR        equ     $A2                 ; PSG data-read port
; (BEEP_DELAY_ITERS and beep_delay moved to sub/beep.asm with the BEEP body --
; the I1 funding carve, docs/spec-basic-input-devices.md §7. Defined THERE only,
; so the calibrated constant cannot drift between two copies.)

; ex_sound and ex_beep, the two STATEMENTS, are in basic/soundstmt.asm: PROMOTED into
; main page 1 (D-DSPFNKSCROLL's room, 2026-11-18), in front of the $6CF3 pin. What stays
; here is what must stay low: psg_silence, which the abort funnel reaches, and the
; port equates.

; --- psg_silence: the GICINI-equivalent teardown (D-GICINI) -----------------
; docs/spec-basic-gicini.md. Stop the PLAY drain and silence the three tone
; amplitudes. Preserves HL (every caller is holding a live pointer across it);
; clobbers AF and B only.
;
; 🔴 THIS ROUTINE IS THE ANSWER TO A DEFERRAL THAT WENT STALE. This file's own
; header used to say a GICINI-equivalent "is deferred to Slice 2 (there are no
; PLAY queues / MUSICF to zero yet ...)". The queues shipped; nothing watched the
; trigger; and what was actually missing turned out to be a TEARDOWN, not the
; init the deferral named. Both references stop the music on an untrapped abort,
; on a break, and on BEEP -- measured, 6 divergent rows, spec §1.
;
; 🎯 MUSICF FIRST, AND DI AROUND BOTH HALVES. Clearing MUSICF makes
; play_service's own fast-out (playsvc.asm) skip the PSG entirely, so the
; amplitude writes below cannot be fought. The `di` closes the one remaining
; window: an ISR that fired just BEFORE the MUSICF store is already past its
; fast-out and would write one more frame of amplitude after ours. One frame of
; leaked tone is exactly the kind of edge that is invisible to a +-1-frame PSG
; trace, which is why it is closed by construction rather than measured away.
; Reached only from statement level and from the abort funnel, both of which run
; with interrupts enabled, so the unconditional `ei` restores the true state.
psg_silence:
                di
                xor     a
                ld      (MUSICF),a          ; the drain's fast-out: no more PSG writes
                ld      b,8                 ; R8/R9/R10 = the three tone amplitudes
psgs_lp:        ld      a,b
                out     (PSG_ADDR),a        ; latch the amplitude register
                xor     a
                out     (PSG_DATW),a        ; amplitude 0
                inc     b
                ld      a,b
                cp      11
                jr      c,psgs_lp
                call    psv_flush           ; D-PLAYQUEUE: the queues empty and the
                                            ; PLAY settings reset (basic/playsvc.asm)
                ei
                ret

