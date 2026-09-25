; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

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

ex_sound:
                rst    $10                ; past the SOUND token
                call    eval                ; DE = register (silent flt_to_int16)
                call    get_byte_arg        ; A = register 0..255 (ERR6 >int16, ERR5 >255/neg)
                cp      14                  ; registers 0..13 are the writable PSG set;
                jp      nc,snd_illegal      ; 14..255 -> Illegal function call (ERR5)
                ld      c,a                 ; C = register number (kept across the value eval)
                call    req_comma           ; D-NGRAM17
                call    eval                ; DE = value (silent flt_to_int16)
                call    get_byte_arg        ; A = value 0..255 (ERR6 >int16, ERR5 >255/neg)
                ld      b,a                 ; B = value byte to write
                ld      a,c
                cp      7                   ; register 7 (mixer) preserves its I/O bits
                jr      nz,snd_nomask
                ; The latch+access below must be atomic against play_service, which
                ; also programs the PSG from the $0038 ISR (audio Slice 3) -- a VBLANK
                ; landing between a latch and its access would misdirect the write.
                ; DI/EI mirrors the reference WRTPSG (Slice-1's "no DI needed" premise
                ; held only while nothing in the ISR touched the PSG latch).
                di
                ld      a,7                 ; --- R7 read-modify-write: keep top 2 bits ---
                out     (PSG_ADDR),a        ; latch register 7
                in      a,(PSG_DATR)        ; A = current R7 (BIOS I/O-direction bits in 6-7)
                and     $C0                 ; keep only the two I/O-direction bits
                ld      c,a                 ; C = preserved top bits
                ld      a,b
                and     $3F                 ; value contributes only bits 0..5
                or      c                   ; merge: (curR7 & $C0) | (val & $3F)
                ld      b,a                 ; B = merged byte to write
                ld      c,7                 ; C = register 7 again (snd_write latches C)
                jr      snd_write
snd_nomask:
                di                          ; single write, likewise atomic vs play_service
snd_write:
                ld      a,c
                out     (PSG_ADDR),a        ; latch the register number
                ld      a,b
                out     (PSG_DATW),a        ; write the data byte
                ei
                jp      exec_stmt           ; out preserves HL (still the cursor); next stmt
; D-DUPSPAN: an ALIAS, not a second copy -- the two instructions were
; byte-identical to interp.asm's gb_illegal, on gfx_absent's own precedent.
; The NAME and every call site survive; un-alias here to give this site a
; distinct face and nothing else moves.
snd_illegal     equ     gb_illegal  ; ERR 5 (register out of 0..13)

; --- BEEP -------------------------------------------------------------------
; BEEP  (no arguments) -- one short fixed tone on PSG channel A, synchronous.
;
; Faithful contract, black-box-captured from the VG-8020 (psgtrace.py, 2026-07-21;
; docs/spec-basic-audio-beep.md §2): tone A period $0055 (85, ~1316 Hz), mixer
; R7' = (R7 & $C0) | $3E (mute B/C + all noise, keep tone A + the two I/O-direction
; bits), channel-A amplitude $07 (FIXED volume 7 -- NOT the hardware envelope; R11-13
; are left untouched), a short fixed delay (~2 VBLANK frames), then silence (R8=0) and
; restore R7 to its saved value. The tone period (R0/R1) is deliberately left set
; afterwards (matches the reference trace). Direct-PSG, not CALL $00C0: consistent
; with ex_sound, VG-8020-gate-able, and C-BIOS's $00C0 is silent on our runtime (§3).
;
; Interrupt discipline (sign-off): each PSG latch+access pair is DI-guarded (atomic vs
; play_service, which programs the PSG from the $0038 ISR); the delay loop runs EI, so
; VBLANK/VDP servicing continues -- matching the reference's live-interrupt software
; delay. A BEEP during an active PLAY drain is fought by play_service in the delay
; window (accepted edge, matches hardware); with no active PLAY it is clean (§4.1).
;
; HL (the statement cursor) is preserved throughout (beep_delay touches only AF/BC),
; so `jp exec_stmt` chains the next `:`-separated statement.
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
                ei
                ret

ex_beep:
                ; D-GICINI: BEEP stops an active PLAY drain on BOTH references
                ; (row `m.beep`), which SOUND -- including a mixer write to R7 --
                ; does not (`m.sound2`/`m.sound7`). Sited BEFORE the CALSLT: the
                ; ordering is not black-box separable at the trace's ~1-frame
                ; resolution, and silencing first also retires the "a BEEP during
                ; an active PLAY drain is fought by play_service in the delay
                ; window (accepted edge)" note above -- there is no longer a drain
                ; to fight.
                call    psg_silence
                ; The body is a PAGE-0 sub-ROM tenant (sub/beep.asm,
                ; docs/spec-basic-input-devices.md §7): the 71 B it occupied here
                ; is what funds input-devices slice I1. The carve is clean because
                ; the body is direct PSG port I/O plus a busy-wait -- no BIOS, no
                ; page-0 low region -- and BEEP is cold enough that a CALSLT round
                ; trip is far below the ~33 ms tone it produces. Nothing marshals:
                ; BEEP takes no argument, returns no result, and cannot fail.
                ; HL (the statement cursor) is guarded across the CALSLT.
                inc     hl                  ; past the BEEP token
                push    hl
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_BEEP
                call    subrom_call
                pop     hl
                jp      c,subrom_absent_error
                jp      exec_stmt           ; chain the next statement (HL preserved)

