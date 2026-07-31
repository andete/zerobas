; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

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
; GET/PUT (slice 2) add the on-disk record I/O. The record length is `reclen`,
; per channel — 256 by default (oracle: a CF-3300 PUT of one record makes a
; 256-byte file), or the OPEN..AS #n LEN=r value (disk-BASIC option-closure Item 3;
; parsed in files.asm, held in FCH_RECLENS[ch], loaded into GP_RECLEN per calc).
; r is constrained to a power of two in 1..256 so records TILE the 512-byte sector
; (512/r per sector) and never straddle two sectors. Record N (1-based) occupies
; file bytes [(N-1)*reclen, N*reclen), i.e. file logical sector ((N-1)*reclen)>>9 at
; within-sector offset ((N-1)*reclen)&511 (frnd_calc) — 512/reclen records per
; 512-byte sector (r=256 -> the historical two per sector). PUT does a
; read-modify-write of the sector (preserving the other records) and extends the
; cluster chain when the record lies beyond the current end; GET reads the sector and
; copies the record into the buffer. The buffer choreography keeps the live record in
; FSECTOR_BUF and uses FWBUF for everything else (FAT metadata during allocation, then
; the data sector, then the dir update) — never both at once, so the record survives a
; chain walk. The walk reuses fat_read_fat_sector (FWBUF), NOT fat_next_cluster (which
; reads FAT into FSECTOR_BUF and would clobber the record). fat.asm is untouched.
;
; Scope / documented divergences (PROVENANCE.md):
;   * LSET/RSET require a FIELDed target; on a non-fielded var they error (real
;     MSX-BASIC left-justifies into the var's current value — a Phase-3 nicety).
;   * a fielded READ takes precedence over a plain STRTAB value; assigning a fielded
;     name with plain LET does not "disconnect" the field (real MSX-BASIC does).
;   * field widths are 1..255; FIELD overflow past the record length is not checked.
;   * record numbers are 1..255 (file < 64 KB — the same 16-bit size ceiling the
;     loader text path documents); bare GET/PUT (no record number) default to record
;     1 — the auto-incrementing "current record" is not tracked.
;   * sparse / out-of-order PUT (writing record M before some earlier record exists)
;     leaves the skipped records' bytes undefined; in-order writes are well-defined.

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

; fld_fill_record — moved whole to sub/randio.asm (docs/spec-eviction-g4-
; space.md §3, carve #1): its only caller, fat_rand_open, is itself sub-side
; now (see below), so no resident shim is needed for the repack build.

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
                ; the channel must be open, and open RANDOM. D-NOTOPEN2: this was a
                ; fourth hand-inlined copy of fch_mode_class -- which ALSO returns
                ; CF = disk-vs-device, exactly the 61-vs-5 split measured below.
                push    hl                  ; guard cursor across the classify
                call    fch_mode_class      ; A = FCH_MODES[E]; ERR 59 if NOT OPEN
                pop     hl
                jr      nc,exf_dev          ; device channel (LPT:/CRT:) -> ERR 5
                cp      4
                jr      nz,exf_bfm          ; a disk channel must be RANDOM -> ERR 61
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
; D-NOTOPEN2 §3.1: FIELD on an open channel that is not RANDOM. Until this slice
; ex_field tested only "open at all", so `OPEN "X" FOR INPUT AS #1 : FIELD #1,…`
; was accepted SILENTLY -- measured `0` (nothing raised) against the CF-3300's
; ERR 61. ⚠️ The device answer is 5, NOT the 58 that GET/PUT give on the very same
; LPT: channel; `wm_lpt_fld` and `wm_lpt_get` are the pair that pins that apart.
exf_dev:
                ld      a,5                 ; illegal function call (LPT:/CRT:)
                jr      exf_raise
exf_bfm:
                ld      a,61                ; bad file mode (disk, not RANDOM)
exf_raise:
                jp      raise_error         ; no `pop hl` -- raise_error resets SP on
                                            ; BOTH arms (trap and abort)

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
                push    hl                  ; guard field start
                ld      h,d
                ld      l,e                 ; HL = source descriptor addr
                call    pu_deref_body       ; HL -> source bytes (arrays
                                            ; slice-4a; shared with
                                            ; printusing.asm — page 1 has no
                                            ; slack for a 3rd duplicate)
                ex      de,hl               ; DE = source bytes
                pop     hl                  ; HL = field start (restored)
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
; out: CF set  -> BC is fielded; STRPTR -> the slice descriptor.
;      CF clear -> not fielded (caller falls back to str_get_key). BC may be clobbered.
; Clobbers A,BC,DE,HL.
; ===========================================================================
; --- repack: a resident stub over the SUBROM_IDX_FLDLOOK page-0 tenant ------
; docs/decision-clearpool-funding.md §6.1 — the D-CLP funding carve. The body
; (60 B of main page 1) moved whole to sub/fldlook.asm; this stub is 22 B, so
; the carve returns 38 B, against D-CLP's measured 22 B requirement.
;
; THE SEAM IS THE TABLE LOOKUP, not the routine boundary, and that is what makes
; the tenant legal: `fld_find` and `fch_select` are main PAGE-1 routines (fine to
; call from a page-0 tenant in principle, but the sub-ROM has no import mechanism
; for main page-1 addresses — sub/basic-resident-abi.inc is ceiling-checked to
; < $4000 because it exists for the opposite direction), and the old body's third
; callee `mk_rvdesc` is main LOW REGION, which a page-0 CALSLT switches out
; outright. Keeping the two lookups resident costs the carve nothing: both are
; shared services with other callers (fld_find for LSET/RSET, fch_select for the
; whole file-channel surface), so neither could have moved anyway. What crosses
; is the pure RAM leaf — slice copy + descriptor build — and mk_rvdesc's three
; instructions are inlined sub-side.
;
; The located entry pointer rides in HL, which subrom_call passes straight
; through CALSLT (the same path `tokenise`'s HL=src uses); nothing marshals
; through RAM. subrom_call's CF means "sub-ROM absent", never "found", so the
; stub asserts the found-CF itself — it is the side that ran fld_find.
;
; IX is clobbered here where the old body preserved it. That is safe at the one
; call site: str_eval_one's OTHER branch on the same variable path is
; `call str_get_key`, which reaches `ary_engine_call` and clobbers IX already.
fld_lookup:
                call    fld_find            ; CF set -> HL -> entry
                ret     nc                  ; not fielded -> caller's str_get_key
                ld      a,(hl)              ; chan
                push    hl                  ; guard the entry across the select
                call    fch_select          ; FSECTOR_BUF = this channel's record buffer
                pop     hl                  ; HL = entry (the tenant's only arg)
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_FLDLOOK
                call    subrom_call         ; fills FLD_DESC/RVDESC, sets STRPTR
                jp      c,subrom_absent_error
                scf                         ; fielded
                ret

; --- repack: resident shims replacing the fat_rand_* engine ----------------
; docs/spec-eviction-g4-space.md §3 (carve #1). Bodies moved whole to sub/
; randio.asm (fatprim.asm's fp_table extended with 3 new selector rows,
; DISKOP_SEL_RAND_OPEN/GET/PUT = 15/16/17 -> t_fat_rand_open/get/put). These
; shims keep the ORIGINAL names + calling convention (Cy-only; no caller
; reads HL/A back from any of the three) so files.asm's `call fat_rand_open`
; and gp_common's `call fat_rand_put`/`call fat_rand_get` call sites are
; unchanged.
;
; SWAP-funding carve (2026-07-28): these three were three byte-identical 20 B
; copies of one body differing only in the selector immediate — 60 B saying one
; thing three times, and tools/clone_scout.py's top row. They now bounce off
; `fatprim_bounce` (basic/fat.asm), the shared body the FAT tenant-shim collapse
; (6f8ac0f) already built for exactly this shape, so the whole carve is three
; two-instruction heads: 60 B -> 15 B.
;
; ⚠️ WHY THE SHARED BODY IS SAFE HERE, and it is NOT the same contract.
; `fatprim_bounce` ends with two extra FLAG-TRANSPARENT reloads the old bodies
; did not have — `ld hl,(DISKOP_HL)` and `ld a,(DISKOP_A)` — so it CLOBBERS HL
; (which the old bodies preserved) and returns a DIFFERENT A (DISKOP_A, stale
; for a randio op, where the old bodies left DISKOP_STATUS). Cy/Z are unchanged,
; which is the whole contract these three callers use. Both call sites were
; re-read before this carve, not assumed from the header line above:
;   * gp_common (below) `push hl` … `pop hl` around the call and then tests
;     `jp c,load_error` only;
;   * files.asm oo_random_setup falls into `oo_done`, which `pop de`/`pop hl`
;     and tests Cy, then RELOADS A from E — and that same `oo_done` tail is
;     already shared with fat_io_create/fat_io_append, which route through
;     `fatprim_bounce` themselves. So HL/A clobber is already the norm there.
; If a future caller of these three ever needs HL or A back, it needs its own
; tail (the `name_cmp`/`fat_count_free` pattern in fat.asm), not this bounce.
fat_rand_open:
                ld      a,DISKOP_SEL_RAND_OPEN
                jp      fatprim_bounce
fat_rand_put:
                ld      a,DISKOP_SEL_RAND_PUT
                jp      fatprim_bounce
fat_rand_get:
                ld      a,DISKOP_SEL_RAND_GET
                jp      fatprim_bounce

; ===========================================================================
; GET [#]f [, recno]   /   PUT [#]f [, recno]
; ===========================================================================
; Select the channel (must be open RANDOM), then read/write the record. The text
; cursor (HL) is guarded across fch_select + the disk op (CALSLT clobbers all).
ex_put:
    IF G7_RESIDENT
                ; `PUT SPRITE ...` is a graphics statement, not a record write --
                ; two reserved words (PUT $B3 + SPRITE $C7), disambiguated at RUN
                ; time on the token that follows (basic/graphics.asm ex_put_sprite).
                push    hl
                inc     hl
                call    skip_spaces
                ld      a,(hl)
                cp      SPRITE_TOKEN
                jp      z,pus_is_sprite
                pop     hl
    ENDIF
                ld      a,1                 ; mode = PUT (write)
                jr      gp_common
    IF G7_RESIDENT
pus_is_sprite:
                pop     af                  ; drop the guarded PUT-token cursor
                jp      ex_put_sprite       ; HL is ON the SPRITE token
    ENDIF
ex_get:
                xor     a                   ; mode = GET (read)
gp_common:
                ld      (GP_MODE),a
                inc     hl                  ; past the GET/PUT token
                call    skip_spaces
                ld      a,(hl)
                cp      '#'
                jr      nz,gp_nochan
                inc     hl
gp_nochan:
                call    eval                ; DE = channel
                ld      a,d
                or      a
                jp      nz,stmt_error
                ld      a,e
                call    fch_valid
                jp      nc,stmt_error
                ld      a,e
                ld      (GP_CHAN),a
                ; optional ", recno" (else default record 1)
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,gp_defrec
                inc     hl
                call    eval                ; DE = record number
                jr      gp_haverec
gp_defrec:
                ld      de,1
gp_haverec:
                ld      (GP_RECNO),de
                push    hl                  ; guard cursor across select + disk op
                ; the channel must be open RANDOM (FCH_MODES[ch] == 4). D-NOTOPEN2:
                ; the old `cp 4` conflated THREE conditions the reference separates --
                ; not open (59), open-but-not-RANDOM (61), device channel (58).
                ld      a,(GP_CHAN)
                ld      e,a
                call    fch_mode_class      ; ERR 59 if NOT OPEN; CF set = disk channel
                jr      nc,gp_dev           ; LPT:/CRT: -> ERR 58 sequential i/o only
                cp      4
                jr      nz,gp_bfm           ; a disk channel must be RANDOM -> ERR 61
                ld      a,(GP_CHAN)
                call    fch_select          ; FSECTOR_BUF + FWR_* = this channel's state
                ld      a,(GP_MODE)
                or      a
                jr      z,gp_doget
                call    fat_rand_put
                jr      gp_fin
gp_doget:
                call    fat_rand_get
gp_fin:
                pop     hl
                jp      c,load_error        ; disk error
                jp      exec_stmt
gp_dev:
                ld      a,58                ; sequential i/o only (LPT:/CRT:)
                jr      gp_raise
gp_bfm:
                ld      a,61                ; bad file mode (disk, not RANDOM)
gp_raise:
                jp      raise_error         ; no `pop hl` -- raise_error resets SP
