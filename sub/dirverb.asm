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
                ld      a,(DISKOP_OP)
                or      a
                jp      z,tnt_kill              ; DISKOP_SEL_KILL = 0
                cp      DISKOP_SEL_FILES
                jp      z,tnt_files             ; 2 -> FILES  (screen)
                cp      DISKOP_SEL_LFILES
                jp      z,tnt_files             ; 3 -> LFILES (printer)
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
; back (0 -> the head raises "File not found").
tnt_kill:
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
                ; Seed the matched-any flag. A filespec starts at "nothing matched"
                ; so a miss can raise ERR 53; a BARE listing starts at "ok", because
                ; an EMPTY directory is not `File not found` on this build and that
                ; arm is unmeasured (spec §2.4 — it needs an empty-disk fixture this
                ; battery does not have). FILES_HASPAT is 0 or 1 only, so one `xor`
                ; inverts it.
                ld      a,(FILES_HASPAT)
                xor     1
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
                ; SCREEN: terminate the final line if we stopped mid-line
                ; (CSRX != column 1). PRINTER: nothing to do — R-LF1 says every
                ; entry already ended its own line, and CSRX is the SCREEN cursor,
                ; which a printer does not move.
                ld      a,(DISKOP_OP)
                cp      DISKOP_SEL_LFILES
                ret     z
                ld      a,(CSRX)
                dec     a
                ret     z
                jp      df_crlf
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
                ; not at line start: does " " + a 12-char field still fit?
                ld      b,a                     ; B = current 0-based column
                ld      a,(LINLEN)
                sub     b                       ; A = columns left on this line
                cp      13                      ; need 1 (space) + 12 (field)
                jr      nc,de_sep               ; room -> print the separating space
                call    df_crlf                 ; no room -> wrap to a new line
                jr      de_field
de_sep:
                push    hl
                ld      a,' '
                call    df_out
                pop     hl
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
                ; R-LF2: on the PRINTER the entry carries a TRAILING SPACE after
                ; the extension, and then ends its line. On the screen it carries
                ; neither — the space there is a SEPARATOR emitted BEFORE the next
                ; field (de_sep), which is not the same byte in the same place, and
                ; knife K4 is the row that says so.
                ld      a,(DISKOP_OP)
                cp      DISKOP_SEL_LFILES
                ret     nz
                ld      a,' '
                call    df_out
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
