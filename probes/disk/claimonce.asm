; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; CLAIMONCE -- a test cartridge that claims EXACTLY N bytes of RAM in its INIT, once: HIMEM ($FC4A, published)
; := $F380 - N, but only while HIMEM is still the untouched $F380. claimer.asm subtracts 16 every time its INIT
; runs, and on the CF-3300 and the VG-8020 its 16 KB image is mirrored into page 2 and its INIT runs twice there
; (32 B claimed; scratchpad/AE_wasize.md). This one's second run sees HIMEM moved and returns.
; N is the word at claim_n ($4010): probes/disk/disk_probe_guard.py patches it per row (0 never: that row boots
; without a cartridge). On zerobas an A>BASIC restart puts HIMEM back to $F380 and reruns every INIT, so this one
; claims its N again there (disk/kernel.asm bt_keep).
; CLEAN-ROOM: 100% own code; only the published HIMEM cell.
HIMEM           equ     $FC4A
                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0
claim_n:        dw      16                  ; $4010: N, patched by the probe
init:
                ld      hl, (HIMEM)
                ld      de, $F380
                or      a
                sbc     hl, de
                ret     nz                  ; claimed already (the page-2 mirror's run)
                ld      hl, $F380
                ld      de, (claim_n)
                sbc     hl, de              ; Cy clear: the sbc above gave Z, no borrow
                ld      (HIMEM), hl
                ret
