; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; soundstmt.asm -- the SOUND and BEEP statement handlers, PROMOTED from basic/sound.asm
; (the low region) into main page 1, in front of the $6CF3 pin, whose pad absorbs their
; 60 B (D-DSPFNKSCROLL's room, Joost 2026-11-18: "scout a promote pass").
; tools/promote_scout.py, seeded with the BIOS entries (bios_*), crt_rows / crt_cp and the
; ISR path as well as the page-1 tenants' ABI: ex_sound / snd_nomask / ex_beep PROMOTABLE --
; statement-level only, reached through the statement table, ending in `jp`s, with no
; fallthrough or `jr` across the move. psg_silence, the PSG_* equates and the contract
; notes stay in basic/sound.asm, whose header documents both statements.
;
; Clean-room: original code, moved unchanged from basic/sound.asm. SOUND / BEEP semantics are
; from the public MSX-BASIC language reference and the black-box VG-8020 captures cited in
; sound.asm's header and docs/spec-basic-audio-beep.md (see basic/PROVENANCE.md). No
; disassembly.

ex_sound:
                rst    $10                ; past the SOUND token
                call    eval_byte_arg       ; A = register 0..255 (ERR6 >int16, ERR5 >255/neg)
                cp      14                  ; registers 0..13 are the writable PSG set;
                jp      nc,snd_illegal      ; 14..255 -> Illegal function call (ERR5)
                ; 🔴 D-SNDVAR (2026-09-27): THE REGISTER RIDES THE STACK, NOT C. It was
                ; `ld c,a` "kept across the value eval" -- and eval kept it only for a
                ; LITERAL. A variable's lookup clobbers C, so `V=12:SOUND 8,V` wrote
                ; the value to whatever register C held and R8 stayed 0; the VG-8020
                ; reads 12. Every SOUND row used literals. Found by D-STACKFLOOR,
                ; whose first cut clobbered BC for literals too and test_sound caught it.
                push    af                  ; [register]
                call    req_comma           ; D-NGRAM17
                call    eval_byte_arg       ; A = value 0..255 (ERR6 >int16, ERR5 >255/neg)
                ld      b,a                 ; B = value byte to write
                pop     af                  ; A = register number
                ; The latch+access below must be atomic against play_service, which
                ; also programs the PSG from the $0038 ISR (audio Slice 3) -- a VBLANK
                ; landing between a latch and its access would misdirect the write.
                ; DI/EI mirrors the reference WRTPSG (Slice-1's "no DI needed" premise
                ; held only while nothing in the ISR touched the PSG latch).
                ; 💰 D-REREAD batch 3 (2026-10-31, -10 B): one latch before the test;
                ; R7's merge is ((cur ^ v) & $C0) ^ v. The R7 latch is repeated so the
                ; port sequence stays latch, latch, data (tests/test_sound.py pins it).
                di
                out     (PSG_ADDR),a        ; latch the register number
                cp      7                   ; register 7 (mixer) preserves its I/O bits
                jr      nz,snd_nomask
                out     (PSG_ADDR),a        ; latch 7 again (latch, latch, data, as before)
                in      a,(PSG_DATR)        ; A = current R7 (BIOS I/O-direction bits in 6-7)
                xor     b
                and     $C0
                xor     b                   ; = (curR7 & $C0) | (val & $3F)
                ld      b,a                 ; B = merged byte to write
snd_nomask:
                ld      a,b
                out     (PSG_DATW),a        ; write the data byte
                ei
                jp      exec_stmt           ; out preserves HL (still the cursor); next stmt
; D-DUPSPAN: an ALIAS, not a second copy -- the two instructions were
; byte-identical to interp.asm's gb_illegal, on gfx_absent's own precedent.
; The NAME and every call site survive; un-alias here to give this site a
; distinct face and nothing else moves.
; (snd_illegal = gb_illegal: its equ is in basic/aliases-early.inc -- pasmo 0.5.3, D-PASMO053)

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
                ; D-GICINI: BEEP stops an active PLAY drain on BOTH references
                ; (row `m.beep`), which SOUND -- including a mixer write to R7 --
                ; does not (`m.sound2`/`m.sound7`). Sited BEFORE the CALSLT: the
                ; ordering is not black-box separable at the trace's ~1-frame
                ; resolution, and silencing first also retires the "a BEEP during
                ; an active PLAY drain is fought by play_service in the delay
                ; window (accepted edge)" note above -- there is no longer a drain
                ; to fight.
                call    psg_silence
                ; The body is a sub-ROM tenant (sub/beep.asm, PAGE 1 since step 2d;
                ; docs/spec-basic-input-devices.md §7): the 71 B it occupied here
                ; is what funds input-devices slice I1. The carve is clean because
                ; the body is direct PSG port I/O plus a busy-wait -- no BIOS, no
                ; page-0 low region -- and BEEP is cold enough that a CALSLT round
                ; trip is far below the ~33 ms tone it produces. Nothing marshals:
                ; BEEP takes no argument, returns no result, and cannot fail.
                ; HL (the statement cursor) is guarded across the CALSLT.
                inc     hl                  ; past the BEEP token
                ; D-TOKOVF put the body in zerobas-sub2 page 0 (its 71 B funded the
                ; crunch bound in zerobas-sub); D-SUB2RETIRE step 2d (2026-11-04)
                ; moved it to zerobas-sub's PAGE 1 (SUBROM_IDX_BEEP). The open-coded
                ; form stays: the absent test is the site's own.
                push    hl
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_BEEP
                call    subrom_call
                pop     hl
                jp      c,subrom_absent_error
                jp      exec_stmt           ; chain the next statement (HL preserved)

