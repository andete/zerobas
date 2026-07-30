; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — format.asm  (CALL FORMAT build/write-engine tenant)
; ===========================================================================
; The CALL FORMAT sector-build/write BULK, evicted from the repack main ROM's
; basic/format.asm into sub-ROM PAGE 1 (docs/spec-evict-call-format.md), to free
; page-1 window space for the error-handling S2b slice.
;
; WHY PAGE 1, AND WHY A SPLIT (not a whole-tenant move). do_format straddles both
; main pages: it needs main-BASIC page-1 console I/O (print_string/read_line, the
; 360k/720k menu) AND the page-0 BIOS (write_sector -> dskio_calslt -> CALSLT
; $001C). Neither a page-0 tenant (BIOS switched out) nor a page-1 tenant (main
; page-1 switched out) alone can run the whole thing (playbook §2/§3; spec §0's
; classification correction). So the menu + dispatch STAY main-resident
; (basic/format.asm), and only the pure geometry-driven build/write engine —
; which needs the BIOS but NOTHING from main page-1 — comes here, as a page-1
; tenant (mirrors the disk DSKIO / math-pack precedent, SUBROM_ENTRY_BASE_P1).
;
; The shared body lives in basic/format-body.inc (the shared
; inline copy — same file, same bytes, see that file's own header). Here it
; binds `write_sector` to a SUB-LOCAL CALSLT write path (below): main's
; basic/fat.asm write_sector/dskio_calslt are main-page-1-resident, invisible to
; a page-1 tenant (CALSLT switches page 1 OUT, not page 0 — playbook §2), so
; write_sector cannot be shared by reference; the ~20 B write path is duplicated
; (spec §3, "the one duplication" — read_sector is NOT needed, FORMAT is
; write-only). GEOM_360K/GEOM_720K move here too (format-body.inc), selected by
; FMT_GEOMSEL (RAM, set by the main-resident menu before the call).
;
; RESULT. Cy from write_sector cannot ride back through subrom_call/CALSLT to
; the resident stub (subrom_call's own `or a` clears it, spec §4) — so the
; sub-local write_sector ALSO stashes its disposition in FMT_RESULT (RAM) on
; every call; every exit path in format-body.inc (an early `ret c`, or the
; final `jp write_sector` tail from fmt_boot) funnels through it, so FMT_RESULT
; always reflects the last write attempted by the time control returns to the
; resident stub.
;
; CLEAN-ROOM: original code (the bulk is copied verbatim from our own
; basic/format.asm via basic/format-body.inc; the sub-local write path is a
; straight duplication of basic/fat.asm's own write_sector/dskio_calslt, already
; our own clean-room DSKIO engine — see that file's header for the citations).
; No disassembly.
; ===========================================================================

; --- format_tenant: the SUBROM_IDX_FORMAT entry ----------------------------
; Read FMT_GEOMSEL (0 = 360k, 1 = 720k; set by the resident menu before the
; call) and tail into the shared build/write body (format-body.inc) with
; HL = the chosen descriptor's base — exactly the argument fmt_selected
; expects in the pre-eviction shape. Every exit from that body returns
; (via an early `ret c` or the final write_sector tail) straight back through
; here to subrom_call's caller; FMT_RESULT is already current by then (see the
; sub-local write_sector below), so this entry needs no wrap-up code of its own.
format_tenant:
                ld      a,(FMT_GEOMSEL)
                or      a
                jr      nz,ft_720
                ld      hl,GEOM_360K
                jr      fmt_selected        ; tail into the shared body
ft_720:
                ld      hl,GEOM_720K
                jr      fmt_selected

; write_sector — sub-local write path (page-1 tenant; own CALSLT copy, per
; spec §3's "one duplication" — mirrors basic/fat.asm's write_sector +
; dskio_calslt, write-only, drive/media ignored exactly as the resident
; original). Also stashes the disposition in FMT_RESULT (RAM) — see header.
;   in:  DE = logical sector number, HL = buffer (512 bytes)
;   out: Cy = 0 ok, Cy = 1 error; FMT_RESULT set to the same 0/1
write_sector:
                ld      b,1                 ; one sector
                ld      c,$F9               ; media byte (ignored, single drive)
                xor     a                   ; drive 0
                scf                         ; Cy = 1 = WRITE direction (MSX2 TH DSKIO)
                push    af                  ; preserve the direction Cy across IY setup
                ld      a,(DISKSLOT)
                ld      (SCAN_IY+1),a       ; IYh = disk ROM slot id
                ld      iy,(SCAN_IY)
                ld      ix,DSKIO_ENTRY      ; standard DSKIO entry ($4010)
                pop     af                  ; restore A=drive and the direction Cy
                call    CALSLT              ; cross-slot DSKIO; returns DSKIO's Cy/A/B
                jr      c,ws_err
                xor     a
                ld      (FMT_RESULT),a
                or      a                   ; Cy = 0
                ret
ws_err:
                ld      a,1
                ld      (FMT_RESULT),a
                scf                         ; Cy = 1
                ret

; The shared build/write body (fmt_selected../fmt_boot + fmt_geom_byte/word +
; fmt_zero_buf + GEOM_360K/GEOM_720K). Binds write_sector to the sub-local copy
; above (defined first, co-resident).
                include "basic/format-body.inc"
