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
; So a fielded variable was recorded in a SIDE TABLE (FLD_TAB): each entry
; mapped a 2-char var key to a (channel, offset, width) slice. The record buffer
; was the channel's FSECTOR_BUF (the same 512-byte buffer the write-back cache
; swapped per channel, basic/files.asm §channel manager), so a field's bytes lived
; in the channel's context and travelled with it. Two hooks made a fielded
; variable behave:
;   * READ  — str_eval's variable path called fld_lookup, which selected the
;             field's channel, copied the slice into FLD_DESC as a [len][bytes]
;             descriptor, and pointed STRPTR there.
;   * WRITE — LSET/RSET selected the channel and copied a string into the slice.
; 🏗️ D-FLDDESC (2026-10-17): THE PREMISE ABOVE HAD BEEN FALSE SINCE ARRAYS
; SLICE-4C, AND THE TABLE IS GONE. Every string variable is a [len][ptr]
; descriptor now -- the MS-BASIC shape -- and the string GC already leaves a
; descriptor whose pointer is outside the heap alone (sub/strheap.asm
; sg_inrange; D-LITREF's program-text pointers live with it). The CF-3300 was
; measured doing exactly that (scratchpad/fieldram_run.out): after
; `FIELD #1,2 AS A$,3 AS B$`, A$ is [2][VARPTR(#1)+9] and B$ [3][VARPTR(#1)+11],
; 0 B of FRE spent. So:
;   * FIELD writes each variable's OWN descriptor, [w][block+9+offset] -- the
;     channel's record, which LIVES at its block's +9 (FCH_HDRSZ) and no longer
;     travels (disk.rom's record engine addresses it there; sub/fatprim.asm's
;     t_fch_load / t_fch_save stopped copying it);
;   * a READ is an ordinary variable read (no lookup, no copy);
;   * LSET / RSET are the non-FIELDed in-place store (docs/spec-basic-lrvar.md):
;     the target's own body at its own length -- which IS the record slice;
;   * MID$ writes the record, SWAP exchanges descriptors, `C$=A$` copies into the
;     heap and a plain `A$="Z"` moves A$ there (scratchpad/flddesc_run.out r1-r9).
;
; Clean-room: original code. Verb semantics (FIELD partitions a buffer; LSET left-
; justifies + space-pads, RSET right-justifies; a too-long value truncates from the
; right) follow the public MSX-BASIC language reference; the side-table layout is
; zerobas' own design (forced by the inline string store). Tokens are oracle-locked
; to the VG-8020 crunch (FIELD $B1, LSET $B8, RSET $B9). No disassembly. See
; basic/PROVENANCE.md §random-access records.
;
; 🧭 S10.D (2026-10-15): everything below about the record I/O -- the offset, the
; read-modify-write, the chain walk, the buffers -- describes the engine that now
; runs in disk.rom (disk/kernel.asm, hk_dget and fat_rand_get / fat_rand_put),
; not code in this file. What is left here is GET / PUT's head (below).
; GET/PUT (slice 2) add the on-disk record I/O. The record length is `reclen`,
; per channel — 256 by default (oracle: a CF-3300 PUT of one record makes a
; 256-byte file), or the OPEN..AS #n LEN=r value (disk-BASIC option-closure Item 3;
; parsed in files.asm, held in FCH_RECLENS[ch], loaded into GP_RECLEN per calc).
; r is any length in 1..256 (D-RECLENFIX; it was a power of two, so records tiled
; the sector -- no longer: D-STRADDLE reads / writes a record split across two
; sectors in two passes). Record N (1-based) occupies
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
; (D-FLDDESC, 2026-10-17: the record is the block's +9 now, in no sector buffer.)
;
; Scope / documented divergences (PROVENANCE.md):
;   * (closed by D-LRVAR 2026-08-08) LSET/RSET no longer require a FIELDed target:
;     a non-fielded one is overwritten IN PLACE at its CURRENT length, space-padded
;     and left/right-justified, a longer source keeping its first len(target) bytes
;     — all measured on the CF-3300, docs/spec-basic-lrvar.md §1.
;   * (closed by D-FLDDESC 2026-10-17) a fielded READ took precedence over a plain
;     value, and assigning a fielded name with plain LET did not "disconnect" the
;     field. Now the descriptor IS the binding: LET repoints it into the heap, as
;     the CF-3300 does (fieldram_run.out: `A$="Z"` moves it to string space).
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
;   * record numbers: any int16 above 0 (D-PUTU32 lifted the old 1..255; numbers
;     above 32767 are D-RECBIG, open); a bare GET/PUT (no record number) takes the
;     NEXT record -- the channel's last one (LOC, FCH_RECNOS) + 1 (D-RECAUTO).
;   * sparse / out-of-order PUT (writing record M before some earlier record exists)
;     leaves the skipped records' bytes undefined; in-order writes are well-defined.

; ===========================================================================
; (Field-table primitives -- fld_init, fld_clear_chan, fld_find, and fld_add
; further down -- are GONE with FLD_TAB: D-FLDDESC, 2026-10-17. There is no
; table to clear at NEW / RUN / CLEAR / CLOSE / re-FIELD and none to search; a
; FIELDed variable is cleared with every other variable.)
; ===========================================================================

; fld_fill_record — moved whole to sub/randio.asm (docs/spec-eviction-g4-
; space.md §3, carve #1), and on to disk.rom with S10.D (2026-10-15): the RANDOM
; open that space-fills the record is disk/kernel.asm's hk_frnd now (fill_sp).

; ===========================================================================
; D-FLDARY — an ARRAY ELEMENT as a FIELD / LSET / RSET target
; (docs/spec-basic-fldary.md §4.1/§4.2)
; ===========================================================================
; Both parse sites used to `call var_name_key` and use the 2-byte NAME key
; verbatim, so a `(` after the name stopped the cursor dead and the statement was
; `Syntax error` (measured, CF-3300: `FIELD#1,10 AS A$(1)` is `OK` there).
; D-FLDARY gave an element a key of its own -- ((elem - ARYTAB) >> 8) | $80 and
; the low byte, ARYTAB-relative so a scalar allocation between FIELD and LSET
; could not move it, with an assembly-time proof that the two key spaces were
; disjoint -- in `tgt_parse_fld` / `fld_key_de`, here.
; 🏗️ D-FLDDESC (2026-10-17): THE KEY, THE PROOF AND BOTH ROUTINES ARE GONE. FIELD
; writes the ELEMENT'S OWN DESCRIPTOR, so an element needs no identity beyond its
; slot: an ARYTAB move carries the slot (and the pointer in it) along, an ERASE of
; a sibling slides it down with the rest (sub/arrays.asm aeng_erase; the D-LRVAR
; key fixup there went too), and a string GC leaves its out-of-heap pointer
; alone. Both parse sites call tgt_parse_req directly: BC = the name key and
; (TGT_ADDR) = the element or 0, which is what tgt_store_desc (FIELD) and
; tgt_desc (LSET / RSET) take. A failed array resolve still does not return:
; tgt_parse_req raises it (spec §5.3, K-FA5 -- see D-STMTPEND's note in TODO.md).

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
; to run, which is the whole point: correctness, not bytes. (D-FLDDESC: the
; write is into each variable's own descriptor now -- still main's, still one
; file.)
; ⚠️ THE CURSOR CROSSES IN FN_RESUME, NOT IN HL, and every bundle reads it and
; writes it back — so the `push hl`/`pop hl` pairs that used to guard it across
; fch_mode_class and fld_clear_chan (fch_ctx_addr since D-FLDDESC) are still
; LOCAL to a bundle. A push that straddles a calbak would straddle a CALSLT.
ex_field:
                inc     hl                  ; past the FIELD token
                ld      (FN_RESUME),hl      ; the handler's cursor
                ld      hl,H_FIELD
fld_gate_resume:                            ; C4 shared tail (2026-10-03): LSET/RSET
                call    chan_gate_bare      ; unclaimed -> ERR 5, trappable.
                                            ; BARE: this verb WRITES the
                                            ; channel's record, so the full
                                            ; gate's restore would undo it
                ld      hl,(FN_RESUME)      ; where the handler left it
                jp      exec_stmt

    IF BASICINT_PINS
; 📌 LAYOUT FOR D-BASICINT2'S PINS $72D4 / $72E9 (2026-10-16). Demonia's machine
; code calls the reference's $72E9 once and then $72D4 per byte to read its tape
; (Demonia stopped with `Syntax error in 50`). Both addresses fell inside FIELD.
; tools/pin_plan.py's exact layout from here to the $73AC pin, no pad: fld_init_g
; + exf_fits (18 B), the $72D4 body (13 B), se_pending (8 B), the $72E9 body
; (13 B), then FIELD's call-backs in an order every `jr` reaches. fld_add went
; past the $73E5 pin to make room, and ex_on_key back to basic/program.asm. In
; the BASICINT_PINS=0 build the same order runs without the two bodies.
; (D-FLDDESC, 2026-10-17: fld_init_g went with the table; the bytes it and the
; field-table primitives above freed in front of $72D4 are REFILLED below, and
; exf_comma moved in front of exf_fits.)
    ENDIF

; 📌 PIN REFILL (D-FLDDESC, 2026-10-17): the field-table primitives and
; fld_init_g left 105 B in front of $72D4 (113 once D-FCHNUM's dir_line / run_kw
; moved out, 107 once exf_comma moved in). Refilled EXACTLY (tools/pin_plan.py's
; chunks, an exact-fill search), in this order: lrset_finish + lrset_store (18 B,
; from past $73E5), the GET / PUT heads -- ex_put .. gp_nochan, then gp_dev ..
; gp_raise, which they `jr` to (71 B, from past $73E5; gp_fin stays there, beside
; basic/format.asm's `jr gp_fin`), ex_delete (18 B, basic/program.asm), and
; exf_comma (6 B, from behind $72E9). exf_fits stays LAST, so field_item's
; `jr exf_fits` and its own `jr z,exf_comma` reach as before; dir_line / run_kw
; (D-FCHNUM's 8 B) moved on to the $73E5 gap. Every chunk is whole and entered
; only by label or by a `jr` from inside its own group.
; --- lrset_finish: call-back 3 -- the destination, then store ----------------
; The descriptor is re-fixed for any ARYTAB move the RHS caused, then
; lrset_store dispatches the sub-ROM tenant — and that dispatch stays MAIN-side
; deliberately: a disk->sub CALSLT is a nesting this tree has never made and
; this slice does not invent one.
; 🏗️ D-FLDDESC (2026-10-17): the FIELDed arm (FLD_CHAN != 0: fch_select, then
; the store into FSECTOR_BUF + the field's offset) is gone; the variable arm
; below serves both, because a FIELDed variable's body IS its record slice.
lrset_finish:
                call    tgt_desc_fix        ; HL = the descriptor, corrected for any
                                            ; ARYTAB move since (auto-DIM, string GC)
                ld      a,(hl)              ; the target's CURRENT length IS the width
                ld      (LRSET_W),a         ; -- it never changes (measured: n.len)
                call    pu_deref_body       ; HL = the body (main LOW region)
                ld      (LRSET_DEST),hl
                ; ...and FALLS THROUGH into lrset_store (the `jr` here was to the
                ; very next instruction: -2 B, GA-CROSS-ROMSCAN)

lrset_store:
                call    sc_inl0             ; D-STUBINL: no args, no result, cannot fail
                db      low (SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_LRSETST)
                ret

; ===========================================================================
; GET [#]f [, recno]   /   PUT [#]f [, recno]
; ===========================================================================
; 🧭 S10.D (2026-10-15, D-ROMSIZE step 1): THE RECORD I/O RUNS IN disk.rom, AND
; SO DOES THE `, recno` PARSE -- the reference's split, measured on the CF-3300
; (TODO D-ROMSIZE, "S10.D's SECOND MEASUREMENT": scratchpad/dget_run*.out). Its
; main ROM raises "File not OPEN" with NO hook entered, then enters $FE80 (H.DGET)
; with the record number NOT YET EVALUATED: record 0 (5), 300 and -1 (55) all
; enter the hook first, so the disk side raises them. So MAIN keeps exactly what
; comes before that cell -- the PUT SPRITE split, `#n`, the channel number's
; 5 / 59 / 52 and the mode class's 59 / 58 / 61 -- and crosses. disk/kernel.asm
; hk_dget does the rest: the `, recno` parse (a call-back into eval_int16_checked),
; record 0 -> 5, the bare form's NEXT record (D-RECAUTO), making the channel live
; (a call-back into fch_select, AFTER the evaluator: `GET #1,LOF(2)` selects
; channel 2 on the way), the EOF bound (55, D-GETEOF), LOC (D-LOC), the offset
; math (D-PUTU32), D-STRADDLE's two passes, the size and LOF.
; ⚠️ THE ORDER CHANGED WITH IT, ON PURPOSE. This used to parse the record BEFORE
; the mode checks, so `GET #1,0` on a CLOSED channel was 5 and `GET #1,"A"` was 13;
; with the parse in the hook they are 59, the reference's order (its check is
; main's and comes first). An OPEN channel answers exactly as before.
; ⚠️ chan_gate_BARE, NOT THE FULL GATE (the FIELD / LSET rule, files.asm): GET
; writes the live channel's record in FSECTOR_BUF and PUT reads it there; the full
; gate would save the record before the crossing and LDIR the stale copy back
; after it, undoing every GET. (D-FLDDESC, 2026-10-17: the record is the block's
; +9 now and nothing copies it; the bare gate stays -- hk_dget does its own
; channel bookkeeping.)
; 🟢 THE DISKLESS ANSWER IS UNCHANGED, AND IT IS STRUCTURAL: no hook is reached
; without an OPEN disk channel of mode 4, which a machine without disk.rom cannot
; create -- so the VG-8020-shaped 59 comes from fch_mode_class, before the cell.
;   crossing: A = 0 GET / 1 PUT, C = the channel, FN_RESUME = the cursor past `#n`
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
                push    af                  ; the mode, for the crossing
                rst    $10                ; past the GET/PUT token
                cp      '#'
                jr      nz,gp_nochan
                inc     hl
gp_nochan:
                call    eval                ; DE = channel
                call    fch_check           ; D-BADFNUM: 5 / 59 / 52, all three
                                            ; previously stmt_error (ERR 2)
                ; the channel must be open RANDOM (FCH_MODES[ch] == 4). D-NOTOPEN2:
                ; the old `cp 4` conflated THREE conditions the reference separates --
                ; not open (59), open-but-not-RANDOM (61), device channel (58).
                push    hl                  ; fch_mode_class's index uses HL
                call    fch_mode_class      ; ERR 59 if NOT OPEN; CF set = disk
                pop     hl                  ; channel; E (the channel) survives
                jr      nc,gp_dev           ; LPT:/CRT: -> ERR 58 sequential i/o only
                cp      4
                jr      nz,gp_bfm           ; a disk channel must be RANDOM -> ERR 61
                ld      (FN_RESUME),hl      ; the cursor past `#n`, for the handler
                ld      c,e                 ; C = the channel
                pop     af                  ; A = 0 GET / 1 PUT
                ld      hl,H_DGET
                call    chan_gate_bare      ; disk.rom's hk_dget: `,r`, the record
                                            ; (claimed: a mode-4 channel exists only
                                            ; where disk.rom opened it)
                ei                          ; a CALLF returns with interrupts OFF
                ld      hl,(FN_RESUME)      ; where the handler left the cursor
                jp      exec_stmt
gp_dev:
                ld      a,58                ; sequential i/o only (LPT:/CRT:)
                jr      gp_raise
; gp_past_eof -- `Input past end` (55), RAISED. GET's own use of it is disk.rom's
; since S10.D (fat_rand_get); INPUT$ (strvar.asm sid_read) and the
; sequential reader's end (files.asm) still raise it here.
gp_past_eof:
                ld      a,55
                jr      gp_raise
gp_bfm:
                ld      a,61                ; bad file mode (disk, not RANDOM)
gp_raise:
                jp      raise_error         ; no `pop` -- raise_error resets SP
; (ex_delete: basic/program.asm, whose header there is its contract.)
ex_delete:
                ld      (SL_DELPTR),hl      ; the statement cursor, on the token
                ld      a,LE_OP_DELRANGE
                ; LE_STATUS carries the ERR CODE ITSELF for this op (basic/
                ; sysvars.inc): 0 = ok, 2 = R-D6 trailing junk, 5 = R-D2 (the high
                ; end names no stored line) or R-D4 (lo > hi). One compare, no
                ; second table.
                call    le_call_op          ; A = LE_STATUS, Z = ok
                jp      nz,raise_error
                ; R-D7: a SUCCEEDING delete is a program EDIT. The tenant has
                ; already run relink + vars_reset (its own tail, exactly as
                ; store_line's op does); CONTVALID is the resident half, and it is
                ; cleared HERE and only here -- a FAILING delete must leave the
                ; CONT point alone, which dlt-contbad is the row for (its CONT
                ; still resumes, reading 5 like its control).
                xor     a
                ld      (CONTVALID),a
                ; R-D8: and then the run stops. Same mechanism as ex_end -- the
                ; run loop tests ENDFLAG immediately after `exec` returns
                ; (rp_run, above) and BEFORE it dereferences CURLINE, which
                ; matters here more than it does for END: the text this statement
                ; just memmoved is where CURLINE points.
                jp      end_line_end        ; -> 1, and the run stops
; (exf_comma / exf_fits -- field_item's comma tail, CF = another item -- are
; GONE, D-DISKREST slice 5, 2026-10-20: hk_field reads the comma itself. Their
; 15 B are free space in front of the $72D4 pin.)
    IF BASICINT_PINS
; 📌 D-BASICINT2 PIN $72D4 (2026-10-16): the reference's tape-byte read, CALLED by
; Demonia (HL is its own pointer). Black-box on the VG-8020
; (scratchpad/basicint_tape_probe.py): A = the next byte off the tape, across
; block boundaries; HL and B come back intact (the probe's stub loops on both);
; a read failure raises ERR 19 (Device I/O error). BC/DE/HL are kept here because
; this tree's TAPIN clobbers C (sub2/tapeprog.asm ctp_line, once basic/cload.asm's).
                ds      $72D4 - $, $00
basicint_taprd:
                push    bc
                push    de
                push    hl
                call    TAPIN
                pop     hl
                pop     de
                pop     bc
                jp      c,dpl_dio           ; motor off, ERR 19 (basic/cload.asm)
                ret
    ENDIF
; --- D-WSZERO S9 (2026-10-15): the disk-only cells, made disk-only in fact -----
; FLD_TAB and DISKOP_ERR are the disk machine's: on a diskless one no FIELD can
; exist and no DSKIO can fail. But a string-variable read walked the table
; (fld_lookup, then in this file) and NEW / RUN / CLEAR re-wrote it, and a tape INPUT # past
; the end read the error cell -- so when the diskless ceiling rises over them
; (S15) a program's own bytes there would be read as fields and error codes. Each
; reader now asks diskslot_test first. (They lived past the $73E5 pin until
; D-BASICINT2 moved them in front of $72E9 -- see the layout note below.)
; (D-FLDDESC, 2026-10-17: FLD_TAB, fld_lookup and fld_init_g are gone, so the
; table half of this is moot; se_pending's error-cell half stands.)
; se_pending: A = the DSKIO failure code pending, 0 without a disk ROM. Z/NZ unset.
se_pending:
                call    diskslot_test
                ret     z                   ; A = 0: nothing pending
                ld      a,(DISKOP_ERR)
                ret
    IF BASICINT_PINS
; 📌 D-BASICINT2 PIN $72E9 (2026-10-16): the reference's tape start -- motor on,
; lock onto the next block's leader, as TAPION. Demonia calls it with HL=$A000 and
; DE=$A600 and then steps HL itself, so they are kept. Ctrl-STOP while it waits
; raises ERR 19 on the VG-8020 (scratchpad/basicint_tape_probe.out, row break).
                ds      $72E9 - $, $00
basicint_tapst:
                push    bc
                push    de
                push    hl
                call    TAPION
                pop     hl
                pop     de
                pop     bc
                jp      c,dpl_dio           ; motor off, ERR 19
                ret
    ENDIF
; --- field_item: call-back 2 -- ONE `w AS v$`, parsed, bounds-checked, stored --
; in:  FN_RESUME = the cursor at a field item; FLD_CUROFF / FLD_END as
;      field_prologue (or the previous item) left them.
; out: the variable's own descriptor = [w][FLD_CUROFF] and FLD_CUROFF += w
;      (D-FLDDESC: it was an FLD_TAB entry); FN_RESUME = the cursor past the item
;      (and past its trailing comma, when there is one).
;      CF = 1 -> another item follows; CF = 0 -> the field list ended.
; 🔑 ONE BUNDLE PER ITEM, NOT ONE PER HELPER. The item is eval_byte_checked +
; the `AS` + is_letter + var_str_type + tgt_parse_req + the ERR 50 bound + the
; store — SEVEN calls for one logical act. Bundling is what keeps a four-field
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
                call    tgt_parse_req       ; BC = the name key, (TGT_ADDR) = the
                                            ; element (D-FLDARY) or 0; HL past the
                                            ; name + `$` + any `(subs)`. A failed
                                            ; array resolve raises from in there
                pop     de                  ; DE = width (E = width, D = 0 for w<=255)
                ret                         ; DE = width, BC = key, HL = the cursor
                ; 🔁 D-DISKREST slice 5 (2026-10-20): THE REST OF THE ITEM IS
                ; disk.rom's hk_field now -- the [w][ptr] descriptor into RVDESC,
                ; FLD_CUROFF's advance, the ERR 50 bound against FLD_END (still
                ; BEFORE the store, D-FLDDESC's order and D-RECLEN's reclen-not-256
                ; bound), the call-back to tgt_store_desc and the comma loop. BC and
                ; TGT_ADDR cross untouched: hk_field writes only RAM, A, DE and HL
                ; between this return and tgt_store_desc.

; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to elas_err,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
exf_syn         equ     elas_err
; (field_prologue -- FIELD's call-back 1: `#`, the channel, its mode class (5 /
; 52 / 59 / 61), the record's span into FLD_CUROFF / FLD_END, the comma -- and its
; refusal tails exf_dev / exf_bfm are GONE, D-DISKREST slice 4, 2026-10-20:
; disk.rom's hk_field does all of it, calling back for the channel expression,
; fch_check and fch_mode_class, and reading the record's address from its own
; RANDOM row instead of fch_ctx_addr's sub-ROM call. D-NOTOPEN2's split stays
; where it was measured: a device channel is 5 here (GET / PUT say 58 on the same
; LPT:, `wm_lpt_fld` / `wm_lpt_get`), a disk channel not RANDOM is 61.)
; 📌 PIN REFILL (D-FLDDESC, 2026-10-17): with exf_comma gone to the $72D4 gap,
; fld_lookup's 20 B gone and field_prologue 11 B larger, 16 B were left in front
; of $73AC: derive_directf (basic/program.asm, whose header there is its
; contract), whole and entered only by `call`.
derive_directf:
                ld      a,(CURLINE+1)
                cp      dir_line >> 8
                ld      a,0                 ; (xor a would clobber the flags)
                jr      nz,dd_mode
                inc     a
dd_mode:
                ld      (DIRECTF),a
                ; 🏗️ D-CURLIN (Joost, 2026-09-24): publish CURLIN ($F41C) as the
                ; reference does. Every line entry and mid-line resume passes
                ; rp_exec, which calls this; both callers save HL or have spent it.
                ; The body is in the LOW region (str-engine.asm): inline it did not
                ; fit page 1 (14 B free, it needed ~23).
                jp      curlin_pub          ; A = DIRECTF
; ===========================================================================
; (fld_lookup -- the READ hook str_eval's variable path called, a 22 B resident
; stub over the SUBROM_IDX_FLDLOOK page-0 tenant that copied a field's slice into
; FLD_DESC -- is GONE with D-FLDDESC, 2026-10-17, and so is the tenant (its
; sub-ROM row is retired). A FIELDed variable's own descriptor points into the
; record, so str_get_key reads it like any other.)
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
                ld      de,H_LSET           ; (left / right is the TOKEN's bit 0,
                jr      lrset_common        ; read by disk.rom's hk_lrset -- D-WSZERO S9)
    IF (LSET_TOKEN & 1) != 0 || RSET_TOKEN != LSET_TOKEN + 1
                db      LRSET_JUST_BIT0_RULE_NEEDS_LSET_EVEN_AND_RSET_LSET_PLUS_1
    ENDIF
ex_rset:
                ld      de,H_RSET
lrset_common:
                ; 🏗️ D-LRSETMOVE (Joost, 2026-09-17). The body is in disk.rom as
                ; `hk_lrset`; what is left here is the hand-off, the gate and the
                ; resume -- and, since D-DISKREST slice 1 (2026-10-20), ONE bundle
                ; the handler calls back into (lrset_finish). Until then there
                ; were three, and the paragraphs below are why.
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
                ; 🔁 REVERSED 2026-10-20 (D-DISKREST slice 1): the bundles saved
                ; crossings but kept ~49 B of PARSE in main page 1, which then had
                ; 1 B free; Joost had just ruled ROM space before speed. hk_lrset
                ; now parses and calls back one helper at a time -- 8 crossings
                ; where there were 3, the price this paragraph named.
                ; 🏗️ D-FLDDESC (2026-10-17): the field-entry walk that was the
                ; handler's only disk work is gone (no table; a FIELDed target's
                ; own descriptor points at the record), so ALL of LSET is these
                ; three bundles and disk.rom keeps only the decision to run.
                ; ⚠️ THE CURSOR CROSSES IN FN_RESUME, NOT IN HL: the handler reads
                ; it there and leaves the resume cursor there (since slice 1 it
                ; threads HL between its own call-backs, which carry HL both ways).
                ; Before slice 1 every bundle read it and wrote it back --
                ; and the two `push hl`/`pop hl` pairs the old body used to guard
                ; it across fld_find and the store are GONE rather than moved,
                ; which matters because a push that straddles a calbak straddles
                ; a CALSLT.
                inc     hl                  ; past the LSET/RSET token
                ld      (FN_RESUME),hl      ; the handler's cursor
                ex      de,hl               ; HL = this verb's own hook cell
    IF BASICINT_PINS
                jr      lrc_go              ; over the D-BASICINT pin below
; 📌 D-BASICINT PIN $73AC (2026-10-15), bridged: the reference's RUN-without-
; argument, which tape games (Loopy Laundry, Punch & Judy) jump to after loading
; a BASIC program and setting VARTAB ($F6C2) to its end themselves. Measured
; black-box on the VG-8020 (scratchpad/basicint_probe.out): variables cleared,
; DATA restored, the variables start AT VARTAB AS GIVEN (a VARTAB moved +64
; stays moved), HL ignored, the rest of the calling statement dropped -- a bare
; RUN in every way but where the program ends. zerobas keeps that end in PRGEND
; (vars_reset derives VARTAB = PRGEND + 2), so it is taken FROM the game's
; VARTAB, then RUN starts at the top level (run_prog_top resets SP, dropping
; BLOAD,R's frames). RELINKED first, like every load (cload.asm
; load_commit_prog): the VG-8020 runs a program whose first line link was
; garbled, and without the relink zerobas answered `Syntax error in 4803`
; (scratchpad/basicint_pins.out, row run_link). FIXED ADDRESS, from tools/pin_plan.py's `jr`
; bridge (no pad today; `pin_plan.py --check` caps it -- Joost: no growing
; holes). The `jr` above costs LSET / RSET 12 T-states.
                ds      $73AC - $, $00
basicint_run:
                ld      hl,(VARTAB)
                dec     hl
                dec     hl
                ld      (PRGEND),hl         ; the $0000 end marker the game's VARTAB implies
                call    relink              ; the game's own loader set the links
                jp      run_prog_top
lrc_go:
    ENDIF
                jp      fld_gate_resume     ; chan_gate_bare, then resume at
                                            ; FN_RESUME -- FIELD's tail (C4)
; 📌 PIN REFILL (D-FCHNUM, 2026-10-17): 8 B of data moved from basic/program.asm,
; past the $73E5 pin, to take back what D-FCHNUM and D-JRSLICE3 freed ahead of
; $72D4 -- where it sat until D-FLDDESC (2026-10-17) moved it HERE, with
; lrset_tgt's 8 freed bytes in front of $73E5 to fill. Never executed (the `jp`
; above). Sited BEFORE lrset_tgt, not after it: tools/check_dead_code.py keeps
; the pinned basicint_73e5 live through lrset_tgt's span running into the pin's
; `ds`, and a data-only span in between cuts that edge (its fix 11). dir_line's
; link is self-relative, so it holds anywhere, and derive_directf's
; `cp dir_line >> 8` asks only that it is in ROM (header: basic/program.asm).
dir_line:       dw      dir_line + 2        ; [link] -> the word below
                dw      0                   ; [lineno] = 0 == the $0000 end marker
run_kw:         db      "RUN",0

; (lrset_tgt -- LSET / RSET's target parse, call-back 1 -- and lrset_rhs below
; are GONE, D-DISKREST slice 1, 2026-10-20: disk.rom's hk_lrset parses both
; itself, calling back one helper at a time. Their bytes here are free space in
; front of the $73E5 pin (Joost 2026-10-20: a pin pad is free space, `make
; basic-reloc` lists it). hk_lrset still reads the justify flag as the token's
; bit 0; the rule it rests on is asserted beside ex_lset.)
    IF BASICINT_PINS
; 📌 D-AVTAK PIN $73E5 (2026-10-15): the reference's PLAY body, which A View to a
; Kill CALLs with HL at its own "..." arguments (scratchpad/basicint_73e5_probe.py).
; Placed by tools/pin_plan.py after the `ret` above with a 6 B gap, and the gap is
; REFILLED, not padded: ex_on_key (6 B, a `jp z` target only) moved here from
; basic/program.asm, whose copy is now the ELSE arm (Joost: no growing holes).
; D-WSZERO S9 (2026-10-15): the gap is now lrset_tgt's own 6 B (the justify flag
; read from the token), and ex_on_key moved on, in front of the $73AC pin, to
; refill the 6 B the justify store left there. D-BASICINT2 (2026-10-16) sent it
; back to basic/program.asm, unconditional (the $72D4 / $72E9 layout above).
                ds      $73E5 - $, $00
basicint_73e5:
                jp      basicint_play       ; basic/missing.asm: call PLAY's body, return
    ENDIF

; (dev_cas -- the "CAS:" device name -- moved back in front of the $6CF3 pin,
; basic/files.asm before oo_fail_syn, D-DISKREST slice 2 (2026-10-20): with
; sep_eval, the exact 12 B refill for what that slice took out ahead of it.)

; cl_leaf -- the evaluator's leaf for each binary operator, by id (token -
; GT_TOKEN, 3..14), read only by basic/expr.asm's climber (`ld hl,cl_leaf-6`).
; 📌 HERE, PAST EVERY PIN, SINCE D-EVALSLOPE (2026-10-20): the one climber that
; replaced the three precedence layers came out 24 B larger in front of the
; pinned $6CF3, whose pad is 0 (a `jr` bridge), and this table is that exact 24 B,
; moved out the way dev_cas above was. Pure data: nothing falls into it, no `jr`
; reaches it.
cl_leaf:
                dw      combine_add         ; + (combine_*: the typed frame)
                dw      combine_sub         ; -
                dw      combine_mul         ; *
                dw      combine_div_float   ; /  ALWAYS float (spec §10.1)
                dw      combine_pow         ; ^
                dw      lg_and              ; AND (lg_apply's byte cores)
                dw      lg_or
                dw      lg_xor
                dw      lg_eqv
                dw      lg_imp
                dw      signed_mod_de_bc    ; MOD (DE = dividend, BC = divisor)
                dw      signed_div_de_bc    ; \ (integer division)
    IF (PLUS_TOKEN-GT_TOKEN != 3) || (AND_TOKEN-GT_TOKEN != 8) || (MOD_TOKEN-GT_TOKEN != 13) || (IDIV_TOKEN-GT_TOKEN != 14) || (EQ_TOKEN != GT_TOKEN+1) || (LT_TOKEN != GT_TOKEN+2) || (POW_TOKEN != PLUS_TOKEN+4) || (IMP_TOKEN != AND_TOKEN+4)
                db      CL_TOKEN_ORDER_CHANGED  ; cl_lvtab / cl_leaf / the id tests assume it
    ENDIF


; (fld_add -- the FLD_TAB append, here since D-BASICINT2 -- is GONE with the
; table, D-FLDDESC 2026-10-17: field_item writes the variable's descriptor.)

; (fat_rand_open / fat_rand_put / fat_rand_get -- the three two-instruction
; fatprim_bounce heads of the sub-ROM record engine, DISKOP_SEL_RAND_* 15/16/17 --
; are GONE since S10.D, 2026-10-15: the engine runs in disk.rom. OPEN RANDOM
; crosses H_FOPEN with FOPEN_SEL_RAND (basic/files.asm oo_random_setup), GET /
; PUT cross H_DGET below, CLOSE crosses H_CHCLOSE as an OUTPUT channel does.)

; gp_fin -- C4 shared tail (2026-10-03): pop the cursor; CF -> disk_error (the
; pending DSKIO code, else `load error`); else the next statement. GET / PUT's
; own use of it went to disk.rom with S10.D; CALL FORMAT (basic/format.asm
; exc_go, a `jr`) still ends here.
gp_fin:
                pop     hl
                jp      c,disk_error
                jp      exec_stmt
