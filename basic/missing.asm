; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; missing.asm — LOCATE / SWAP / TRON / TROFF / MOTOR, the MISSING class.
; ===========================================================================
; The five MSX1 reserved words that this BASIC did not have at all: the
; tokeniser did not crunch them and exec_stmt had nowhere to send them, so each
; one was a Syntax error on a line the reference runs. They are collected here
; rather than scattered into screen.asm / vars.asm / program.asm because they
; land as ONE slice against ONE gate, and because a slice you can delete in one
; piece is a slice you can falsify.
;
; Normative surface, all VG-8020-measured, none assumed:
;   docs/spec-basic-missing-class.md          (signed off S-MC-1..6)
;   docs/missing-vg8020-characterization.md   (175 cases + the locrow battery)
;
; ⚠️ REPACK-ONLY, deliberately (S-MC-5). The whole file is behind one
; `IF ROM_BASE < $4000`, so the lean 16 KB cart assembles NOTHING from it and
; stays byte-identical -- LEAN_SHA256 does not move. The five words therefore do
; not exist on the lean cart, which was confirmed knowingly: the lean cart is
; byte-full and its kwtable is inline in page 1, where the repack build's
; kwtable is a sub.rom tenant with ~8 KB free.
; ===========================================================================

    IF ROM_BASE < $4000

; --- ex_motor: MOTOR | MOTOR ON | MOTOR OFF ---------------------------------
; Exactly three forms, and everything else is a Syntax error (measured, spec
; §3.5): MOTOR 1, MOTOR 0, MOTOR "ON", MOTOR A, MOTOR ON,OFF, MOTOR ON, -- and,
; unlike every other ON/OFF statement in this tree, **MOTOR STOP**. That last
; one is why onoff_decode returns "which sub-keyword" instead of "is this
; allowed": the 2-way policy is the caller's single `cp ZTS_STOP`, not a second
; flavour of the shared decoder (see its header in program.asm).
;
; The body is a BIOS call. tape/tape.asm implements STMOTR ($00F3) with the MSX
; convention -- A=0 stop, A=$FF toggle, otherwise start -- and tape/tape.asm is
; a dependency of the merged repack ROM, so the entry is present on the target
; machine. ZTS_OFF/ZTS_ON are literally 0/1 (sysvars.inc), so onoff_decode's
; answer IS the STMOTR argument with no mapping step.
ex_motor:
                inc     hl                  ; past the MOTOR token
                call    skip_spaces         ; returns A = (HL)
                call    onoff_decode
                jr      c,mot_onoff
                ; Not ON/OFF/STOP. A bare MOTOR is the TOGGLE form, but only at a
                ; statement boundary -- `MOTOR 1` and `MOTOR A` must NOT silently
                ; toggle and swallow their argument. onoff_decode hands the
                ; original token back in A on the CF=0 path precisely so this
                ; test can be made without re-reading (HL).
                or      a
                jr      z,mot_toggle        ; end of line
                cp      COLON
                jp      nz,trap_syntax      ; MOTOR <anything else> -> ERR 2
mot_toggle:
                ld      a,$FF               ; STMOTR: toggle
                jr      mot_go
mot_onoff:
                cp      ZTS_STOP
                jp      z,trap_syntax       ; MOTOR STOP -> ERR 2 (MEASURED -- do not
                                            ; "harmonise" this with SPRITE/KEY/STRIG,
                                            ; which all accept STOP)
                inc     hl                  ; consume the ON/OFF sub-keyword
mot_go:
                push    hl                  ; guard the cursor across the BIOS call
                call    STMOTR
                pop     hl
                jp      exec_stmt           ; continue the line (a bare `ret` would
                                            ; swallow the rest of it -- the T1 lesson)

    ENDIF
