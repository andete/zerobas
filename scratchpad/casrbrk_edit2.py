#!/usr/bin/env python3
"""D-CASRBRK BASIC half: a broken tape READ raises 19 -- BLOAD's data arms, and
the ASCII loader (LOAD / MERGE "CAS:"), which took a failed refill for the end."""
import sys

def sub(path, old, new, count=1):
    s = open(path).read()
    n = s.count(old)
    if n != count:
        sys.exit(f"REFUSE {path}: anchor found {n}x (want {count}): {old[:60]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

B = "basic/bload-body.inc"
sub(B, """                call    TAPION              ; sync block 2 (data)
                jp      c,bl_load_error
""", """                call    TAPION              ; sync block 2 (data)
                jp      c,bl_tape_dio       ; D-CASRBRK: Ctrl-STOP / I/O -> 19, raised
""")
sub(B, """load_loop:
                call    TAPIN
                jp      c,bl_load_error
""", """load_loop:
                call    TAPIN
                jp      c,bl_tape_dio       ; D-CASRBRK: Ctrl-STOP in the data -> 19
""")

C = "basic/cload.asm"
sub(C, """cal_getbyte:
                ld      a,(CAL_NEEDFILL)
                cp      2
                scf                         ; terminal EOF, latched by a prior drain:
                ret     z                   ; answered here, no crossing
""", """cal_getbyte:
                ld      hl,CAL_NEEDFILL
                ld      a,(hl)
                cp      2
                jr      nc,cal_gb_past      ; terminal EOF, latched by a prior drain
""")
sub(C, """                call    TAPIOF              ; motor off (file fully read), as ctp_done
                pop     af
                ret

; --- cal_getbyte: cassette ASCII-load byte source (D2 indirection target) ----
""", """                call    TAPIOF              ; motor off (file fully read), as ctp_done
                pop     af
                ret     c
                ; 🔴 D-CASRBRK (2026-10-11): THE SOURCE RAN DRY BEFORE THE CTRL-Z.
                ; A tape ASCII file always ends in $1A (SAVE pads its last block),
                ; so cal_getbyte's mark 3 means the read was cut -- Ctrl-STOP in
                ; the data (TAPION / TAPIN return CF). The VG-8020 says `Device
                ; I/O error`; this loaded the lines read so far and said nothing
                ; (scratchpad/casrbrk_diag.out). Raised HERE, after the hook is
                ; back on fat_io_getbyte, never from inside the reader.
                ld      a,(CAL_NEEDFILL)
                cp      3
                jp      nc,dpl_dio
                ret
; cal_gb_past -- cal_getbyte asked at the latched terminal EOF: answered here, no
; crossing, and MARKED (2 -> 3+): a reader that asks PAST the end never met the
; file's Ctrl-Z (cas_in_getbyte stops at it too), so the data stopped early.
cal_gb_past:
                inc     (hl)
                scf
                ret

; --- cal_getbyte: cassette ASCII-load byte source (D2 indirection target) ----
""")
