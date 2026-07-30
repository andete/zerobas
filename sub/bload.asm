; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — bload.asm  (the BLOAD verb tenant)
; ===========================================================================
; The whole BLOAD verb body — device dispatch, the cassette load loop and the
; disk load loop — evicted from main page 1 into sub-ROM PAGE 1
; (docs/spec-traps-t3-key.md §7.6) to fund the interrupt-traps T3 slice. This is
; the fcbname/casmatch eviction pattern one level larger: the moved code is
; VERBATIM, shared through basic/bload-body.inc, and
; includes at its original position so that ROM stays byte-identical.
;
; WHY PAGE 1, AND WHY THAT IS THE WHOLE POINT. A page-1 tenant runs with main
; page 1 switched out but the sub-ROM's own page 1 mapped — so it sits beside
; `fatprim_tenant` and calls `fat_mount` / `fat_find` / `fat_open` /
; `fat_read_file_sector` **sub-locally**, as ordinary in-page calls. In main page
; 1 those same four names are marshalling stubs that CALSLT into this very ROM.
; That round trip is exactly what made BLOAD look un-evictable (`do_disk_bload ->
; fat_io_open -> fat_find -> subrom_call`, a low-region call that is paged out
; while a tenant runs — and a nested sub-ROM call besides). Moving the caller to
; the callee's side dissolves it. Same for `build_83_name`, already resident here
; as a page-1 tenant body (sub/fcbname.asm): the resident marshalling shim
; disappears for our path.
;
; WHAT STAYS RESIDENT, and why each one has to:
;   * `load_handoff` — the `,R` tail ends in `jp (hl)` INTO THE LOADED PROGRAM and
;     never returns. Run inside this tenant's CALSLT it would leave main page 1
;     switched out forever. The tenant returns normally; the resident stub does
;     the handoff (basic/bload.asm).
;   * `load_error` / `print_string` — the reporter, 61 external callers.
;   * `parse_disk_fcb` (9 external callers) and `parse_close_run` (6) — shared
;     service routines that merely LIVED in bload.asm. They are COPIED here, not
;     moved: a duplicate in the sub-ROM costs zero main page-1 bytes.
;
; INTERRUPTS. The cassette path holds the CPU for the length of a tape read.
; subrom_call enters DI, so this tenant re-enables interrupts at entry and
; disables them before returning. That is safe here for the same reason
; play_service is: an IRQ vectors to $0038 in MAIN page 0, which stays mapped
; throughout a page-1 tenant, and `htimi_guard` (basic/subromcall.asm) sees that
; page 1 is not main-ROM and skips the PLAY/trap seam for that frame. Without
; that guard this would be a wild jump — it is the same hazard
; docs/spec-traps-t1-htimi-page1-safety.md was written for.
;
; MARSHALLING: BL_PTR in (the token cursor after the BLOAD token), BL_STAT out
; (0 = loaded, 1 = load_error). subrom_call clobbers every register and forces
; CF=0 on return, so neither the cursor nor a carry can ride in registers — the
; fatprim/fcbname pattern. Unlike fcbname these need cells of their OWN rather
; than aliasing DISKOP_HL/DISKOP_STATUS: the status is held ACROSS the whole
; load, during which the fatprim cells are live on every getbyte.
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/bload.asm and
; basic/fat.asm. Provenance for the BSAVE tape/disk formats, the DSKIO contract
; and FAT12 is unchanged (basic/PROVENANCE.md). The dispatch/marshalling glue is
; own-design, the casmatch/fatprim/fcbname precedent. No reference-ROM
; disassembly. See sub/PROVENANCE.md.
; ===========================================================================

; --- bload_tenant: the SUBROM_IDX_BLOAD entry ------------------------------
bload_tenant:
                xor     a
                ld      (BL_STAT),a         ; assume success; load_error flips it
                ld      hl,(BL_PTR)         ; token cursor (from the resident stub)
                ei                          ; the tape path needs a live ISR; htimi_guard
                                            ; makes that safe while page 1 is ours
                call    do_bload
                di                          ; subrom_call's CALSLT returns under DI
                ret

; --- sub-local clones of the resident helpers the body calls ----------------
; These are COPIES, not evictions: every one of them stays resident too, for
; callers outside bload.asm. A sub-ROM duplicate costs no main page-1 bytes.

; bl_skip_spaces — byte-identical clone of basic/interp.asm. It needs a distinct
; name because the sub image already defines `skip_spaces` in its PAGE 0
; (sub/readdata.asm), which is unmapped while this page-1 tenant runs -- the same
; reason fcbname.asm's upcaser is called fcb_upcase.
bl_skip_spaces:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      bl_skip_spaces

; bl_upcase — page-1 upcaser clone. sub/fcbname.asm already carries an identical
; one (fcb_upcase), and `bl_upcase equ fcb_upcase` would have reused it — but
; check_tenant_closure.py --page1 tells a sub-local routine from a switched-out
; main one BY NAME (a defined label vs an imported equ), so an alias reads to the
; gate as a main-page-1 escape. Six bytes of free sub-ROM space is a better
; answer than weakening a standing gate to accept aliases.
bl_upcase:
                cp      'a'
                ret     c
                cp      'z'+1
                ret     nc
                sub     $20
                ret

; load_error — sub-local reporter. Deliberately MIRRORS the resident routine's
; shape (TAPIOF, ERRMARK, then `ret`) instead of aborting, because the body
; reaches it by `jp` from several stack depths — including from inside
; parse_disk_fcb, where the `ret` lands back in the CALLER (a known nested-reject
; hazard, [[load-error-is-not-abort]]). Changing the stack behaviour here would
; silently change control flow on the error path, so it is preserved exactly; the
; only difference is that the message is not printed here. The resident stub sees
; BL_STAT and reports once, which also removes the double-report the resident
; path could produce.
bl_load_error:
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
                ld      a,1
                ld      (BL_STAT),a
                ret

; parse_close_run — verbatim copy of the resident routine (basic/bload.asm),
; which stays resident for its six external callers. parse_disk_fcb needs no copy
; here: it arrives with the body via basic/pdfcb-body.inc, and binds to the
; sub-local build_83_name rather than the resident marshalling shim.
parse_close_run:
                ld      a,(hl)
                cp      '"'                 ; closing quote required
                jr      nz,pcr_err
                inc     hl
                xor     a
                ld      (RUNFLAG),a         ; default: no ,R handoff
                ld      (VRAM_FLAG),a       ; default: RAM load
                call    bl_skip_spaces
                ld      a,(hl)
                or      a
                jr      z,pcr_ok
                cp      COLON
                jr      z,pcr_ok
                cp      ','
                jr      nz,pcr_err
                inc     hl                  ; past the comma
                call    bl_skip_spaces
                ld      a,(hl)
                call    bl_upcase              ; accept ,r / ,s as well
                cp      'R'
                jr      z,pcr_run
                cp      'S'
                jr      z,pcr_vram
                jr      pcr_err
pcr_run:
                ld      a,1
                ld      (RUNFLAG),a
                jr      pcr_flag_end
pcr_vram:
                ld      a,1
                ld      (VRAM_FLAG),a
pcr_flag_end:
                inc     hl                  ; past the flag letter
                call    bl_skip_spaces
                ld      a,(hl)
                or      a
                jr      z,pcr_ok
                cp      COLON
                jr      z,pcr_ok
                ; fall through to pcr_err
pcr_err:
                scf
                ret
pcr_ok:
                or      a                   ; CF clear = success
                ret

; dev_cas — the device name the body compares against.
dev_cas:
                db      "CAS:",0

; The sequential FAT12 read layer. Identical source to the resident copy, but
; here fat_mount/fat_find/fat_open/fat_read_file_sector bind to sub/fatprim.asm's
; REAL implementations instead of the marshalling stubs -- the whole reason this
; tenant is affordable.
                include "basic/fatio-body.inc"       ; fat_io_open + fat_io_getbyte

; The verb body itself, shared with the resident side.
                include "basic/bload-body.inc"       ; do_bload .. disk_load_fin
