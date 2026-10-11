#!/usr/bin/env python3
"""D-CASDIRECT (D-LOADERRRET's content arms): a line with no line number in an
ASCII program -- LOAD / MERGE, tape and disk -- is 57 `Direct statement in
file`, UNTRAPPED and with no line, on the VG-8020 and the CF-3300. Ours said
`load error` (and ran on) or `Syntax error` (with a garbage line).
Anchored on text; refuses otherwise."""
import sys

def sub(path, old, new):
    s = open(path).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE {path}: anchor found {n}x: {old[:60]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

C = "basic/cload.asm"
sub(C, """dpl_err:
                call    load_error
                scf
                ret
""", """dpl_err:
                call    load_error
                scf
                ret
; dpl_direct -- D-CASDIRECT (2026-10-11): an ASCII program with a line that has
; NO line number. Both references print `Direct statement in file` (57) with no
; line and run NO handler, for LOAD and MERGE, from tape and from disk -- and for
; a BSAVE binary LOADed as a program, which trips the same reader guard
; (scratchpad/casdirect_diag.out, _disk.out, _bin.out). The verb has left the run
; (LOAD at `Found:`, MERGE returns to command level), so it is a direct-mode,
; forced abort: DIRECTF for the missing line, raise_error_forced for no trap.
; Ours printed `load error` and RAN ON (LOAD) or raised `Syntax error` with a
; garbage line (MERGE, via stmt_error).
dpl_direct:
                ld      a,1
                ld      (DIRECTF),a
                ld      a,57                ; Direct statement in file
                jp      raise_error_forced
""")
sub(C, """                call    cas_ascii_drive     ; read+tokenise+store via the tape source
                jr      c,dpl_err           ; non-numbered line -> abort (jp -> jr)
""", """                call    cas_ascii_drive     ; read+tokenise+store via the tape source
                jr      c,dpl_direct        ; non-numbered line -> 57 (D-CASDIRECT)
""")
sub(C, """                call    dsk_ascii_drive     ; tokenise + store; CF set = bad line
                jr      c,dpl_err           ; non-numbered line / not an ASCII program
""", """                call    dsk_ascii_drive     ; tokenise + store; CF set = bad line
                jr      c,dpl_direct        ; non-numbered line / not an ASCII program
                                            ; -> 57, as on the CF-3300 (D-CASDIRECT)
""")
F = "basic/files.asm"
sub(F, """                jp      c,stmt_error        ; non-numbered line -> "Direct statement in file"
""", """                jp      c,dpl_direct        ; non-numbered line -> 57 "Direct statement in
                                            ; file", untrapped (D-CASDIRECT; this said so
                                            ; and raised stmt_error's Syntax error)
""")
