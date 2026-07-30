; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fcbname-body.inc — the build_83_name 8.3-FCB-name builder body.
; ===========================================================================
; Shared, byte-identical, between:
;   * (retired) the lean 16 KB cart, inline at its original position;
;   * the sub-ROM PAGE-1 tenant (sub/fcbname.asm, SUBROM_IDX_FCBNAME) — evicted
;     here to free repack-main page-1 space for the interrupt-traps T1 slice
;     (docs/spec-basic-interrupt-traps.md §10.4, D-T-8c/D-T-8d).
; The repack main ROM (the repack build) does NOT include this body: it carries
; only the resident marshalling shim (basic/bload.asm IF branch), which stores
; the source pointer to BN_PTR, subrom_calls the tenant, and reloads BN_PTR /
; converts BN_STAT back to CF — the casmatch/cas_open_match precedent.
;
; The one external callee is `fcb_upcase`. Resident it is a zero-byte EQU
; onto basic/interp.asm's `upcase` (so the body assembles byte-identical
; to the frozen cart); in the page-1 tenant (where main page 1 is switched OUT, and
; the sub's own `upcase` clone is in the unmapped page-0 island) it is a co-located
; page-1 clone label. The indirection gives the page-1 tenant a reachable upcaser
; without a name collision, and leaves the resident bytes untouched.
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/bload.asm.
; Rules quarantined in basic/PROVENANCE.md §disk-BLOAD scratch FCB. No
; reference-ROM disassembly. See basic/PROVENANCE.md / sub/PROVENANCE.md.
; ===========================================================================

; build_83_name — convert the filename at HL into the 11-byte 8.3 field at
; DISK_FCB_NAME (8 name + 3 ext, space-padded $20, upper-case).
;   in:  HL -> first filename char (the byte after any drive prefix)
;   out: HL -> the closing '"' (so parse_close_run resumes there);
;        CF clear on success, CF set if the name doesn't fit 8.3 or is empty.
; Rules (own design, documented in PROVENANCE.md §disk-BLOAD scratch FCB):
;   - split on the FIRST '.'; up to 8 chars before -> name, up to 3 after -> ext
;   - no '.' -> all-name, ext = 3 spaces
;   - the filename ends at the closing '"' (or NUL, defensively)
;   - more than 8 name chars or 3 ext chars, or an empty name, is REJECTED
;     (CF set) — truncation hides typos, so we error instead.
build_83_name:
                ; pre-fill the 11-byte field with spaces
                push    hl
                ld      hl,DISK_FCB_NAME
                ld      b,11
                ld      a,' '
bn_fill:
                ld      (hl),a
                inc     hl
                djnz    bn_fill
                pop     hl
                ; --- name part: up to 8 chars, until '.', '"', or NUL --------
                ld      de,DISK_FCB_NAME    ; DE -> name field write cursor
                ld      b,8                 ; max name chars remaining
bn_name:
                ld      a,(hl)
                cp      '"'
                jr      z,bn_done           ; end of filename, no extension
                or      a
                jr      z,bn_done           ; NUL (defensive) -> end
                cp      '.'
                jr      z,bn_ext            ; start of extension
                cp      '*'
                jr      z,bn_star_name      ; '*' -> fill the rest of the name with '?'
                ; another name char
                ld      c,a                 ; must consume even if field full
                ld      a,b
                or      a
                jr      z,bn_reject         ; >8 name chars -> reject
                ld      a,c
                call    fcb_upcase
                ld      (de),a
                inc     de
                inc     hl
                dec     b
                jr      bn_name
bn_ext:
                ; HL -> '.'; skip it, write up to 3 ext chars
                inc     hl
                ld      de,DISK_FCB_NAME + 8 ; DE -> ext field write cursor
                ld      b,3                 ; max ext chars remaining
bn_ext_loop:
                ld      a,(hl)
                cp      '"'
                jr      z,bn_done
                or      a
                jr      z,bn_done
                cp      '.'
                jr      z,bn_reject         ; a second '.' is malformed 8.3
                cp      '*'
                jr      z,bn_star_ext       ; '*' -> fill the rest of the ext with '?'
                ld      c,a
                ld      a,b
                or      a
                jr      z,bn_reject         ; >3 ext chars -> reject
                ld      a,c
                call    fcb_upcase
                ld      (de),a
                inc     de
                inc     hl
                dec     b
                jr      bn_ext_loop
bn_done:
                ; reject an empty name (e.g. "" or ".EXT" or "A:")
                ld      a,(DISK_FCB_NAME)
                cp      ' '
                jr      z,bn_reject         ; first name char still space -> empty
                or      a                   ; CF clear = success
                ret
bn_reject:
                scf
                ret

; bn_star_name / bn_star_ext — expand a '*' wildcard (FILES/KILL 8.3 pattern): fill
; the REMAINING positions of the current field (name = B left, or ext = B left) with
; '?', then swallow any source chars up to '.' / '"' / NUL (CP/M FCB '*' semantics:
; the rest of the field becomes '?', trailing chars before the separator are ignored).
; DE = field write cursor, B = positions left in the field, HL -> the '*'.
bn_star_name:
                call    bn_star_fill        ; DE[0..B) := '?'
bn_star_nskip:
                inc     hl                  ; skip source chars until '.', '"' or NUL
                ld      a,(hl)
                cp      '.'
                jr      z,bn_ext            ; extension follows
                cp      '"'
                jr      z,bn_done
                or      a
                jr      z,bn_done
                jr      bn_star_nskip
bn_star_ext:
                call    bn_star_fill        ; DE[0..B) := '?'
bn_star_eskip:
                inc     hl                  ; skip source chars until '"' or NUL
                ld      a,(hl)
                cp      '"'
                jr      z,bn_done
                or      a
                jr      z,bn_done
                jr      bn_star_eskip
; bn_star_fill — write '?' to (DE) B times (B may be 0 = field already full).
bn_star_fill:
                ld      a,b
                or      a
                ret     z                   ; field full -> nothing to fill
                ld      a,'?'
bsf_loop:
                ld      (de),a
                inc     de
                djnz    bsf_loop
                ret
