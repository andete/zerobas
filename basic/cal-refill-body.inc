; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; cal-refill-body.inc — cal_refill shared body (TAPION-relock + slurp one
; 256-byte tape block into CAL_BUF).
;
; docs/spec-eviction-g5-space.md. Extracted verbatim from basic/cload.asm so
; the SAME source feeds two homes, both UNCONDITIONAL (cal_refill itself does
; not move -- only the reason it needs a second home changed):
;   * basic/cload.asm: included at this file's
;     ORIGINAL position, unchanged -- still the routine cal_getbyte /
;     ascii_read_lines call.
;   * sub-ROM PAGE-1 tenant (sub/casmatch.asm, repack only): a DUPLICATE,
;     because cas_skip_data's csd_ascii arm (basic/casmatch-body.inc) moved
;     sub-side whole and still needs to call cal_refill; sharing this file
;     keeps the two copies from drifting apart.
;
; Clean-room: our own code, extracted verbatim from basic/cload.asm (see
; that file's header for the cassette file-format provenance).

; --- cal_refill: TAPION-relock + slurp one 256-byte tape block into CAL_BUF --
; TAPION then a tight TAPIN*256 loop that keeps its position in CAL_CNT (RAM) —
; NOTHING on the stack across TAPIN (requirement 1 in the cas_ascii_load header),
; and no gap between the lock and the first read (requirement 2). Leaves CAL_CNT
; = 0 (wrapped after 256) so the caller/cal_getbyte serves from position 0.
; TAPION failure (no such block) or a TAPIN short-read (corrupt/truncated tape)
; -> CF set = EOF.
cal_refill:
                call    TAPION              ; (re-)lock onto the block's leader
                ret     c                   ; no block -> EOF
                xor     a
                ld      (CAL_CNT),a         ; fill from position 0
cal_fill_lp:
                call    TAPIN               ; clobbers all; position is in CAL_CNT (RAM)
                jr      c,cal_fill_fail     ; short block / read fail -> EOF
                ld      c,a                 ; C = the byte
                ld      a,(CAL_CNT)
                ld      l,a
                ld      h,CAL_BUF >> 8      ; HL = CAL_BUF + pos (page-aligned)
                ld      (hl),c
                inc     a
                ld      (CAL_CNT),a         ; pos++ (255 -> 0 ends the 256-byte block)
                jr      nz,cal_fill_lp
                ret                         ; CF clear; buffer full, CAL_CNT = 0
cal_fill_fail:
                scf                         ; truncated block -> EOF
                ret
