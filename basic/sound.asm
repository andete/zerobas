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
    ENDIF
