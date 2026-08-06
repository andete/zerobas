; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fldlook.asm -- the FIELDed-variable READ hook as a PAGE-0 sub-ROM tenant
; (SUBROM_IDX_FLDLOOK). docs/decision-clearpool-funding.md §6.1 -- the D-CLP
; funding carve.
;
; Clean-room: zerobas's own code, promoted verbatim out of the main ROM's
; FIELD/string layer to fund the CLEAR string-pool partition. Nothing here is
; derived from a disassembly or byte-copy of any reference ROM.
; Basis: basic/PROVENANCE.md.
;
; WHY THIS ONE. The CLEAR string-pool partition (docs/spec-basic-clearpool.md)
; measured 25 B of main page 1 against 3 B free -- a 22 B shortfall -- and
; clone_scout.py reports ZERO clone groups, so the only lever left is a
; promotion to the sub-ROM. Of the corrected viable set (funding doc §4a),
; fld_lookup is the one with a SINGLE caller (basic/strvar.asm str_eval_one),
; no timing gate, no ISR context and no boot-ordering dependency. `tok_skip` is
; the same size class but its two callers (if_skip_to_else, skip_to_eol) are
; per-token LOOPS -- a CALSLT inside those would be paid once per token of every
; line walked, which is not a trade worth making.
;
; PAGE-0 CLEAN, and the seam is what makes it so. The resident routine's own
; closure had three callees: fld_find + fch_select (main page 1 -- legal for a
; page-0 tenant, but the sub-ROM has no import mechanism for main PAGE-1
; addresses; sub/basic-resident-abi.inc is ceiling-checked to < $4000 because it
; exists for page-1 tenants calling the low region) and mk_rvdesc (main LOW
; REGION -- switched out under a page-0 CALSLT, so a hard blocker).
; So the carve is SPLIT AT THE TABLE LOOKUP rather than at the routine boundary:
;   * the resident stub keeps `call fld_find` and `call fch_select` -- both are
;     shared services with other callers that must stay resident anyway
;     (fld_find for LSET/RSET, fch_select for the whole file-channel surface),
;     so keeping them costs the carve nothing;
;   * the tenant takes the located entry pointer in HL and does the part that is
;     a pure RAM leaf: read [off:2][width:1], copy the slice out of FSECTOR_BUF
;     into FLD_DESC, and wrap it as an RVDESC rvalue descriptor.
; mk_rvdesc's three instructions are INLINED here (10 B) rather than imported --
; duplicating a 4-instruction RAM-cell store is cheaper and less fragile than a
; second generated address-import file, and RVDESC's contract (one shared cell,
; consumed immediately) is unchanged by which side writes it.
;
; NOTHING MARSHALS THROUGH RAM. The entry pointer rides in HL, which subrom_call
; passes straight through CALSLT (the same path tokenise's HL=src uses). The
; result is the STRPTR sysvar the resident routine already set, so there is no
; return value to smuggle past subrom_call's CF (which means "sub-ROM absent",
; not "found"); the stub re-asserts the found-CF itself, since it -- not the
; tenant -- is the one that knows fld_find succeeded.
;
; COLD ENOUGH. This runs once per read of a FIELDed variable, i.e. per
; random-access record field touched by an expression -- already downstream of a
; 512-byte fch_select LDIR pair when the channel changes. One CALSLT round trip
; (~100 T) is noise against that.

; --- fld_lookup_tenant -----------------------------------------------------
; in:  HL -> the field-table entry located by the resident stub's fld_find:
;            [chan:1][k0:1][k1:1][off:2][width:1] (FLD_ENTSZ, basic/sysvars.inc).
;            The stub has ALREADY run fch_select on the entry's channel, so
;            FSECTOR_BUF holds that channel's record buffer.
; out: FLD_DESC := [width][the slice's bytes]; RVDESC := [width][ptr FLD_DESC+1];
;      STRPTR -> RVDESC. No failure mode (a located entry always has a slice;
;      width 0 yields an empty string, exactly as the resident routine did).
; Clobbers AF,BC,DE,HL.
fld_lookup_tenant:
                inc     hl
                inc     hl
                inc     hl                  ; -> off lo (past chan,k0,k1)
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = off
                inc     hl
                ld      a,(hl)              ; width
                ld      (FLD_DESC),a        ; descriptor length = width
                ld      hl,FSECTOR_BUF
                add     hl,de               ; HL = slice start
                ld      de,FLD_DESC+1       ; DE = descriptor bytes
                or      a
                jr      z,flt_done          ; width 0 -> empty
                ld      b,a
flt_cp:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                djnz    flt_cp
flt_done:
                ; FLD_DESC stays a fixed inline [len][bytes:255] buffer (never in
                ; the heap, arrays slice-4a spec §5.2) -- wrap it as a [len][ptr]
                ; rvalue descriptor in the shared RVDESC. This is basic/str-
                ; engine.asm `mk_rvdesc` INLINED: that routine is main low region,
                ; which a page-0 CALSLT switches out. Safe as one shared cell for
                ; the same reason it always was -- fld_lookup's result is consumed
                ; immediately by str_eval_one's caller.
                ld      a,(FLD_DESC)
                ld      hl,FLD_DESC+1
                ld      (RVDESC),a          ; RVDESC.len
                ld      (RVDESC+1),hl       ; RVDESC.ptr = the descriptor bytes
                ld      hl,RVDESC
                ld      (STRPTR),hl
                ret
