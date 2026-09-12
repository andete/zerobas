; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — dirverb.asm  (directory-verb I/O-body tenant)
; ===========================================================================
; The disk I/O bodies of the directory verbs KILL and NAME, evicted from the
; repack main ROM's basic/files.asm into sub-ROM PAGE 1 (docs/spec-evict-
; diskfile-cluster.md §12, Phase 2 of the disk/file cluster eviction). The
; verbs' eval/parse heads (parse_disk_fcb, the "AS" scan, DISKSLOT_OK check)
; stay MAIN-RESIDENT -- a page-1 tenant cannot reach eval/the parser -- and
; marshal their result into DISK_FCB_NAME / FWR_DIRSEC / FWR_DIROFF (page-3 RAM,
; visible from both sides) before a single subrom_call hands off to this tenant
; for the CALSLT-side sector work (spec §3 head/body split).
;
; ONE index, SELECTOR-DISPATCHED (like fatprim_tenant): DISKOP_OP picks KILL's
; delete loop vs NAME's dir-entry stamp. Both bodies call the Phase-1 FAT12
; primitives (fat_delete / read_sector / fatprim_write_sector, basic/fat-prim-
; body.inc + basic/fat-delete-body.inc, already in this sub.rom assembly)
; SUB-LOCALLY -- no nested marshalling, no subrom_call, since those primitives
; are co-resident in the tenant's own page 1. This is exactly why Phase 2 is
; cheap: Phase 1 already put the heavy sector/cluster engine here, so a verb
; body is just a short orchestration over sub-local calls.
;
; RESULT MARSHALLING. Cy cannot ride back through subrom_call/CALSLT (its own
; `or a` clears it, sub/format.asm's rule), so each body funnels its
; disposition into DISKOP_STATUS (basic/sysvars.inc); the resident head reads
; it back. The two bodies use DIFFERENT status polarity, each interpreted only
; by its OWN head:
;   * NAME_STAMP -- STATUS = 0 ok / 1 error (standard, like fatprim).
;   * KILL       -- STATUS = deleted-any flag (0 = nothing matched -> the head
;                   raises "File not found" via load_error; nonzero = ok). This
;                   mirrors basic/files.asm's ORIGINAL do_kill semantics
;                   bug-for-bug: a real I/O error mid-loop is treated (as
;                   before) as "no further match" -- fat_delete's Cy stops the
;                   loop, and success is reported iff at least one entry was
;                   freed before the error (the earlier resident build did exactly
;                   this).
;
; CLEAN-ROOM: original code (the dispatch/marshalling glue is own-design, the
; CALL FORMAT / fatprim precedent + MSX2 Technical Handbook CALSLT ABIs). The
; sector work reuses our own basic/fat.asm primitives via the shared bodies;
; KILL/NAME *semantics* trace to basic/files.asm's headers (public MSX-BASIC
; language reference + black-box CF-3300). No reference-ROM disassembly.
; ===========================================================================

; --- dirverb_tenant: the SUBROM_IDX_DIRVERB entry --------------------------
; Read DISKOP_OP (RAM, set by the resident head before subrom_call) and branch
; to the requested body. Four ops, still a plain chain rather than a jp table:
; the table would cost more than the three `cp`/`jr` it replaces. HL/DE are
; irrelevant on entry (every body reads all inputs from RAM), so nothing needs
; preserving through the dispatch.
;
; ⚠️ DISKOP_OP IS READ AGAIN, DEEP INSIDE THE FILES BODY. It is not only the
; dispatch key: DISKOP_SEL_FILES vs DISKOP_SEL_LFILES is also the SINK selector
; (df_out) and the LAYOUT selector (df_emit / df_end), so it must stay intact for
; the whole listing. Nothing between here and the return writes it — the sub-local
; fat primitives take their inputs in registers and RAM of their own, and the
; fatprim TENANT wrapper (which does read DISKOP_OP, in its own value namespace)
; is not on this path: this tenant calls the primitive BODIES directly.
dirverb_tenant:
                xor     a
                ld      (DISKOP_ERR),a      ; D-DISKERR: no DSKIO failure pending yet
                ld      a,(DISKOP_OP)
                or      a
                jp      z,tnt_kill              ; DISKOP_SEL_KILL = 0
                cp      DISKOP_SEL_FILES
                jp      z,tnt_files             ; 2 -> FILES  (screen)
                cp      DISKOP_SEL_LFILES
                jp      z,tnt_files             ; 3 -> LFILES (printer)
                cp      DISKOP_SEL_DSKO
                jp      z,tnt_dsko              ; 4 -> DSKO$ (D-DSKIO)
                cp      DISKOP_SEL_DSKI
                jp      z,tnt_dski              ; 5 -> DSKI$
                cp      DISKOP_SEL_COPYSTASH
                jp      z,tnt_copystash         ; 6 -> COPY, first half (D-COPY)
                cp      DISKOP_SEL_COPY
                jp      z,tnt_copy              ; 7 -> COPY, the body
                ; fall through -> DISKOP_SEL_NAME_STAMP = 1

; --- NAME "old" AS "new": stamp the new 8.3 name over the located dir entry --
; Inputs (from the resident head): FWR_DIRSEC/FWR_DIROFF locate the OLD file's
; directory entry (the head already ran fat_mount + fat_find via the resident
; shims); DISK_FCB_NAME holds the NEW 8.3 name. Read that dir sector, overwrite
; the 11-byte name field in place, write it back. Byte-for-byte the same logic
; as basic/files.asm's do_name tail.
tnt_name_stamp:
                ld      de,(FWR_DIRSEC)
                ld      hl,FSECTOR_BUF
                call    read_sector            ; sub-local primitive body
                jr      c,dv_err
                ld      hl,FSECTOR_BUF
                ld      de,(FWR_DIROFF)
                add     hl,de                  ; HL -> the entry in the buffer
                ex      de,hl                  ; DE -> dest name field
                ld      hl,DISK_FCB_NAME       ; source = the new 8.3 name
                ld      bc,11
                ldir                           ; overwrite the 11-byte 8.3 name
                ld      de,(FWR_DIRSEC)
                ld      hl,FSECTOR_BUF
                call    fatprim_write_sector   ; sub-local (renamed) primitive
                jr      c,dv_err
                xor     a
                ld      (DISKOP_STATUS),a       ; ok
                ret
dv_err:
                ld      a,1
                ld      (DISKOP_STATUS),a       ; error -> head does load_error
                ret

; --- KILL "name": delete every matching entry ------------------------------
; Input: DISK_FCB_NAME holds the 8.3 wildcard pattern. fat_delete frees + $E5-
; marks the FIRST match per call (name_cmp honours '?'/'*'), so loop until no
; match remains. C accumulates the deleted-any flag; DISKOP_STATUS carries it
; back (0 = nothing matched -> the head raises ERR 53 "File not found";
; 1 = deleted at least one; 2 = mount error -> the head does load_error).
;
; 🔴 THE MOUNT IS SEPARATED FROM THE MISS ON PURPOSE, AND IT IS WHY THE FILED
; "the fix is 0 B" WAS WRONG (D-DSKMSG, docs/spec-basic-dskmsg.md §4.1).
; fat_delete's own contract is `Cy = 1 not found / mount / I-O error` -- it calls
; fat_mount itself -- so before this the deleted-any flag was 0 for ALL THREE, and
; simply re-pointing the head's `jp z` at df_notfound would have turned a
; disk-offline KILL into a TRAPPABLE ERR 53 on no reading at all. Mounting here
; and taking tf_ioerr gives KILL the same three-way DISKOP_STATUS disposition
; tnt_files already has (0 = nothing matched -> ERR 53; 1 = deleted at least one;
; 2 = mount error -> load_error). fat_delete still mounts; a second mount of a
; mounted volume re-reads the BPB and is idempotent.
;
; ⚠️ STILL CONFLATED, said out loud: an I-O error INSIDE fat_delete, after the
; mount and before anything was deleted, still returns C=0 and reads as "nothing
; matched". Separating that needs a status out of fat_delete itself, a
; primitive-layer change D-DSKMSG does not make.
tnt_kill:
                call    fat_mount               ; sub-local primitive body
                jp      c,tf_ioerr              ; STATUS = 2 -> head does load_error
                ld      c,0                     ; C = deleted-any flag
dvk_loop:
                push    bc
                call    fat_delete             ; sub-local primitive body
                pop     bc
                jr      c,dvk_done              ; no (further) match -> stop
                ld      c,1                     ; deleted at least one
                jr      dvk_loop
dvk_done:
                ld      a,c
                ld      (DISKOP_STATUS),a       ; deleted-any (0 = none)
                ret

; --- DSKO$ / DSKI$: one sector between (DSKBUF_PTR) and sector FWR_DIRSEC ------
; D-DSKIO, docs/spec-basic-dskio.md §3. The head parsed drive and sector; the
; buffer is whatever DSKBUF_PTR names (FSECTOR_BUF, written at disk-ROM init).
; No mount and no BPB: a raw sector needs neither, and the reference reads
; sector 9999 without complaint. STATUS = 0 ok, $FF = DSKIO error.
tnt_dsko:
                call    dsk_regs
                call    fatprim_write_sector    ; sub-local primitive body
                jr      dsk_status
tnt_dski:
                call    dsk_regs
                call    read_sector             ; sub-local primitive body
dsk_status:
                sbc     a,a                     ; CF -> $FF, clear -> 0
                ld      (DISKOP_STATUS),a
                ret
dsk_regs:
                ld      de,(FWR_DIRSEC)         ; the sector
                ld      hl,(DSKBUF_PTR)         ; the buffer
                ret


; ===========================================================================
; FILES / LFILES — the root-directory walk and the 8.3 entry emit
; (D-LFILES, docs/spec-basic-lfiles.md §2; the eviction Phase 2 listed as
; "FILES ~150 B" and dropped).
;
; MOVED HERE VERBATIM from basic/files.asm, except where the split or the printer
; mode forces a change. The three forced changes, and nothing else:
;   * every CHPUT emit site goes through `df_out`, which picks CHPUT or LPTOUT off
;     DISKOP_OP. For FILES that is byte-identical to what it replaced: print_crlf
;     is pchar(13)+pchar(10), pchar with PRDEST=0 IS `call CHPUT`, and exec_stmt
;     zeroes PRDEST at the top of every statement, so this path never ran with any
;     other sink. `disk_probe_files.py`, `disk_probe_files_wildcard.py`,
;     `diskbasic-acceptance` and `lfl-ctlf` are four independent readers of those
;     exact bytes, and they are this move's falsification (spec §2.1.2).
;   * the disposition rides DISKOP_STATUS instead of Cy + the statement tail, which
;     is the standard head/body contract here (Cy cannot survive CALSLT).
;   * the LFILES layout branches (R-LF1/R-LF2), which cost SUB-ROM bytes — the
;     whole reason this slice could afford the verb at all.
;
; ⚠️ EMITTED UNDER DI. subrom_call wraps the tenant, so a whole directory listing
; now reaches CHPUT with interrupts off where it previously ran with them on.
; errmsg_tenant and title_tenant already emit from this island the same way, and
; read_sector's dskio_calslt EIs mid-walk in any case — htimi_guard exists exactly
; because a VBLANK can land inside a page-1 tenant. Named because it is a real
; change of condition, not because it is novel (spec §3.3).
;
; Clean-room: our own code, relocated from basic/files.asm; see that file's header
; for the FILES/LFILES provenance and the CF-3300 oracle citations.
; ===========================================================================

; --- tnt_files: FILES / LFILES ---------------------------------------------
; in:  DISKOP_OP = DISKOP_SEL_FILES | DISKOP_SEL_LFILES (op AND sink AND layout)
;      FILES_HASPAT = 1 if DISK_FCB_NAME holds an 8.3 wildcard pattern
; out: DISKOP_STATUS = 0 nothing matched / 1 ok / 2 mount or DSKIO error
tnt_files:
                ; Seed the matched-any flag at "nothing matched", ALWAYS: the walk
                ; itself sets it to 1 at df_do_emit the first time it emits an
                ; entry, so a listing that emits nothing raises ERR 53 whether the
                ; caller gave a filespec or not.
                ;
                ; 🔴 IT USED TO SEED A *BARE* LISTING AT "ok"
                ; (`ld a,(FILES_HASPAT) / xor 1`), which made an EMPTY DIRECTORY
                ; silent -- docs/spec-basic-lfiles.md §2.4 called that arm
                ; unmeasured and left it alone, and its knife K7 predicted the miss
                ; before the run. D-DSKMSG measured it (R-LF7,
                ; docs/lptverb-msx1-characterization.md §4.2): the CF-3300 raises
                ; `File not found` for a bare FILES *and* a bare LFILES over a
                ; mounted, WRITABLE, empty volume -- the same disposition as a
                ; filespec that matched nothing, not a different one. 4 B saved.
                ;
                ; The filespec rows are bit-identical either way: HASPAT=1 -> the
                ; old `xor 1` wrote the same 0 this writes unconditionally.
                ; A directory holding only deleted or volume-label entries now
                ; takes this arm too -- the same disposition (the walk emitted
                ; nothing), stated rather than measured; no fixture has one.
                xor     a
                ld      (DISKOP_STATUS),a
                ; (2) mount the volume (BPB geometry into the fat.asm scratch).
                call    fat_mount               ; sub-local primitive body
                jp      c,tf_ioerr
                ; (3) walk the root directory: FAT_DIRSEC/FAT_DIRREM track position.
                ld      hl,(FAT_FIRSTROOT)
                ld      (FAT_DIRSEC),hl
                ld      hl,(FAT_ROOTSECS)
                ld      (FAT_DIRREM),hl
df_secloop:
                ld      hl,(FAT_DIRREM)
                ld      a,h
                or      l
                jr      z,df_end                ; scanned every root sector
                ld      de,(FAT_DIRSEC)
                ld      hl,FSECTOR_BUF
                call    read_sector             ; sub-local primitive body
                jp      c,tf_ioerr              ; FDC / DSKIO error
                xor     a
                ld      (FILES_ENTIDX),a        ; entry 0..15 within this sector
df_entloop:
                call    df_entptr               ; HL -> current 32-byte dir entry
                ld      a,(hl)
                or      a
                jr      z,df_end                ; $00 = first free slot -> end of dir
                cp      $E5
                jr      z,df_nextent            ; deleted entry
                push    hl
                ld      de,11
                add     hl,de
                ld      a,(hl)                  ; attribute byte (+11)
                pop     hl
                and     $18                     ; volume-label | sub-dir -> skip
                jr      nz,df_nextent
                ; filespec filter: match the entry name (HL) against the pattern
                ; (DISK_FCB_NAME) with '?'/'*' wildcards; skip non-matches.
                ld      a,(FILES_HASPAT)
                or      a
                jr      z,df_do_emit            ; bare listing -> everything
                push    hl                      ; name_cmp advances HL by 11
                ld      de,DISK_FCB_NAME
                call    name_cmp                ; sub-local; DE=pattern, HL=entry
                pop     hl                      ; restore entry ptr (flags preserved)
                jr      nz,df_nextent           ; no match -> skip
df_do_emit:
                ld      a,1
                ld      (DISKOP_STATUS),a       ; at least one entry matched
                call    df_emit                 ; print this entry's 8.3 field
df_nextent:
                ld      a,(FILES_ENTIDX)
                inc     a
                ld      (FILES_ENTIDX),a
                cp      16                      ; 512 / 32 entries per sector
                jr      c,df_entloop
                ld      hl,(FAT_DIRSEC)         ; advance to the next root-dir sector
                inc     hl
                ld      (FAT_DIRSEC),hl
                ld      hl,(FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM),hl
                jr      df_secloop
df_end:
                ; 🔴 D-DFEND (2026-09-12): BOTH SINKS ENDED THE WALK WRONG, IN
                ; OPPOSITE DIRECTIONS — the statement's two halves, one tail.
                ;
                ; SCREEN: this used to terminate the final line when CSRX was not
                ; column 1. The CF-3300 does NOT: measured three ways
                ; (scratchpad/kwdrain_fileseol.out, scratchpad/kwdrain_dfend.out)
                ; `FILES"HI.TXT"`, `FILES"PROG.BIN"` and a bare five-entry `FILES`
                ; all leave the cursor WHERE THE LAST ENTRY ENDED — column 18/19/31
                ; on the reference against column 0 of the next row here. The
                ; entries, the 8.3 padding and the three-per-row wrap agree
                ; exactly; only this one CR/LF did not. It is invisible from the
                ; prompt (`Ok` starts a fresh row either way), which is why it
                ; stood: it shows the moment a PROGRAM prints after `FILES`.
                ;
                ; PRINTER: the head column now goes back to 0, which
                ; docs/spec-basic-lfiles.md §3.3 recorded as deliberately NOT done
                ; — *"every LFILES entry ends with CR/LF, so the head is at column
                ; 0 when the statement ends and the R-LP16 flush at command level
                ; is a no-op either way. No row measures it."* The premise is true
                ; and the conclusion does not follow: the head is at column 0 when
                ; the statement ends only if nothing PARKED it mid-line first.
                ; `LPRINT"AB";` then `LFILES` reads LPOS 2 here against 0 on the
                ; CF-3300, and R-LP16 then puts two extra bytes on the printer
                ; (79 against 77) [[a-justification-parenthesis-is-an-unrun-claim]].
                ;
                ; 🔴 AND THE STORE IS CONDITIONAL BECAUSE THE UNCONDITIONAL ONE WAS
                ; MEASURED WRONG BEFORE IT WAS WRITTEN. `df_end` is reached whether
                ; or not the walk emitted anything, and on a no-match BOTH machines
                ; print `File not found`, send NOTHING to the printer, and leave the
                ; head parked — the R-LP16 flush must still fire, and both logs read
                ; 4 B. Zeroing unconditionally would have fixed the emitting arm and
                ; broken the empty one [[two-rules-that-coincide-on-every-row-you-have]].
                ; DISKOP_STATUS is 1 exactly when df_do_emit ran, and `dec a` leaves
                ; the 0 the store needs, so the condition costs one byte.
                ld      a,(DISKOP_OP)
                cp      DISKOP_SEL_LFILES
                ret     nz                      ; SCREEN: leave the cursor put
                ld      a,(DISKOP_STATUS)
                dec     a                       ; 1 = at least one entry emitted
                ret     nz                      ; nothing emitted -> head never moved
                ld      (LPTPOS),a              ; A is 0 here
                ret
tf_ioerr:
                ld      a,2
                ld      (DISKOP_STATUS),a       ; -> the head does load_error
                ret

; df_entptr — HL = FSECTOR_BUF + FILES_ENTIDX*32 (the current dir entry).
; Recomputed from RAM each time so the emit path's register clobber is harmless.
df_entptr:
                ld      a,(FILES_ENTIDX)
                ld      l,a
                ld      h,0
                add     hl,hl                   ; *2
                add     hl,hl                   ; *4
                add     hl,hl                   ; *8
                add     hl,hl                   ; *16
                add     hl,hl                   ; *32
                ld      de,FSECTOR_BUF
                add     hl,de
                ret

; df_emit — print one directory entry's 8.3 name field. HL -> the 32-byte
; directory entry (name at +0..10). Clobbers regs; the entry index lives in RAM
; so the caller re-derives the pointer.
df_emit:
                ; 🎯 R-LF1, THE RULE THAT COSTS THE BYTES. The printer form has no
                ; separator and no wrap: the wrap decision reads CSRX and LINLEN —
                ; the SCREEN cursor and the SCREEN width — so on the printer it is
                ; not merely wrong, it is reading an unrelated device. Knife K3
                ; sends the printer down this branch and predicts lfl-all/lfl-wild/
                ; lfl-sink go to three-per-row while both controls hold.
                ld      a,(DISKOP_OP)
                cp      DISKOP_SEL_LFILES
                jr      z,de_field
                ; separator / wrap decision from the live cursor column.
                ld      a,(CSRX)
                dec     a                       ; 0-based column (0 = line start)
                or      a
                jr      z,de_field              ; first field on the line
                ; not at line start: does a 12-char field + its trailing space
                ; still fit?
                ; 🔴 D-DFEND: THE SPACE IS NO LONGER A SEPARATOR EMITTED *BEFORE*
                ; THE NEXT FIELD. It is a TRAILING space, shared with the printer
                ; (see R-LF2 at the tail) -- because the two arrangements are
                ; indistinguishable ROW BY ROW and differ at the one place the
                ; reference could be read: where the cursor comes to REST. After
                ; `FILES"PROG.BIN"` the CF-3300 sits at column 19 and this sat at
                ; 18; after a bare five-entry listing, 26 against 25
                ; (scratchpad/kwdrain_dfend.out, three widths' worth of arms).
                ; The `cp 13` is DELIBERATELY UNCHANGED: requiring field+space to
                ; fit is what keeps the trailing space from landing past the last
                ; column and wrapping the cursor itself, and it reproduces the
                ; reference's three-per-row at LINLEN 40 and two-per-row at the
                ; pinned WIDTH 29 exactly as the separator form did.
                ld      b,a                     ; B = current 0-based column
                ld      a,(LINLEN)
                sub     b                       ; A = columns left on this line
                cp      13                      ; need 12 (field) + 1 (its space)
                jr      nc,de_field             ; room -> emit the field here
                call    df_crlf                 ; no room -> wrap to a new line
de_field:
                ; 8 name chars (raw, already upper-case + space-padded on disk)
                ld      b,8
de_name:
                ld      a,(hl)
                push    hl
                push    bc
                call    df_out
                pop     bc
                pop     hl
                inc     hl
                djnz    de_name
                push    hl                      ; '.' between name and extension
                ld      a,'.'
                call    df_out
                pop     hl
                ld      b,3                     ; 3 extension chars
de_ext:
                ld      a,(hl)
                push    hl
                push    bc
                call    df_out
                pop     bc
                pop     hl
                inc     hl
                djnz    de_ext
                ; R-LF2, WIDENED BY D-DFEND: the trailing space is now emitted on
                ; BOTH sinks; only the CR/LF after it stays printer-only. The old
                ; rule ("on the screen it carries neither -- the space there is a
                ; SEPARATOR emitted BEFORE the next field") described this code and
                ; not the reference: measured, the CF-3300's screen cursor rests one
                ; column PAST the last entry, which is the trailing space. Knife K4
                ; must move with it -- it pinned the arrangement, and the
                ; arrangement is what changed.
                ld      a,' '
                call    df_out
                ld      a,(DISKOP_OP)
                cp      DISKOP_SEL_LFILES
                ret     nz                      ; SCREEN: no CR/LF, the reference ends here
                ; fall through -> CR/LF

; df_crlf — end the current line on the active sink. This is print_crlf's body;
; print_crlf itself is main PAGE 1 and invisible from here, which is precisely the
; "head/body fork" that kept FILES out of the Phase-2 eviction.
df_crlf:
                ld      a,13
                call    df_out
                ld      a,10
                ; fall through -> df_out (its `ret` is this routine's)

; df_out — emit the byte in A to the active sink: CHPUT for FILES, LPTOUT for
; LFILES. Preserves HL/DE/BC, exactly as main's `pchar` does, so it is a drop-in
; for the `call CHPUT` sites this code carried while it was resident. Knife K2
; nails it to CHPUT and predicts an EMPTY printer log with both controls holding —
; the cut that separates the SINK from the LAYOUT.
df_out:
                push    hl
                push    de
                push    bc
                ld      c,a                     ; C survives the DISKOP_OP load
                ld      a,(DISKOP_OP)
                cp      DISKOP_SEL_LFILES
                ld      a,c
                jr      z,dfo_lpt
                call    CHPUT
                jr      dfo_done
dfo_lpt:
                call    LPTOUT
dfo_done:
                pop     bc
                pop     de
                pop     hl
                ret

; --- COPY "src" TO "dst": the body (D-COPY, docs/spec-basic-copy.md §3) ----------
; At the END of the file: placed between tnt_kill and tnt_files it pushed one of
; tnt_files' own `jr`s out of range.
; Op 6 stashes the parsed SOURCE name (DISK_FCB_NAME is the only 8.3 buffer and
; the destination reuses it). Op 7, with DISK_FCB_NAME = the destination:
;   mount; refuse a self-copy and a wildcard source (STATUS 3 -> ERR 5, both
;   measured); fat_find the source FIRST -- it records the entry's location in
;   FWR_DIRSEC/FWR_DIROFF, which the destination's create must own afterwards --
;   and stash its first cluster and size (the destination's delete and create
;   clobber FAT_FIRSTCLUS/FAT_FILESIZE through fat_find); delete an old
;   destination (the reference overwrites), create the new one and reset the
;   write cursor exactly as fat_io_create does; reopen the source; then per
;   sector: fat_read_file_sector -> FSECTOR_BUF, n = min(512, left),
;   FWR_BUFLEN = n, FWR_BYTES += n, fat_flush_data_sector (which allocates the
;   chain as it goes); finally fat_dir_update stamps size + first cluster.
; The read iterator (FAT_CURCLUS/FAT_CLUSSEC) and the write cursor (FWR_*) are
; disjoint cells; FSECTOR_BUF is the one shared buffer and that is the point.
; STATUS: 0 source not found (ERR 53), 1 copied, 2 mount/full/I-O (load_error),
; 3 refused (ERR 5).
tnt_copystash:
                ld      hl,DISK_FCB_NAME
                ld      de,COPY_SRC
                ld      bc,11
                ldir
                ret
tnt_copy:
                call    fat_mount
                jp      c,tf_ioerr              ; STATUS = 2
                ld      hl,COPY_SRC
                ld      de,DISK_FCB_NAME
                ld      b,11
tc_same:        ld      a,(de)
                cp      (hl)
                jr      nz,tc_differ
                inc     hl
                inc     de
                djnz    tc_same
                jp      tc_ill                  ; all 11 bytes equal: a self-copy
tc_differ:      ld      hl,COPY_SRC
                ld      b,11
tc_wild:        ld      a,(hl)
                cp      '?'                     ; pdfcb turns '*' into '?'s too
                jp      z,tc_ill
                inc     hl
                djnz    tc_wild
                ld      hl,COPY_SRC
                call    fat_find
                jp      c,tc_notfound           ; STATUS = 0
                ld      hl,(FAT_FIRSTCLUS)
                ld      (COPY_CLUS),hl
                ld      hl,(FAT_FILESIZE)
                ld      (COPY_LEFT),hl
                ld      hl,(FAT_FILESIZE+2)
                ld      (COPY_LEFT+2),hl
                call    fat_delete              ; an old destination; Cy = 1 "none" is fine
                ld      hl,DISK_FCB_NAME
                call    fat_dir_create
                jp      c,tf_ioerr
                xor     a
                ld      (FWR_SECIDX),a
                ld      hl,0
                ld      (FWR_CLUS),hl
                ld      (FWR_FIRST),hl
                ld      (FWR_BYTES),hl
                ld      (FWR_BYTES+2),hl
                ld      hl,(COPY_CLUS)
                ld      (FAT_FIRSTCLUS),hl
                call    fat_open
tc_loop:
                ld      hl,(COPY_LEFT)
                ld      a,(COPY_LEFT+2)
                or      h
                or      l
                jr      z,tc_done
                call    fat_read_file_sector    ; -> FSECTOR_BUF
                jr      c,tc_done               ; chain ended before the size did: stamp what arrived
                ld      de,512
                ld      hl,(COPY_LEFT)
                ld      a,(COPY_LEFT+2)
                or      a
                jr      nz,tc_n                 ; >= 65536 left: a whole sector
                or      a
                sbc     hl,de
                jr      nc,tc_n                 ; >= 512 left: a whole sector
                ld      de,(COPY_LEFT)          ; the tail: n = left
tc_n:           ld      (FWR_BUFLEN),de
                ld      hl,(COPY_LEFT)          ; left -= n
                or      a
                sbc     hl,de
                ld      (COPY_LEFT),hl
                jr      nc,tc_nb
                ld      hl,COPY_LEFT+2
                dec     (hl)
tc_nb:          ld      hl,(FWR_BYTES)          ; FWR_BYTES += n
                add     hl,de
                ld      (FWR_BYTES),hl
                jr      nc,tc_fl
                ld      hl,FWR_BYTES+2
                inc     (hl)
tc_fl:          call    fat_flush_data_sector   ; allocates/extends, writes FSECTOR_BUF
                jp      c,tf_ioerr
                jr      tc_loop
tc_done:        call    fat_dir_update          ; true size + first cluster
                jp      c,tf_ioerr
                ld      a,1
                jr      tc_st
tc_ill:         ld      a,3
                jr      tc_st
tc_notfound:    xor     a
tc_st:          ld      (DISKOP_STATUS),a
                ret
