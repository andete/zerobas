#!/usr/bin/env python3
"""D-CASRBRK edit: TAPION / TAPIN honour Ctrl-STOP (cas_stop, shared with
TAPOUT's wait for the release); cas_latch + the two inline level reads fold
into cas_level to pay for it. Anchored on text; refuses otherwise."""
import sys
T = "tape/tape.asm"

def sub(old, new):
    s = open(T).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE: anchor found {n}x: {old[:60]!r}")
    open(T, "w").write(s.replace(old, new))
    print("ok")

sub("""; cas_latch: select PSG R14 so IN (PSG_STAT) returns the CAS-in byte.
; Changes: AF
cas_latch:
                ld      a,CASIN_R14
                out     (PSG_REGS),a
                ret
""", """; cas_level: select PSG R14 (so IN (PSG_STAT) returns the CAS-in byte) and read
; the current CAS-in level. (D-CASRBRK: was cas_latch, with the read inlined at
; its two callers -- folded, -5 B, to pay for cas_stop.)
; Out:     D = level (bit 7: $00 or $80).   Changes: AF, D
cas_level:
                ld      a,CASIN_R14
                out     (PSG_REGS),a
                in      a,(PSG_STAT)
                and     $80
                ld      d,a
                ret

;--------------------------------
; cas_stop: CF = Ctrl-STOP is down -- and then it returns only once the key is
; up again (cas_stop_w), so the press is CONSUMED, as on the VG-8020: it runs
; the ON ERROR handler at once and breaks it only if the key is still down
; ~0.7 s later (D-CASWBRK, scratchpad/caswbrk_hold_tap.out). Changes: AF
cas_stop:
                call    BREAKX
                ret     nc
cas_stop_w:
                call    BREAKX
                jr      c,cas_stop_w    ; Ctrl-STOP still down
                scf                     ; CF = broken
                ret
""")
sub("""                di
                call    cas_latch
                in      a,(PSG_STAT)
                and     $80
                ld      d,a             ; current CAS-in level
""", """                di
                call    cas_level       ; D = current CAS-in level
""")
sub("""tapion_relock:
                ld      bc,CAS_FLATMAX  ; 16-bit flat-timeout budget for this attempt
""", """tapion_relock:
                ; D-CASRBRK: Ctrl-STOP while hunting the leader breaks the read
                ; (the VG-8020 does; scratchpad/casrbrk_diag.out). Each attempt,
                ; not each half: the halves' loops stay lean (see above).
                call    cas_stop
                ret     c
                ld      bc,CAS_FLATMAX  ; 16-bit flat-timeout budget for this attempt
""")
sub("""tapin:
                call    cas_latch
                in      a,(PSG_STAT)
                and     $80
                ld      d,a             ; current level
""", """tapin:
                ; D-CASRBRK: Ctrl-STOP between bytes breaks the read, as on the
                ; VG-8020 (a BLOAD broken in its data: `19 in 15` there, read on
                ; to the end here, scratchpad/casrbrk_diag2.out). Before the
                ; hunt, which only looks for a LONG half: the stop bits' slack.
                call    cas_stop
                ret     c
                call    cas_level       ; D = current level
""")
sub("""tapout_brk:
                call    BREAKX
                jr      c,tapout_brk    ; Ctrl-STOP still down
                pop     de              ; drop the byte
                scf                     ; CF = failed
                ret
""", """tapout_brk:
                call    cas_stop_w      ; until the key is up; CF = failed
                pop     de              ; drop the byte (CF kept)
                ret
""")
