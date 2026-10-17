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

; (bl_skip_spaces, the space-skipper clone, went with the tail parse it served
; -- D-BLOADOFS, 2026-10-07; check_dead_code reported it the same build.)

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

; bl_tape_dio -- D-CASBIN (2026-10-08): the tape SEARCH failed (an I/O error or
; Ctrl-STOP -- cas_open_match's CF): motor off, BL_STAT = 19, and the resident
; stub RAISES it, as main's dpl_dio does for LOAD / CLOAD / RUN / OPEN / MERGE
; (D-CASBRK: the VG-8020's `19 in 20`). Reached by `jp` at do_bload's depth.
bl_tape_dio:
                call    TAPIOF
                ld      a,19                ; Device I/O error
                ld      (BL_STAT),a
                ret

                include "basic/cascap-body.inc"     ; cas_capture_name (D-CASBIN)
                include "basic/cascut-body.inc"     ; cas_capture_cut: a '.' ends the name (D-CASDOT)

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

; 🗑️ D-BLOADOFS (2026-10-07): the tenant's own copy of the option-tail parse is
; GONE. BLOAD's tail now carries an `,offset` EXPRESSION, and `eval` is main page
; 1, switched out while this page-1 tenant runs -- so main parses the whole tail
; (basic/bload.asm pcr_bload) before calling in, as the SAVE family always has.

; dev_cas — the device name the body compares against.
dev_cas:
                db      "CAS:",0

; The sequential FAT12 read layer. Identical source to the resident copy, but
; here fat_mount/fat_find/fat_open/fat_read_file_sector bind to sub/fatprim.asm's
; REAL implementations instead of the marshalling stubs -- the whole reason this
; tenant is affordable.
                include "basic/fatio-body.inc"       ; fat_io_find + fat_io_getbyte

; --- seqio_tenant: EOF() on a NON-DISK channel (SUBROM_IDX_SEQIO) -----------------
; 🗑️ S10.C (D-ROMSIZE, 2026-10-15): THIS TENANT USED TO READ DISK TEXT FILES.
; It was D-SEQEOF's (scratchpad/ipe_probe.py, ipe_run*.out -- R1 Ctrl-Z a soft end
; never consumed, R2 INPUT# swallowing the LF after its CR, R3 a read at the end
; is 55) and D-CHANSWITCH's numeric item (inpnum_run2/3.out): L = 0 a byte, 2
; EOF()'s test, 4 one numeric INPUT # item, over this copy of fatio-body.inc on
; main's FREAD_* globals. An INPUT channel is disk.rom's FCB since S10.C, and those
; three ops moved there whole, rules and all (disk/fat.asm hk_chin: din_byte /
; din_peek / din_num). Its `sq_eoftest` arm for modes other than INPUT was already
; dead -- ev_ff_eof raises 61 for them before it calls (D-EOFMODE).
; What is left is op 6, the TAPE's EOF, and it is now the only op: main's eof_dev
; (basic/expr.asm) sends H = the channel's mode and no op byte.
;   in : H = the channel's FCH_MODES value (not a disk file)
;   out: SEQ_EOF = 1 at the end, else 0 (subrom_call returns only A, so the flag
;        rides in RAM).
seqio_tenant:
; --- sq_deveof: EOF() on a NON-DISK channel, H = its mode (D-EOFCAS) --------
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
                ld      hl,(CAS_BUFP)       ; D-CASFCB: the channel's own buffer
                ld      a,(CAL_CNT)
                ld      e,a
                ld      d,0
                add     hl,de
                ld      a,(hl)              ; the next byte, not consumed
                ; 🔴 LOOK PAST ONE LF. The reference's INPUT# swallows the LF after
                ; its CR; our line reader (read_into_strscr) ignores an LF only when
                ; it REACHES it, so after the last line the LF is still next and a
                ; bare peek read 0 where the CF-3300 reads -1 (eofcas_after.out,
                ; first cut). The byte after it may be the read-ahead buffer's
                ; first -- or nothing, when no block follows (CAL_NEEDFILL != 0).
                cp      $0A
                jr      nz,sq_dev1a
                inc     hl
                inc     e
                jr      nz,sq_devnext       ; still inside this buffer
                ; D-CASFCB: the LF is the buffer's LAST byte, and with one buffer the
                ; byte after it is not read yet. Consume the LF (the line reader
                ; ignores it anyway) and read the next block: none -> the end.
                call    cal_refill          ; CAL_CNT 0 after; CF = no further block
                ld      a,2
                jr      c,sq_devlast
                xor     a
sq_devlast:
                ld      (CAL_NEEDFILL),a
                jr      c,sq_end
                ld      hl,(CAS_BUFP)       ; the new block, offset 0
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
sq_byte:                                    ; not at the end
                ld      hl,SEQ_EOF
                ld      (hl),0
                ret
sq_end:                                     ; at the end
                ld      a,1
                ld      (SEQ_EOF),a
                ret

; The verb body itself, shared with the resident side.
                include "basic/bload-body.inc"       ; do_bload .. disk_load_fin
