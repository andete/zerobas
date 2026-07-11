; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; subromcall.asm — zerobas-sub discovery recorder + dispatch helper
; (repack build only — included inside `IF ROM_BASE < $4000`, basic/main.asm,
; in the PAGE-0 low region freed by evicting the float PRINT formatter).
; docs/spec-basic-subrom.md §3c/§3g, WAVE-1 AMENDMENT.
;
; WHY PAGE 0. init_ext_roms (basic/initext.asm) lives in page 1, whose tail is
; nearly full; these ~90 B of bodies would overrun the $8000 ceiling there. They
; belong in the space the formatter eviction frees (page 0 low region). Their
; callers reach them under normal (fully slot-0-mapped) contexts — try_sub_slot
; from the boot scan, subrom_call from the PRINT stub — so a page-1→page-0 call
; is fine. subrom_call issuing a page-0 CALSLT from page-0 code is also fine:
; CALSLT restores page 0 to slot 0 before returning, exactly as the 163 disk
; call sites already switch their OWN page (page 1) out across a CALSLT.
;
; SOURCES (allowed, new vs initext.asm's block): CD sub-ROM signature + EXBRSA
; $FAF8 sub-ROM-slot work area — MSX2 Technical Handbook. The RDSLTs read only
; our OWN sub-ROM bytes; no C-BIOS code is read or relocated (firewall §3g).

; try_sub_slot: if the slot just scanned by try_init_slot (SCAN_SLOT) carries the
; MSX2 sub-ROM signature "CD" at $0000 (page 0), record it. Called right after
; try_init_slot in ier_sloop, so SCAN_SLOT already holds this subslot's id and
; RDSLT can reuse it via rdslt_scan. Unlike the disk case there is NO INIT CALSLT
; — the sub-ROM is a passive callee (D-7); recording the slot is the whole job.
try_sub_slot:
                ld      hl,$0000
                call    rdslt_scan
                cp      'C'
                ret     nz
                ld      hl,$0001
                call    rdslt_scan
                cp      'D'
                ret     nz
                ; found: record the slot in the private path AND the MSX2 work area
                ld      a,(SCAN_SLOT)
                ld      (SUBSLOT),a
                ld      (EXBRSA),a          ; convention-compat (D-6); dispatch uses SUBSLOT
                ld      a,1
                ld      (SUBSLOT_OK),a
                ret

; subrom_call: dispatch to a sub-ROM page-0 tenant. IX = entry address
; (SUBROM_ENTRY_BASE_P0 + 3*index); args/results marshalled in page-2/3 RAM by
; the caller. Returns CF=1 WITHOUT calling if the sub-ROM is absent (reduced
; builds); CF=0 after a completed call. The tenant runs with slot-0 page 0 (BIOS
; + $0038 ISR) switched out, so the whole call is under DI (§3b/§3d); CALSLT
; clobbers all registers — the caller guards anything live (e.g. the text cursor).
subrom_call:
                ld      a,(SUBSLOT_OK)
                or      a
                scf
                ret     z                   ; absent -> CF=1, no call (caller errors)
                ld      a,(SUBSLOT)
                ld      d,a
                ld      e,0
                push    de
                pop     iy                  ; IYh = sub-ROM slot id (CALSLT ABI)
                di
                call    CALSLT              ; page-0 tenant runs under DI
                ei
                or      a                   ; CF=0: call completed
                ret

; subrom_absent_error: defensive statement abort for a sub-ROM-backed statement in
; a build without the sub-ROM (never reached on the merged machine, which always
; ships it — §3d). Mirrors fp_runtime_error's tail (zero PRDEST, print, ret to the
; statement driver's caller); own lowercase wording, D-8/D-2 pattern.
subrom_absent_error:
                xor     a
                ld      (PRDEST),a
                ld      hl,err_subrom_absent
                jp      print_string
err_subrom_absent:
                db      "illegal function call",13,10,0
