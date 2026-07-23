; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; title.asm — zerobas startup header.
;
; The few left-aligned lines printed at the top of the screen before the
; interpreter is ready — the same role as MSX-BASIC's "version / copyright /
; Bytes free" header that precedes its READ-EVAL prompt. The text is ORIGINAL
; to zerobas: no header text is copied from any reference ROM (which would be a
; clean-room violation and a false copyright claim). See PROVENANCE.md.
;
; The body (show_title + banner_text) lives in basic/title-body.inc, which this
; file includes for the lean cart and sub/title.asm includes for the repack
; build — see that file's header for the split rationale.

    IF ROM_BASE < $4000
; --- repack: show_title is a sub-ROM PAGE-1 tenant --------------------------
; docs/spec-basic-input-devices.md §9.5. The ~74 B of routine + banner text moved
; to sub/title.asm (SUBROM_IDX_TITLE) to fund the I2 slice's 55 B page-1 deficit.
;
; Nothing to marshal — no arguments, no return value, no RAM state — so this stub
; is the whole resident side. Called once, from `init` just before the REPL
; (basic/interp.asm), and `init_ext_roms` on the line above it has already run the
; slot scan that sets SUBSLOT_OK, so the sub-ROM is reachable by the time we get
; here.
;
; NO absent-sub-ROM error path, deliberately: subrom_call returns CF=1 when the
; sub-ROM is missing, and the correct behaviour then is simply to print no header
; and carry on booting. Every other tenant guards a statement whose silent failure
; would be a bug; a cosmetic banner's is not.
show_title:
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_TITLE
                jp      subrom_call         ; CF=1 (absent) -> no header, just return
    ELSE
                include "basic/title-body.inc"   ; lean: inline, byte-identical
    ENDIF
