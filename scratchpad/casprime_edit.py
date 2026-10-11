#!/usr/bin/env python3
"""D-CASPRIME (D-LOADERRRET's last live tape arms): a tape read that fails while
OPEN / MERGE prime the first data block (Ctrl-STOP, an I/O error) is 19, as on
the VG-8020 -- OPEN in its line, MERGE in 65535 (it has left the run at
`Found:`) and TRAPPED. Ours: `load error` and ran on (OPEN), and the STALE disk
code 255 in the line (MERGE, mc_ioerr -> disk_error). Anchored; refuses."""
import sys

def sub(path, old, new):
    s = open(path).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE {path}: anchor found {n}x: {old[:60]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

F = "basic/files.asm"
sub(F, """                call    cas_ascii_setup     ; prime data block 1
                jr      c,oocas_ioerr
                jr      oocas_mark
""", """                call    cas_ascii_setup     ; prime data block 1
                jp      c,dpl_dio           ; D-CASPRIME: a failed read is 19, raised
                                            ; (ours: `load error`, and the run went on)
                jr      oocas_mark
""")
sub(F, """                call    cas_ascii_setup     ; prime data block 1
                jr      c,mc_ioerr
                ; NB: NO new_prog — MERGE inserts into the current program.""",
    """                call    cas_ascii_setup     ; prime data block 1
                jr      c,mc_found_dio      ; D-CASPRIME: 19 in 65535, trapped
                ; NB: NO new_prog — MERGE inserts into the current program.""")
sub(F, """mc_ioerr:
                pop     hl
                jp      disk_error          ; D-DISKERR
""", """mc_ioerr:
                pop     hl
                jp      disk_error          ; D-DISKERR
; mc_found_dio -- D-CASPRIME (2026-10-11): the first data block failed to read
; (Ctrl-STOP / an I/O error) after `Found:`. The VG-8020 raises 19 TRAPPED with
; ERL 65535 -- the MERGE has left the run there (basic_probe_casrbrk's mb2); its
; search failing BEFORE `Found:` is `19 in <line>` (D-CASBRK's pmerge), and a
; later block untrapped (mb8). Ours raised the STALE disk code, 255 on the
; diskless machine, through mc_ioerr -> disk_error. DIRECTF is 0 here.
mc_found_dio:
                ld      hl,DIRECTF
                inc     (hl)                ; 0 -> 1: ERL 65535
                jp      dpl_dio             ; motor off, 19, raised
""")
