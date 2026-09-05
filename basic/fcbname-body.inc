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
;   - more than 8 name chars: the extension starts THERE, positionally (D-FSPEC,
;     measured: `TOOLONGNAME.BAS` -> `TOOLONGN.AME` on both references)
;   - more than 3 ext chars: the remainder is IGNORED (`AB.EXTRA` -> `AB.EXT`)
;   - a SECOND '.' while the extension is still filling, or an empty name, is
;     REJECTED (CF set) — the caller raises `Bad file name` (ERR 56)
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
                call    bn_chk              ; D-FSPECCHAR: the illegal set
                jr      c,bn_reject
                ld      c,a                 ; must consume even if field full
                ld      a,b
                or      a
                ; 🔴 D-FSPEC: A FULL NAME IS NOT A REJECT -- IT IS WHERE THE
                ; EXTENSION STARTS. Measured by writing (SAVE names the file it
                ; creates): `SAVE"TOOLONGNAME.BAS"` creates **TOOLONGN.AME** on
                ; both references -- 8 characters of name, then the NEXT THREE
                ; POSITIONALLY, with the dot neither required nor consumed once
                ; the name is full. ⚠️ The '.' test above comes FIRST and must
                ; stay there: `ABCDEFGH.IJK` has a dot exactly at position 8 and
                ; must take the normal separator path, not have the dot land in
                ; the extension field.
                jr      z,bn_ext_pos        ; name full -> extension, positionally
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
bn_ext_pos:                                 ; ...or entered with NO dot at all,
                                            ; HL already on the first ext char
                                            ; (the name-full path above)
                ld      de,DISK_FCB_NAME + 8 ; DE -> ext field write cursor
                ld      b,3                 ; max ext chars remaining
bn_ext_loop:
                ld      a,(hl)
                cp      '"'
                jr      z,bn_done
                or      a
                jr      z,bn_done
                ; 🔴 D-FSPEC: THE FULL TEST COMES BEFORE THE '.' TEST, AND THE
                ; ORDER IS THE WHOLE OF `TOOLONGNAME.BAS`. Once three extension
                ; characters are in, everything left is IGNORED -- including a
                ; dot, which is what that name has after `AME`. With the tests
                ; the other way round the leftover `.BAS` reads as a second dot
                ; and the name is rejected, which is what this code did before.
                ld      a,b
                or      a
                jr      z,bn_skip           ; ext full -> swallow the rest (NOT
                                            ; an error: `AB.EXTRA` -> `AB.EXT`)
                ld      a,(hl)
                cp      '.'
                jr      z,bn_reject         ; a second '.' WHILE STILL FILLING is
                                            ; malformed -- `A.B.C` is `Bad file
                                            ; name` on the reference
                cp      '*'
                jr      z,bn_star_ext       ; '*' -> fill the rest of the ext with '?'
                call    bn_chk              ; D-FSPECCHAR: the illegal set
                jr      c,bn_reject
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
bn_skip:
                ; the 8.3 field is full; consume the rest of the quoted name and
                ; report success. D-FSPEC measured both overflow forms as SILENT
                ; on the reference -- `SAVE"AB.EXTRA"` creates `AB.EXT` and
                ; `SAVE"TOOLONGNAME.BAS"` creates `TOOLONGN.AME`, no error either.
                ld      a,(hl)
                cp      '"'
                jr      z,bn_done
                or      a
                jr      z,bn_done
                inc     hl
                jr      bn_skip
bn_reject:
                scf
                ret

; --- bn_chk: is this byte legal in an 8.3 field? (D-FSPECCHAR, 2026-09-05) ----
; in:  A = the candidate byte.   out: CF SET if the byte is ILLEGAL. A preserved
; (neither `cp` nor `cpir` writes it), DE untouched, BC/HL saved across.
;
; The domain is MEASURED, not assumed: `scratchpad/fspecchar_probe.py` swept 47
; byte values as `FILES CHR$(n)+"BC.TXT"` on the CF-3300 and here. The reference
; refuses the whole $01..$1F control band, the nine separators below, and $FF,
; and ACCEPTS everything else -- letters upper and lower, digits, and
; `! # $ % & ' ( ) - < > ? @ ^ _ ` { | } ~`, $7F and $80.
;
; ⚠️ TWO READINGS THAT LOOK LIKE RULES AND ARE NOT, both measured:
;   * $80 is ACCEPTED while $FF is REFUSED, so this is NOT a high-bit test and
;     must not be written as one.
;   * `<` and `>` are BOTH accepted -- they are not a separator pair here.
;
; ⚠️ AND FOUR BYTES ARE ALREADY DISPOSED BEFORE THIS IS REACHED, which is why
; they are absent from the table: `"` and NUL are TERMINATORS, `.` is the 8.3
; SEPARATOR, and a leading space is caught by bn_done's empty-name test. Putting
; any of them here would change a terminator into a reject.
bn_chk:
                cp      ' '
                ret     c                   ; $01..$1F -> CF set by the compare
                push    bc
                push    hl
                ld      hl,bn_badchars
                ld      bc,BN_NBAD
                cpir                        ; Z if A is in the table (A untouched)
                pop     hl
                pop     bc
                scf
                ret     z                   ; illegal
                or      a                   ; legal -> CF clear
                ret
bn_badchars:
                db      '+', ',', '/', ':', ';', '=', '[', $5C, ']', $FF
BN_NBAD         equ     10

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
