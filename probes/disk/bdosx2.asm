; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSX2.COM -- Tier-2 BDOS exerciser, Phase 2 block A+B (console tier + misc
; non-destructive). See disk/docs/tier2-bdos-remaining-spec.md SS5.1 for the
; full design. Calls a fixed sequence of console/clock/flag/drive BDOS
; functions ($0C/$18/$2D/$2C/$2E/$0D/$0B/$01/$07/$08/$06) and records every
; call's outward registers into a fixed RAM buffer, then self-loops at `done`
; -- the anchor for disk_probe_diff.py's `capture --at <done> --mem ...`
; differential. Needs a SECOND, later-timed keystroke burst (harness
; --keys2/--keys2-at) staged after this program's own disk load is done --
; see SS3 of the spec for why (ours drops type-ahead typed during disk I/O).
;
; CLEAN-ROOM: 100% own code. BDOS function contracts are the published
; map.grauw.nl MSX-DOS 2 function spec (documents this DOS-1-compatible
; subset verbatim) + MSX2 Technical Handbook Chapter 3, cross-checked live
; during this spec's implementation for CONST/DIRIO/CPMVER/GTIME/STIME/
; LOGIN/DSKRST/VERIFY. No stock/kernel bytes decoded.
;
; Build: pasmo -s bdosx2.sym --bin bdosx2.asm bdosx2.com

                org     $0100

BDOS            equ     $0005

; ---------------------------------------------------------------------------
; entry: CPMVER -> LOGIN -> STIME -> GTIME -> VERIFY(on) -> VERIFY(off) ->
;        DSKRST -> CONST(poll-until-ready) -> CONIN -> DIRIN -> INNOE ->
;        DIRIO(in,drained) -> CONST(drained) -> DIRIO(out)
;
; Each call is immediately followed by a snapshot of A/B/C/D/E/H/L into the
; matching `regs` record via IX (same pattern as bdosx.asm Phase 1 SS "snap").
; Records 8-10 (CONIN/DIRIN/INNOE) consume the three staged --keys2 chars in
; order; record 7's poll loop is what the staged burst lands during -- by the
; time it returns A<>0, one char is already queued, so records 8-10 never
; block. Records 11-12 then see a drained queue deterministically.
; ---------------------------------------------------------------------------
start:
                ; --- record 0: $0C CPMVER (bare) ---
                ld      c, $0C
                call    BDOS
                ld      ix, regs+0*8
                ld      (ix+0), $0C
                call    snap

                ; --- record 1: $18 LOGIN (bare) ---
                ld      c, $18
                call    BDOS
                ld      ix, regs+1*8
                ld      (ix+0), $18
                call    snap

                ; --- record 2: $2D STIME (H=12 L=34 D=56 E=0) ---
                ld      h, 12
                ld      l, 34
                ld      d, 56
                ld      e, 0
                ld      c, $2D
                call    BDOS
                ld      ix, regs+2*8
                ld      (ix+0), $2D
                call    snap

                ; --- record 3: $2C GTIME (immediately after STIME) ---
                ld      c, $2C
                call    BDOS
                ld      ix, regs+3*8
                ld      (ix+0), $2C
                call    snap

                ; --- record 4: $2E VERIFY on (E=1) ---
                ld      e, 1
                ld      c, $2E
                call    BDOS
                ld      ix, regs+4*8
                ld      (ix+0), $2E
                call    snap

                ; --- record 5: $2E VERIFY off (E=0, leave default state) ---
                ld      e, 0
                ld      c, $2E
                call    BDOS
                ld      ix, regs+5*8
                ld      (ix+0), $2E
                call    snap

                ; --- record 6: $0D DSKRST (bare; DTA->$0080 side effect, last
                ;     misc record so nothing downstream depends on DTA) ---
                ld      c, $0D
                call    BDOS
                ld      ix, regs+6*8
                ld      (ix+0), $0D
                call    snap

                ; --- record 7: $0B CONST, poll until a key is ready. Doubles
                ;     as the --keys2 delivery smoke test: if chars are ever
                ;     lost even at this idle poll window, this loop never
                ;     exits and the alignment guard fails loudly (no silent
                ;     garbage reaching the buffer diff). ---
const_poll:
                ld      c, $0B
                call    BDOS
                or      a
                jr      z, const_poll
                ld      ix, regs+7*8
                ld      (ix+0), $0B
                call    snap

                ; --- record 8: $01 CONIN (consumes staged char 1, echoes) ---
                ld      c, $01
                call    BDOS
                ld      ix, regs+8*8
                ld      (ix+0), $01
                call    snap

                ; --- record 9: $07 DIRIN (consumes staged char 2, no echo) ---
                ld      c, $07
                call    BDOS
                ld      ix, regs+9*8
                ld      (ix+0), $07
                call    snap

                ; --- record 10: $08 INNOE (consumes staged char 3, no echo) ---
                ld      c, $08
                call    BDOS
                ld      ix, regs+10*8
                ld      (ix+0), $08
                call    snap

                ; --- record 11: $06 DIRIO input direction (E=$FF); queue is
                ;     now drained by records 8-10 -> deterministic A=$00 ---
                ld      e, $FF
                ld      c, $06
                call    BDOS
                ld      ix, regs+11*8
                ld      (ix+0), $06
                call    snap

                ; --- record 12: $0B CONST (drained -> deterministic A=$00) ---
                ld      c, $0B
                call    BDOS
                ld      ix, regs+12*8
                ld      (ix+0), $0B
                call    snap

                ; --- record 13: $06 DIRIO output direction (E='!', visible) ---
                ld      e, '!'
                ld      c, $06
                call    BDOS
                ld      ix, regs+13*8
                ld      (ix+0), $06
                call    snap

done:
                jr      done                    ; self-loop; the disk_probe_diff.py `capture --at
                                                ; <done> --arm-check-val` anchor (arm-gated on
                                                ; $0102 == BDOSX2.COM's own 3rd byte, so the count
                                                ; only starts once BDOSX2.COM -- not COMMAND.COM's
                                                ; own busy-poll loop -- is the resident program;
                                                ; same pattern as bdosx.asm Phase 1).

; ---------------------------------------------------------------------------
; snap -- store A, B, C, D, E, H, L into (ix+1)..(ix+7). (ix+0) is pre-filled
; by the caller with the literal BDOS function number. Clobbers nothing live.
; ---------------------------------------------------------------------------
snap:
                ld      (ix+1), a
                ld      (ix+2), b
                ld      (ix+3), c
                ld      (ix+4), d
                ld      (ix+5), e
                ld      (ix+6), h
                ld      (ix+7), l
                ret

; ---------------------------------------------------------------------------
; regs (14 records x 8 B); no FCB/data buffer needed by this program.
; ---------------------------------------------------------------------------
                ds      $0340 - $, $00
regs:           ds      14*8                    ; $0340-$03AF
