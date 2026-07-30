; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — casmatch.asm  (cassette name-match/skip tenant)
; ===========================================================================
; cas_open_match + cas_skip_data (tape Tier-3 name-matching, basic/cload.asm),
; evicted whole into sub-ROM PAGE 1 (docs/spec-eviction-g5-space.md) to free
; main-ROM page-1 tail space for the G5 PAINT slice. Follows the landed G4-
; eviction pattern (sub/randio.asm, sub/lineedit.asm): the moved code is
; VERBATIM (shared via basic/casmatch-body.inc, included both here and at
; basic/cload.asm's own original position -- byte-
; identical there).
;
; NO MARSHALLING: cas_open_match takes no register inputs and its only
; caller-visible output is CF (matched vs not-found/tape-error) + the RAM
; cell CAS_HDRID it already sets on a match. Since subrom_call always clears
; CF on return (CALSLT's own `or a` after the call, basic/subromcall.asm),
; the CF result cannot ride back directly -- casmatch_tenant (below) converts
; it to a status byte (CM_STATUS, aliased onto the shared DISKOP_STATUS cell,
; the fatprim/dirverb/audio/lineedit precedent: one subrom_call reaches
; exactly one tenant, so the separate value namespaces never collide) that
; the resident stub (basic/cload.asm `cas_open_match`) converts back to CF.
;
; cal_refill (basic/cload.asm) is DUPLICATED here (shared source via basic/
; cal-refill-body.inc, so the resident copy -- still needed by cal_getbyte/
; ascii_read_lines -- and this one can never drift apart): cas_skip_data's
; csd_ascii arm calls it, and TAPION/TAPIN (page-0 BIOS) + CAL_BUF/CAL_CNT
; (RAM) are the only things it touches -- no straddle, nothing in the
; resident-ABI import list needed.
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/cload.asm
; (see that file's header for the cassette file-format provenance: MSX2
; Technical Handbook cassette file format, an allowed source). The dispatch/
; marshalling glue is own-design, the fatprim/dirverb/lineedit precedent. No
; reference-ROM disassembly. See sub/PROVENANCE.md.
; ===========================================================================

; --- casmatch_tenant: the SUBROM_IDX_CASMATCH entry ------------------------
casmatch_tenant:
                call    cas_open_match
                jr      c,cmt_fail
                xor     a
                jr      cmt_store
cmt_fail:
                ld      a,1
cmt_store:
                ld      (CM_STATUS),a
                ret

                include "basic/casmatch-body.inc"    ; cas_open_match..cas_skip_data
                include "basic/cal-refill-body.inc"  ; cal_refill (sub-local duplicate)
