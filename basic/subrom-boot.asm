; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; subrom-boot.asm — the BOOT-TIME half of the zerobas-sub plumbing
; (repack build only, guarded below; the lean 16 KB cart has no sub-ROM).
;
; WHY THIS FILE EXISTS — A PROMOTION, NOT A NEW FEATURE. Every routine here was
; written in basic/subromcall.asm and lived in the page-0 low region. That
; placement was never a correctness requirement: subromcall.asm's own header
; records the reason as "init_ext_roms lives in page 1, whose tail is nearly
; full; these ~90 B of bodies would overrun the $8000 ceiling there." The BLOAD
; carve (docs/spec-traps-t3-key.md §7.5) freed 262 B of main page 1, so the
; premise is gone — and the KEY trap needs the low region for the one thing that
; genuinely cannot leave it, its $0038-path hook (basic/keytrap.asm). So the
; boot-time half moves UP and pays for the ISR-path half. tools/promote_scout.py
; is the gate that says which low-region routines may do this.
;
; WHAT MAY BE PROMOTED, AND WHY THESE TWO QUALIFY. Two callers cannot see main
; page 1, so anything they reach is pinned low: a sub-ROM PAGE-1 tenant (main
; page 1 is switched out under it) and the $0038 ISR (which can land inside that
; window). Both routines below run exactly once, from init_ext_roms, under the
; boot DI, BEFORE any tenant has ever been dispatched — so neither caller can
; reach them, by construction rather than by audit. Promotion is also
; monotonically safe for page-0 tenants, which see main page 1 but not the low
; region: moving a routine up can only remove a violation.
;
; WHAT STAYS IN basic/subromcall.asm, and why it is not an arbitrary line:
;   * subrom_call / subrom_absent_error — the RUNTIME dispatcher. It is the one
;     routine that issues the CALSLT into a sub-ROM tenant, so it stays on the
;     side of the slot boundary that no tenant can page out. Not moved, and not
;     to be moved on a promote_scout "promotable" verdict alone (see that tool's
;     --switchers note: the pin is on the code that performs the switch, which a
;     call-graph walk cannot see).
;   * htimi_guard — literally the ISR path.
;   * sub_int_template — the RAM trampoline BODY. It is copied to SUB_INT_RAM and
;     executed from there, so its own residence is free; it is left beside the
;     guard it belongs to rather than moved for 72 B this slice does not need.
;
; Clean-room: nothing here is derived from a disassembly or byte-copy of any
; reference BIOS/BASIC ROM; the routines are unchanged from their reviewed form
; in subromcall.asm. Sources are recorded there and in basic/PROVENANCE.md.

    IF ROM_BASE < $4000

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

; sub_int_install: copy the trampoline template into RAM and record the two slot
; configs. Called from init_ext_roms (basic/initext.asm) after the CD scan, under
; the boot DI, only when a sub-ROM was found. Clobbers AF/BC/DE/HL.
; The `ldir` source (sub_int_template) stays in the low region — a plain in-slot
; read under the fully-mapped boot configuration, the same as any page-1 routine
; calling a low-region one.
sub_int_install:
                ld      a,(SUBSLOT_OK)
                or      a
                ret     z                   ; no sub-ROM -> no trampoline to install
                ld      hl,sub_int_template
                ld      de,SUB_INT_RAM
                ld      bc,sub_int_template_end - sub_int_template
                ldir                        ; copy the stub into page-3 RAM
                ; MAIN page-0 primary field (page 0 is the BIOS right now).
                in      a,(PSLTREG)
                and     %00000011
                ld      (INT_MAIN_PRIM),a
                ; SUB page-0 primary + subslot fields, from the recorded slot id
                ; (bit7 exp | %ss bits3-2 | %pp bits1-0).
                ld      a,(SUBSLOT)
                ld      c,a
                and     %00000011           ; sub primary  -> page-0 primary field (3)
                ld      (INT_SUB_PRIM),a
                ld      a,c
                rrca
                rrca
                and     %00000011           ; sub secondary -> page-0 subslot field (2)
                ld      (INT_SUB_SUBSL),a
                ret

    ENDIF
