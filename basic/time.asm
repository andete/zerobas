; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; time.asm — the `TIME` software-clock pseudo-variable (read and write).
; ===========================================================================
;   PRINT TIME        -> the 16-bit UNSIGNED word at JIFFY ($FC9E), as a float
;   TIME = <expr>     -> stores into JIFFY through the ADDRESS domain
;
; docs/spec-basic-time.md. `TIME` is standard MSX1 BASIC and was absent from
; zerobas entirely until this slice — not in the keyword table, so a program
; writing `TIME` got the *variable* `TI` and read 0 forever. That is a SILENT
; divergence: an `IF TIME-T<400` loop never terminates. It also taxed the probe
; harness — the T3-era rule "no probe program may use `TIME` on the zerobas
; side" existed only because of this gap, and every acceptance window since has
; been sized by iteration count instead of elapsed jiffies.
;
; The read is a FACTOR (expr.asm's ev_f dispatch, `ev_f_time`); the write is a
; STATEMENT with no statement token of its own — a statement that STARTS with
; the `TIME` token IS the assignment, exactly like G8's `VDP(n)=` / `BASE(n)=`
; (interp.asm exec_stmt). `LET TIME=5` is ERR 2 on the reference and needs an
; explicit guard in `ex_letkw`, for the reason the G8 comment there records:
; without it `ex_let` takes the token for a variable name and silently assigns
; to nothing.
;
; THE CONVERSION IS THE HOUSE ADDRESS DOMAIN, unchanged: `eval_addr` (eval +
; fac_to_int_addr -> domain_convert_core in address mode), the same one POKE
; and VPOKE call. Domain -32768..65535; values >= 32768 wrap by -65536 first,
; then TRUNCATE toward zero; outside -> Overflow (ERR 6) via FPERR. Measured
; against the VG-8020 in spec §1.3 — including `65534.6` -> 65535 and
; `65535.4` -> 0, which only wrap-then-truncate explains.
;
; ⚠️ Interrupt-traps T5 needs the SAME conversion for `ON INTERVAL=n` (measured
; 2026-07-26, docs/spec-traps-t5-interval.md §1.2 — `-65531` raises ERR 6, which
; a raw mod-65536 reading would have accepted as a legal 5-frame period). This
; slice is therefore the first of two consumers, not a one-off.
;
; CLEAN-ROOM: black-box VG-8020 characterization only (probes/basic/
; basic_probe_time.py, 45/45) + the public MSX-BASIC language reference for the
; JIFFY work-area address. No disassembly. See basic/PROVENANCE.md.
; ===========================================================================


; --- ex_time_assign: `TIME = <expr>` ---------------------------------------
; Entry: HL -> the TIME token (exec_stmt dispatched on it without consuming it,
; the VDP/BASE convention). g8_assign is the template, minus the parenthesised
; index — including both error checks: the explicit end-of-statement test that
; yields ERR 24, and str_eval_one's ERR 13 on a string operand.
;
; ⚠️ ERR 24 IS RAISED AT THIS SITE ON PURPOSE (D-TIME-3). zerobas silently
; accepts a bare `A=` and `POKE 100,` today where the reference says "Missing
; operand" — a PRE-EXISTING divergence wider than `TIME`, which `TIME=` would
; otherwise inherit. Six bytes make `TIME=` correct where it stands; the general
; gap is tracked separately rather than widened into this slice.
ex_time_assign:
                inc     hl                  ; past the TIME token
                call    skip_spaces
                cp      EQ_TOKEN
                jr      nz,tm_err2          ; `TIME` bare / `TIME 5` / `TIME(1)=5` -> ERR 2
                inc     hl
                call    skip_spaces
                or      a
                jr      z,tm_err24          ; `TIME=` at end of line -> Missing operand
                cp      ':'
                jr      z,tm_err24          ; `TIME=:PRINT 1` -> likewise
                call    str_eval_one        ; CF=1 -> a STRING operand, HL past it
                jr      c,tm_err13          ; `TIME="A"` -> Type mismatch
                call    eval_addr           ; DE = value in the ADDRESS domain
                call    check_fperr_only    ; outside -32768..65535 -> Overflow (ERR 6)
                ; --- the store, guarded --------------------------------------
                ; `ld (JIFFY),de` is TWO byte writes and the timer ISR ticks
                ; between them, so an unguarded store can be torn by an interrupt
                ; landing mid-word (D-TIME-2). The same idiom sound.asm already
                ; uses against play_service. BASIC always runs with interrupts
                ; enabled, so the unconditional `ei` is safe.
                di
                ld      (JIFFY),de
                ei
                jp      exec_stmt

tm_err2:
                ld      a,2                 ; Syntax error   (trappable, not stmt_error:
                jr      tm_raise            ; a program can ON ERROR its own bad TIME)
tm_err13:
                ld      a,13                ; Type mismatch
                jr      tm_raise
tm_err24:
                ld      a,24                ; Missing operand
tm_raise:
                jp      raise_error

