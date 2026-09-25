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
; zerobas stores a string variable as a [len:1][ptr:2] descriptor in the unified
; variable chain (arrays slice-4c; an array ELEMENT slot is the identical 3-byte
; shape) — it has NO MS-BASIC-style descriptor that a FIELD could simply re-point
; into the record buffer, because the ptr is a string-HEAP root that the GC owns.
; ⚠️ This header said "INLINE in STRTAB ([name0][name1][len][bytes])" until
; D-LRVAR; that was the PRE-slice-4c layout and reading it is what made a
; non-FIELDed LSET look like two different stores (docs/spec-basic-lrvar.md §5.1).
; So a fielded variable is recorded in a SIDE TABLE (FLD_TAB): each entry
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
;   * (closed by D-LRVAR 2026-08-08) LSET/RSET no longer require a FIELDed target:
;     a non-fielded one is overwritten IN PLACE at its CURRENT length, space-padded
;     and left/right-justified, a longer source keeping its first len(target) bytes
;     — all measured on the CF-3300, docs/spec-basic-lrvar.md §1.
;   * a fielded READ takes precedence over a plain STRTAB value; assigning a fielded
;     name with plain LET does not "disconnect" the field (real MSX-BASIC does).
;   * (corrected by D-FLDWIDTH 2026-08-08) field widths are **0..255**, not
;     1..255: the CF-3300 accepts `FIELD#1,0 AS A$` and reports LEN(A$) = 0
;     (row d.zero). The old claim was this file's own invention and a fix built
;     on it would have shipped a divergence -- see docs/spec-basic-fldwidth.md
;     §1. The domain is now enforced by get_byte_arg at field_item (ERR 6 past
;     int16, ERR 5 outside 0..255), which is the reference's own two-stage rule.
;   * (closed by D-RECLEN) FIELD overflow past the RECORD LENGTH raises ERR 50.
;     ⚠️ THIS BULLET SAID "still not checked -- DECLINED with numbers" UNTIL
;     D-FIELDMOVE, while the check stood ~30 lines below it at field_item: the
;     price it quoted (~27 B against a 6 B page-1 wall) was real when written and
;     the carve that paid for it never came back here. The bound is
;     FCH_RECLENS[ch] and NOT a constant 256 -- row r.mid FIELDs a width of 200
;     into a LEN=64 record and the CF-3300 refuses it, which no default-256 row
;     could ever separate (docs/spec-basic-fldwidth.md §6.5 addendum).
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
; D-FLDARY — an ARRAY ELEMENT as a FIELD / LSET / RSET target
; (docs/spec-basic-fldary.md §4.1/§4.2)
; ===========================================================================
; Both parse sites below used to `call var_name_key` and use the 2-byte NAME key
; verbatim, so a `(` after the name stopped the cursor dead and the statement was
; `Syntax error` (measured, CF-3300: `FIELD#1,10 AS A$(1)` is `OK` there).
;
; 🎯 THE TABLE DOES NOT CHANGE, AND THAT IS THE WHOLE PRICE DIFFERENCE. D-LVFIX
; §7 declined this pair partly because an element needs a stable discriminator
; BESIDE the name key -- FLD_ENTSZ 6 -> 8, i.e. 128 B into the 96 B hole below
; GP_RECNO, costing FLD_SLOTS 16 -> 12 or 32 B of rehomed RAM. It costs neither,
; because the discriminator does not have to sit beside the key: IT CAN BE THE
; KEY. fld_find matches on (k0,k1) alone, so an element entry stores
;   k0 = ((elem_addr - ARYTAB) >> 8) | $80 ,  k1 = (elem_addr - ARYTAB) & $FF
; and a scalar entry stores today's name key. fld_init / fld_clear_chan /
; fld_find / fld_add / fld_lookup and the sub/fldlook.asm page-0 tenant are all
; UNTOUCHED; FLD_ENTSZ stays 6, FLD_SLOTS stays 16, no RAM grows and the tenant
; ABI (basic/PROVENANCE.md §random-access records) does not move.
;
; 🔴 THE TWO KEY SPACES ARE DISJOINT BY CONSTRUCTION, AND THE PROOF IS AN ASSERT.
; A scalar's k0 is the UPCASED FIRST CHARACTER of a name whose is_letter every
; caller has already checked, so k0 is $41..$5A -- always < $80. An element's k0
; is >= $80 iff the ARYTAB-relative offset fits 15 bits, and the variable region
; is bounded below by TXTBASE ($8001) and above by min(HIMEM,TXTMAX) = TXTMAX
; ($BB00): at most 15103 B, a factor of 2.17 inside the bound. That is a fact
; about the MEMORY MAP, not about this code, so it is checked at assembly time
; right here rather than assumed.
;
; ⚠️ `set 7,h` IS NOT FALSIFIABLE BY ANY ROW, and that is stated rather than
; defended (spec §4.2). Without it the spaces are STILL disjoint today, because
; offset>>8 <= $3A < $41; a colliding program needs an array-region offset of at
; least $4100 = 16640 B, which the 15103 B ceiling forbids. The two bytes buy the
; margin from 1.1x to 2.17x and survive a memory-map change the bare `< $41`
; argument would not. Its knife is the ASSERT below (spec §8 K-FA7), not a row.
    IF (TXTMAX - TXTBASE) > $7FFF
                db      FLD_ELEMENT_KEY_BIT15_NOT_FREE__ARRAY_REGION_MAY_EXCEED_32K
    ENDIF

; --- tgt_parse_fld: parse an lvalue target -> its FLD_TAB key ---------------
; in:  HL = cursor at the name's first letter (the caller has already checked
;           is_letter); A = var_str_type's mode, exactly as tgt_parse wants it.
;           🎯 BOTH call sites already hold it: each does `call var_str_type` /
;           `or a` / `jp z,<syntax>`, which leaves A = 1.
; out: BC = the key to add/match; HL = cursor past the whole reference (past `)`
;      for an element). A failed array resolve does NOT return (spec §5.3).
; Clobbers A,BC,DE (and HL, which is the advanced cursor).
tgt_parse_fld:
                call    tgt_parse_req      ; BC=key, (TGT_ADDR)=elem addr or 0
                                           ; FPERR already mapped by
                                            ; ary_op0_resolve -> the reference's
                                            ; own `Subscript out of range`.
                                            ; 🎯 FALSIFIABLE here, unlike D-LVFIX's
                                            ; two aborts: exec_stmt CLEARS FPERR at
                                            ; the statement boundary (interp.asm)
                                            ; and ex_field runs no check between,
                                            ; so cutting this makes FIELD..A$(9)
                                            ; print OK. Spec §8 K-FA5.
                                            ; ⚠️ D-STMTPEND (spec-basic-stmtpend.md
                                            ; §6.3): THE PREMISE OF THAT SENTENCE IS
                                            ; GONE. exec_stmt no longer clears the
                                            ; cell -- it READS it and raises -- so a
                                            ; cut here falls through to a report,
                                            ; not to silence. This abort still earns
                                            ; its place because it raises BEFORE
                                            ; ex_field's side effects, which the
                                            ; statement boundary is by construction
                                            ; too late for. What K-FA5 now reads is
                                            ; UNMEASURED and filed in TODO.md; it is
                                            ; not predicted here.
                ld      de,(TGT_ADDR)
                ld      a,d
                or      e
                ret     z                   ; scalar: BC is already the name key
                                            ; fall through with DE = elem addr

; --- fld_key_de: DE = an element address -> BC = its FLD_TAB key ------------
; Preserves HL (the caller's text cursor -- both parse sites need it, and so does
; nothing at the read hook, which simply does not care). Clobbers A, DE.
; 🔴 ARYTAB-RELATIVE, NOT ABSOLUTE (spec §5.1): a FIELD and the LSET that uses it
; are different statements, and every scalar allocation in between moves the
; whole array region up (arrays slice-4b §13a). ARYTAB moves by the same delta,
; so the offset is invariant under it -- and under a new DIM (arrays append
; above) and under a string GC (which compacts bodies, not element slots).
; ⚠️ NOT invariant under ERASE, which compacts the descriptor list. A named limit
; with a price and no oracle -- spec §5.4.
fld_key_de:
                push    hl                  ; guard the caller's cursor
                ex      de,hl               ; HL = the element address
                ld      de,(ARYTAB)
                or      a                   ; (A is d|e, non-zero; this clears CF)
                sbc     hl,de               ; HL = ARYTAB-relative offset
                set     7,h                 ; -> the half of the key space no
                                            ; var_name_key key can reach
                ld      b,h
                ld      c,l
                pop     hl
                ret

; ===========================================================================
; FIELD #f, w1 AS v1$, w2 AS v2$, ...
; ===========================================================================
; HL = cursor at the FIELD token. Drops any prior fields on the channel, then walks
; the comma list assigning each variable a slice [running offset, width].
; 🔴 D-FLDGATE (2026-09-15): THE DISK-PRESENCE GATE. Measured on four sides
; (D-NODISKGAP): the diskless VG-8020 answers ERR 5 to `FIELD` and to
; `FIELD#1,2 AS A$`, where this tree answered 24 and 59 -- the CHANNEL's own
; errors, because nothing here asked whether a disk ROM exists. The zb-DISK
; column already matched the CF-3300 on both forms, so the VERB was never wrong;
; only the diskless target was.
; ⚠️ THE GATE COMES BEFORE THE PARSE, as it does for every other disk verb: the
; reference answers ERR 5 to the BARE form too, so a malformed FIELD must not
; reach its own syntax error first on a machine that has no disk ROM at all.
; 💰 It waited on bytes -- main page 1 had 3 B free on 2026-09-15 -- and the
; hook re-architecture (D-DISKVERB..D-DISKVERB4) is what paid for it.
; 🏗️ D-FIELDMOVE (Joost, 2026-09-17/18). The body is in disk.rom as `hk_field`;
; what is left here is the hand-off, the gate and the resume — plus TWO BUNDLES
; the handler calls back into. Same ruling as LSET/RSET, same reason: a gate-only
; hook is a PRESENCE TEST, and main redoing the work after it discards the answer
; a claiming ROM just gave.
; 🎯 AND FIELD IS THE EXTREME CASE OF THE ACCOUNTING IN spec-diskcode-eviction.md
; §7.3: essentially NONE of this statement is disk work. It is a parse, a channel
; classify and a write into FLD_TAB — and FLD_TAB is main's table by the rule
; Joost set, so the entry shape stays in one file. What crosses is the DECISION
; to run, which is the whole point: correctness, not bytes.
; ⚠️ THE CURSOR CROSSES IN FN_RESUME, NOT IN HL, and every bundle reads it and
; writes it back — so the `push hl`/`pop hl` pairs that used to guard it across
; fch_mode_class and fld_clear_chan are still LOCAL to a bundle. A push that
; straddles a calbak would straddle a CALSLT.
ex_field:
                inc     hl                  ; past the FIELD token
                ld      (FN_RESUME),hl      ; the handler's cursor
                ld      hl,H_FIELD
                call    chan_gate_bare      ; unclaimed -> ERR 5, trappable.
                                            ; BARE: this verb WRITES the
                                            ; channel's record, so the full
                                            ; gate's restore would undo it
                ld      hl,(FN_RESUME)      ; where the handler left it
                jp      exec_stmt

; --- field_prologue: call-back 1 -- the channel, its mode, and the reset -----
; in:  FN_RESUME = the cursor, just past the FIELD token.
; out: FLD_CHAN = the channel, FLD_CUROFF = 0, this channel's old fields dropped,
;      FN_RESUME = the cursor past the comma that ends the channel clause.
; May RAISE (ERR 5 / 52 / 59 / 61), which is safe from a call-back: it runs in
; MAIN with main page 1 mapped, so the unwind discards the disk-ROM frame and
; the handler never resumes.
field_prologue:
                ld      hl,(FN_RESUME)
                call    skip_spaces
                cp      '#'
                jr      nz,exf_havech
                inc     hl
exf_havech:
                call    eval                ; DE = channel; HL advanced
                call    fch_check           ; D-BADFNUM: D!=0 -> ERR 5, 0 -> ERR 59,
                                            ; > MAXF -> ERR 52. All three used to be
                                            ; stmt_error (ERR 2, `Syntax error`)
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
                call    req_comma           ; D-NGRAM17
                ld      (FN_RESUME),hl
                ret

; --- field_item: call-back 2 -- ONE `w AS v$`, parsed, added and bounds-checked
; in:  FN_RESUME = the cursor at a field item.
; out: the entry is in FLD_TAB and FLD_CUROFF is bumped; FN_RESUME = the cursor
;      past the item (and past its trailing comma, when there is one).
;      CF = 1 -> another item follows; CF = 0 -> the field list ended.
; 🔑 ONE BUNDLE PER ITEM, NOT ONE PER HELPER. The item is eval_byte_checked +
; the `AS` + is_letter + var_str_type + tgt_parse_fld + fld_add + the ERR 50
; bound — SEVEN calls for one logical act. Bundling is what keeps a four-field
; FIELD at five crossings rather than thirty.
; May RAISE (ERR 2 / 5 / 6 / 11 / 13 / 50). See field_prologue on why that is safe.
field_item:
                ld      hl,(FN_RESUME)
                ; D-FLDWIDTH (docs/spec-basic-fldwidth.md): THE WIDTH IS A BYTE
                ; ARGUMENT, and it is the ordinary two-stage one every other
                ; numeric argument in this tree already uses. Until this slice
                ; the `call eval` below was followed by NOTHING -- no type check,
                ; no coercion, no domain test -- so `pop de` took whatever eval
                ; left in E: type_mismatch_set's hard 0 for a STRING (measured:
                ; `FIELD#1,B$ AS A$` was accepted at width 0, not merely "OK"),
                ; and the low byte of anything out of range (`-1` -> 255,
                ; `256` -> 0, `257` -> 1).
                ; ⚠️ THE `call skip_spaces` THAT USED TO BE HERE IS GONE, AND IT
                ; WAS DEAD: eval reaches ev_f (basic/expr.asm), whose very first
                ; instruction is `call ev_sp` -- the identical $20 loop. The
                ; neighbouring exf_havech already proved the pattern from the
                ; other side (it `call eval`s with no skip at all). Rows c.wsp /
                ; c.wsp2 are green before and after and K-FW4 is the knife; the
                ; 3 bytes pay for half of what follows.
                ; ORDER IS FORCED, NOT CHOSEN (spec §4.1): on a TMISMATCH state
                ; type_mismatch_set has hard-zeroed DE and left FAC untouched, so
                ; coercing first would fault on a value that means nothing. This
                ; is eval_chan's documented constraint at the identical join.
                ; 🎯 D-EVALCHK (docs/spec-basic-evalchk.md) turned the three
                ; calls this used to be -- `eval`, `check_expr_errors`,
                ; `get_byte_arg` -- into ONE, and the collapse is BEHAVIOUR-
                ; IDENTICAL here: this site already had the check ahead of the
                ; coercion, which is why FIELD was the one of the four sites
                ; with no divergence to fix. It is also why that ordering is the
                ; helper's, rather than the inline one ex_width/ex_clear had.
                ; -6 B; the shipped `fldwidth-acceptance` is the guard and knife
                ; K-EV4 is the falsification.
                ;   string -> ERR 13; a deferred `1/0` -> ERR 11 via
                ;   fp_runtime_error's fperr_to_err; ERR 6 past int16 (70000),
                ;   ERR 5 outside 0..255 -- and 0 IS INSIDE, measured, against
                ;   this file's own header claim of "1..255" (corrected above).
                ; Returns D=0, E=width and PRESERVES HL (get_int16_checked
                ; push/pops it), which is what the comment on the `pop de` below
                ; always claimed and nothing enforced.
                call    eval_byte_checked   ; DE = field width; HL advanced
                push    de                  ; save width across the "AS" + name parse
                call    skip_spaces
                call    upcase
                cp      'A'
                jp      nz,exf_syn
                inc     hl
                ld      a,(hl)
                call    upcase
                cp      'S'
                jp      nz,exf_syn
                rst    $10     
                call    is_letter           ; a string variable name?
                jp      nc,exf_syn
                call    var_str_type        ; A=1 if `$` suffix
                or      a
                jp      z,type_mismatch_error
                                            ; D-FLDWIDTH spec §4.3: a NUMERIC
                                            ; TARGET is ERR 13, not ERR 2 --
                                            ; measured, `FIELD#1,10 AS A` is
                                            ; `Type mismatch` on the CF-3300 and
                                            ; was `Syntax error` here. Exactly
                                            ; D-LRVAR's move one statement over:
                                            ; lrset_common, in this same file,
                                            ; already answers 13 to the identical
                                            ; test. Byte-neutral (same `jp cc,nn`).
                                            ; 🔴 ONLY THIS ONE of ex_field's FOUR
                                            ; exf_syn arms moves: t.noas
                                            ; (`FIELD#1,10 A$`) and t.nonm
                                            ; (`FIELD#1,10 AS 5`) are the negative
                                            ; controls that keep the rule from
                                            ; widening to "anything ex_field
                                            ; dislikes" (spec §3.2).
                call    tgt_parse_fld       ; BC = key (name, or the ARYTAB-relative
                                            ; element key -- D-FLDARY); HL past the
                                            ; name + `$` + any `(subs)`
                pop     de                  ; DE = width (E = width, D = 0 for w<=255)
                push    hl                  ; guard cursor across the table write
                call    fld_add             ; add [FLD_CHAN, BC, FLD_CUROFF, E]; bump offset
                ; --- D-RECLEN: the running total may not exceed the RECORD LENGTH -
                ; `FIELD overflow` (ERR 50). Sited HERE, after fld_add has bumped
                ; FLD_CUROFF, so the test reads the total INCLUDING this item and
                ; needs no second add; the cursor is on the stack, so HL/DE/A are
                ; free. The raise leaves that pushed HL there ON PURPOSE -- the
                ; same argument exf_raise already documents below: raise_error
                ; resets SP from SAVSTK on BOTH its arms.
                ; 🔴 THE BOUND IS FCH_RECLENS[ch], NOT A CONSTANT 256, and one row
                ; is why: r.mid FIELDs a width of 200 into a LEN=64 record and the
                ; CF-3300 refuses it -- 200 is UNDER 256, so a constant-256 test
                ; passes it. Every row that existed before D-RECLEN used the
                ; DEFAULT 256-byte record and could not tell the two apart
                ; (docs/spec-basic-fldwidth.md §6.5 addendum).
                ; There is no accessor to borrow -- load_reclen is sub-ROM -- so
                ; the table is read inline, exactly as oo_parse_reclen WRITES it
                ; inline at basic/files.asm:283.
                ld      a,(FLD_CHAN)
                add     a,a                 ; channel * 2 (word index)
                ld      e,a
                ld      d,0
                ld      hl,FCH_RECLENS
                add     hl,de
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = FCH_RECLENS[ch], 1..256
                ld      hl,(FLD_CUROFF)     ; HL = the total INCLUDING this item
                or      a
                sbc     hl,de
                jr      c,exf_fits          ; total < record
                jr      z,exf_fits          ; total == record -> exactly fills it
                                            ; (row r.ok: LEN=64, width 64 -> ` 64 `)
                ld      a,50                ; ERR 50: FIELD overflow
                jr      exf_raise
exf_fits:
                pop     hl
                call    skip_comma
                jr      z,exf_comma
                ld      (FN_RESUME),hl      ; end of the field list
                or      a                   ; CF = 0: the handler's loop stops
                ret
exf_comma:
                inc     hl                  ; past ',' -> the next field item
                ld      (FN_RESUME),hl
                scf                         ; CF = 1: go round again
                ret
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to elas_err,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
exf_syn         equ     elas_err
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
; 🔴 D-FLDGATE: the same gate, and ONE site for both verbs -- but each consults
; its OWN cell, so the hook address rides beside the justify flag rather than
; being shared. Sharing the CELL would be a different claim from sharing the
; CODE: un-claiming H_LSET must break LSET and not RSET, which is exactly how
; both addresses were identified in the first place.
; Measured diskless (D-NODISKGAP): the VG-8020 answers ERR 5 to `LSET A$="X"`
; and `RSET A$="X"`, where this tree simply RAN them.
ex_lset:
                xor     a                   ; justify = left
                ld      de,H_LSET
                jr      lrset_common
ex_rset:
                ld      a,1                 ; justify = right
                ld      de,H_RSET
lrset_common:
                ; 🏗️ D-LRSETMOVE (Joost, 2026-09-17). The body is in disk.rom as
                ; `hk_lrset`; what is left here is the hand-off, the gate and the
                ; resume — and THREE BUNDLES the handler calls back into.
                ; 🎚️ HE RULED THIS AFTER BEING SHOWN THE PRICE AND ARGUING THE
                ; OTHER WAY: only ~25 B of the old 122 B body is disk work (the
                ; field-entry walk); the rest is PARSE, so the move buys ~15 B and
                ; costs three call-backs. *"cut it anyway, it is the correct place
                ; for it"* — placement, not economy. Recorded because the
                ; arithmetic here invites the reverse conclusion on sight.
                ; 🔑 THE BUNDLES ARE WHY IT IS THREE CROSSINGS AND NOT TEN. The
                ; target parse alone is req_letter + var_str_type + the `$` check
                ; + tgt_parse_fld + fld_find — FIVE calls for ONE logical act. A
                ; bundle per act (target, RHS, finish) is what keeps LSET at
                ; ~1.94 ms against the CF-3300's measured 2.59 ms.
                ; ⚠️ THE CURSOR CROSSES IN FN_RESUME, NOT IN HL. Every bundle
                ; reads it and writes it back, so the handler never threads it —
                ; and the two `push hl`/`pop hl` pairs the old body used to guard
                ; it across fld_find and the store are GONE rather than moved,
                ; which matters because a push that straddles a calbak straddles
                ; a CALSLT.
                ld      (LRSET_JUST),a
                inc     hl                  ; past the LSET/RSET token
                ld      (FN_RESUME),hl      ; the handler's cursor
                ex      de,hl               ; HL = this verb's own hook cell
                call    chan_gate_bare      ; unclaimed -> ERR 5, trappable.
                                            ; BARE: this verb WRITES the
                                            ; channel's record, so the full
                                            ; gate's restore would undo it
                ld      hl,(FN_RESUME)      ; where the handler left it
                jp      exec_stmt

; --- lrset_tgt: call-back 1 -- the whole target parse AND the field lookup ----
; out: CF=1 -> HL = the FLD_TAB entry; CF=0 -> not fielded (D-LRVAR), FLD_CHAN
;      already 0 and MIDS_DEST already the descriptor. FN_RESUME = the cursor
;      past the reference. May RAISE (ERR 13 on a non-string target), which is
;      safe from a call-back: it runs in MAIN with main page 1 mapped, so the
;      unwind discards the disk-ROM frame and the handler never resumes.
lrset_tgt:
                ld      hl,(FN_RESUME)
                call    req_letter          ; D-NGRAM: a FIELD target must be a name
                call    var_str_type        ; A=1 if `$`
                or      a
                jp      z,type_mismatch_error
                call    tgt_parse_fld       ; BC = key
                ld      (FN_RESUME),hl      ; past the whole reference
                call    fld_find            ; CF set -> HL -> entry (BC preserved)
                ret     c
                ; D-LRVAR: no field -> the variable's own storage
                call    tgt_desc            ; HL = the STRTAB descriptor
                ld      (MIDS_DEST),hl
                xor     a
                ld      (FLD_CHAN),a        ; 0 = "not fielded" -- never a legal chan
                ret                         ; CF=0 from `xor a`

; --- lrset_rhs: call-back 2 -- the `=` and the RHS string expression ---------
; out: STRPTR -> [len][ptr]; FN_RESUME = cursor past the RHS. May RAISE.
lrset_rhs:
                ld      hl,(FN_RESUME)
                call    skip_eq             ; '='
                jp      nz,stmt_error
                inc     hl                  ; past '='
                call    req_operand         ; `LSET A$=` / `= :` -> ERR 24
                call    str_eval            ; STRPTR -> [len][ptr]; HL advanced
                jp      nc,type_mismatch_error  ; a non-string RHS -> ERR 13
                ld      (FN_RESUME),hl
                ret

; --- lrset_finish: call-back 3 -- pick the destination, then store -----------
; The FIELDed arm needs fch_select (which reloads FSECTOR_BUF for the channel);
; the variable arm needs the descriptor re-fixed for any ARYTAB move the RHS
; caused. Both end in lrset_store, which dispatches the sub-ROM tenant — and
; that dispatch stays MAIN-side deliberately: a disk->sub CALSLT is a nesting
; this tree has never made and this slice does not invent one.
lrset_finish:
                ld      a,(FLD_CHAN)
                or      a
                jr      z,lrf_var           ; 0 -> non-FIELDed (spec §4.2)
                call    fch_select          ; FSECTOR_BUF = this channel's record
                jr      lrset_store
lrf_var:
                call    tgt_desc_fix        ; HL = the descriptor, corrected for any
                                            ; ARYTAB move since (auto-DIM, string GC)
                ld      a,(hl)              ; the target's CURRENT length IS the width
                ld      (LRSET_W),a         ; -- it never changes (measured: n.len)
                call    pu_deref_body       ; HL = the body (main LOW region)
                ld      (LRSET_DEST),hl
                jr      lrset_store

lrset_store:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_LRSETST
                jp      sc_call     ; no args, no result, cannot fail

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
                call    sc_call             ; fills FLD_DESC/RVDESC, sets STRPTR
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
                rst    $10     
                cp      SPRITE_TOKEN
                jr      z,pus_is_sprite
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
                rst    $10                ; past the GET/PUT token
                cp      '#'
                jr      nz,gp_nochan
                inc     hl
gp_nochan:
                call    eval                ; DE = channel
                call    fch_check           ; D-BADFNUM: 5 / 59 / 52, all three
                                            ; previously stmt_error (ERR 2)
                ld      a,e
                ld      (GP_CHAN),a
                ; optional ", recno" (else default record 1)
                call    skip_comma
                jr      nz,gp_defrec
                call    inc_eval            ; DE = record number
                jr      gp_haverec
gp_defrec:
                ld      de,1
gp_haverec:
                ld      (GP_RECNO),de
                ; D-LOC: the per-channel copy of this number (FCH_RECNOS[GP_CHAN]) is
                ; written SUB-SIDE in frnd_calc (basic/randio-body.inc, sub page 1):
                ; here it cost 14 B of main page 1 and the image overran $8000.
                ; 🔴 D-GETREC: RECORD 0 IS `Illegal function call`, AND TRAPPABLE.
                ; `GET#1,0` and `PUT#1,0` are ERR 5 on the CF-3300; here they reached
                ; fat_rand_get's own zero test, whose failure returns CF to gp_fin's
                ; `jp c,load_error` — which PRINTS and does not raise, so a program
                ; guarding its disk I/O with ON ERROR was told nothing went wrong.
                ; Same class as D-SAVETRAP, in a second verb pair.
                ; 🎯 ONLY RECORD 0 IS FIXED HERE, AND THAT IS THE WHOLE POINT.
                ; The reference's OTHER refusals (`,256`, `,300`, `,-1`, and `,2` on
                ; a one-record file — all ERR 55) are bounded by END OF FILE, not by
                ; a record cap: `PUT#1,256` is ACCEPTED there and extends the file,
                ; and `GET#1,2` is refused though 2 is inside any cap. zerobas's
                ; 1..255 test in randio-body.inc is a DIFFERENT RULE that coincides
                ; on three rows. Record 0 is invalid whatever the file's length, so
                ; it is the one part that can ship without settling the EOF bound
                ; [[two-rules-that-coincide-on-every-row-you-have]].
                ld      a,d
                or      e
                jp      z,gb_illegal        ; record 0 -> ERR 5, RAISED
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
                ; 🔴 D-GETEOF: A RECORD THAT *STARTS* AT OR PAST EOF IS `Input past
                ; end` (ERR 55) ON THE REFERENCE, AND WAS SILENT SUCCESS HERE.
                ; `GET#1,3` on a 14-byte file at LEN=10 reads ERR 55 on the
                ; CF-3300 and 0 here (D-GETREC row `g.past`).
                ; 🎯 AND THE BOUND IS THE RECORD'S START, NOT ANY BYTE OF IT.
                ; D-GETSTRADDLE measured the separating case the filed design had
                ; guessed at: `GET#1,2` on that same file -- bytes 10..19, so it
                ; STARTS inside and ENDS past -- is **accepted and padded** on the
                ; reference. Refusing on "any part past EOF" would have broken a
                ; row that agrees today [[two-rules-that-coincide-on-every-row-you-have]].
                ; ⚠️ GET ONLY. `PUT` past the end EXTENDS the file on the reference
                ; (`PUT#1,256` is ERR 0 there), so this must not sit above the
                ; mode split.
                ; 🟢 AND IT IS RESIDENT, WHICH IS WHY IT COSTS NO CONTRACT CHANGE.
                ; The filed design wanted a new tenant status byte to tell "past
                ; EOF" from an I/O error, because `gp_fin` sees only Cy. It is not
                ; needed: `FWR_BYTES` is page-3 RAM bound by the `fch_select`
                ; above, `FCH_RECLENS` is a resident table, and `mul16` is a
                ; resident multiply -- so the test happens BEFORE the tenant is
                ; ever called and raises directly.
                ; ⚠️ THE MULTIPLY MUST NOT TRUNCATE, AND `mul16` DOES.
                ; (recno-1)*reclen can exceed 16 bits -- record 300 at reclen 256
                ; is 76800, low word 11264, which reads as INSIDE any file bigger
                ; than 11 KB. D-GETEOF shipped with the test bounded to
                ; recno <= 255 so overflow was impossible; D-GETEOF2 replaces that
                ; bound with `mul16sat`, which saturates to $FFFF -- past any
                ; 16-bit file size by definition -- so ALL record numbers get the
                ; EOF rule instead of only the ones inside the tenant's own cap.
                ld      hl,(FWR_BYTES+2)
                ld      a,h
                or      l
                jr      nz,gp_get_go        ; file > 64 KB: recno <= 255 and
                                            ; reclen <= 256 cap the offset at
                                            ; 65024, so it is inside by construction
                ld      a,(GP_CHAN)
                add     a,a                 ; channel * 2 (word index), the same
                ld      e,a                 ; inline read ex_field uses above
                ld      d,0
                ld      hl,FCH_RECLENS
                add     hl,de
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = reclen (1..256)
                ld      hl,(GP_RECNO)
                dec     hl                  ; HL = recno - 1
                call    mul16sat            ; HL = (recno-1) * reclen, saturated
                ld      de,(FWR_BYTES)
                or      a
                sbc     hl,de
                jr      nc,gp_past_eof      ; offset >= size -> starts at/past EOF
gp_get_go:
                call    fat_rand_get
gp_fin:
                pop     hl
                jp      c,load_error        ; disk error
                jp      exec_stmt
gp_dev:
                ld      a,58                ; sequential i/o only (LPT:/CRT:)
                jr      gp_raise
gp_past_eof:
                ld      a,55                ; `Input past end` -- RAISED, so ON ERROR
                jr      gp_raise            ; sees it (no `pop hl`: raise_error
                                            ; resets SP, exactly as gp_dev/gp_bfm)
gp_bfm:
                ld      a,61                ; bad file mode (disk, not RANDOM)
gp_raise:
                jp      raise_error         ; no `pop hl` -- raise_error resets SP
