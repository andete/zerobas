; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; field.asm — random-access record fields (Phase 2c slice 1): FIELD / LSET / RSET.
;
; MSX random-access files partition a channel's fixed record buffer into named
; string "fields"; GET reads a record into that buffer and PUT writes it back
; (slice 2). FIELD declares the partitioning; LSET/RSET store a value into a field
; left/right-justified and space-padded; reading a fielded variable yields its
; current slice of the buffer.
;
; zerobas stores string variables INLINE in STRTAB ([name0][name1][len][bytes]) —
; it has NO MS-BASIC-style descriptor that could simply point into the record
; buffer. So a fielded variable is recorded in a SIDE TABLE (FLD_TAB): each entry
; maps a 2-char var key to a (channel, offset, width) slice. The record buffer is
; the channel's FSECTOR_BUF (the same 512-byte buffer the write-back cache swaps
; per channel, basic/files.asm §channel manager), so a field's bytes live in the
; channel's context and travel with it. Two hooks make a fielded variable behave:
;   * READ  — str_eval's variable path calls fld_lookup, which selects the field's
;             channel, copies the slice into FLD_DESC as a [len][bytes] descriptor,
;             and points STRPTR there (so PRINT/CVI/comparison see the live bytes).
;   * WRITE — LSET/RSET select the channel and copy a string into the slice.
;
; Clean-room: original code. Verb semantics (FIELD partitions a buffer; LSET left-
; justifies + space-pads, RSET right-justifies; a too-long value truncates from the
; right) follow the public MSX-BASIC language reference; the side-table layout is
; zerobas' own design (forced by the inline string store). Tokens are oracle-locked
; to the VG-8020 crunch (FIELD $B1, LSET $B8, RSET $B9). No disassembly. See
; basic/PROVENANCE.md §random-access records.
;
; Slice-1 scope / documented divergences (PROVENANCE.md):
;   * RANDOM open (OPEN "name" AS #n, no FOR) sets up a spaces-filled in-RAM record
;     buffer but does NOT yet open/create the file on disk — GET/PUT (the disk
;     record I/O) are slice 2. So a slice-1 RANDOM open is observable only through
;     FIELD/LSET/RSET + reading fielded vars, not on disk.
;   * LSET/RSET require a FIELDed target; on a non-fielded var they error (real
;     MSX-BASIC left-justifies into the var's current value — a Phase-3 nicety).
;   * a fielded READ takes precedence over a plain STRTAB value; assigning a fielded
;     name with plain LET does not "disconnect" the field (real MSX-BASIC does).
;   * field widths are 1..255; FIELD overflow past the record length is not checked.

; ===========================================================================
; Field-table primitives
; ===========================================================================

; fld_init — mark every field-table slot free (chan byte = 0). Clobbers A,B,DE,HL.
; Called at cold start (init_filechan) and on NEW/CLEAR/RUN (clear_vars).
fld_init:
                ld      hl,FLD_TAB
                ld      b,FLD_SLOTS
fldi_lp:
                ld      (hl),0              ; chan = 0 -> free slot
                ld      de,FLD_ENTSZ
                add     hl,de
                djnz    fldi_lp
                ret

; fld_clear_chan — free every field entry belonging to channel A (used when the
; channel is closed). A = channel. Clobbers A,B,C,DE,HL.
fld_clear_chan:
                ld      c,a                 ; C = channel to clear
                ld      hl,FLD_TAB
                ld      b,FLD_SLOTS
fldcc_lp:
                ld      a,(hl)              ; entry chan
                cp      c
                jr      nz,fldcc_next
                ld      (hl),0              ; matches -> free it
fldcc_next:
                ld      de,FLD_ENTSZ
                add     hl,de
                djnz    fldcc_lp
                ret

; fld_find — locate a field entry by variable key BC (B=name0, C=name1).
; out: CF set  -> found,     HL -> entry (chan byte).
;      CF clear -> not found.
; Clobbers A, DE, HL (BC preserved).
fld_find:
                ld      hl,FLD_TAB
fldf_lp:
                ld      a,(hl)              ; chan
                or      a
                jr      z,fldf_next         ; free slot -> skip
                inc     hl
                ld      a,(hl)              ; k0
                inc     hl                  ; HL -> k1
                cp      b
                jr      nz,fldf_back
                ld      a,(hl)              ; k1
                cp      c
                jr      nz,fldf_back
                dec     hl
                dec     hl                  ; HL -> chan (entry start)
                scf
                ret
fldf_back:
                dec     hl
                dec     hl                  ; back to chan
fldf_next:
                ld      de,FLD_ENTSZ
                add     hl,de
                ld      a,h
                cp      high FLD_TABEND
                jr      nz,fldf_lp
                ld      a,l
                cp      low FLD_TABEND
                jr      nz,fldf_lp
                or      a                   ; reached end -> CF clear (not found)
                ret

; fld_fill_record — fill the active channel's record buffer (FSECTOR_BUF, 512
; bytes) with spaces. Used by a RANDOM open so unwritten fields read as spaces.
; Clobbers A? no — only BC/DE/HL.
fld_fill_record:
                ld      hl,FSECTOR_BUF
                ld      de,FSECTOR_BUF+1
                ld      bc,511
                ld      (hl),' '
                ldir
                ret

; ===========================================================================
; FIELD #f, w1 AS v1$, w2 AS v2$, ...
; ===========================================================================
; HL = cursor at the FIELD token. Drops any prior fields on the channel, then walks
; the comma list assigning each variable a slice [running offset, width].
ex_field:
                inc     hl                  ; past the FIELD token
                call    skip_spaces
                ld      a,(hl)
                cp      '#'
                jr      nz,exf_havech
                inc     hl
exf_havech:
                call    eval                ; DE = channel; HL advanced
                ld      a,d
                or      a
                jp      nz,stmt_error       ; > 255 -> bad file number
                ld      a,e
                call    fch_valid
                jp      nc,stmt_error       ; 0 or > MAXF -> bad file number
                ld      a,e
                ld      (FLD_CHAN),a
                ; the channel must be open (FCH_MODES[ch] != 0).
                push    hl                  ; guard cursor across the array read
                ld      d,0
                ld      e,a
                ld      hl,FCH_MODES
                add     hl,de
                ld      a,(hl)
                pop     hl
                or      a
                jp      z,stmt_error        ; channel not open
                ; re-FIELD replaces: drop prior fields on this channel, offset = 0.
                push    hl
                ld      a,(FLD_CHAN)
                call    fld_clear_chan
                pop     hl
                xor     a
                ld      (FLD_CUROFF),a
                ld      (FLD_CUROFF+1),a
                ; a comma separates the channel from the field list: FIELD #f , w AS v$
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,stmt_error
                inc     hl
exf_item:
                call    skip_spaces
                call    eval                ; DE = field width; HL advanced
                push    de                  ; save width across the "AS" + name parse
                call    skip_spaces
                ld      a,(hl)              ; "AS" (verbatim ASCII, not tokenised)
                call    upcase
                cp      'A'
                jp      nz,exf_syn
                inc     hl
                ld      a,(hl)
                call    upcase
                cp      'S'
                jp      nz,exf_syn
                inc     hl
                call    skip_spaces
                call    is_letter           ; a string variable name?
                jp      nc,exf_syn
                call    var_str_type        ; A=1 if `$` suffix
                or      a
                jp      z,exf_syn           ; must be a string var
                call    var_name_key        ; BC = key; HL past name + `$`
                pop     de                  ; DE = width (E = width, D = 0 for w<=255)
                push    hl                  ; guard cursor across the table write
                call    fld_add             ; add [FLD_CHAN, BC, FLD_CUROFF, E]; bump offset
                pop     hl
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      z,exf_comma
                jp      exec_stmt           ; end of the field list
exf_comma:
                inc     hl                  ; past ',' -> next field item
                jr      exf_item
exf_syn:
                pop     de                  ; discard the saved width
                jp      stmt_error

; fld_add — append a field entry: chan=(FLD_CHAN), key=BC, offset=(FLD_CUROFF),
; width=E; then advance FLD_CUROFF by the width. Silently drops if the table is
; full (documented). Clobbers A,DE,HL (BC,E preserved through the write).
fld_add:
                push    de                  ; preserve the width (E)
                ld      hl,FLD_TAB
fadd_lp:
                ld      a,(hl)
                or      a
                jr      z,fadd_free
                ld      de,FLD_ENTSZ
                add     hl,de
                ld      a,h
                cp      high FLD_TABEND
                jr      nz,fadd_lp
                ld      a,l
                cp      low FLD_TABEND
                jr      nz,fadd_lp
                pop     de                  ; table full -> drop this field
                ret
fadd_free:
                pop     de                  ; E = width
                ld      a,(FLD_CHAN)
                ld      (hl),a              ; chan
                inc     hl
                ld      (hl),b              ; k0
                inc     hl
                ld      (hl),c              ; k1
                inc     hl
                ld      a,(FLD_CUROFF)
                ld      (hl),a              ; off lo
                inc     hl
                ld      a,(FLD_CUROFF+1)
                ld      (hl),a              ; off hi
                inc     hl
                ld      (hl),e              ; width
                ; FLD_CUROFF += width
                ld      hl,(FLD_CUROFF)
                ld      d,0                 ; add the 8-bit width only
                add     hl,de
                ld      (FLD_CUROFF),hl
                ret

; ===========================================================================
; LSET / RSET v$ = s$
; ===========================================================================
ex_lset:
                xor     a                   ; justify = left
                jr      lrset_common
ex_rset:
                ld      a,1                 ; justify = right
lrset_common:
                ld      (LRSET_JUST),a
                inc     hl                  ; past the LSET/RSET token
                call    skip_spaces
                call    is_letter
                jp      nc,stmt_error
                call    var_str_type        ; A=1 if `$`
                or      a
                jp      z,stmt_error        ; must be a string var
                call    var_name_key        ; BC = key; HL advanced past name + `$`
                push    hl                  ; guard cursor across the lookup
                call    fld_find            ; CF set -> HL -> entry
                jr      nc,lrset_notfld
                ld      a,(hl)              ; chan
                ld      (FLD_CHAN),a
                inc     hl
                inc     hl
                inc     hl                  ; -> off lo
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = off
                ld      (LRSET_OFF),de
                inc     hl
                ld      a,(hl)              ; width
                ld      (LRSET_W),a
                pop     hl                  ; restore cursor
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '='
                jp      nz,stmt_error
                inc     hl
                call    skip_spaces
                call    str_eval            ; STRPTR -> [len][bytes]; HL advanced
                jp      nc,stmt_error       ; RHS not a string operand
                push    hl                  ; guard cursor across select + store
                ld      a,(FLD_CHAN)
                call    fch_select          ; FSECTOR_BUF = this channel's record buffer
                call    lrset_store
                pop     hl
                jp      exec_stmt
lrset_notfld:
                pop     hl
                jp      stmt_error          ; LSET/RSET on a non-fielded var (slice-1 limit)

; lrset_store — copy the [len][bytes] string at STRPTR into the record-buffer field
; FSECTOR_BUF+(LRSET_OFF), width (LRSET_W), justify (LRSET_JUST). The field is first
; space-filled, then min(srclen,width) bytes are copied (left- or right-aligned);
; a longer source truncates from the right. Clobbers A,BC,DE,HL.
lrset_store:
                ld      hl,(LRSET_OFF)
                ld      de,FSECTOR_BUF
                add     hl,de               ; HL = field start
                ; space-fill the whole field
                push    hl
                ld      a,(LRSET_W)
                or      a
                jr      z,lrs_filled
                ld      b,a
lrs_fill:
                ld      (hl),' '
                inc     hl
                djnz    lrs_fill
lrs_filled:
                pop     hl                  ; HL = field start
                ld      de,(STRPTR)
                ld      a,(de)              ; source length
                ld      c,a                 ; C = source length
                inc     de                  ; DE -> source bytes
                ld      a,(LRSET_W)
                cp      c
                jr      nc,lrs_ncopy        ; width >= len -> copy len
                ld      c,a                 ; width < len -> copy width (truncate)
lrs_ncopy:
                ld      a,(LRSET_JUST)
                or      a
                jr      z,lrs_copy          ; left: dest = field start
                ; right: dest = field start + (width - ncopy)
                ld      a,(LRSET_W)
                sub     c
                add     a,l
                ld      l,a
                jr      nc,lrs_copy
                inc     h
lrs_copy:
                ld      a,c
                or      a
                ret     z                   ; nothing to copy
                ld      b,c
lrs_cp:
                ld      a,(de)
                ld      (hl),a
                inc     de
                inc     hl
                djnz    lrs_cp
                ret

; ===========================================================================
; fld_lookup — READ hook for str_eval's variable path.
; in:  BC = variable key.
; out: CF set  -> BC is fielded; STRPTR -> FLD_DESC holds the slice [len][bytes].
;      CF clear -> not fielded (caller falls back to str_get_key). BC may be clobbered.
; Clobbers A,BC,DE,HL; preserves IX (fch_select is LDIR-only for a RANDOM channel).
; ===========================================================================
fld_lookup:
                call    fld_find            ; CF set -> HL -> entry
                ret     nc
                ld      a,(hl)              ; chan
                ld      (FLD_CHAN),a
                inc     hl
                inc     hl
                inc     hl                  ; -> off lo
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = off
                inc     hl
                ld      a,(hl)              ; width
                ld      (FLD_DESC),a        ; descriptor length = width
                push    de                  ; save offset
                push    af                  ; save width
                ld      a,(FLD_CHAN)
                call    fch_select          ; FSECTOR_BUF = this channel's record buffer
                pop     af                  ; A = width
                pop     de                  ; DE = offset
                ld      hl,FSECTOR_BUF
                add     hl,de               ; HL = slice start
                ld      de,FLD_DESC+1       ; DE = descriptor bytes
                or      a
                jr      z,fll_done          ; width 0 -> empty
                ld      b,a
fll_cp:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                djnz    fll_cp
fll_done:
                ld      hl,FLD_DESC
                ld      (STRPTR),hl
                scf
                ret
