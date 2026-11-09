; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; DSKENT.COM -- D-ENTRYTIERS (TODO.md): the published disk-ROM entries the entry
; table (tools/entry_table.py --disk) found NOT MEASURED, called directly from
; a program under MSX-DOS through CALSLT ($001C, which MSX-DOS keeps in page 0)
; with the disk interface's slot from $FB22:
;   record 0  MTOFF  ($401F)                      no input
;   record 1  DSKCHG ($4013)  A = 0 (drive A), B = 0, C = $F9 (media), HL = dpb
;   record 2  DSKCHG again (the disk was just read: "unchanged" expected)
;   record 3  GETDPB ($4016)  A = 0, B = $F9 (media), C = $F9, HL = dpb
; Each record holds the function's CONTRACT only (Cy at +1, DSKCHG's B at +2;
; the rest $EE), since D-ENTRYTIERS step 3 gates it in bdos-acceptance. The DPB
; buffer GETDPB fills is captured too. DSKFMT ($401C) is NOT called: it formats the
; disk; it needs its own probe on a scratch image.
; Self-loop at `done` -- the disk_probe_diff.py capture anchor.
;
; CLEAN-ROOM: 100% own code. The entry addresses and register contracts are
; the published disk-ROM interface (MSX2 Technical Handbook, disk ROM); CALSLT
; and $FB22 are the documented BIOS / work-area interface. No ROM byte is read.
;
; Build: pasmo --bin dskent.asm dskent.com dskent.sym

                org     $0100

CALSLT          equ     $001C
DSKSLT          equ     $FB22                   ; slot of disk interface 1

start:
                ld      ix, $401F               ; record 0: MTOFF
                ld      hl, regs+0*8
                call    xcall
                xor     a                       ; record 1: DSKCHG
                ld      b, 0
                ld      c, $F9
                ld      hl, dpb
                ld      ix, $4013
                ld      (outp), hl
                ld      hl, regs+1*8
                call    xcall_chg
                xor     a                       ; record 2: DSKCHG again
                ld      b, 0
                ld      c, $F9
                ld      ix, $4013
                ld      hl, regs+2*8
                call    xcall_chg
                xor     a                       ; record 3: GETDPB
                ld      b, $F9
                ld      c, $F9
                ld      ix, $4016
                ld      hl, regs+3*8
                push    af
                xor     a
                ld      (bmask), a              ; GETDPB: B is not its answer
                pop     af
                call    xcall_keep
done:
                jr      done

; xcall -- CALSLT the disk ROM at IX (no register input), record at HL.
xcall:
                ld      (recp), hl
                jr      xc_go
; xcall_keep -- the same with A / B / C kept and HL := the DPB buffer.
xcall_keep:
                ld      (recp), hl
                ld      hl, dpb
xc_go:
                push    af
                ld      a, (DSKSLT)
                ld      iyh, a
                pop     af
                call    CALSLT
                ; D-ENTRYTIERS step 3 (2026-11-09): only each entry's CONTRACT is
                ; recorded, so the record can be gated byte for byte: +1 = Cy (bit 0
                ; of F), +2 = B where B is the answer (DSKCHG; `bmask` $FF), 0 for
                ; MTOFF / GETDPB. A, the rest of F, C, D, E, H, L are outside the
                ; published contracts and differ (scratchpad/dskent_both3.out); the
                ; other bytes keep their $EE fill on both machines.
                ld      d, b                    ; D = the call's B
                push    af
                pop     bc                      ; C = the call's F
                ld      hl, (recp)
                inc     hl
                ld      a, c
                and     1
                ld      (hl), a                 ; +1 Cy
                inc     hl
                ld      a, (bmask)
                and     d
                ld      (hl), a                 ; +2 B (DSKCHG's answer) or 0
                ret

; xcall_chg -- xcall_keep for DSKCHG: B is its answer, recorded
xcall_chg:
                push    af
                ld      a, $FF
                ld      (bmask), a
                pop     af
                jr      xcall_keep

bmask:          db      0
recp:           dw      0
outp:           dw      0

; ---------------------------------------------------------------------------
; captured block $0400-$043F: 4 records x 8 B, then the DPB buffer (32 B)
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
regs:           ds      4*8, $EE
dpb:            ds      32, $EE
