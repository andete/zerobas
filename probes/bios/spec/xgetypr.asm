; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XGETYPR -- docs/bios/GETYPR.md round 1 (2026-11-18): GETYPR ($0028, RST 28h) for every VALTYP ($F663) value 0..255,
; with entry F $00 and then $FF (512 cases); run 3 adds two passes, entry A $00 / F $00 and entry A $FF / F $FF, with
; every register marker complemented (1024 cases in all). It runs from RAM ($D000) with page 1 switched to the main ROM's slot
; (ENASLT, EXPTBL): on the VG-8020 the interpreter entries continue into the BASIC ROM there, which a cartridge's own
; page 1 would hide (run 1, from the cartridge, never finished on the VG-8020). Entry A = $A7; BC = $1357, DE = $9BDF, HL = $2468, IX = $4321, IY = $8765,
; compared after the call. VALTYP itself is read back too.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xgetypr.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; per case 4 bytes from CAP+1: A after, F after, a "kept" byte (0 = BC / DE /
; HL / IX / IY all kept, else 1), VALTYP after; VALTYP 0..255 per pass, the four passes as `passes` lists; then $C3.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry and a published work-area cell.
;
; @cap C000
; @caplen 1010
; @timeout 60

VALTYP  equ     $F663
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
ef      equ     $EF02
vt      equ     $EF03
ea      equ     $EF04                   ; run 3: entry A
mx      equ     $EF05                   ; run 3: the markers' XOR ($00 = as listed, $FF = complemented)
pidx    equ     $EF06                   ; run 3: the pass (0..3)
RAMB    equ     $D000                   ; where the probe's RAM block runs

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $100F
                ld      (hl), 0
                ldir
                ld      hl, blk                 ; the probe runs from RAM: page 1 must be the main ROM's (BASIC),
                ld      de, RAMB                ; where the reference's interpreter entries continue
                ld      bc, blk_end - blk
                ldir
                jp      RAMB

; ---- the RAM block: copied to RAMB; its internal call / jp targets are written R(label) = RAMB + label - blk ----
blk:
                ld      a, ($FCC1)              ; EXPTBL: the main ROM's slot
                ld      h, $40
                call    $0024                   ; ENASLT: page 1 := the main ROM
                di
                ld      hl, CAP+1
                ld      (ptr), hl
                xor     a
                ld      (pidx), a
pass:
                ld      a, (pidx)               ; the pass's entry F, entry A, marker XOR (passes in `passes`)
                ld      c, a
                add     a, a
                add     a, c                    ; 3 * pidx
                ld      hl, RAMB + passes - blk
                add     a, l
                ld      l, a
                jr      nc, p_nc
                inc     h
p_nc:
                ld      a, (hl)
                ld      (ef), a
                inc     hl
                ld      a, (hl)
                ld      (ea), a
                inc     hl
                ld      a, (hl)
                ld      (mx), a
                xor     a
                ld      (vt), a
v_lp:
                call    RAMB + one - blk
                ld      hl, vt
                inc     (hl)
                jr      nz, v_lp
                ld      hl, pidx
                inc     (hl)
                ld      a, (hl)
                cp      4
                jr      c, pass
                jp      RAMB + finish - blk
passes:
                db      $00, $A7, $00           ; run 1-2: entry F $00, A $A7, markers as listed
                db      $FF, $A7, $00           ;          entry F $FF
                db      $00, $00, $FF           ; run 3:   entry F $00, A $00, every marker complemented
                db      $FF, $FF, $FF           ;          entry F $FF, A $FF, complemented

; one -- VALTYP := (vt); A = (ea), F = (ef), register markers XOR (mx); RST 28h; record A, F, kept, VALTYP
one:
                ld      a, (vt)
                ld      (VALTYP), a
                ld      a, (ef)
                ld      c, a
                ld      a, (ea)
                ld      b, a
                push    bc
                ld      a, (mx)
                ld      e, a
                xor     $13
                ld      b, a
                ld      a, e
                xor     $57
                ld      c, a
                push    bc
                ld      a, e
                xor     $43
                ld      b, a
                ld      a, e
                xor     $21
                ld      c, a
                push    bc
                pop     ix
                ld      a, e
                xor     $87
                ld      b, a
                ld      a, e
                xor     $65
                ld      c, a
                push    bc
                pop     iy
                ld      a, e
                xor     $24
                ld      h, a
                ld      a, e
                xor     $68
                ld      l, a
                ld      a, e
                xor     $9B
                ld      d, a
                ld      a, e
                xor     $DF
                ld      e, a
                pop     bc
                pop     af
                rst     $28
                push    af
                ; kept? each register XOR (mx) against its listed marker
                push    hl
                ld      hl, mx
                ld      a, b
                xor     (hl)
                xor     $13
                jr      nz, o_moved_h
                ld      a, c
                xor     (hl)
                xor     $57
                jr      nz, o_moved_h
                ld      a, d
                xor     (hl)
                xor     $9B
                jr      nz, o_moved_h
                ld      a, e
                xor     (hl)
                xor     $DF
                jr      nz, o_moved_h
                pop     de                      ; DE := the HL after the call
                ld      a, d
                xor     (hl)
                xor     $24
                jr      nz, o_moved
                ld      a, e
                xor     (hl)
                xor     $68
                jr      nz, o_moved
                push    ix
                pop     de
                ld      a, d
                xor     (hl)
                xor     $43
                jr      nz, o_moved
                ld      a, e
                xor     (hl)
                xor     $21
                jr      nz, o_moved
                push    iy
                pop     de
                ld      a, d
                xor     (hl)
                xor     $87
                jr      nz, o_moved
                ld      a, e
                xor     (hl)
                xor     $65
                jr      nz, o_moved
                ld      c, 0
                jr      o_rec
o_moved_h:
                pop     de                      ; drop the saved HL
o_moved:
                ld      c, 1
o_rec:
                pop     hl                      ; H = A after, L = F after
                ld      a, h
                call    RAMB + emit - blk
                ld      a, l
                call    RAMB + emit - blk
                ld      a, c
                call    RAMB + emit - blk
                ld      a, (VALTYP)
                jp      RAMB + emit - blk

finish:
                ld      a, $C3
                call    RAMB + emit - blk
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret
blk_end:
