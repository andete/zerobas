#!/usr/bin/env python3
"""D-CASWBRK edit: a tape WRITE honours Ctrl-STOP (TAPOUT -> CF) and BASIC
raises 19 for it, as the VG-8020 does. Anchored on text; refuses on a missing
or non-unique anchor."""
import sys

def sub(path, old, new, count=1):
    s = open(path).read()
    n = s.count(old)
    if n != count:
        sys.exit(f"REFUSE {path}: anchor found {n}x (want {count}): {old[:60]!r}")
    s = s.replace(old, new)
    open(path, "w").write(s)
    print(f"ok {path} ({count}x)")

T = "tape/tape.asm"
sub(T, """PPI_PORTC:      equ     $AA             ; i8255 PPI Port C (motor bit 4, CASW bit 5)
""", """PPI_PORTC:      equ     $AA             ; i8255 PPI Port C (motor bit 4, CASW bit 5)
KBD_IN:         equ     $A9             ; i8255 PPI Port B: the selected keyboard row
""")
sub(T, """CAS_BITCOMP0:   equ     14              ; '0' bit: its own tail, its own figure
""", """CAS_BITCOMP0:   equ     14              ; '0' bit: its own tail, its own figure
; D-CASWBRK: the byte boundary also carries TAPOUT's STOP test (`in` / `and` /
; `jr` not taken = 25 T + 3 M1 waits = 28 T = two 14 T iterations). Its own
; figure, so the '1' bit's last cycle keeps CAS_BITCOMP. 15 < CAS_HHALF24.
CAS_BYTECOMP:   equ     CAS_BITCOMP + 2
""")
sub(T, """                call    stmotr          ; motor on
                di                      ; waveform timing must not be jittered
                call    cas_short       ; C = leader carrier half (cached baud)
""", """                call    stmotr          ; motor on
                di                      ; waveform timing must not be jittered
                ; D-CASWBRK: select keyboard row 7 (STOP is bit 4) for TAPOUT's
                ; per-byte test. Interrupts stay off until TAPOOF, so nothing
                ; moves the row in between; the other Port C bits are kept.
                in      a,(PPI_PORTC)
                and     $F0
                or      7
                out     (PPI_PORTC),a
                call    cas_short       ; C = leader carrier half (cached baud)
""")
sub(T, """; Input:   A  = data to write
; Output:  CF = set if failed
; Changes: all
; Frames A as: start bit (0), 8 data bits LSB-first, 2 stop bits (1).
tapout:
                di
                push    af              ; save the data byte across cycle calls
                call    cas_long        ; start bit = '0' = one low-freq cycle
""", """; Input:   A  = data to write
; Output:  CF = set if failed: Ctrl-STOP held (nothing written)
; Changes: all
; Frames A as: start bit (0), 8 data bits LSB-first, 2 stop bits (1).
; 🔴 D-CASWBRK (2026-10-11): THE VG-8020 BREAKS A TAPE WRITE ON Ctrl-STOP -- a 2 KB
; BSAVE / a 1.6 KB CSAVE broken in the data raise `19 in 15` there, trapped, and
; ran to the end here (scratchpad/caswbrk_diag4.out); STOP ALONE does not break it
; (an 8 KB BSAVE under a STOP press every 4 s completes, caswbrk_diag5.out). Each
; byte tests row 7's STOP (TAPOON selected the row); only a STOP that reads down
; pays for the CTRL test, so the waveform's byte boundary grows by one fixed
; 28 T, compensated in CAS_BYTECOMP.
tapout:
                di
                push    af              ; save the data byte across cycle calls
                in      a,(KBD_IN)      ; row 7 (TAPOON): bit 4 = STOP, 0 = down
                and     $10
                jr      z,tapout_chk    ; STOP down: is CTRL down too?
tapout_go:
                call    cas_long        ; start bit = '0' = one low-freq cycle
""")
sub(T, """                ld      e,CAS_BITCOMP
                call    cas_cycle_last
                or      a               ; CF = 0: success
                ret

;--------------------------------
; $00F0 TAPOOF""", """                ld      e,CAS_BYTECOMP  ; D-CASWBRK: + the STOP test
                call    cas_cycle_last
                or      a               ; CF = 0: success
                ret
; tapout_chk: STOP read down on the selected row. CTRL is row 6 bit 1; row 7 is
; then re-selected and STOP read again (a row a caller left selected without
; TAPOON reads as a false STOP here and carries on). Both down: CF, no byte.
tapout_chk:
                in      a,(PPI_PORTC)
                and     $F0
                or      6
                out     (PPI_PORTC),a   ; row 6
                in      a,(KBD_IN)
                ld      b,a             ; bit 1 = CTRL, 0 = down
                in      a,(PPI_PORTC)
                inc     a               ; row 6 -> 7
                out     (PPI_PORTC),a
                in      a,(KBD_IN)
                and     $10
                jr      nz,tapout_go    ; not STOP after all
                ld      a,b
                and     2
                jr      nz,tapout_go    ; STOP alone: the VG-8020 writes on
                pop     af
                scf                     ; Ctrl-STOP: CF = failed
                ret

;--------------------------------
; $00F0 TAPOOF""")

# --- the sub tenant: a tape engine's failure is SV_STAT 19 ----------------
sub("sub/save.asm", """sv_load_error:
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
                ld      a,1
                ld      (SV_STAT),a
                ld      sp,(SVT_SP)         ; D-DISKFULLRETRY: ABORT, from any depth
                ret                         ; -> save_tenant, after `call svt_go`
""", """sv_load_error:
                ld      a,1
sv_fail:                                    ; A = the SV_STAT code
                ld      (SV_STAT),a
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
                ld      sp,(SVT_SP)         ; D-DISKFULLRETRY: ABORT, from any depth
                ret                         ; -> save_tenant, after `call svt_go`
; sv_tape_err -- a TAPE engine's TAPOON/TAPOUT failed (D-CASWBRK: Ctrl-STOP in
; the write). SV_STAT 19 and sv_tenant RAISES it -- `Device I/O error`, as the
; VG-8020 does. Not through DISKOP_ERR: a stale 19 there would outlive this.
sv_tape_err:
                ld      a,19
                jr      sv_fail
""")
for f in ("basic/sv-tsb.inc", "basic/sv-bsvcas.inc"):
    s = open(f).read()
    n = s.count("jp      c,sv_load_error")
    want = {"basic/sv-tsb.inc": 6, "basic/sv-bsvcas.inc": 8}[f]
    if n != want:
        sys.exit(f"REFUSE {f}: {n} sites (want {want})")
    open(f, "w").write(s.replace("jp      c,sv_load_error", "jp      c,sv_tape_err"))
    print(f"ok {f} ({n}x)")

# --- main: sv_tenant raises SV_STAT 19 --------------------------------------
sub("basic/save.asm", """                ld      a,(SV_STAT)         ; D-DISKERR: a DSKIO failure raises its code below
                or      a
                jr      nz,disk_error       ; the tenant hit sv_load_error: report ONCE --
""", """                ld      a,(SV_STAT)         ; D-DISKERR: a DSKIO failure raises its code below
                cp      19                  ; D-CASWBRK: a tape write broken with
                jp      z,raise_error       ; Ctrl-STOP -- Device I/O error (motor off)
                or      a
                jr      nz,disk_error       ; the tenant hit sv_load_error: report ONCE --
""")
sub("basic/save.asm", """                call    cas_write_ea_header ; $EA header block (name in TSV_NAME); CAS_WCNT=0
                jp      c,load_error
""", """                call    cas_write_ea_header ; $EA header block (name in TSV_NAME); CAS_WCNT=0
                jp      c,dpl_dio           ; D-CASWBRK: Ctrl-STOP -> 19, raised
""")
sub("basic/save.asm", """                call    TAPOUT              ; emit the byte (CF ignored: best-effort)
                ld      hl,CAS_WCNT
""", """                call    TAPOUT              ; emit the byte
                jp      c,dpl_dio           ; D-CASWBRK: Ctrl-STOP -> 19, raised
                ld      hl,CAS_WCNT
""")
sub("basic/files.asm", """                call    cas_write_ea_header ; TAPOON long + $EA*10 + TSV_NAME + TAPOOF
                jr      c,oocas_ioerr       ; CAS_WCNT reset to 0 on success
""", """                call    cas_write_ea_header ; TAPOON long + $EA*10 + TSV_NAME + TAPOOF
                jp      c,dpl_dio           ; D-CASWBRK: Ctrl-STOP -> 19, raised
""")
