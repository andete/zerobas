; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; cal-refill-body.inc — cal_refill shared body (TAPION-relock + slurp one
; 256-byte tape block into CAL_BUF).
;
; docs/spec-eviction-g5-space.md. Extracted verbatim from basic/cload.asm so
; the SAME source once fed two homes. 🔴 SINCE D-CARVECAS (2026-09-27) IT FEEDS
; ONE: sub/casmatch.asm (sub-ROM page 1), whose casmatch_tenant and
; casget_tenant hold every caller -- cas_skip_data's csd_ascii arm, cal_getbyte's
; serve/read-ahead body (cal_serve) and cas_ascii_setup. basic/cload.asm no
; longer includes it; its cal_getbyte and cas_ascii_setup are stubs into the
; casget tenant. The file stays a separate include so its history reads whole.
;
; Clean-room: our own code, extracted verbatim from basic/cload.asm (see
; that file's header for the cassette file-format provenance).

; --- cal_refill: TAPION-relock + slurp one 256-byte tape block into WHICHEVER
; buffer CAL_CURHI is NOT currently pointing at ---------------------------------
; TAPION then a tight TAPIN*256 loop that keeps its position in CAL_CNT (RAM) —
; NOTHING on the stack across TAPIN (requirement 1 in the cas_ascii_load header),
; and no gap between the lock and the first read (requirement 2). The fill
; TARGET is derived fresh each byte as CAL_CURHI XOR CAL_XORHI (RAM + a constant,
; not a register — TAPIN clobbers everything, same reason CAL_CNT lives in RAM).
; Every caller of cal_refill wants "the buffer I am not currently serving/using"
; filled: cal_getbyte's double-buffer read-ahead (basic/cload.asm) wants the
; JUST-DRAINED buffer refilled with the block after next, and cas_ascii_setup
; primes block 1 then block 2 by toggling CAL_CURHI between calls (see cload.asm).
; cas_skip_data's csd_ascii arm (sub/casmatch.asm) wants a SINGLE fixed buffer
; (CAL_BUF) every call, which it gets for free by setting CAL_CURHI to CAL_BUF2's
; high byte ONCE before its loop and never touching it again.
; Leaves CAL_CNT = 0 (wrapped after 256) so a caller that then swaps CAL_CURHI to
; this buffer serves from position 0. TAPION failure (no such block) or a TAPIN
; short-read (corrupt/truncated tape) -> CF set = EOF.
cal_refill:
                call    TAPION              ; (re-)lock onto the block's leader
                ret     c                   ; no block -> EOF
                xor     a
                ld      (CAL_CNT),a         ; fill from position 0
cal_fill_lp:
                call    TAPIN               ; clobbers all; position is in CAL_CNT (RAM)
                jr      c,cal_fill_fail     ; short block / read fail -> EOF
                ld      c,a                 ; C = the byte
                ld      a,(CAL_CURHI)
                xor     CAL_XORHI           ; A = the OTHER buffer's high byte
                ld      h,a
                ld      a,(CAL_CNT)
                ld      l,a                 ; HL = (not-CAL_CURHI) + pos
                ld      (hl),c
                inc     a
                ld      (CAL_CNT),a         ; pos++ (255 -> 0 ends the 256-byte block)
                jr      nz,cal_fill_lp
                ret                         ; CF clear; buffer full, CAL_CNT = 0
cal_fill_fail:
                scf                         ; truncated block -> EOF
                ret
