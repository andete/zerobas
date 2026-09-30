; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — bload.asm  (the BLOAD verb tenant)
; ===========================================================================
; The whole BLOAD verb body — device dispatch, the cassette load loop and the
; disk load loop — evicted from main page 1 into sub-ROM PAGE 1
; (docs/spec-traps-t3-key.md §7.6) to fund the interrupt-traps T3 slice. This is
; the fcbname/casmatch eviction pattern one level larger: the moved code is
; VERBATIM, shared through basic/bload-body.inc, and
; includes at its original position so that ROM stays byte-identical.
;
; WHY PAGE 1, AND WHY THAT IS THE WHOLE POINT. A page-1 tenant runs with main
; page 1 switched out but the sub-ROM's own page 1 mapped — so it sits beside
; `fatprim_tenant` and calls `fat_mount` / `fat_find` / `fat_open` /
; `fat_read_file_sector` **sub-locally**, as ordinary in-page calls. In main page
; 1 those same four names are marshalling stubs that CALSLT into this very ROM.
; That round trip is exactly what made BLOAD look un-evictable (`do_disk_bload ->
; fat_io_open -> fat_find -> subrom_call`, a low-region call that is paged out
; while a tenant runs — and a nested sub-ROM call besides). Moving the caller to
; the callee's side dissolves it. Same for `build_83_name`, already resident here
; as a page-1 tenant body (sub/fcbname.asm): the resident marshalling shim
; disappears for our path.
;
; WHAT STAYS RESIDENT, and why each one has to:
;   * `load_handoff` — the `,R` tail ends in `jp (hl)` INTO THE LOADED PROGRAM and
;     never returns. Run inside this tenant's CALSLT it would leave main page 1
;     switched out forever. The tenant returns normally; the resident stub does
;     the handoff (basic/bload.asm).
;   * `load_error` / `print_string` — the reporter, 61 external callers.
;   * `parse_disk_fcb` (9 external callers) and `parse_close_run` (6) — shared
;     service routines that merely LIVED in bload.asm. They are COPIED here, not
;     moved: a duplicate in the sub-ROM costs zero main page-1 bytes.
;
; INTERRUPTS. The cassette path holds the CPU for the length of a tape read.
; subrom_call enters DI, so this tenant re-enables interrupts at entry and
; disables them before returning. That is safe here for the same reason
; play_service is: an IRQ vectors to $0038 in MAIN page 0, which stays mapped
; throughout a page-1 tenant, and `htimi_guard` (basic/subromcall.asm) sees that
; page 1 is not main-ROM and skips the PLAY/trap seam for that frame. Without
; that guard this would be a wild jump — it is the same hazard
; docs/spec-traps-t1-htimi-page1-safety.md was written for.
;
; MARSHALLING: BL_PTR in (the token cursor after the BLOAD token), BL_STAT out
; (0 = loaded, 1 = load_error, 2 = file not found — D-BLNF). subrom_call clobbers every register and forces
; CF=0 on return, so neither the cursor nor a carry can ride in registers — the
; fatprim/fcbname pattern. Unlike fcbname these need cells of their OWN rather
; than aliasing DISKOP_HL/DISKOP_STATUS: the status is held ACROSS the whole
; load, during which the fatprim cells are live on every getbyte.
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/bload.asm and
; basic/fat.asm. Provenance for the BSAVE tape/disk formats, the DSKIO contract
; and FAT12 is unchanged (basic/PROVENANCE.md). The dispatch/marshalling glue is
; own-design, the casmatch/fatprim/fcbname precedent. No reference-ROM
; disassembly. See sub/PROVENANCE.md.
; ===========================================================================

; --- bload_tenant: the SUBROM_IDX_BLOAD entry ------------------------------
bload_tenant:
                xor     a
                ld      (BL_STAT),a         ; assume success; load_error flips it
                ld      (DISKOP_ERR),a      ; D-DISKERR: no DSKIO failure pending yet
                ld      hl,(BL_PTR)         ; token cursor (from the resident stub)
                ei                          ; the tape path needs a live ISR; htimi_guard
                                            ; makes that safe while page 1 is ours
                call    do_bload
                di                          ; subrom_call's CALSLT returns under DI
                ret

; --- sub-local clones of the resident helpers the body calls ----------------
; These are COPIES, not evictions: every one of them stays resident too, for
; callers outside bload.asm. A sub-ROM duplicate costs no main page-1 bytes.

; bl_skip_spaces — byte-identical clone of basic/interp.asm. It needs a distinct
; name because the sub image already defines `skip_spaces` in its PAGE 0
; (sub/readdata.asm), which is unmapped while this page-1 tenant runs -- the same
; reason fcbname.asm's upcaser is called fcb_upcase.
bl_skip_spaces:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      bl_skip_spaces

; bl_upcase — page-1 upcaser clone. sub/fcbname.asm already carries an identical
; one (fcb_upcase), and `bl_upcase equ fcb_upcase` would have reused it — but
; check_tenant_closure.py --page1 tells a sub-local routine from a switched-out
; main one BY NAME (a defined label vs an imported equ), so an alias reads to the
; gate as a main-page-1 escape. Six bytes of free sub-ROM space is a better
; answer than weakening a standing gate to accept aliases.
bl_upcase:
                cp      'a'
                ret     c
                cp      'z'+1
                ret     nc
                sub     $20
                ret

; load_error — sub-local reporter. Deliberately MIRRORS the resident routine's
; shape (TAPIOF, ERRMARK, then `ret`) instead of aborting, because the body
; reaches it by `jp` from several stack depths — including from inside
; parse_disk_fcb, where the `ret` lands back in the CALLER (a known nested-reject
; hazard, [[load-error-is-not-abort]]). Changing the stack behaviour here would
; silently change control flow on the error path, so it is preserved exactly; the
; only difference is that the message is not printed here. The resident stub sees
; BL_STAT and reports once, which also removes the double-report the resident
; path could produce.
; D-FSPEC: the TENANT's binding for parse_disk_fcb's malformed-name exit. The
; RESIDENT copy raises ERR 56 `Bad file name` (basic/str-engine.asm); here it
; keeps the file-and-return shape, because the only caller of this copy is
; do_bload below and BLOAD's answer to a malformed name is UNMEASURED. Moving an
; unmeasured verb on a reading taken for five others is exactly what D-DSKMSG
; declined to do for NAME.
pdf_badname     equ     bl_load_error
pdf_baddrive    equ     bl_load_error   ; D-DRVNAME: the same, for a drive past B:

bl_load_error:
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
                ld      a,1
                ld      (BL_STAT),a
                ret

; bl_notfound — the DISK not-found arm (D-BLNF). Same shape and same stack
; behaviour as bl_load_error above (reached by `jp`, returns into whoever called
; the tenant body), but it files BL_STAT = 2 instead of 1 and the resident stub
; turns that into a RAISED ERR 53 `File not found` — which is what both
; references answer (docs/loaderr-msx1-characterization.md §4).
;
; ⚠️ NO TAPIOF AND NO ERRMARK, ON PURPOSE, AND NEITHER IS AN OVERSIGHT. This arm
; is reachable ONLY from do_disk_bload after a SUCCESSFUL fat_mount, so no tape
; is running to stop; and `$EE` at ERRMARK is the landmark for the PRINTED `load
; error` (basic/bload.asm), which this is not. Dropping it here would make a
; raised error indistinguishable from a printed one to every probe that reads
; that cell.
;
; 🔴 AND THIS IS WHY THE TAPE ARM IS UNTOUCHED. D-LOADERR-FIX broke the cassette
; by guarding one instance of a shared tail instead of the class; the answer was
; to keep the SHARED tail's default the safe one and make the not-found reading
; opt-in. Same discipline here: bl_load_error still serves every cassette
; failure, every parse failure and every mount failure, and only a call site
; that has PROVED the volume mounted may come here.
;
; 🔴 D-BLMODE (2026-08-21): THE CELL NOW CARRIES AN **ERR CODE**, NOT AN INDEX.
; BL_STAT is 0 = loaded, 1 = `load error` PRINTED, and **anything else is the MSX
; ERR code the resident stub must RAISE**. That is one byte of main page 1 for
; the whole family (`cp 1` instead of `dec a`, then `jp raise_error` with A
; already right) where a fourth enumerated value would have cost six.
; ⚠️ THE HAZARD, NAMED RATHER THAN DISCOVERED: **BLOAD can never raise ERR 1**
; (`NEXT without FOR`) through this cell, because 1 is taken. That is not a
; restriction anything could want, but it is a real one and it is written down
; here so the next arm does not find it by measuring.
bl_badmode:
                ld      a,61                ; ERR 61 `Bad file mode` -- the file
                                            ; EXISTS and is not a BSAVE binary.
                                            ; MEASURED 2026-08-21: the CF-3300
                                            ; RAISES this and STOPS the program,
                                            ; for `PROG.BAS` (tokenised BASIC)
                                            ; AND for `TEST.BIN` (data with a
                                            ; .BIN name) alike -- so the rule is
                                            ; about the $FE MARKER, not the
                                            ; extension.
                jr      bl_stat_raise
bl_notfound:
                ld      a,53                ; ERR 53 `File not found` -- mounted,
                                            ; name not in the directory (D-BLNF)
bl_stat_raise:
                ld      (BL_STAT),a
                ret

; pcr_noquote — the `,R` / `,S` option tail. Near-verbatim copy of the resident
; routine (basic/bload.asm); parse_disk_fcb needs no copy here, it arrives with
; the body via basic/pdfcb-body.inc and binds to the sub-local build_83_name
; rather than the resident marshalling shim.
;
; 🔴 D-FNEXPR2: THE `parse_close_run` HEAD IS **GONE FROM THIS COPY**, AND THE
; DEADCODE GATE IS WHAT SAID SO. Once the filename is a string EXPRESSION the
; tenant's two arms both enter at `pcr_noquote` — there is no closing quote in
; the program text to consume, only the one `fname_expr` appended to its staged
; copy in STRSCR — so the four-instruction quote check had no caller left in
; THIS build and `check_dead_code.py` reported it as an unreachable 6 B span.
; 🔴 AND THE RESIDENT COPY LOST ITS HEAD ONE COMMIT LATER (D-FNRUN), WHICH IS
; NOT THE ASYMMETRY THIS NOTE ORIGINALLY CLAIMED. It read: *"the resident copy
; KEEPS its head, and that asymmetry is the point rather than an oversight:
; `do_run` still parses a literal quote out of program text."* True for exactly
; one commit. `do_run` was the head's last caller anywhere, and once RUN took a
; string EXPRESSION the resident four instructions were dead too.
; ⚠️ **The gate did not say so, and the reason is in basic/bload.asm beside the
; surviving routine**: the three mentions of the old name in THIS comment seeded
; the main-build label, because `check_dead_code.py` scrapes identifiers out of
; `sub/` and `tools/` including from comments. "Dead" is still per-build — that
; part stands — but a per-build reading can be masked by prose in the other
; build's tree.
pcr_noquote:
                xor     a
                ld      (RUNFLAG),a         ; default: no ,R handoff
                ld      (VRAM_FLAG),a       ; default: RAM load
                call    bl_skip_spaces
                or      a
                jr      z,pcr_ok
                cp      COLON
                jr      z,pcr_ok
                cp      ','
                jr      nz,pcr_err
                inc     hl                  ; past the comma
                call    bl_skip_spaces
                call    bl_upcase              ; accept ,r / ,s as well
                cp      'R'
                jr      z,pcr_run
                cp      'S'
                jr      z,pcr_vram
                jr      pcr_err
pcr_run:
                ld      a,1
                ld      (RUNFLAG),a
                jr      pcr_flag_end
pcr_vram:
                ld      a,1
                ld      (VRAM_FLAG),a
pcr_flag_end:
                inc     hl                  ; past the flag letter
                call    bl_skip_spaces
                or      a
                jr      z,pcr_ok
                cp      COLON
                jr      z,pcr_ok
                ; fall through to pcr_err
pcr_err:
                scf
                ret
pcr_ok:
                ld      (FN_RESUME),hl      ; D-SAVECOLON: the cursor past the tail,
                                            ; for main's load_handoff to continue at
                or      a                   ; CF clear = success
                ret

; dev_cas — the device name the body compares against.
dev_cas:
                db      "CAS:",0

; The sequential FAT12 read layer. Identical source to the resident copy, but
; here fat_mount/fat_find/fat_open/fat_read_file_sector bind to sub/fatprim.asm's
; REAL implementations instead of the marshalling stubs -- the whole reason this
; tenant is affordable.
                include "basic/fatio-body.inc"       ; fat_io_open + fat_io_getbyte

; --- seqio_tenant: a sequential TEXT file's bytes, the reference's way (D-SEQEOF) --
; SUBROM_IDX_SEQIO. Measured on the CF-3300 (scratchpad/ipe_probe.py, 16 cases:
; ipe_run.out, ipe_run2.out, ipe_run3.out), three rules zerobas broke:
;   R1  Ctrl-Z ($1A) is a SOFT end of file and is never consumed: INPUT stops
;       before it, EOF() is -1 when it is NEXT, a read at it is 55.
;   R2  INPUT# / LINE INPUT# swallow the LF after their CR; INPUT$ does not.
;   R3  a read at the end raises 55 -- main's side (files.asm, strvar.asm).
; It runs HERE because main had ~42 B and the rules cost ~59 there: this is the
; same fatio copy BLOAD uses, bound to the real primitives, on main's own FREAD_*
; and FAT_DBUF. A crossing per byte is what the reference does too (H.INDS).
;   in : L = 0 -> the next byte (FCH_RDMODE 2 = INPUT$, raw; else the INPUT#
;               line rule); L = 2 -> EOF()'s test for the selected channel;
;        L = 4 -> one NUMERIC INPUT # item into STRSCR (D-CHANSWITCH, sq_numitem)
;   out: A = the byte; SEQ_EOF = 1 when there was none (the end, or Ctrl-Z next),
;        else 0 -- subrom_call returns only A, so the flag rides in RAM.
seqio_tenant:
                ld      a,l
                cp      4
                jp      z,sq_numitem        ; D-CHANSWITCH (`jp`: sq_deveof sits between)
                cp      6
                jr      z,sq_deveof         ; D-EOFCAS
                or      a
                jr      nz,sq_eoftest
                call    seq_peek            ; A = next byte; CF = nothing to read
                jr      c,sq_end
                call    fat_io_getbyte      ; consume it
                cp      $0D
                jr      nz,sq_byte
                ld      a,(FCH_RDMODE)
                cp      2                   ; INPUT$ reads the CR-LF pair as data
                jr      z,sq_cr
                call    seq_peek            ; INPUT#: what follows the CR?
                jr      c,sq_cr
                cp      $0A
                call    z,fat_io_getbyte    ; an LF: swallow it (R2)
sq_cr:
                ld      a,$0D
sq_byte:
                ld      hl,SEQ_EOF
                ld      (hl),0
                ret
sq_eoftest:
                ld      a,(FCH_MODE)
                dec     a                   ; open FOR INPUT?
                jr      z,sq_eofpeek
                ld      hl,(FREAD_LEFT)     ; any other mode: the byte count, as
                ld      de,(FREAD_LEFT+2)   ; EOF() always read it -- never a peek,
                ld      a,h                 ; which could refill FAT_DBUF over an
                or      l                   ; OUTPUT channel's unwritten bytes
                or      d
                or      e
                jr      z,sq_end
                jr      sq_byte
sq_eofpeek:
                call    seq_peek
                jr      nc,sq_byte
sq_end:
                ld      a,1
                ld      (SEQ_EOF),a
                ret

; --- sq_deveof: L = 6 -- EOF() on a NON-DISK channel, H = its mode (D-EOFCAS) --
; Measured on the CF-3300 (scratchpad/eofcas_run.out): a tape opened FOR INPUT
; answers 0 while data remains and -1 once the last line is read. The tape
; reader keeps (CAL_CURHI:CAL_CNT) on the NEXT byte after every serve (a drained
; buffer is swapped for the read-ahead one on the byte that drains it), and
; latches CAL_NEEDFILL = 2 when there is none -- so the end is that latch, or a
; Ctrl-Z next, the same soft end cas_in_getbyte stops INPUT# on. A peek, nothing
; consumed. Any OTHER device channel keeps ev_f_ifc's answer, which is main's
; deferred FPERR=3 (first error wins) with EOF reading 0.
sq_deveof:
                ld      a,h
                cp      CAS_IN_MODE
                jr      nz,sq_devifc
                ld      a,(CAL_NEEDFILL)
                cp      2
                jr      z,sq_end            ; the tape's last byte was served
                ld      a,(CAL_CURHI)
                ld      h,a
                ld      a,(CAL_CNT)
                ld      l,a
                ld      a,(hl)              ; the next byte, not consumed
                ; 🔴 LOOK PAST ONE LF. The reference's INPUT# swallows the LF after
                ; its CR; our line reader (read_into_strscr) ignores an LF only when
                ; it REACHES it, so after the last line the LF is still next and a
                ; bare peek read 0 where the CF-3300 reads -1 (eofcas_after.out,
                ; first cut). The byte after it may be the read-ahead buffer's
                ; first -- or nothing, when no block follows (CAL_NEEDFILL != 0).
                cp      $0A
                jr      nz,sq_dev1a
                inc     l
                jr      nz,sq_devnext       ; still inside this buffer
                ld      a,(CAL_NEEDFILL)
                or      a
                jr      nz,sq_end           ; the LF was the tape's last byte
                ld      a,h
                xor     CAL_XORHI
                ld      h,a                 ; the read-ahead buffer, offset 0
sq_devnext:
                ld      a,(hl)
sq_dev1a:
                cp      $1A
                jr      z,sq_end            ; Ctrl-Z next: the soft end
                jr      sq_byte
sq_devifc:
                ld      a,(FPERR)
                or      a
                jr      nz,sq_byte          ; a fault is already pending: it wins
                ld      a,3                 ; FPERR 3 -> ERR 5, as ev_f_ifc
                ld      (FPERR),a
                jr      sq_byte

; --- sq_numitem: L = 4 -- ONE NUMERIC INPUT # item into STRSCR (D-CHANSWITCH) --
; Measured on the CF-3300 (scratchpad/inpnum_run2.out, inpnum_run3.out): leading
; blanks, CRs and LFs are skipped; the item ends at a blank, a comma or a CR; then
; the blanks after it are eaten, and ONE comma, or ONE CR with its LF, with them
; -- but any other byte belongs to the NEXT item and stays: `" 1  2 "` read with
; INPUT #1,X leaves "2 " for a LINE INPUT, `" 1 \r\n"` leaves nothing (EOF is -1
; after the last number), `"1   ,2"` leaves "2". Leaving a byte needs a PEEK,
; which is why this lives here and not in main's read_into_strscr (D-INPNUM's
; first cut ended the item at the blank and left " \r\n": the NEXT read met the
; CR and returned 0, so two numbers on two lines read `1 0 2 0`).
; out: STRSCR = [len][bytes]; SEQ_EOF = 1 only when the end came before any byte.
sq_numitem:
                xor     a
                ld      (IN_RDLEN),a
sqn_lead:
                call    seq_peek
                jr      c,sqn_eof           ; the end before any byte
                cp      ' '
                jr      z,sqn_skip
                cp      $0D
                jr      z,sqn_skip
                cp      $0A
                jr      nz,sqn_body
sqn_skip:
                call    fat_io_getbyte
                jr      sqn_lead
sqn_body:
                call    seq_peek
                jr      c,sqn_done          ; the end (or Ctrl-Z) closes the item
                cp      ' '
                jr      z,sqn_tail
                cp      ','
                jr      z,sqn_tail
                cp      $0D
                jr      z,sqn_tail
                call    fat_io_getbyte      ; A = the byte (it clobbers the rest)
                ld      c,a
                ld      a,(IN_RDLEN)
                cp      STRMAX
                jr      nc,sqn_body         ; full: drop it, keep consuming
                ld      e,a
                ld      d,0
                ld      hl,STRSCR+1
                add     hl,de
                ld      (hl),c
                ld      hl,IN_RDLEN
                inc     (hl)
                jr      sqn_body
sqn_tail:
                call    seq_peek
                jr      c,sqn_done
                cp      ' '
                jr      nz,sqn_delim
                call    fat_io_getbyte      ; a blank after the number
                jr      sqn_tail
sqn_delim:
                cp      ','
                jr      z,sqn_eat
                cp      $0D
                jr      nz,sqn_done         ; the NEXT item's byte: leave it
                call    fat_io_getbyte      ; the CR ...
                call    seq_peek
                jr      c,sqn_done
                cp      $0A
                jr      nz,sqn_done
sqn_eat:
                call    fat_io_getbyte      ; ... and its LF, or the comma
sqn_done:
                ld      a,(IN_RDLEN)
                ld      (STRSCR),a
                jp      sq_byte             ; SEQ_EOF = 0
sqn_eof:
                xor     a
                ld      (STRSCR),a
                jp      sq_end              ; `jp`: sq_deveof sits between (D-EOFCAS)

; seq_peek -- the next byte WITHOUT consuming it: A = it, CF clear; CF set when
; nothing is left or the next byte is Ctrl-Z (R1). fat_io_getbyte's own bounds
; and refill, stopped short of the advance, so a peek that refills leaves
; FREAD_OFF at 0 exactly as the getbyte after it expects.
seq_peek:
                ld      hl,(FREAD_LEFT)
                ld      de,(FREAD_LEFT+2)
                ld      a,h
                or      l
                or      d
                or      e
                jr      z,sqp_end
                ld      hl,(FREAD_OFF)
                ld      de,512
                or      a
                sbc     hl,de
                jr      c,sqp_have
                call    fat_read_file_sector
                jr      c,sqp_end
                ld      hl,0
                ld      (FREAD_OFF),hl
sqp_have:
                ld      hl,(FREAD_OFF)
                ld      de,FAT_DBUF
                add     hl,de
                ld      a,(hl)
                cp      $1A
                jr      z,sqp_end
                or      a
                ret
sqp_end:
                scf
                ret

; The verb body itself, shared with the resident side.
                include "basic/bload-body.inc"       ; do_bload .. disk_load_fin
