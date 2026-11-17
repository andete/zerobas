#!/usr/bin/env python3
"""D-DISKVE (2026-11-17): the BDOS calls DISKVE's disk-error handler. One wrapper, bdos_dskio,
in the pin-free [$607B, $75A5) span (D-DISKCARVE6's 76 B hole); write_sector, dskio_calslt and
the merged RDABS / WRABS body call it. Refuses on any missing or non-unique anchor."""
import sys


def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)}: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))


K = "disk/kernel.asm"
# --- the wrapper ---------------------------------------------------------------------------
edit(K, '''                ld      a, 2
                scf
                ret

; 🔴 D-ALIASWCELL (2026-09-23)''', '''                ld      a, 2
                scf
                ret

; bdos_dskio -- 🎯 D-DISKVE (2026-11-17): dskio for the BDOS's OWN transfers (write_sector,
; dskio_calslt -> read_sector, RDABS / WRABS; never the published $4010, whose raw codes PHYDIO
; and Disk BASIC expect). Same interface as dskio. On an error, when a disk-error handler is
; installed -- DISKVE ($F323) names a cell holding its address; our init zeroes the high byte
; under BASIC (install_basic_hooks), MSX-DOS's own leaves $D609 on both machines
; (scratchpad/XE3_stock.out, XE3_ours.out) -- the handler is entered as on the CF-3300
; (scratchpad/XE2_ign_stock.out): A = the drive, B = 1, C = DSKIO's code | 1 for a write. Its
; answer in C: 1 Retry (the same transfer again), 2 Abort (a warm boot: the CF-3300 lands at
; COMMAND.COM's prompt, scratchpad/XE4_scr_stock.out), 0 Ignore -- Cy = 0 with A = $FF (dskio's
; own success leaves A = 0), so FMAKE carries on and RDABS / WRABS tell the two apart.
; With no handler: dskio's result, every register as it left it (BASIC's route, unchanged).
bdos_dskio:
                push    hl
                push    de
                push    bc
                push    af
                call    dskio
                jr      nc, bdd_drop
                push    af
                ld      a, (DISKVE + 1)     ; the key: a handler cell outside page 0
                or      a
                jr      nz, bdd_hand
                pop     af
bdd_drop:                                   ; drop the saved inputs, nothing else touched
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                ret
bdd_hand:
                ld      hl, (DISKVE)
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ex      de, hl              ; HL = the handler
                pop     af
                ld      e, a                ; DSKIO's code
                pop     af                  ; A = the drive, Cy = a write
                push    af
                ld      b, a
                sbc     a, a
                and     1
                or      e
                ld      c, a                ; C = the code | the write bit
                ld      a, b                ; A = the drive
                ld      b, 1
                call    jp_hl
                ld      a, c
                dec     a
                jr      z, bdd_retry        ; 1 Retry
                jp      p, $0000            ; 2 Abort: the warm boot
                pop     af                  ; 0 Ignore
                pop     af
                pop     de
                pop     hl
                ld      a, $FF
                or      a                   ; Cy = 0, A = $FF: "ignored"
                ret
bdd_retry:
                pop     af
                pop     bc
                pop     de
                pop     hl
                jr      bdos_dskio

; 🔴 D-ALIASWCELL (2026-09-23)''')
# --- init: DISKVE's high byte := 0 under BASIC ----------------------------------------------
edit(K, '''                ld      hl, FWBUF           ; D-DSKIO: publish the DSKI$/DSKO$ buffer at the
                ld      (DSKBUF_PTR), hl    ; cell the MSX idiom PEEKs (docs/spec-basic-dskio.md)
                ld      hl, hook_tab''', '''                ld      hl, FWBUF           ; D-DSKIO: publish the DSKI$/DSKO$ buffer at the
                ld      (DSKBUF_PTR), hl    ; cell the MSX idiom PEEKs (docs/spec-basic-dskio.md)
                xor     a                   ; D-DISKVE: no disk-error handler under BASIC --
                ld      (DISKVE + 1), a     ; bdos_dskio's key (it held $C9C9 here)
                ld      hl, hook_tab''')
# --- write_sector ----------------------------------------------------------------------------
edit(K, '''                jp      dskio           ; tail-call: dskio returns to our caller''',
     '''                jp      bdos_dskio      ; tail-call (D-DISKVE: DISKVE's handler on an error)''')
# --- jp_hl: the `jp (hl)` already at fmt_key+3 ------------------------------------------------
edit(K, '''fmt_key:
                ld      hl,(FDC_DEST)
                jp      (hl)''', '''fmt_key:
                ld      hl,(FDC_DEST)
jp_hl:                                      ; (D-DISKVE: bdos_dskio's call into the handler)
                jp      (hl)''')
# --- dskio_calslt ----------------------------------------------------------------------------
edit("basic/fat-prim-body.inc", '''dskio_calslt:
                call    dskio               ; LOCAL: no slot to cross, and the''',
     '''dskio_calslt:
                call    bdos_dskio          ; LOCAL (D-DISKVE: through DISKVE's handler); no slot to cross, and the''')
# --- equate ----------------------------------------------------------------------------------
edit("disk/equates.inc", '''DSKBUF_PTR      equ     $F351''', '''DISKVE          equ     $F323   ; word -> a cell holding the disk-error handler's address (D-DISKVE)
DSKBUF_PTR      equ     $F351''')
# --- RDABS / WRABS: one body ----------------------------------------------------------------
F = "disk/fat.asm"
s = open(F).read()
a = s.index("rdabs_body:\n")
b = s.index("                ld      l, a                ; H=L=$00 (pinned exit value)\n                ret\n", s.index("wrabs_body:\n"))
b += len("                ld      l, a                ; H=L=$00 (pinned exit value)\n                ret\n")
old = s[a:b]
if old.count("call    dskio") != 2 or s.count(old) != 1:
    sys.exit("rdabs/wrabs block")
new = '''rdabs_body:
                ; 🔴 D-SDSBOOT (2026-11-07): through $F37D the CF-3300 hands DE (the
                ; sector) back unchanged and leaves F = $42 (Z, N -- a `sub`), where this
                ; returned dskio's DE and F = $44 (`xor`). SDSNAT1C.DSK's boot code reads
                ; DE after RDABS and took another road here
                ; (scratchpad/bdosregs_probe.py -> bdosregs_run2.out).
                ; 🎯 D-DISKVE (2026-11-17): RDABS and WRABS are ONE body now (the write
                ; was its mirror), through bdos_dskio -- DISKVE's handler on an error.
                xor     a                   ; drive ignored (single-drive); Cy=0 = read
                jr      abs_go
; wrabs_body -- MSX-DOS-1 WRABS ($30), canonical entry $4720 (M26, tier2-m26-spec.md §2.5/§7):
; RDABS's mirror, the DTA as the source; pinned by BDOSX3 record 23 (H=1) -- the same shape as
; RDABS's: A=$00 B=$00 C=$01 D=$00 E=$00 H=$00 L=$00 on success.
wrabs_body:
                xor     a                   ; drive 0 (ignored, single-drive)
                scf                         ; Cy=1 = write direction (MSX2 TH DSKIO)
abs_go:
                push    de                  ; the sector, handed back as on the CF-3300
                ld      b, h                ; B := sector count (dskio's own count param)
                push    bc                  ; preserve original count across the dskio call
                ld      hl, (DOS_DTAPTR)    ; the runtime DTA
                call    bdos_dskio
                pop     bc                  ; B := original count again (dskio clobbers B/C)
                pop     de                  ; (flags kept: CF is dskio's)
                jr      c, rdabs_ioerr
                inc     a                   ; A = $FF: DISKVE's handler answered Ignore
                jr      z, abs_ign
                ld      a, b                ; A := original count
                ld      c, a                ; C := count (pinned exit value)
                sub     a                   ; A = 0, F = $42 as on the CF-3300 (not xor's $44)
                ld      b, a                ; B := $00 (pinned exit value)
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      h, a
                ld      l, a                ; H=L=$00 (pinned exit value)
                ret
abs_ign:
                ; After Ignore the CF-3300 returns A = $FF, B = 1, C = the handler's C (0
                ; for Ignore), DE = the sector, H = 1, L = $FF (scratchpad/XE2_ign_stock.out).
                ld      bc, $0100
                ld      hl, $01FF
                dec     a                   ; A = $FF
                push    af
                call    clr_f306            ; M20 dispatcher-flag rule
                pop     af
                ret
rdabs_ioerr:
                ld      b, a                ; preserve dskio's error code
                call     clr_f306   ; M20 dispatcher-flag rule
                ld      a, b                ; restore error code
                scf
                ret
'''
if "rdabs_ioerr:\n                ld      b, a" not in old:
    sys.exit("rdabs_ioerr not in the block")
s = s[:a] + new + s[b:]
open(F, "w").write(s)
print("ok")
