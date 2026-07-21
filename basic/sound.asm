; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sound.asm — the SOUND statement handler (audio arc, Slice 1).
;
;   SOUND register, value    write one byte to a PSG register
;
; SOUND is a synchronous single register write — no interrupt, no queue, no
; sub-ROM tenant (spec-basic-audio-play.md §3.D). Slice 1 is SOUND-only; the
; GICINI-equivalent init is deferred to Slice 2 (there are no PLAY queues /
; MUSICF to zero yet, and C-BIOS's own boot GICINI already leaves the PSG quiet
; — amplitudes 0 — so a fresh SOUND works with no init of ours).
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
    IF ROM_BASE < $4000
PSG_ADDR        equ     $A0                 ; PSG register-latch port (write reg number)
PSG_DATW        equ     $A1                 ; PSG data-write port
PSG_DATR        equ     $A2                 ; PSG data-read port
; BEEP delay length (busy-wait iterations). Loop body ~26 T; ~33 ms (2 VBLANK
; frames, the VG-8020 beep duration) at 3.579545 MHz is ~4540 iters. Tuned by the
; psgtrace gate (duration +-1 frame tolerant); see beep_delay / spec §2.
BEEP_DELAY_ITERS equ    $1200               ; 4608 -> ~33 ms nominal

ex_sound:
                inc     hl                  ; past the SOUND token
                call    skip_spaces
                call    eval                ; DE = register (silent flt_to_int16)
                call    get_byte_arg        ; A = register 0..255 (ERR6 >int16, ERR5 >255/neg)
                cp      14                  ; registers 0..13 are the writable PSG set;
                jr      nc,snd_illegal      ; 14..255 -> Illegal function call (ERR5)
                ld      c,a                 ; C = register number (kept across the value eval)
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; comma required between register and value
                jp      nz,stmt_error
                inc     hl
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
snd_illegal:
                ld      a,5
                jp      raise_error         ; ERR 5 Illegal function call (register out of 0..13)

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
ex_beep:
                inc     hl                  ; past the BEEP token
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
                ei                          ; delay with interrupts live (reference-faithful)
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
                jp      exec_stmt           ; chain the next statement (HL preserved)

; beep_delay -- a plain counted busy-wait, ~2 VBLANK frames (~33 ms) at 3.58 MHz.
; A software delay, exactly as the reference BEEP times its tone (not a JIFFY read --
; self-contained, no dependence on the timer hook). BC-only; AF clobbered; HL kept.
; BC calibrated so the psgtrace gate sees the beep span >=1 sampled frame (duration
; is not black-box-pinnable finer than ~1 frame, so the gate is +-1 frame tolerant).
beep_delay:
                ld      bc,BEEP_DELAY_ITERS
bd_loop:
                dec     bc
                ld      a,b
                or      c
                jr      nz,bd_loop
                ret
    ENDIF
