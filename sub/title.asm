; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — title.asm  (startup-header tenant)
; ===========================================================================
; show_title + banner_text (basic/title.asm), evicted whole into sub-ROM PAGE 1
; to free main-ROM page-1 tail space for the input-devices I2 slice
; (docs/spec-basic-input-devices.md §9.5 — a measured 55 B deficit). Follows the
; landed casmatch/lineedit/randio eviction pattern: the moved code is VERBATIM,
; shared through basic/title-body.inc, which basic/title.asm still includes at
; its own original position for the lean 16 KB cart (byte-identical there).
;
; PAGE 1, not page 0: the body's only outward edges are INITXT and CHPUT, which
; are page-0 BIOS. A page-1 tenant keeps page 0 mapped and so can call them; a
; page-0 tenant would have the BIOS switched out from under it.
;
; NO MARSHALLING AT ALL — the simplest tenant in the tree. show_title takes no
; arguments, returns no value, and touches no RAM state, so unlike casmatch (which
; has to convert CF into a CM_STATUS byte because subrom_call always clears CF)
; there is nothing to hand back. The resident side is a bare stub.
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/title.asm. The
; header text is zerobas's own — no reference-ROM text is copied, which is the
; point of that file's header note. INITXT/CHPUT are published BIOS entries. No
; reference-ROM disassembly. See sub/PROVENANCE.md.
; ===========================================================================

; --- title_tenant: the SUBROM_IDX_TITLE entry ------------------------------
; `show_title` already ends in `ret`, so the entry IS the body — no wrapper.
title_tenant:
                include "../basic/title-body.inc"
