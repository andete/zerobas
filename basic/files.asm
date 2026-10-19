; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; files.asm — Disk BASIC file-channel verbs (Phase 2), built by EXTEND over the
; existing basic/fat.asm engine (file-channel-protocol.md §4/§5: the file verbs
; move bytes through the SAME standard DSKIO+FAT12 substrate as the loader, so
; they are layered on fat.asm, not delegated to the in-slot Disk BASIC).
;
; First verbs: FILES / LFILES — list the root-directory file names.
;
;   FILES  ["[drive:]pattern"]   list the root directory on the SCREEN
;   LFILES ["[drive:]pattern"]   list it on the PRINTER, one entry per line
;
; Output format (oracle-pinned, black-box, real National CF-3300 Disk BASIC v1.0,
; diskbasic_probe_files.py): each entry renders as the 8.3 name in a fixed 12-char
; field — 8-char name (space-padded) + '.' + 3-char extension (space-padded).
; Deleted ($E5) and volume/sub-dir entries are skipped; the listing stops at the
; first free ($00) directory slot. The two verbs then differ, and 🎯 THAT IS THE
; WHOLE POINT OF D-LFILES (docs/spec-basic-lfiles.md, R-LF1):
;   * FILES  packs as many fields as fit the active text width, separated by a
;     single space, wrapping on the live cursor column (CSRX) against the active
;     width (LINLEN) — the faithful MSX algorithm, so it reproduces CF-3300's
;     2-per-line at WIDTH 29 and scales to any width;
;   * LFILES prints ONE ENTRY PER LINE, each field followed by a trailing space
;     and CR/LF — no separator and no wrap arithmetic at all, because the wrap
;     reads the SCREEN cursor and the SCREEN width and a printer moves neither.
; A sink re-point alone would put the screen layout on the printer and pass any
; battery that only checked which DEVICE got the bytes; `lfl-all`/`lfl-wild` read
; the bytes (docs/lptverb-msx1-characterization.md §4).
;
; A filespec argument filters with 8.3 '*'/'?' wildcards (R-LF3); no match prints
; nothing and raises ERR 53 `File not found` (R-LF4, and R-LF6 says FILES answers
; the same way — see df_notfound below).
;
; 🎯 THE WALK AND THE EMIT ARE NOT HERE. They are the fourth and fifth ops of the
; sub-ROM page-1 dirverb_tenant (sub/dirverb.asm, DISKOP_SEL_FILES /
; DISKOP_SEL_LFILES) — the eviction Phase 2 of the disk/file cluster listed and
; DROPPED, because "its emit loop interleaves CHPUT + main-resident print_crlf, a
; head/body fork" (docs/spec-evict-diskfile-cluster.md §12). That reason is spent:
; a page-1 tenant keeps page 0 mapped, so CHPUT and LPTOUT are both reachable, and
; print_crlf is pchar(13)+pchar(10) over a sink that is CHPUT whenever PRDEST=0 —
; which exec_stmt guarantees at the top of every statement. What stays here is the
; head the split forces: the DISKSLOT_OK test, the eval-side filespec parse, one
; subrom_call and the statement tail. docs/spec-basic-lfiles.md §2.
;
; ✅ AN EMPTY DIRECTORY TAKES THE SAME ARM SINCE 2026-08-07 (D-DSKMSG, R-LF7,
; docs/lptverb-msx1-characterization.md §4.2). A bare FILES/LFILES over a
; mounted, writable, EMPTY volume raises `File not found` on both references and
; on zerobas; the divergence listed below used to read "prints nothing rather
; than `File not found` — an arm no row measures (spec §2.4), left as it was",
; and it is gone because the fixture now exists (`make_test_dsk.py --empty`).
;
; Divergences (own design, documented in basic/PROVENANCE.md §FILES):
;   * the disk-name / "Ok" framing is the REPL's, not emitted here;
;   * on a missing disk slot / mount / I-O error FILES/LFILES reuse load_error,
;     not a Disk-BASIC-specific message. Only the no-match / empty disposition is
;     reference-exact.
;
; Clean-room: original code. FILES/LFILES *semantics* + the 8.3 field layout and
; the one-entry-per-line printer form from the MSX-BASIC language reference and
; black-box CF-3300 observation; the FAT12 directory walk reuses the engine's
; primitives (read_sector, now in basic/fat-prim-body.inc on the tenant side,
; + the on-disk directory-entry layout, Microsoft FAT
; spec). No disassembly. See file-channel-protocol.md and basic/PROVENANCE.md
; §FILES.

; ex_files / ex_lfiles — statement trampolines (entered from exec_stmt with HL on
; the token). They differ in ONE byte of immediate data, and that byte is doing
; two jobs: it is the tenant's op selector AND the tenant's SINK selector. So
; LFILES needs no mode cell of its own — the mode rides marshalling that had to
; happen anyway.
; --- chan_gate: the channel verbs' disk-ROM presence gate (D-CHANHOOK) ------
; docs/spec-basic-nodisk.md §11/§12. FILES/KILL/NAME are Disk BASIC's, and a
; diskless MSX answers `Illegal function call` because the handler is not there.
; zerobas RAN them and failed on the MEDIUM instead -- `load error` -- which is a
; different answer to a different question, and it was measured only after the
; "unreadable cell" excuse for those rows was withdrawn.
;
;   in   HL = the verb's hook cell
;   out  returns to the CALLER with CF set when a disk ROM claimed it; otherwise
;        raises ERR 5 and never returns.
; One helper rather than three inline gates: 6 B per verb instead of 12, which
; matters at 75 B of page 1 (2026-09-03).
;
; 📜 HISTORY from here to S10.E's note below, which retired the bookkeeping.
; 🔴 D-ALIASBITE (2026-09-23, Joost: *"go with the bookkeeping fix"*): THE
; CROSSING IS ALSO A CHANNEL SWITCH, AND IT HAS TO BE BOOKKEPT LIKE ONE.
; `FAT_DBUF` ($E5C0) holds the OPEN channel's staged sector, and a disk-ROM verb
; refills it -- measured: `KILL` writes 416 B of its own `WBUF` straight through
; it, `NAME` 832+192, `DSKF` 1664+384. Before this, a verb run while a channel
; was open made the next read serve 4 bytes of the verb's leftovers (no error,
; no short read) and made the next write COMMIT them to the disk.
; 🎯 THE PAIR THAT FIXES IT WAS ALREADY SHIPPED, for the channel-switch case:
; `fch_flush_active` (fat_detach_channel) writes a dirty partial sector out IN
; PLACE and steps back onto it, and `fch_restage` (fat_restage_channel) re-reads
; whatever the live channel had staged. `fch_load_ctx` has always ended in
; `jp fch_restage`. A channel switch was safe BECAUSE it took that path; a verb
; was unsafe only because it did not. So take it here too.
; 🔴 AND "THAT PATH" IS THE *WHOLE* PAIR, NOT ITS BUFFER HALF -- CORRECTED
; 2026-09-23 AFTER THE FIRST CUT SHIPPED THE HALF. The first cut called
; `fch_flush_active`/`fch_restage` directly, which move the SECTOR and nothing
; else, and it fixed every read but only 4 of 8 writes. A channel switch does
; not merely flush: `fch_save_active` LDIRs the 50-byte `FCH_STATE0` span
; ($E9C9..$E9FA) into the channel's context and `fch_load_ctx` LDIRs it back --
; and the ENGINE STATE is what the surviving failures were losing.
; 🔬 MEASURED, NOT INFERRED (`scratchpad/aliaswcell_probe.py`,
; `scratchpad/aliaswcell_run.out`): a named-cell snapshot either side of the
; crossing, with the FIXED `KILL` as the contrast arm rather than a control.
; The two surviving failures fail for TWO DIFFERENT REASONS, and both are cells
; in that span that nothing restored:
;   * `NAME` leaves `FWR_DIROFF` moved ($E0 -> $C0) -- it walked the directory
;     with main's own cursor, so `CLOSE` then stamped the open file's size and
;     first cluster into the WRONG directory entry. The buffer was intact; the
;     POINTER TO THE DIRECTORY was not.
;   * `DSKF` leaves `FWR_CLUS` holding its free-cluster count ($0000 -> $02CB)
;     and `FAT_WRTMP`/`FAT_WRTMP2` its walk state. The re-stage then faithfully
;     computed a sector address FROM THAT and re-read the wrong sector: the
;     buffer comes back ZEROED ($E5C0.. `AAAA` -> $00) across the crossing.
;     The re-stage did not fail; it was handed poisoned state.
; 🎯 SO THE RE-STAGE IS ONLY AS GOOD AS THE STATE IT READS. Restoring the sector
; without restoring the cursors that address it is not a cache -- it is a cache
; with a dangling key.
; 🔬 THE REFERENCE DOES THE SAME THING AND WAS MEASURED DOING IT
; (`scratchpad/refbuf_ref_*.out`, National_CF-3300): its directory/raw sector
; buffer and its file-data sector buffer never write each other's range, and the
; data buffer is re-read on switch-back. Relocating our buffers to be disjoint
; instead was priced and REFUSED: main leaves no 512 B span anywhere in
; [$E000,$F380) -- 1325 B free but the largest hole is 444 B
; (`scratchpad/disjoint_mainonly.out`).
; 🗑️ S10.E (2026-10-19): AND THE BOOKKEEPING IS GONE, BECAUSE WHAT IT KEPT IS.
; One by one the things a verb could wreck left main: the staged sector (S10.C:
; an INPUT channel reads its block's +9 in disk.rom), the engine cursors (S10.B /
; S10.C / S10.D: every disk channel is disk.rom's FCB in its own row), RANDOM's
; record (D-FLDDESC: it lives at block+9). What the save / restore pair still
; carried at the end was the sub-ROM's t_fch_load MIRRORING the live channel's
; LOF / LOC into FAT_FILESIZE / FWR_BYTES -- and LOF / LOC read the FCB through
; disk.rom now (H_CHIN ops 6 / 8). So the flush arm before the crossing
; (fch_save_active) and the restore after it (chan_restore_st -> fch_load_ctx)
; are deleted, and so is disk.rom's D-ERRKEEP dodge (hk_claim_status zeroing
; FCH_ACTIVE) that kept a pending code alive past the restore. Every cell a verb
; can touch is the verb's own or disk.rom's; nothing of a channel's is in main.
; 🎯 GA-VERBRUN (2026-10-03): THE CLAIMED PATH RETURNS A = DISKOP_STATUS, AND
; THAT IS LOAD-BEARING: verb_run, fopen_cross and kill_status decode A directly
; and do not reload the cell (3 B each). It was the last instruction of
; chan_restore_st; since S10.E cg_back loads it itself. A future second
; claimed-path exit must hand A back the same way. The unclaimed path raises
; ERR 5 and never returns.
; ⚠️ NO CALLER TESTS Cy AFTER `chan_gate` -- checked at every call site, each
; one loads `FN_RESUME` next or decodes A with `or a`/`cp` -- so the claimed
; path may return with Cy as the crossing left it.
chan_gate:
                ld      (FOPEN_SEL),a       ; D-SAVEOPEN: the caller's A is fopen_cross's
                                            ; selector. Every other gate's hook
                                            ; ignores it: FILES sets its own,
                                            ; DSKI$/DSKO$ pass theirs in A again.
cg_cross:
                ld      de,cg_back          ; call THROUGH HL: the cell is
                push    de                  ; `F7 <slot> <lo> <hi> C9`, so its own
                or      a                   ; `ret` lands here; unclaimed it is a
                jp      (hl)                ; bare `ret` and lands here at once
cg_back:
                ; S10.B: C-BIOS's CALSLT -- which a hook's CALLF is -- RETURNS WITH
                ; INTERRUPTS OFF (cbios src/slot.asm calslt_restore: `di`, no `ei`).
                ; Every older path went on through subrom_call's own `ei`; OPEN FOR
                ; OUTPUT now ends here. Hygiene, NOT a measured fix: it was written
                ; for diskbasic-acceptance's lost keys and MEASURED not to cure them
                ; (the WRBLK record writer's sector count was the cause, TODO S10.B).
                ei
                ; 🔴 `DISKOP_STATUS` IS A SHARED CHANNEL -- the verb writes it LAST
                ; (disk.rom hk_claim_status) and nothing may run between that and
                ; this read. Until S10.E the restore ran here and was itself a
                ; DISKOP; the first cut of D-ALIASBITE let it land its own result
                ; on top of the verb's and `KILL`/`NAME` came back `File not found`.
                ld      a,(DISKOP_STATUS)   ; `ld` keeps Cy: the crossing's answer
                ret     c                   ; claimed -> A = the verb's status
cg_unclaimed:
                jp      gb_illegal          ; Illegal function call -- TRAPPABLE,
                                            ; which is what the reference gives
                                            ; (ld a,5 / jp raise_error: interp.asm's
                                            ; tail, C4 shared 2026-10-03)

; --- fopen_cross (D-CARVEFO, 2026-09-27): the `$FE5D` open-hook crossing ------
; A = the FOPEN_SEL selector. Stores it, crosses H_FOPEN through chan_gate, and
; returns A = DISKOP_STATUS with Z iff it is 0 (CF clear). The five-instruction
; sequence stood verbatim at FOUR page-1 sites (disk_prog_load, sav_is_disk,
; dsk_aopen, dsk_agetbyte); one body + four calls = 26 B of main page 1, carved
; for D-CLEARFIT. chan_gate keeps its own return point (cg_back) and inspects no
; caller frame, so one more call level changes nothing on the main side.
; 🔴 D-SAVEOPEN (2026-09-28): THE SELECTOR IS STORED BY chan_gate, AFTER ITS
; FLUSH, NOT HERE BEFORE IT. FOPEN_SEL aliases DISKOP_OP, and with a channel LIVE
; chan_gate first flushed it -- fch_save_active -> a FAT primitive marshalled
; through DISKOP_OP -- which overwrote the selector, so disk.rom's H_FOPEN
; dispatcher saw no verb and did nothing: `SAVE` with a file open wrote NOTHING
; and answered OK (the CF-3300 saves; scratchpad/errkeep2_probe.py sv_openrw read
; 255 there and 53 here). S10.E (2026-10-19) deleted the flush; the store stays in
; chan_gate, the last thing before the crossing, which is still the safe place.
fopen_cross:
                ld      hl,H_FOPEN
                call    chan_gate           ; A = the selector, stored by the gate;
                or      a                   ; back with A = DISKOP_STATUS (GA-VERBRUN)
                ret

; chan_gate_bare -- the SAME crossing with NO channel bookkeeping, for the two
; verbs whose whole job is to write the live channel's record.
; 🏗️ S10.E (2026-10-19): THE FULL GATE HAS NO BOOKKEEPING LEFT EITHER (chan_gate's
; note), so the two differ only in what they hand back: chan_gate stores A as
; FOPEN_SEL and returns A = DISKOP_STATUS; this one passes A / BC to the hook
; untouched (GET / PUT's op and channel, DSKI$ / DSKO$'s selector and sector) and
; returns what the hook returned. The rule below is history, kept for its reason.
; 🏗️ D-FLDDESC (2026-10-17): THE HAZARD BELOW IS GONE AND THE RULE STAYS. A
; RANDOM record lives at its block's +9 now, not in FSECTOR_BUF, so the full
; gate's restore would no longer undo a store -- but FIELD / LSET / RSET still do
; no sector I/O, so they still need none of its bookkeeping, and GET / PUT still
; make their own channel live (hk_dget). The history, as it stood:
; 🔴 FIELD AND LSET/RSET MUST NOT TAKE THE FULL GATE, AND FIVE SUITES SAID SO.
; `hk_lrset` walks main's FLD_TAB and stores the field's bytes INTO FSECTOR_BUF
; -- that buffer IS the channel's record. The full gate saves the record before
; the crossing and LDIRs it back after, so it copied the PRE-LSET record over
; the store and undid it: `fldary`, `fldwidth`, `lrvar`, `lvfix` and `tgtspc`
; all went red with the target reading back as spaces, including their own
; positive controls.
; 🎯 AND THE RULE IS THE ONE THIS ARC ALREADY MEASURED: the bookkeeping exists
; because a disk-ROM verb REFILLS main's staged sector behind an open channel.
; FIELD and LSET/RSET touch no disk and move no sector; they write the record
; deliberately, on purpose, and there is nothing to restore it from.
; ⚠️ A verb added here must be one that does NO sector I/O. When in doubt take
; the full gate -- the cost of the bookkeeping is a re-read, the cost of missing
; it is data on the medium (D-ALIASBITE).
; 🔴 ONE EXCEPTION, AND IT IS NOT A LOOSENING: GET / PUT (S10.D, 2026-10-15) DO
; sector I/O through this gate. They are LSET's case one level up -- a GET writes
; the live record on purpose, so the full gate's restore would undo it -- and
; their handler (disk.rom hk_dget) does the channel bookkeeping ITSELF: it calls
; back `fch_select` on the GET's own channel after parsing `, recno`, which saves
; whatever was live and loads this channel, exactly as main's GET used to. A verb
; that does sector I/O here WITHOUT making its own channel live first is the
; D-ALIASBITE bug. (S10.E: hk_dget stores FCH_ACTIVE itself now -- there is
; nothing left to save or load -- and the rule stands: make the channel live.)
chan_gate_bare:
                ld      de,cgb_back
                push    de
                or      a                   ; CF = 0; unclaimed the cell is a
                jp      (hl)                ; bare `ret` and lands below at once
cgb_back:
                ret     c                   ; claimed -> back to the caller
                jr      cg_unclaimed        ; ERR 5, same face as the full gate

; (chan_restore / chan_restore_st -- GONE with S10.E, 2026-10-19. They reloaded
; the live channel after a crossing -- the FCH_STATE0 span and its staged sector
; once, at the end only the sub-ROM t_fch_load's LOF / LOC mirror -- with
; DISKOP_STATUS held across it; chan_gate's claimed path and dsk_core's second
; crossing (basic/str-engine.asm) were the two callers. Both read DISKOP_STATUS
; directly now. LOF / LOC ask disk.rom for the FCB's own value: H_CHIN ops 6 / 8.)

; (dirverb_op -- `ld (DISKOP_OP),a` + the sub-ROM dirverb tenant -- is GONE since
; D-DSKLOCAL, 2026-10-15: DSKI$ / DSKO$, its last callers, cross their hook to
; disk.rom's hk_dsk instead.)

; --- COPY "src" TO "dst" — the run half (D-COPY) -----------------------------------
; copy_parse (low region) did the gate and both names; this runs dirverb op 7
; and decodes STATUS: 0 source not found -> ERR 53, 1 copied, 2 mount / full /
; I-O -> load_error -- KILL's own tail, shared -- and 3 (self-copy, wildcard
; source) -> ERR 5.
; 🧭 D-DISKVERB3 (2026-09-15): BOTH HALVES ARE IN disk.rom NOW, as `hk_copy`.
; The parse half lived in the page-0 LOW REGION (`copy_parse`) and it and its
; helper `fname_fcb` are GONE with it -- KILL and NAME stopped routing through
; either when their own bodies moved, so COPY was the last caller of both. That
; makes this the first verb whose saving is LOW-REGION bytes, the scarcer of the
; two budgets at 0 B free.
; --- verb_run: the whole-verb-in-disk.rom prologue (GA-VERBRUN, 2026-10-03) ---
;   in   HL = the statement cursor ON the verb token, DE = the verb's hook cell
;   out  A  = DISKOP_STATUS (chan_gate's claimed path returns it in A),
;        HL = FN_RESUME, the cursor the handler resumed at; unclaimed -> ERR 5
; COPY, FILES/LFILES, KILL and NAME opened with the same 10 B -- stage the
; cursor past the token in FN_RESUME, cross the hook through chan_gate -- and
; each then reloaded the status and the cursor: one 12 B body, 6 B per site.
; `ex de,hl` is free because chan_gate clobbers DE building its return address.
verb_run:
                inc     hl                  ; HL -> bytes after the verb token
                ld      (FN_RESUME),hl      ; stage the cursor for the handler
                ex      de,hl               ; HL = the hook cell
                call    chan_gate           ; unclaimed -> ERR 5 (trappable);
                                            ; claimed -> disk.rom ran the whole verb
                ld      hl,(FN_RESUME)      ; the cursor the handler resumed at
                ret

ex_copy:
                ld      de,H_COPY
                call    verb_run            ; A = status, HL = resume cursor
                cp      3
                jp      z,gb_illegal        ; 3: refused, or no `TO` -> ERR 5
                jp      kill_status         ; 0 / 1 / 2 exactly as KILL decodes them

; --- seq_end: INPUT # / LINE INPUT # reached "the end" (Cy from the read) ------
; 🔴 D-LINEJECT (2026-10-11): THE END WAS ALSO A FAILED READ. With the disk ejected
; mid-file, LINE INPUT # raised 55 `Input past end` here where the CF-3300 raises
; 70 `Disk offline` -- the read failure came back as end-of-file
; (scratchpad/ejectsweep_run.out), GET's D-GETEJECT twin. A failed DSKIO leaves
; its code in DISKOP_ERR (the tenant clears it on entry), so a pending code is
; RAISED; else nothing read is 55, as before; else the item's bytes stand.
; raise_error resets SP, so the callers' pushes need no unwinding.
seq_end:
                call    se_pending          ; D-WSZERO S9: 0 without a disk ROM
                or      a
                jp      nz,raise_error      ; a failed read: its own code
                ld      a,(STRSCR)
                or      a
                jp      z,gp_past_eof       ; the end, and not one byte read -> 55
                ret

; --- disk_error: raise the last DSKIO failure's code, else the old face --------
; D-DISKERR (docs/spec-basic-diskerr.md). Every post-tenant DSKIO-failure exit of
; the disk verbs comes here instead of load_error: with a code pending (the disk
; tenant's dskio_calslt mapped it -- 70 for an empty drive) it is RAISED, so ON
; ERROR traps it, ERR/ERL read it and the program STOPS, as the CF-3300 does
; (D-NMFAIL measured all five verbs); with none pending (a bad BPB after a
; successful read, an absent sub-ROM) the `load error` face is unchanged. The
; cassette exits keep load_error itself [[a-shared-tail-is-not-a-decision]].
disk_error:
                call    se_pending          ; D-WSZERO S9: 0 without a disk ROM
                or      a
                jp      nz,raise_error
                jp      load_error

; 🔴 D-NODISKGAP (2026-09-15): `ex_lfiles` USED TO ENTER *PAST* THE GATE.
; D-CHANHOOK routed FILES/KILL/NAME through their hooks and LFILES was missed --
; not because anyone decided against it, but because `do_files` is a shared TAIL
; WITH TWO HEADS and only the first head carried the gate. Measured on four sides
; (scratchpad/nodiskgap_probe.py): the diskless VG-8020 answers ERR 5 to `LFILES`
; exactly as it does to `FILES`, and this tree RAN it -- while `FILES` beside it
; refused correctly, which is what made the hole invisible.
; 🎯 The selector now goes in FIRST and the gate is shared, so a third head
; cannot repeat this: there is nowhere to enter that skips it. Costs 2 B against
; the 10 B a second inline gate would have.
; 🧭 D-DISKVERB4 (2026-09-15): THE BODY IS IN disk.rom, as `hk_files`. Both
; verbs share ONE hook cell (H_FILE, which is what the reference gives them), so
; the handler tells them apart by reading the verb's own TOKEN back out of the
; program text at FN_RESUME-1 -- the same trick NAME uses for `AS` and COPY for
; `TO`. That is why these two trampolines collapse into one body here.
;
; 🎯 THE DECODE IS kill_status, UNCHANGED. do_files ended `or a / jr z,df_notfound
; / dec a / jr nz,disk_error / jp exec_stmt`, which IS kill_status instruction for
; instruction -- so FILES joins KILL, NAME and COPY on the shared tail rather than
; keeping a fourth copy of it.
;
; 🔴 D-NODISKGAP's finding still holds and is now structural: `ex_lfiles` used to
; enter PAST the gate, so a diskless LFILES answered differently from a diskless
; FILES. There is only one entry now, so that divergence cannot come back by
; someone adding a second one.
ex_files:
ex_lfiles:
                ld      de,H_FILE
                call    verb_run            ; A = status, HL = resume cursor
                jp      kill_status         ; 0 none matched / 1 listed / 2 I-O
; df_notfound — R-LF4 + R-LF6: a filespec that matches nothing prints `File not
; found`, on the SCREEN, for LFILES *and* for FILES. Measured on the CF-3300 for
; both verbs (lfl-noneb / lfl-nonef); zerobas printed nothing at all before this
; slice, which is why lfl-nonef exists at all.
;
; 🎯 IT COSTS FIVE BYTES, because the message already ships: D-MSGSUB hosts ERR 53
; in sub/errmsg.asm (em_file_notfound) and err_msgtab[53] is the one-byte
; err_subhosted marker. raise_error, NOT load_error — so this is a real MSX error:
; ERR reads 53 and ON ERROR traps it. Neither is measured by any row here; stated
; as a consequence of the mechanism, not claimed as a rule.
;
; ✅ do_kill's no-match REACHES HERE SINCE 2026-08-07 (D-DSKMSG,
; docs/spec-basic-dskmsg.md §4). This note used to read "deliberately NOT
; re-pointed here ... changing it would move an UNMEASURED verb on the strength
; of a reading taken for a different one. Filed, not fixed." The reading was
; taken (R-DK1, docs/dskmsg-msx1-characterization.md): the CF-3300 answers
; `File not found` for KILL too, and fat-error-acceptance's `kill-missing` pin
; moved in the same commit as the code. `NAME` was measured at the same time and
; deliberately NOT changed — §4.5 of the spec has the three reasons.
df_notfound:
                ld      a,53
                jp      raise_error

; --- df_or_loaderr: GONE (S10.C, 2026-10-15) -------------------------------
; D-LOADERR (docs/loaderr-msx1-characterization.md) split a failed OPEN into
; ERR 53 for "mounted fine, the name is not there" and disk_error for the rest,
; keyed on DISKOP_OP == DISKOP_SEL_FAT_FIND: `fatprim_bounce` wrote the selector
; of the primitive it ran, so after main's fat_io_open failed the cell named
; which one. Its last caller was OPEN FOR INPUT. Since S10.C every disk mode
; opens in disk.rom (hk_finp / hk_fmake / hk_fapp / hk_frnd) through fopen_cross,
; DISKOP_OP holds an FOPEN_SEL_* selector there and never FAT_FIND, and the
; not-found reading is the disk side's own: it parks 53 in DISKOP_ERR, so OPEN's
; oo_fail goes straight to disk_error. The REFERENCE's rule is unchanged and so
; is the face: 53 raised for a missing file, a DSKIO code for a fault.
; ⚠️ BLOAD never came here and still does not (D-BLNF): its tenant files
; BL_STAT = 2 and the resident stub jumps to df_notfound above.

; ===========================================================================
; Sequential file channel (Phase 2). A SINGLE open channel, layered on the
; existing fat.asm sequential engine (fat_io_open/getbyte + fat_io_create/putbyte/
; close), per the EXTEND verdict (file-channel-protocol.md §4/§5). Verbs:
;   OPEN "name" FOR INPUT  AS #n       open the named file for sequential read
;   OPEN "name" FOR OUTPUT AS #n       create/truncate the file for sequential write
;   LINE INPUT #n, A$                  read one line (to CR) into a string var
;   INPUT #n, A$                       read one field (to ',' or CR) into A$
;   PRINT #n, <items>                  write PRINT-formatted items to the file
;   CLOSE [#n]                          close the open channel (OUTPUT: flush + EOF)
; The channel state (FCH_NUM/FCH_MODE) persists across statements in RAM. PRINT#
; reuses the screen PRINT item loop, redirected byte-by-byte to the channel via
; the PRDEST flag + the `pchar` sink (basic/print.asm).
;
; Clean-room: original code; verb *semantics* + the FCB-by-name / sequential
; read+write model from the public MSX-BASIC language reference and the black-box
; CF-3300 DSKIO trace (file-channel-protocol.md §2/§3); the byte stream reuses
; fat.asm. No disassembly. See basic/PROVENANCE.md §file channel.
;
; Divergences (own design, quarantined; documented in PROVENANCE.md):
;   * up to FCH_CEIL channels open at once — a real multi-channel table
;     (MAXFILES) over fat.asm's single global state, via the write-back context
;     cache in the channel-manager section below. Channel numbers are
;     range-checked to MAXF. ⚠️ FCH_CEIL is 15 — the MEASURED reference ceiling
;     (D-FCH §3.2 made the table dynamic, so unused channels cost nothing).
;     The per-channel CHARGE (50 B out of FRE(0),
;     vs the reference's 267) is the remaining deliberate divergence.
;   * a value longer than STRMAX is truncated (the string layer's own limit).
; 🔴 STALE AS A WHOLE, CORRECTED 2026-10-15 (S10.C) RATHER THAN DELETED: this
; block described the Phase-2 tree. Since then numeric INPUT# (D-INPNUM),
; console INPUT (basic/input.asm), graphics LINE, APPEND (S10.B), RANDOM
; (S10.D) and RAISED channel errors (D-BADFNUM, D-CHDIR, D-LOADERR) all
; shipped, and every disk channel's bytes now live in disk.rom -- OUTPUT /
; APPEND since S10.B, RANDOM since S10.D, INPUT since S10.C. What is left of
; "layered on fat.asm" is the header above, kept as history.

; --- OPEN "name" FOR INPUT AS #n -------------------------------------------
ex_open:
                inc     hl                  ; HL -> bytes after the OPEN token
                jr      do_open
do_open:
                call    fname_expr          ; D-FNEXPR: the filename is a string
                                            ; EXPRESSION; HL -> the staged,
                                            ; '"'-terminated copy in STRSCR
                ; --- device-name dispatch: "LPT:"/"CRT:" -> character-device
                ; channel (no disk file); anything else -> disk filename. Peeked
                ; case-insensitively; HL is restored on a miss (dev_cmp). CAS:/GRP:/
                ; COM: OPEN are not in this tier (an unknown xxx: stays a disk name).
                ; ⚠️ D-FNEXPR: THE DISPATCH NOW RUNS ON THE STAGED COPY, NOT ON
                ; PROGRAM TEXT, so `OPEN A$ AS #1` with A$="CAS:X" reaches the
                ; tape arm exactly as the literal does. That is a behaviour
                ; claim and it is MEASURED (rows d.opendev/f.var, and the
                ; cassette batteries), not assumed.
                ld      de,dev_lpt
                call    dev_cmp
                jp      z,oo_dev_lpt
                ld      de,dev_crt
                call    dev_cmp
                jp      z,oo_dev_crt
                ld      de,dev_grp          ; D-OPENGRP: the graphics screen
                call    dev_cmp
                jp      z,oo_dev_grp
                ld      de,dev_cas
                call    dev_cmp
                jp      z,oo_dev_cas
                ; ✅ D-NODISKOPEN (2026-10-07): ON A DISKLESS MACHINE THE CASSETTE
                ; IS THE DEFAULT DEVICE. Measured on the VG-8020 (no disk,
                ; probes/basic/basic_probe_nodiskopen.py): `OPEN "X" FOR OUTPUT`
                ; opens, and a second cassette OPEN beside it is 52 exactly as for
                ; `OPEN "CAS:X"` -- the same device; a drive name (`"A:X"`) is 56.
                ; Ours printed `load error` (oo_nodisk, now gone).
                call    nodisk_dev          ; shared since D-NODISKVERBS (str-engine.asm)
                jp      z,oo_dev_cas        ; no disk: the cassette; `d:` raised 56
                call    pdfcb_resume      ; build DISK_FCB_NAME; HL -> closing '"'
                ; D-OPENWILD (2026-10-07): a WILDCARD name is `Bad file name` (56)
                ; on the CF-3300 (`OPEN "A*.TXT" FOR INPUT AS #1`); ours looked it
                ; up and said 53. The parser takes wildcards because KILL / FILES
                ; need them (`*` fills with `?`), so OPEN refuses a `?` itself,
                ; before any disk work.
                push    hl
                ld      hl,DISK_FCB_NAME
                ld      b,11
                ld      a,'?'
oo_wild:
                cp      (hl)
                jp      z,pdf_badname       ; 56
                inc     hl
                djnz    oo_wild
                pop     hl
                call    skip_spaces
                cp      FOR_TOKEN           ; FOR
                jr      nz,oo_random        ; no FOR clause -> RANDOM mode (OPEN..AS #n)
                inc     hl
                ; mode keyword: INPUT ($85); OUTPUT = OUT ($9C) + PUT ($B3); or
                ; APPEND = "APP" (verbatim ASCII $41 $50 $50) + END ($81) — none of
                ; these are single keywords: OUTPUT is two reserved words, and
                ; "APPEND" is not a reserved word at all, so the main-ROM tokeniser
                ; crunches it as the name "APP" followed by the END token (oracle:
                ; VG-8020 + zerobas both emit $41 $50 $50 $81 — already byte-identical).
                call    skip_spaces
                cp      INPUT_TOKEN
                jr      z,oo_input
                cp      OUT_TOKEN
                jr      z,oo_output
                ; APPEND? match the literal "APP" + END-token sequence.
                ; D-INPLIST carve: this was four unrolled `cp`/`jp nz`/`inc hl`/
                ; `ld a,(hl)` groups, 27 B. The sequence is DATA, so it is data
                ; now -- 13 B of loop plus the 5-byte oo_app_seq below. The
                ; oracle fact it encodes is unchanged and still written down at
                ; the block above: the main-ROM tokeniser crunches "APPEND" to
                ; $41 $50 $50 $81, so this matches bytes and not a keyword.
                call    oo_is_app           ; D-NODISKOPEN: shared with the tape arm
                jr      nz,oo_synerr
                ld      a,3                 ; mode = APPEND (provisional open action)
                jr      oo_setmode
; oo_is_app: Z and HL past it iff HL is at APPEND ("APP" + END, crunched)
oo_is_app:
                ld      de,oo_app_seq
oo_app_lp:
                ld      a,(de)              ; expected byte
                cp      (hl)                ; against the line
                ret     nz
                inc     hl
                inc     de
                ld      a,(de)
                or      a                   ; 0 terminates the sequence
                jr      nz,oo_app_lp
                ret                         ; Z
; ⚠️ ONE LOCAL `stmt_error` TRAMPOLINE FOR THE WHOLE OPEN PARSE (D-INPLIST
; carve). Six sites reached it with `jp cc,stmt_error` (3 B each); they reach it
; with `jr cc,oo_synerr` (2 B) now, which pays for itself from the third site on.
; ⚠️ EVERY ONE OF THE SIX MUST STAY WITHIN `jr` RANGE OF THIS LABEL -- the
; assembler is the guard: move a caller out of range and the BUILD fails rather
; than the branch going wrong. Placed here because nothing falls into it (the
; APPEND arm above ends in `jr oo_setmode`).
oo_synerr:
                jp      stmt_error
oo_app_seq:
                db      'A','P','P',END_TOKEN,0
oo_output:
                inc     hl
                ld      a,(hl)
                cp      PUT_TOKEN
                jr      nz,oo_synerr
                inc     hl
                ld      a,2                 ; mode = OUTPUT
                jr      oo_setmode
oo_input:
                inc     hl
                ld      a,1                 ; mode = INPUT
                jr      oo_setmode
oo_random:
                ld      a,4                 ; mode = RANDOM (no FOR clause)
oo_setmode:
                ld      (FCH_MODE),a        ; provisional: read below and at oo_done
                                            ; only. 🗑️ 2026-10-19: the clears on
                                            ; OPEN's failure tails, CLOSE and cold
                                            ; start went, with fch_select's store:
                                            ; nothing outside OPEN reads the cell,
                                            ; and OPEN writes it first
                call    oo_parse_as_chan    ; shared "AS [#]n" + ceiling check; DE = ch
                ; --- optional "LEN=r" record-size clause (Phase 2c; disk-BASIC
                ; option-closure Item 3). Parsed for every mode; only RANDOM GET/PUT
                ; reads it. A channel without LEN= defaults to 256; r is any value
                ; in 1..256 (oo_parse_reclen's header: the power-of-two rule left
                ; with D-RECLENFIX / D-STRADDLE). Stored per channel in FCH_RECLENS[ch].
                ld      a,e
                ld      (OO_RECLEN_CHAN),a  ; stash channel across the LEN= eval
                call    oo_parse_reclen     ; DE = reclen (default 256); HL past; Cy=1 bad
                jp      c,oo_fail_ifc       ; D-RECLEN2: out-of-range record size is
                                            ; (`jp`, not `jr` -- the ERR 5 tail this
                                            ; slice adds puts it out of relative range)
                                            ; `Illegal function call` on the CF-3300
                                            ; (LEN=0 / 257 / 512 all ERR 5), NOT the
                                            ; `Syntax error` this used to raise
                ; 🔴 D-OPENEND (2026-10-07): THE STATEMENT MUST END HERE, BEFORE ANY
                ; DISK WORK. `OPEN "X.TXT" FOR APPEND AS 1,2` is Syntax error (2)
                ; on the CF-3300 even with X.TXT missing: it parses the whole
                ; statement first. Ours opened and let exec_stmt meet the `,2`
                ; afterwards -- which read 2 only by ACCIDENT while a missing file
                ; went through the print-and-return load_error (D-LOADERRRET), and
                ; read 53 once disk.rom raised it (S10.B increment 2, ed213e5c;
                ; kwsweep's t8openappend2, which its gate does not fail on). An
                ; OUTPUT open would also have CREATED the file before the 2.
                call    skip_spaces         ; A and HL only: DE (the reclen) survives
                or      a
                jr      z,oo_endok
                cp      ':'
                jp      nz,oo_fail_syn      ; junk after the clause: 2, nothing opened
oo_endok:
                push    hl                  ; GUARD the text cursor -- the store below
                                            ; uses HL as scratch (a bug once: the lost
                                            ; cursor abandoned a same-line ':' tail)
                ld      a,(OO_RECLEN_CHAN)
                add     a,a                 ; channel * 2 (word index)
                ld      l,a
                ld      h,0
                ld      bc,FCH_RECLENS
                add     hl,bc
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; FCH_RECLENS[ch] = reclen
                pop     hl                  ; restore the text cursor
                ld      a,(OO_RECLEN_CHAN)
                ld      e,a
                ld      d,0                 ; restore DE = channel for the rest of do_open
                ; (no disk here is impossible: a diskless OPEN went to the
                ; cassette or 56 above, before pdfcb_resume -- D-NODISKOPEN)
                ; 🔴 D-OPENSAME (2026-09-29): a file ALREADY OPEN on another channel
                ; is `File already open` (54) on the CF-3300 in every mode, and the
                ; first channel keeps its data (scratchpad/opensame_before.out).
                ; disk.rom's hkk_open_check is the walk (KILL/NAME/COPY use it);
                ; asked through the full gate, because it reads directory sectors
                ; into the buffer the live channel stages in. Before the claim, so
                ; a refusal leaves every channel as it was.
                push    de                  ; the channel
                push    hl                  ; the text cursor
                ld      a,FOPEN_SEL_OCHK
                call    fopen_cross         ; NZ: this file is open on a channel
                pop     hl
                pop     de
                jp      nz,oo_fail_54
                ; claim the channel: FCH_ACTIVE = e, the row disk.rom's open handler
                ; builds the FCB in (dout_live). 🗑️ S10.E (2026-10-19): a STORE --
                ; fch_claim, which saved any OTHER live channel first, is gone with
                ; the save (nothing of a channel's lives in main any more), and so
                ; is the HL / DE guard the paragraph below put around it.
                ; 📜 HISTORY: D-OPEN2FIX: HL IS GUARDED HERE, NOT ONE CALL LATER.
                ; `fch_claim` documents "Clobbers regs", and when it claims a
                ; SECOND channel it runs fch_save_active -> fch_ctx_addr, an
                ; op-18 CALSLT that clobbers HL like every other. The guard
                ; below said so in its own words -- "CALSLT ... clobbers HL +
                ; regs" -- and sat one call too late, protecting fat_io_* and
                ; not this. With ONE channel `fch_claim` returns at its `ret z`
                ; before reaching any CALSLT, so the omission is INVISIBLE until
                ; a second disk channel exists: untested by construction, which
                ; is exactly what D-OPEN2 concluded about this path.
                ; Traced 2026-09-02 with an openMSX breakpoint script: the token
                ; cursor goes into fch_claim as $EC15 and the statement boundary
                ; reads it back as $E9FB, so the parser resumes on garbage and
                ; raises `Syntax error` AFTER the OPEN has completed -- which is
                ; why the channel table showed both channels correctly open.
                ; [[a-scratch-register-that-was-the-callers-value]]
                ld      a,e
                ld      (FCH_ACTIVE),a      ; this channel is the live one
                push    hl                  ; guard the text cursor — CALSLT (inside
                push    de                  ; fat_io_*) clobbers HL + regs
                ld      a,(FCH_MODE)        ; action: 1 INPUT/2 OUTPUT/3 APPEND/4 RANDOM
                cp      2
                jr      z,oo_create
                cp      3
                jr      z,oo_append
                cp      4
                jr      z,oo_random_setup
                ; S10.C (2026-10-15): INPUT is disk.rom's too (hk_finp) -- the FCB
                ; in the channel's row, the record the block's +9, read by H_CHIN
                ; (basic/input.asm din_call). It was main's resident fat_io_open
                ; (basic/fatio-body.inc), whose read state lived in the engine
                ; globals the sub-ROM's t_fch_save / t_fch_load copied per switch.
                ; A missing file is 53, raised after the crossing as the CF-3300
                ; raises it after $FE5D (s10c_hook_run.out).
                ld      a,FOPEN_SEL_INP
                jr      oo_cross
; 📌 PIN REFILL (S10.E, 2026-10-19): 46 B moved here from past the $73E5 pin
; (basic/program.asm) to take back the 46 B S10.E freed in front of $6CF3 --
; chan_gate's flush arm and the chan_restore pair (33), OPEN's fch_claim call
; just above (4), and LOF / LOC's mirror reads (basic/expr.asm, 9). Every byte
; removed ahead of a pinned address grows its pad (`ds $6CF3 - $` below, the
; `jr` bridge), and Joost: no growing holes. Sited HERE -- after the last of
; those deletions and BEFORE oo_fail_syn, as D-FCHNUM's refill is: the OPEN
; "CAS:" arm past the pin reaches back to oo_fail_syn / oo_fail_bfname with
; `jr`s, and oo_storemode's `jr oo_hdr_tail` reaches forward across the pad, so
; neither end may move. Both are whole and entered only by label, with no `jr`
; across their edges (tools/pin_plan.py chunks()); their notes stay behind.
; --- new_prog: clear the stored program (NEW) --------------------------------
; Empty program = a $0000 link word at the text base. Clobbers A, HL.
new_prog:
                xor     a
                ld      (CONTVALID),a       ; NEW wipes the program -> no CONT resume
                ld      (TRACEFLAG),a       ; NEW is the ONLY thing that clears TRON
                ld      hl,TXTBASE
                ld      (TXTTAB),hl         ; keep the real sysvar consistent ($8001)
                ld      (PRGEND),hl         ; end marker sits at the base
                ld      hl,0
                ld      (TXTBASE),hl        ; $0000 end marker at the base
                jp      vars_reset          ; rebase the scalar and array regions
; --- store_line: the line STORE's resident marshalling shim (the lineedit tenant
; does the store / delete, relink and vars_reset; basic/program.asm's header) ---
store_line:
                xor     a
                ld      (CONTVALID),a       ; editing the program invalidates CONT
                ld      (SL_NUM),bc
                ld      (SL_TOK),hl
                xor     a                   ; LE_OP_STORE = 0
                call    le_call_op          ; A = LE_STATUS, Z = ok
                ret     z                   ; ok (tenant already relinked +
                                            ; vars_reset)
                ld      a,$CC               ; out-of-memory landmark (distinct byte)
                jp      err7_mark           ; D-TAILMERGE: ERRMARK := A, then ERR 7 --
                                            ; gosub_stk_over's own tail, verbatim
oo_create:
                ; S10.B: OUTPUT and APPEND are disk.rom's -- the channel is an
                ; MSX-DOS FCB in the channel's engine row (hk_fmake / hk_fapp)
                ld      a,FOPEN_SEL_MAKE
                jr      oo_cross
oo_append:
                ld      a,FOPEN_SEL_APND
                jr      oo_cross
oo_random_setup:
                ; S10.D (2026-10-15): RANDOM is disk.rom's too (hk_frnd) -- the same
                ; FCB-in-the-row channel, opened or created, LOC zeroed, the record
                ; (FSECTOR_BUF, live, until D-FLDDESC; the block's +9 since)
                ; space-filled. It was the sub-ROM's
                ; fat_rand_open, through a fatprim_bounce shim; GET / PUT
                ; (basic/field.asm) now cross H_DGET to the same ROM.
                ld      a,FOPEN_SEL_RAND
oo_cross:
                call    fopen_cross         ; A = status, 0 = open
                add     a,$FF               ; CF iff status != 0
oo_done:
                pop     de
                pop     hl
                jr      c,oo_fail           ; not found / dir-full / mount / I-O error
                ; success: record the open mode in the channel table + the mirror.
                ; S10.B (2026-10-06): both write actions are stored as DOUT_MODE
                ; (3), disk.rom's FCB channel (APPEND since increment 2; mode 2,
                ; main's own channel engine, is no longer stored). The FCH_MODES
                ; address math uses HL, so guard the text cursor (HL) that
                ; exec_stmt needs to continue the line.
                ld      a,(FCH_MODE)
                cp      2
                jr      c,oo_storemode      ; 1 INPUT
                cp      4
                jr      nc,oo_storemode     ; 4 RANDOM
                ld      a,DOUT_MODE         ; 2 OUTPUT, 3 APPEND
                ld      (FCH_MODE),a
oo_storemode:
                push    hl
                ld      a,e
                call    fch_modes_ptr
                ld      a,(FCH_MODE)        ; 1 INPUT, 3 OUTPUT/APPEND, 4 RANDOM
                ld      (hl),a              ; FCH_MODES[ch] = mode (now committed)
                ld      (OO_DEVTYPE),a      ; D-FCBHDR: what the header stamp reads
                jr      oo_hdr_tail
oo_fail:
                ; post-claim failure (DE = channel): release the slot we claimed and
                ; mark the channel closed in the table (its globals are stale garbage).
                ld      a,e
                call    fch_modes_ptr
                xor     a
                ld      (hl),a              ; FCH_MODES[ch] = 0
                ld      (FCH_ACTIVE),a      ; no channel live (don't save the garbage)
                ; D-LOADERR: AFTER the channel cleanup, never before -- a raise
                ; here would leave the slot claimed.
                ; 🧭 S10.C (2026-10-15): disk_error, NOT df_or_loaderr any more.
                ; Every disk mode's open is a disk.rom crossing now (INPUT was the
                ; last on main's fat_io_open), so DISKOP_OP holds an FOPEN_SEL_*
                ; selector here, never DISKOP_SEL_FAT_FIND, and the not-found
                ; reading is disk.rom's: it parks 53 in DISKOP_ERR (hk_finp /
                ; hk_fapp), and a mount / DSKIO fault parks its own code.
                jp      disk_error
; 📌 PIN REFILL (D-FCHNUM, 2026-10-17): 8 B moved here from past the $73E5 pin
; (basic/missing.asm, basic/program.asm) to take back the 8 B D-FCHNUM and
; D-JRSLICE3's front-of-pin `jr`s freed ahead of $6CF3. (Its "2 B pad" in
; `pin_plan --check` is the `jr` bridge over the pin, not a `ds`: not refillable.)
; Sited HERE, before oo_fail_syn,
; not at the pad: the OPEN "CAS:" arm's `jr`s reach back across the pad to
; oo_fail_syn / oo_fail_bfname, so its address must not move. Both are whole and
; entered only by label (tools/pin_plan.py chunks()).
basicint_play:                              ; the pinned $73E5's target (header:
                call    pl_args             ; basic/missing.asm)
bp_ret:
                ret                         ; back to the game's `call $73E5`
arl_getbyte:
                ld      hl,(ARL_GETBYTE)
                jp      (hl)
oo_fail_syn:                                ; `jr` reach for the CAS: arm past the pin
                jp      stmt_error
oo_fail_bfname:                             ; the cassette arm's RANDOM / APPEND
                ld      e,56                ; refusal (D-NODISKOPEN): Bad file name
                jr      oo_fail_e

; --- oo_fail_ifc: OPEN's ILLEGAL FUNCTION CALL reject (D-RECLEN2, ERR 5) -----
; oo_fail_syn's sibling with a different face (neither clears FCH_MODE any more,
; 2026-10-19: nothing outside OPEN reads it). Measured: the
; CF-3300 answers ERR 5 to `LEN=0`, `LEN=257` and `LEN=512`, and accepts
; everything in 1..256.
oo_fail_ifc:
                ld      e,5                 ; Illegal function call
oo_fail_e:                                  ; E = the ERR code (D-OPENBUSY shares it)
                ld      a,e
                jp      raise_error

; --- oo_fail_bfn: OPEN's BAD FILE NUMBER reject (S-FCH-2, ERR 52) ------------
; The body lives in main.asm's low region (page 1 is the scarce wall).
; (§5c's second open question was dissolved by aliasing the LABEL rather than
; gating the six reject SITES: every `jp cc,oo_fail_bfn` above then assembled to
; the exact bytes `jp cc,oo_fail_syn` did, so no site needed a gate and no byte
; moved. The retired lean cart, which defined neither body, rode on that alias.)
                                            ; exactly as before this slice

; --- OPEN "LPT:"/"CRT:" device channel --------------------------------------
; A character-device channel: PRINT#n streams to the printer (LPTOUT) or the
; screen (CHPUT) via pchar's PRDEV dispatch. It owns NO FCB row (no disk.rom
; open), so it must never be fch_select'd; it is marked in
; FCH_MODES with the device value LPT_MODE/CRT_MODE and its channel number is
; classified straight from that array by PRINT#/CLOSE. Only FOR OUTPUT is valid
; (INPUT from LPT:/CRT: is an error); LEN= is rejected. Sinks are the already-
; implemented BIOS entry points (LPTOUT $00A5 in zerobas-tape; CHPUT $00A2).
; Entry: HL -> the char after the "LPT:"/"CRT:" prefix, inside the quotes.
oo_dev_lpt:
                ld      a,LPT_MODE
                jr      oo_dev_open
oo_dev_crt:
                ld      a,CRT_MODE
                ; 📌 D-BASICINT PIN $6CF3 (2026-10-15), bridged: games (Harry Fox)
                ; drop BLOAD,R's return address and `jp $6CF3`, the reference's
                ; continuation, which then runs the rest of the statement exactly as
                ; a `ret` would (scratchpad/basicint_probe.out row `cont`). Ours is
                ; load_handoff's tail (basic/bload.asm lh_back). FIXED ADDRESS, from
                ; tools/pin_plan.py's `jr` bridge (no pad today; --check caps it).
    IF BASICINT_PINS
                jr      oo_dev_open
                ds      $6CF3 - $, $00
basicint_6cf3:
                jp      lh_back
    ENDIF
oo_dev_open:
                ld      (OO_DEVTYPE),a      ; remember the device type across the parse
                ; skip any remaining "filename" chars up to the closing quote (ignored)
oodv_fn:
                ld      a,(hl)
                or      a
                jr      z,oo_fail_syn       ; unterminated string
                inc     hl
                cp      '"'
                jr      nz,oodv_fn          ; consume through the closing quote
                ld      hl,(FN_RESUME)      ; D-FNEXPR: that quote was the one
                                            ; fname_expr appended to the staged
                                            ; copy -- resume in the program text
                ; --- D-DEVBARE: the FOR clause is OPTIONAL on a device -------
                ; This read `jr nz,oo_fail_syn ; device channels require FOR
                ; OUTPUT`, and the comment asserted a rule the reference does not
                ; have. Measured on a CF-3300: `OPEN"CRT:"AS #1` and
                ; `OPEN"LPT:"AS #1` are accepted, and the channel then WORKS --
                ; `PRINT#1,"x"` and `CLOSE#1` both fine (rows w.crtbare /
                ; w.crtwrite / w.crtclose / w.lptbare, scratchpad/devbare_probe.py).
                ; A bare device OPEN means OUTPUT, which is the only direction
                ; LPT:/CRT: have.
                ; 🟢 `LEN=` STAYS REFUSED, AND FOR FREE: the terminator check
                ; after oo_parse_as_chan below accepts only end-of-statement or
                ; ':', so `OPEN"CRT:"AS #1 LEN=128` is still `Syntax error` --
                ; which is what BOTH machines answer (row w.crtlen).
                ; ⚠️ `FOR INPUT` ON A DEVICE IS DELIBERATELY NOT COPIED. The
                ; reference's answer there is `<NO OUTPUT>` -- the program dies or
                ; hangs -- and a hang is not a behaviour to reproduce. zerobas
                ; keeps refusing it. [[a-fix-falsifies-the-justification-beside-it]]
                call    skip_spaces
                cp      FOR_TOKEN
                jr      nz,oodv_as          ; no FOR clause -> OUTPUT (measured)
                rst    $10     
                cp      OUT_TOKEN           ; OUTPUT = OUT + PUT (two reserved words)
                jp      nz,oodv_notout      ; INPUT: Syntax error on LPT:/CRT:, 56 on GRP:
                inc     hl
                ld      a,(hl)
                cp      PUT_TOKEN
                jr      nz,oo_fail_syn
                inc     hl
oodv_as:
                call    oo_parse_as_chan    ; shared "AS [#]n" + ceiling check; DE = ch
                call    skipsp_test ; only a terminator may follow (no LEN=)
                jr      z,oodv_ok
                cp      COLON
                jr      nz,oo_fail_syn
oodv_ok:
                ; mark the channel open as a device (FCH_MODES[ch] = LPT/CRT_MODE);
                ; no fat.asm I/O. Guard the text cursor across the array store.
                ; 🎯 D-CARVE2: THE CANONICAL "STAMP THE DEVICE TYPE AND RESUME"
                ; TAIL. Both OPEN arms -- the device arm here and the cassette arm
                ; at oocas_mark -- ended with these seven instructions verbatim.
                ; Entry contract, identical at both: HL = the BASIC text cursor
                ; (pushed and popped here), E = the channel number. oocas_mark
                ; reaches it having just restored both with `pop hl / pop de`.
oo_stamp_devtype:
                push    hl
                ld      a,e
                call    fch_modes_ptr
                ld      a,(OO_DEVTYPE)
                ld      (hl),a
                ; FALL THROUGH
; oo_hdr_tail -- D-FCBHDR (2026-10-08): stamp the channel's FCB HEADER, the
; bytes a program reads through VARPTR(#n): the MODE at +0, the DEVICE at +4,
; the buffer position +6 zeroed (disk OUTPUT / APPEND keep disk.rom's). Ours
; read 255 at +0 and +4 on every channel; the references write them at OPEN
; (probes/basic/basic_probe_fcbhdr.py). The work is the FAT tenant's row 23
; (sub/fatprim.asm t_fch_hdr), which maps OO_DEVTYPE -- the FCH_MODES value
; just stored -- to the reference's codes.
;   in:  E = the channel, OO_DEVTYPE = its FCH_MODES value; the text cursor
;        on the stack (pop_exec takes it).
oo_hdr_tail:
                ld      a,e
                call    fch_ctx_addr        ; HL = the channel's block
                ld      a,DISKOP_SEL_FCH_HDR
                call    fatprim_bounce
                jp      pop_exec            ; D-POPEXEC: pop hl + exec_stmt

; --- OPEN "CAS:name" FOR OUTPUT|INPUT AS #n --------------------------------
; A cassette SEQUENTIAL data channel. Like LPT:/CRT: it owns no fat.asm context
; (never fch_select'd); unlike them it drives the real tape via the M1/M2 ASCII
; block machinery: FOR OUTPUT writes the $EA header now and PRINT#n buffers data
; bytes through the cassette sink (cas_wbyte), CLOSE flushing the final block;
; FOR INPUT re-locks the tape (TAPION), verifies the $EA id, primes data block 1,
; and INPUT#/LINE INPUT#n read via cas_in_getbyte (Ctrl-Z = EOF). Both OUTPUT and
; INPUT are valid (unlike LPT/CRT which are output-only); APPEND/RANDOM and LEN=
; are not. Clean-room: the cassette ASCII/sequential format is the MSX2 Technical
; Handbook cassette chapter (same $EA id + 256-byte blocks + Ctrl-Z as SAVE",A");
; the byte layer is our own M1/M2 code. See spec-cas-ascii-saveload.md §5 + the
; tape option-surface audit. A cassette channel must not be interleaved with a disk
; file channel (they share the $E600 block buffer) — documented (single tape file).
; Entry: HL -> the char after "CAS:" (dev_cmp advanced it), inside the quotes.
;
; D-CASOPEN (docs/spec-basic-casopen.md, reading docs/casopen-msx1-characterization.md):
; the name is captured by `cas_capture_name` — cload.asm's shared cassette-name
; parser — rather than by `tape_parse_name`, so it lands in CAS_WANT and arms
; CAS_WANT_ON for the search. The two parsers produce byte-identical six-byte
; space-padded fields and leave HL in the same place; what the shared one adds is
; the "was a name given?" flag, which is precisely the two behaviours MEASURED on
; both references: the compare is byte-exact (`OPEN"CAS:rt"` does NOT find `RT`)
; and the bare form takes the next file. `merge_cas` below is the landed
; precedent for a files.asm caller.
oo_dev_cas:
                call    cas_capture_cut     ; -> CAS_WANT + CAS_WANT_ON; HL on '"'; a '.' ends the name (D-CASDOT)
                ; D-FNEXPR: cas_capture_name scanned the STAGED copy, whose
                ; closing '"' fname_expr wrote itself -- so the quote can no
                ; longer be missing and the check that used to guard it is gone
                ; with the 4 bytes it cost. Resume in the program text.
                ld      hl,(FN_RESUME)
                ; require FOR INPUT | FOR OUTPUT
                call    skip_spaces
                cp      FOR_TOKEN
                jr      nz,oocas_nofor      ; CAS: needs FOR (no RANDOM cassette)
                rst    $10     
                cp      INPUT_TOKEN
                jr      z,oocas_in
                cp      OUT_TOKEN           ; OUTPUT = OUT + PUT (two reserved words)
                jr      z,oocas_out
                call    oo_is_app           ; D-NODISKOPEN: APPEND is 56 on the
                jr      nz,oo_fail_syn      ; VG-8020 and CF-3300 alike; other
                jr      oo_fail_bfname      ; junk after FOR stays 2 (casfoo)
oocas_nofor:
                ; RANDOM (`AS #n`, no FOR) is 56 on both references; other junk
                ; is 2 (casjunk). The AS clause is parsed first, so a bad channel
                ; there answers before the 56 -- that order is unmeasured.
                call    oo_parse_as_chan    ; 2 unless `AS [#]n`
                jr      oo_fail_bfname
oocas_in:
                inc     hl
                ld      a,CAS_IN_MODE
                jr      oocas_setmode
oocas_out:
                inc     hl
                ld      a,(hl)
                cp      PUT_TOKEN
                jp      nz,oo_fail_syn
                inc     hl
                ld      a,CAS_OUT_MODE
oocas_setmode:
                ld      (OO_DEVTYPE),a      ; remember the CAS mode across the AS/#n parse
                call    oo_parse_as_chan    ; shared "AS [#]n" + ceiling check; DE = ch
                call    skipsp_test ; only a terminator may follow (no LEN=)
                jr      z,oocas_argsok
                cp      COLON
                jp      nz,oo_fail_syn
oocas_argsok:
                ; args fully validated -> now do the tape I/O (so a parse error never
                ; leaves a half-written tape). Guard the channel + text cursor across it.
                push    de                  ; DE = channel
                push    hl                  ; text cursor (TAPOON/TAPIN clobber all)
                ld      a,(OO_DEVTYPE)
                cp      CAS_OUT_MODE
                jr      z,oocas_do_out
                ; --- FOR INPUT: re-lock the tape, verify $EA, prime data block 1 ---
                ; ✅ D-CASOPEN: the name is HONOURED. This arm used to write
                ; `xor a` / `ld (CAS_WANT_ON),a` under the comment "OPEN"CAS:" opens
                ; the NEXT file (name-matching is Item A's CLOAD/LOAD/RUN/MERGE
                ; scope, not OPEN)". That scoping was a GUESS about the reference
                ; that no row had ever checked, and it is measured WRONG: both the
                ; VG-8020 and the CF-3300 step over a non-matching file and open the
                ; named one, so zerobas was handing back the WRONG FILE'S BYTES.
                ; cas_capture_name above has already armed CAS_WANT/CAS_WANT_ON
                ; (0 for a bare OPEN"CAS:" = load next, which the references also
                ; do), so the suppression is simply GONE — the search engine needed
                ; no change at all.
                call    cas_open_match      ; TAPION header + read id/name; CF = tape end
                jp      c,dpl_dio           ; D-CASBRK: an I/O error / Ctrl-STOP is 19, raised
                                            ; (the VG-8020's `19 in 20`); load_error returned
                ld      a,(CAS_HDRID)
                cp      ASCII_ID            ; a cassette data file is an $EA ASCII file
                jr      nz,oocas_ioerr
                pop     hl                  ; D-CASFCB: the file's own channel buffer,
                pop     de                  ;  #n (the search used #0's): stack
                push    de                  ;  [cursor][channel], read and kept
                push    hl
                ld      a,e
                call    cas_bufp_set
                call    cas_ascii_setup     ; prime data block 1
                jp      c,dpl_dio           ; D-CASPRIME: a failed read is 19, raised
                                            ; (ours: `load error`, and the run went on)
                jr      oocas_mark
oocas_do_out:
                ; --- FOR OUTPUT: write the $EA header block; arm the data buffer ---
                ; D-CASOPEN: cas_write_ea_header emits TSV_NAME (it is shared with
                ; SAVE"CAS:"/CSAVE, which fill it from tape_parse_name), so the name
                ; captured above has to be put back where it expects it. This copy
                ; is the WHOLE cost of the slice — the INPUT half is byte-negative.
                ; MEASURED unchanged on all three sides by castail's
                ; `cas-openout:tape` ('WX    ') and `cas-openoutbare:tape` (six
                ; spaces), which are also the first rows in this tree ever to read
                ; what a cassette OPEN actually WRITES. HL/DE/BC are free: both
                ; pushes are above and oocas_mark pops them.
                ld      hl,CAS_WANT         ; 🟡 D-TSVOVL (2026-10-17): TSV_NAME IS
                ld      de,TSV_NAME         ;  CAS_WANT now (FILNAM), so this copies
                ld      bc,6                ;  onto itself -- kept, not removed: the
                ldir                        ;  11 B are in front of a pin (no hole)
                pop     hl                  ; D-CASFCB: write through channel #n's
                pop     de                  ;  own buffer, as the VG-8020 does
                push    de
                push    hl
                ld      a,e
                call    cas_bufp_set
                call    cas_write_ea_header ; TAPOON long + $EA*10 + TSV_NAME + TAPOOF
                jp      c,dpl_dio           ; D-CASWBRK: Ctrl-STOP -> 19, raised
oocas_mark:
                pop     hl                  ; text cursor
                pop     de                  ; channel
                jp      oo_stamp_devtype    ; D-CARVE2 (-10 B, main page 1); jp since
                                            ; D-CASBRK's `jp c,dpl_dio` above (+1 B)
oocas_ioerr:
                pop     hl
                pop     de
                jp      load_error

; dev_cmp — case-insensitive compare of the string at (HL) against the
; 0-terminated device name at (DE). Match: Z, HL advanced past the prefix.
; Mismatch: NZ, HL unchanged. Clobbers A, C, DE.
dev_cmp:
                push    hl                  ; save the start for the mismatch restore
dcmp_lp:
                ld      a,(de)
                or      a
                jr      z,dcmp_hit          ; hit the 0 term -> full prefix matched
                ld      c,a                 ; expected (uppercase) char
                ld      a,(hl)
                call    upcase
                cp      c
                jr      nz,dcmp_miss
                inc     hl
                inc     de
                jr      dcmp_lp
dcmp_hit:
                pop     bc                  ; discard the saved start (keep advanced HL)
                xor     a                   ; Z set
                ret
dcmp_miss:
                pop     hl                  ; restore HL to the string start
                ld      a,1
                or      a                   ; NZ
                ret

; oodv_notout -- a device OPEN whose FOR clause is not OUTPUT. LPT: / CRT: stay
; Syntax error (oo_dev_open's own note says why); GRP: is `Bad file name`, 56,
; at the OPEN -- MEASURED on the VG-8020 (D-OPENGRP round 1, `OPEN"GRP:"FOR
; INPUT AS #1` -> 56 in the OPEN's line). Sited past the `ret` above, not beside
; oo_dev_open: there it sat between oo_fail_* and the `jr`s the device and
; cassette arms aim at them, and pushed them out of range one after another.
oodv_notout:
                ld      a,(OO_DEVTYPE)
                cp      GRP_MODE
                jp      z,pdf_badname
                jp      oo_fail_syn

dev_lpt:        db      "LPT:",0
dev_crt:        db      "CRT:",0
dev_grp:        db      "GRP:",0

; --- fname_expr: a filename ARGUMENT is a string EXPRESSION ------------------
; D-FNEXPR (docs/spec-basic-fnexpr.md). Wherever the reference accepts a
; filename it accepts any string expression -- `OPEN A$ AS #1`,
; `OPEN A$+".DAT"`, `OPEN(A$)` -- and this tree accepted a LITERAL and nothing
; else, at every quote gate. Measured across seven verbs by D-FNARG/D-FNARG2:
; eight divergent rows against four green controls.
;
; 🎯 THE CHANGE SURFACE IS THE QUOTE GATES, NOT THE ELEVEN `parse_disk_fcb`
; CALL SITES THE RESIDUAL NAMED. `parse_disk_fcb` walks (HL) to a '"' and is
; already source-agnostic, so it needs NO second source and does not change --
; which matters, because basic/pdfcb-body.inc is included in three places
; byte-identically, one of them the sub-ROM tenant.
; 🎯 AND A STRING LITERAL IS ITSELF A STRING EXPRESSION, so `str_eval` serves
; both and there is no dual path: `OPEN"X.DAT"` and `OPEN A$` take one route.
;
;   in:  HL -> the filename argument (cursor as skip_spaces left it)
;   out: HL -> a staged, '"'-terminated copy of the name at STRSCR+1;
;        (FN_RESUME) = the text cursor just past the expression.
;        Does NOT return if the operand is not a string -> els_tc_common.
;   Clobbers A, BC, DE.
;
; ✅ THE NON-STRING FACE IS MEASURED NOW, AND D-FNEXPR'S PRESERVED ONE WAS
; WRONG (D-FNEXPR2, docs/spec-basic-fnexpr2.md §3). This header used to read
; "the reference may well answer `Type mismatch` ... but that is UNMEASURED, so
; today's face is preserved rather than guessed at." It was measured, and the
; guess it declined to make was the right one -- at SIX verbs at once, on the
; CF-3300, rows n.opennum/n.killnum/n.savenum/n.loadnum/n.bloadnum/n.filesnum:
;
;   OPEN 5 AS #1 / KILL 5 / SAVE 5 / LOAD 5 / BLOAD 5 / FILES 5  ->  Type mismatch
;
; 🎯 SO THE THREE FACES DO CONVERGE -- AND THAT IS A READING, NOT THE
; ASSUMPTION IT WOULD HAVE BEEN. zerobas answered a non-quote with three
; different things (`Syntax error` raised, `load error` printed-and-returned,
; and a whole DIRECTORY LISTING then a late `Syntax error`); the reference
; answers ONE thing at all six.
;
; 🔴 BUT "NON-STRING -> Type mismatch" IS NOT THE WHOLE RULE, AND THE ROW THAT
; SAYS SO IS `n.savediv` / `n.opendiv`: `SAVE 1/0` and `OPEN 1/0 AS #1` answer
; **Division by zero**, not Type mismatch. The reference EVALUATES the operand
; and the operand's OWN fault wins -- bit for bit the rule D-MISS-1 measured at
; the LET mirror (`A$=1/0` -> Division by zero, basic/missing.asm).
; 🎯 WHICH IS WHY THE EXIT BELOW IS `els_tc_common` AND NOT A NEW ROUTINE: that
; IS D-MISS-1's tail (eval the operand as numeric -> check_expr_errors, so its
; own fault aborts -> ERRMARK $DD means nothing parsed -> stmt_error -> else
; type_mismatch_error). A third entry point costs ZERO BYTES -- `els_typecheck`
; and `elas_typecheck` each pop their own saved word and fall into it, and this
; caller has none to pop, so it enters at the common label directly. The dead
; return address left on the stack is discarded by raise_error's own
; `ld sp,(SAVSTK)` unwind, which every exit from there takes.
;
; ⚠️ THE BARE FORM MOVES TOO, AND IS A DIVERGENCE THIS DOES NOT CLOSE. `SAVE` /
; `LOAD` / `BLOAD` with NO argument answer `Missing operand in 10` on the
; CF-3300 -- raised, with a line number. They answered a PRINTED `load error`
; here and they answer a RAISED `Syntax error` now: closer (it stops, it
; traps), still the wrong wording, because `Missing operand` is a message
; zerobas does not have. That is the SAME disposition D-MISS-1 recorded for the
; LET mirror `A$=`, and rows n.savebare/n.loadbare/n.bloadbare hold it DEFERRED
; rather than letting it read as agreement.
;
; ⚠️ STRSCR SECOND-TENANT ARGUMENT, stated because STRSCR is a single shared
; scratch (the MIDS_DEST-style claim). Its other tenant is `read_into_strscr`
; (INPUT# / LINE INPUT#, below in this file): a filename parse happens at a
; STATEMENT HEAD, `read_into_strscr` runs INSIDE an already-open INPUT#, so the
; two can never nest. Every caller here consumes the staged copy with
; `parse_disk_fcb` -- a pure walk into DISK_FCB_NAME -- before it touches the
; drive; `do_name`'s second operand is the one exception and carries its own
; argument at the site.
; ⚠️ AND THE SELF-OVERLAP IS BENIGN, not unconsidered: `OPEN INPUT$(2,#1) AS #1`
; has str_eval fill STRSCR itself, so RVDESC.ptr IS STRSCR+1 and the `ldir`
; below runs with HL == DE, copying each byte onto itself. A no-op, then the
; terminator is appended past the end as usual.
; 🔴 LEADING SPACES ARE THIS ROUTINE'S JOB, AND FOUR CALLERS FOUND THAT OUT THE
; HARD WAY. D-FNEXPR's five call sites each did `call skip_spaces` immediately
; before `call fname_expr`, so the contract "HL -> the filename argument" was
; satisfied by every caller and never stated. D-FNEXPR2's four new sites
; replaced gates that had BEEN that `skip_spaces` (`call skip_spaces` / `cp '"'`
; / `jp nz,load_error` / `inc hl`), and dropping the gate dropped the skip with
; it: `SAVE A$` handed `str_eval` a SPACE, which is not a string operand, and
; three rows read `<Type mismatch>` where the CF-3300 says `OK`.
; 🎯 AND THE 🟢 LITERAL CONTROLS WERE STRUCTURALLY BLIND TO IT. `SAVE"FC1.DAT"`
; has no space between the verb and the argument and a variable form cannot not
; have one -- so `f.savelit` was green in the same run that `f.savevar` was red,
; and the pair separated the two only by an accident of how each is spelled.
; Absorbing the skip HERE is both the fix and cheaper than four `call`s: the
; four sites that already did it (do_open, do_kill, do_name x2) drop theirs, so
; the contract is stated once, enforced once, and costs -9 B rather than +12.
; ⚠️ do_files keeps its own, and not out of caution: it READS the skipped byte
; to decide whether there is an argument at all.
; --- pdfcb_resume: parse_disk_fcb, then HL := FN_RESUME -------------------------
; 💰 D-PDFCBRESUME (2026-09-10): `call parse_disk_fcb` / `ld hl,(FN_RESUME)`
; stood at NINE sites (cload x2, files x5, save x2), all main page 1, 6 B each,
; against 3 for a call: 9 x 3 saved less this 7-byte body = 20 B of page 1 --
; found by the instruction-PAIR scan D-INCSKIP opened (clone_scout ranks label
; blocks and cannot see a pair), when D-KEYSTR left page 1 at 13 B. Every site
; resumes past the whole EXPRESSION rather than past a quote in the staging
; buffer (D-FNEXPR2), which is what the second instruction has always meant.
; Sited HERE and not in pdfcb-body.inc: that body is included in three places.
; Same contract as parse_disk_fcb (raises on a bad name; clobbers A,B,C,DE,HL).
pdfcb_resume:
                call    parse_disk_fcb
                ld      hl,(FN_RESUME)
                ret

; --- pdf_baddrive: a drive past B: -> ERR 62 `Bad drive name` (D-DRVNAME) -----
; parse_disk_fcb sent it to bl_load_error, and load_error PRINTS AND RETURNS --
; from inside the parser, so the caller carried on with the drive still at its
; default A: and `OPEN "Q:F.TXT" FOR OUTPUT` made the file on A:. The CF-3300
; raises 62 for C: .. H: and Q: (scratchpad/drvname_run.out) on OPEN, KILL, SAVE,
; FILES and RUN (t6enum_b8_zb.out); A:, a: and B: -- its phantom drive, which
; waits for a disk -- are not errors. The same fix D-FSPEC made for a malformed
; NAME (pdf_badname, 56), and bound per build the same way: sub/bload.asm keeps
; bl_load_error for BLOAD, whose answer is unmeasured.
; 🧭 THE BODY MOVED TO THE LOW REGION on 2026-09-28 (D-NEWARG), beside its
; sibling pdf_badname in basic/str-engine.asm: page 1 was where it first went
; because the low region had 2 B that day; D-CARVESEQ left the low region 6 B
; and page 1 2, and NEW's end-of-statement check needed page 1's.

fname_expr:
                call    skip_spaces         ; 🔴 D-FNEXPR2: **INSIDE**, and it was a
                                            ; defect that it was not. See the
                                            ; block above the label.
                call    str_eval            ; STRPTR -> [len][ptr]; HL past the expr
                jp      nc,els_tc_common    ; not a string -> D-MISS-1's measured
                                            ; tail: the operand's OWN fault wins,
                                            ; else ERR 13 `Type mismatch` (see the
                                            ; block above -- 0 B, it already ships)
                ld      (FN_RESUME),hl      ; where the statement resumes
                ld      hl,(STRPTR)
                ld      a,(hl)              ; A = length
                call    pu_deref_body       ; HL = body address (A preserved)
                ld      de,STRSCR+1
                ld      c,a
                ld      b,0
                or      a
                jr      z,fnx_term          ; empty name: BC=0 would ldir 65536
                ldir
fnx_term:
                ld      a,'"'
                ld      (de),a              ; parse_disk_fcb terminates on '"'
                ld      hl,STRSCR+1
                ret

; oo_parse_reclen — parse an optional "LEN = expr" record-size clause at (HL).
; LEN is the $FF $92 function token; '=' is EQ_TOKEN. Absent -> DE = 256 (the
; historical fixed record length), Cy = 0. Present -> DE = the evaluated record
; length, validated to ANY value in 1..256; an out-of-range value returns Cy = 1,
; which the caller raises as ILLEGAL FUNCTION CALL (D-RECLEN2: measured ERR 5 on
; the CF-3300 for LEN=0/257/512, where this used to answer Syntax error).
; 🔴 THIS HEADER SAID "validated to a power of two" AND CALLED THAT RULE
; LOAD-BEARING UNTIL 2026-09-09, WHILE ITS OWN BODY TWENTY LINES BELOW SAID THE
; OPPOSITE -- "✅ THE DOMAIN IS 1..256, AS THE REFERENCE'S IS (D-RECLENFIX,
; 2026-09-06)". All three prerequisites the old text named have landed: D-MULREC
; (mul_reclen was a shift), D-STRADDLE (put/get can span two sectors) and
; D-RECLENFIX (the validator itself). A header and its body disagreeing on the
; load-bearing rule is the shape that gets a reader to "optimise" against a
; restriction the code no longer has [[a-fix-falsifies-the-justification-beside-it]].
; Clobbers A,BC,DE,HL.
oo_parse_reclen:
                call    skip_spaces
                cp      PEEK_PREFIX         ; $FF function-token prefix?
                jr      nz,opr_default
                inc     hl
                ld      a,(hl)
                cp      LEN_TOKEN           ; $92 = LEN
                jr      z,opr_have
                dec     hl                  ; not LEN -> restore cursor to the $FF
opr_default:
                ld      de,256              ; no LEN= -> default record length
                or      a                   ; Cy = 0
                ret
opr_have:
                rst    $10                ; past $92
                ; D-RECLENERR (2026-10-07): the CF-3300 answers a bare `LEN` with
                ; Syntax error (2) and `LEN="A"` with Type mismatch (13); both
                ; reached the range test here and read Illegal function call (5)
                ; (scratchpad/t6enum_b8_zb_1006.out). Only the RANGE is 5.
                cp      EQ_TOKEN            ; '='
                jp      nz,oo_fail_syn      ; no `=`: 2
                inc     hl
                call    eval_int16_checked  ; DE = record length; a string is 13
                ld      a,d
                or      a
                jr      z,opr_lowbyte       ; D=0 -> reclen 1..255
                ; D != 0: the only legal value is exactly 256 (D=1, E=0).
                dec     a
                jr      nz,opr_bad          ; D>=2 -> > 512
                ld      a,e
                or      a
                jr      nz,opr_bad          ; D=1,E!=0 -> > 256
                ld      de,256              ; reclen = 256 (2 records / sector)
                or      a                   ; Cy = 0
                ret
opr_lowbyte:
                ld      a,e
                or      a                   ; also clears Cy for the accept below
                jr      z,opr_bad           ; reclen 0 invalid
                ; ✅ THE DOMAIN IS 1..256, AS THE REFERENCE'S IS (D-RECLENFIX,
                ; 2026-09-06). A power-of-two rule stood here and was
                ; load-bearing for exactly as long as the engine could not
                ; straddle a sector: `fat_rand_put`'s overlay was ONE `ldir` into
                ; `FWBUF + GP_WITHIN`, so record 6 at r=100 (within=500) wrote 88
                ; bytes PAST the 512-byte buffer, and two PUTs at LEN=100
                ; including record 6 killed the program.
                ; 🔴 IT TOOK THREE FIXES, NOT ONE, AND D-RECLEN2 SHIPPED THE
                ; DROP ALONE IN 2026-08-30 AND HAD TO REVERT IT:
                ;   * `mul_reclen` was a SHIFT (HL * 2^floor(log2 r)) -- D-MULREC;
                ;   * `fat_rand_put`/`fat_rand_get` could not span two sectors --
                ;     D-STRADDLE, witnessed by tests/test_rand_straddle.py, which
                ;     builds the expected sector image INDEPENDENTLY and guards
                ;     the bytes above FWBUF+512;
                ;   * only then this.
                ; ⚠️ AND THE ROWS THAT "PROVED IT SAFE" IN AUGUST WERE BLIND TWICE:
                ; the shift put record 6 at within=320 so it never straddled, and
                ; a round-trip cannot see a wrong offset because PUT and GET share
                ; it. Neither blindness is fixable by adding emulator rows of the
                ; same shape, which is why the witness is a HOST test.
                ret                         ; Cy = 0 from the `or a` above
opr_bad:
                scf
                ret

; --- LINE: disambiguate LINE INPUT (file/console) from graphics LINE (G3) ------
; Runtime disambiguation (docs/spec-basic-graphics-g3.md §7, measured §11.1): after
; the LINE token, an INPUT token ($85) means LINE INPUT; anything else — the graphics
; forms all begin with '(' ($28), '-' ($F2) or STEP ($DC) — is a graphics LINE.
ex_line:
                rst    $10                ; HL -> bytes after the LINE token
                cp      INPUT_TOKEN         ; LINE must be followed by INPUT ...
                jp      nz,ex_line_gfx      ; repack: else it's a graphics LINE (graphics.asm)
                inc     hl                  ; HL -> after INPUT
                ld      a,1                 ; read mode = LINE (stop at CR only)
                jr      input_common

; --- INPUT #n, A$  (file form only) ----------------------------------------
ex_input:
                inc     hl                  ; HL -> bytes after the INPUT token
                xor     a                   ; read mode = field (stop at ',' or CR)
input_common:
                ld      (FCH_RDMODE),a
                call    skip_spaces
                cp      '#'                 ; file form (#n) vs the console form
                jp      nz,input_console    ; repack: console INPUT / LINE INPUT (basic/input.asm)
                inc     hl
                ; §5.7 gaps: a mid-statement FP error in the channel-number
                ; expression must abort the RUN here, before the field is read,
                ; matching the reference's abort-before-read ordering (was:
                ; swallowed, then either surfaced late via the post-read
                ; check_expr_errors — the arrays-4c `INPUT#1+0*(1/0)` divzero
                ; ordering fix — or, for an OUT-OF-RANGE channel like
                ; `INPUT#99999*99999`, never raised at all and derailed to "load
                ; error", gap 1). eval_chan (float-arith.asm) = eval + numeric-
                ; channel int coercion (out-of-range -> Overflow) + check_fperr_
                ; only (deferred Division-by-zero). A TMISMATCH channel (INPUT#A$)
                ; still derails through fch_valid to "load error" (coercion skipped
                ; on a hard-zeroed type mismatch) -- that ordering is untouched.
                call    eval_chan
                call    fch_check           ; D-BADFNUM: D!=0 -> ERR 5, 0 -> ERR 59,
                                            ; > MAXF -> ERR 52. Was `jp nc,load_error`,
                                            ; one untrappable message for all three
                ; classify the channel by FCH_MODES[ch] WITHOUT fch_select (a cassette
                ; channel owns no fat.asm ctx — selecting it would LDIR garbage over
                ; the globals). CAS_IN reads via cas_in_getbyte; a disk channel keeps
                ; the fch_select + mode==1 path. read_into_strscr sources bytes
                ; through the ARL_GETBYTE vector, set here per channel type.
                ; D-NOTOPEN (docs/spec-basic-chan-notopen-err59.md): this arm serves
                ; INPUT# *and* LINE INPUT# (both reach input_common), and it used to
                ; hand-inline fch_mode_class's array read while OMITTING its `or a`
                ; -- so a NOT-OPEN channel (mode 0) went on to fch_select the closed
                ; slot and then failed the `cp 1` below into `load_error`, which
                ; PRINTS AND CONTINUES. The CF-3300 raises a trappable ERR 59, as
                ; zerobas's own LOF(1) on the same closed channel already does.
                ; Contract as at the PRINT# site: E preserved (needed by the
                ; fch_select below), A/HL clobbered under the existing push/pop, D
                ; no longer zeroed and not read before `ld de,fat_io_getbyte`.
                push    hl                  ; guard text cursor
                call    fch_mode_class      ; A = FCH_MODES[ch]; ERR 59 if not open
                pop     hl
                cp      CAS_IN_MODE
                jr      z,inp_setsrc        ; cassette: A = CAS_IN_MODE already, and
                                            ; NO fch_select (see above)
                push    hl                  ; guard text cursor
                ld      a,e
                call    fch_select          ; make channel e live; A = its mode
                pop     hl                  ; (2026-10-19: the `ld a,(FCH_MODE)`
                                            ; reload here was dead since S10.E)
                ; D-CHDIR (2026-10-06): as PRINT#'s -- 61 on a RANDOM channel, 52
                ; on one open FOR OUTPUT / APPEND, both trappable on the CF-3300
                ; (scratchpad/chdir_run.out); load_error printed and went on.
                cp      4
                jp      z,sid_badmode
                cp      1                   ; a channel must be open for INPUT
                jp      nz,err_badfnum_raise
inp_setsrc:
                ; D-CASINP: the two-way source choice moved to arl_set_src
                ; (basic/input.asm) so INPUT$ can make it too. -11 B here.
                push    hl                  ; HL is the text cursor; arl_set_src uses it
                call    arl_set_src         ; A = the mode (1 disk / CAS_IN_MODE tape)
                pop     hl
inp_readvar:
                call    req_comma           ; D-NGRAM17
                call    req_letter          ; D-NGRAM: a variable name must follow
                ; 🔴 D-INPNUM (2026-09-29): a NUMERIC target was Type mismatch here for
                ; every value -- `PRINT #1,5` read back with `INPUT #1,X` is 5 on the
                ; CF-3300 (scratchpad/inpnum_run.out). input.asm's inp_numitem reads
                ; it; LINE INPUT # comes straight back to inp_str from there.
                call    var_str_type        ; A = 1 if the name carries a '$'
                or      a
                jp      z,inp_numitem
inp_str:
                call    str_target_parse    ; string-var target: type-check, parse,
                                            ; raise -- D-NGRAM9
                ; D-LVFIX (docs/spec-basic-lvsites.md §4.2): the target is any
                ; string variable REFERENCE, array element included -- measured
                ; on the CF-3300 (docs/lvsites-msx1-characterization.md, f.ary).
                ; This is byte for byte the edit D-ARYLV made at inpc_vstr, and
                ; needs no ARYTAB-delta correction (§5.5): read_into_strscr calls
                ; only arl_getbyte, which allocates no variable.
                                            ; mapped, so this yields the
                                            ; reference's own `Subscript out of
                                            ; range`, not `Syntax error`
                push    hl                  ; guard the BASIC text cursor
                push    bc                  ; guard the variable key across the read
                call    read_into_strscr    ; fill STRSCR [len][bytes] from the file
                call    c,seq_end           ; the end: a failed read raises its code,
                                            ; nothing read raises 55 (D-SEQEOF R3)
inp_got:
                pop     bc
                call    tgt_store_str       ; scalar key OR element address
                pop     hl
inp_tail:                                   ; D-INPNUM: the numeric item rejoins here
                ; arrays slice-4c (§7.3) follow-up, same disposition as
                ; console/LINE INPUT's own checks (basic/input.asm): a
                ; scalar-CHAIN OOM here sets FPERR but does not itself abort.
                ; SP is at statement level (the guard words above are both
                ; popped) -- check_expr_errors (interp.asm) is the SP-clean-
                ; site variant. The channel-number expression's own FPERR is
                ; now caught earlier, before the field read (the FPERR-only
                ; check right after `call eval` above) -- this call only
                ; catches a post-read scalar-chain OOM from str_set_key plus a
                ; TMISMATCH from that same store (the latter always 0 here in
                ; practice: str_set_key's own D-2 path handles a bad source
                ; descriptor before it would reach here).
                call    check_expr_errors
                ; --- D-INPLIST: `INPUT #n` TAKES A LIST OF TARGETS ------------
                ; `INPUT#1,A$,B$` over a `HI,LO` file reads `HILO` on the
                ; CF-3300 and was `Syntax error` here, because this site parsed
                ; exactly ONE target and fell into `jp exec_stmt` -- the leftover
                ; `,` was what errored (docs/spec-basic-lvsites.md, row f.mixctl,
                ; carried DEFERRED in lvfix-acceptance until now).
                ;
                ; 🎯 THE LOOP IS THE ROUTINE ITSELF. inp_readvar already opens by
                ; requiring the separator -- it was written for the comma between
                ; the CHANNEL NUMBER and the first target -- and a comma between
                ; two targets is the same byte in the same place. So the tail
                ; tests for one and re-enters at the top, which consumes it and
                ; parses the next reference with the identical tgt_parse /
                ; read_into_strscr / tgt_store_str path. No second parser, and no
                ; state to carry: the channel was selected before this routine was
                ; entered and each pass simply reads the next field.
                ;
                ; SP is at statement level here (both guard words are popped
                ; above), which is the same depth inp_readvar was first entered
                ; at, so the abort contracts of every callee still hold on the
                ; second and later passes. check_expr_errors returns with HL
                ; untouched on the OK path (interp.asm: `ld a,(FPERR)`/`or a`/
                ; `ret`), so the cursor this test reads is the one tgt_store_str
                ; left. ⚠️ Numeric `INPUT #n` is still rejected at the top of the
                ; loop, exactly as it was for a single target -- this widens the
                ; COUNT of targets, not their type.
                call    skip_comma
                jr      z,inp_readvar       ; another target -> round again
                jp      exec_stmt

; read_into_strscr — read bytes from the open channel into the STRSCR descriptor
; ([len][bytes]) until the mode's delimiter or EOF. FCH_RDMODE: 0 = field (stop at
; ',' or CR), 1 = line (stop at CR). LF bytes are ignored; CR ends the read. A byte
; past STRMAX is dropped (input keeps consuming to the delimiter). All loop state
; is in RAM — the byte source is a CALLF / CALSLT, which clobbers every register.
read_into_strscr:
                xor     a
                ld      (IN_RDLEN),a
                ; 🔴 D-INPQUOTE (2026-09-30): STRSCR's length byte is the QUOTE STATE
                ; while the field is read -- 0 none, `"` inside a quoted field, `,`
                ; past its closing quote -- because every exit (ris_done =
                ; sidr_done) rewrites it with the length. FCH_RDMODE could not
                ; carry it: the statement sets that ONCE and reads it again per
                ; variable, so `INPUT #1,A$,N` would have inherited the state.
                ld      (STRSCR),a
ris_lp:
                call    arl_getbyte         ; byte source vector: fat_io_seqbyte (disk:
                                            ; H_CHIN into disk.rom since S10.C) or
                                            ; cas_in_getbyte (CAS: input), set by
                                            ; arl_set_src per channel type
                jp     c,ris_done          ; EOF -> stop
                cp      $0A                 ; ignore LF entirely
                jr      z,ris_lp
                cp      $0D                 ; CR ends the line / field
                jp     z,ris_done
                ld      c,a                 ; C = candidate data byte
                ld      a,(STRSCR)
                or      a
                jr      nz,ris_quoted       ; D-INPQUOTE: inside or past the quotes
                ld      a,(FCH_RDMODE)
                or      a
                jr      nz,ris_keep         ; line mode keeps everything (but CR/LF)
                ; (D-INPNUM's numeric mode lived here for a day and is gone: a
                ; numeric item's rules need a PEEK -- `" 1  2 "` leaves "2 " for
                ; the next read -- and only the seqio tenant has one; D-CHANSWITCH.)
                ld      a,c
                cp      ','                 ; field mode stops at a comma
                jp     z,ris_done
                ; 🔴 D-INPSTR (2026-09-29): a field's LEADING blanks are not data --
                ; `INPUT #1,A$` of " 5 " (what PRINT #1,5 writes) is "5 " on the
                ; CF-3300 and `INPUT A$` typed "  AB" is "AB" on the VG-8020; trailing
                ; and embedded blanks stay (scratchpad/inpstr_run.out). Console and
                ; file share this field reader, so one test serves both.
                cp      ' '
                jr      nz,ris_nb
                ld      a,(IN_RDLEN)
                or      a
                jr      z,ris_lp            ; a blank before the field's first byte
ris_nb:
                ; D-INPQUOTE: a `"` as the field's FIRST byte (leading blanks
                ; already shed) opens a quoted field: file and console alike, `"A,B"`
                ; is A,B and `"  AB  "` keeps its blanks, on both references
                ; (scratchpad/inpstr_run.out). Anywhere else a quote is data.
                ld      a,c
                cp      '"'
                jr      nz,ris_keep
                ld      a,(IN_RDLEN)
                or      a
                ld      a,c                 ; the state IS the awaited byte: `"`
                jr      z,ris_setq
ris_keep:
                ld      a,(IN_RDLEN)
                cp      STRMAX
                jr      nc,ris_lp           ; full -> drop, keep consuming to delim
                ld      e,a
                ld      d,0
                ld      hl,STRSCR+1
                add     hl,de               ; HL -> STRSCR+1+len
                ld      (hl),c              ; store the byte
                ld      hl,IN_RDLEN
                inc     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
                jr      ris_lp
; ris_quoted -- A = the quote state (the byte awaited), C = the byte read. Inside
; the quotes every byte but `"` is data, commas included; the closing quote
; switches to `,`, and past it everything up to the comma is DISCARDED (both
; references consume the rest of the field). CR and EOF already ended the read.
ris_quoted:
                cp      c
                jr      z,ris_qhit
                cp      '"'
                jr      z,ris_keep          ; inside: data
                jr      ris_lp              ; past the closing quote: dropped
ris_qhit:
                cp      ','
                jp      z,ris_done          ; past it, the comma ends the field
                ld      a,','               ; the closing quote: now await the comma
ris_setq:
                ld      (STRSCR),a
                jr      ris_lp
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to sidr_done,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
ris_done        equ     sidr_done

; --- CLOSE [#n] -------------------------------------------------------------
; CLOSE [#n] — close one channel, or (bare CLOSE) every open channel. An OUTPUT
; channel is flushed + Ctrl-Z-stamped via fch_do_close_ch (which selects it first,
; so the right channel's buffer/dir state is the one flushed).
ex_close:
                call    stmt_bare_end       ; D-BAREEND: Z iff the statement ends here
                jr      z,dc_all
                ; CLOSE [#]n [, [#]m ...] — a comma-separated channel list. Loop:
                ; parse one [#]expr, close it, and while the next token is ',' repeat.
dc_listloop:
                call    skip_spaces
                cp      '#'
                jr      nz,dc_num
                inc     hl
dc_num:
                call    eval                ; DE = channel number; HL = text cursor
                push    hl                  ; guard the cursor (HL is reused + CALSLT)
                ; D-BADFNUM: the reference is lenient about channel 0 ONLY. CLOSE #2
                ; / #16 / #256 / #-1 all RAISE there, while this used to no-op every
                ; one of them silently -- `CLOSE #2 : PRINT 7` printed 7.
                call    fch_check_d         ; D != 0 -> ERR 5; else A = E, Z <=> ch 0
                jr      z,dc_done           ; channel 0 -> the one lenient no-op
                call    fch_check_nz        ; > MAXF -> ERR 52
                ld      a,e                 ; FCH_MODES[ch] == 0 ? -> already closed
                call    fch_modes_ptr       ; (preserves E for the fch_do_close_ch below)
                ld      a,(hl)
                or      a
                jr      z,dc_done           ; not open -> no-op
                ld      a,e
                call    fch_do_close_ch     ; flush (if OUTPUT) + mark closed
dc_done:
                pop     hl                  ; restore the text cursor
                call    skip_comma
                jp     nz,dc_finish        ; no more channels in the list
                inc     hl                  ; consume ',' and parse the next channel
                jr      dc_listloop
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; ed_done and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
dc_finish       equ     ed_done
dc_all:
                push    hl                  ; guard text cursor across CALSLT
                call    fch_close_all
                jp      pop_exec            ; D-POPEXEC: pop hl + exec_stmt

; init_filechan — cold-start the file-channel state: no channel open, PRINT to
; screen, the multi-channel table empty, and MAXFILES = 1 (the observed default:
; OPEN #1 works with no MAXFILES on the real CF-3300). Called from `init` before
; the banner is printed.
init_filechan:
                xor     a                   ; (no FCH_MODE store since 2026-10-19:
                ld      (PRDEST),a          ; OPEN writes it before its only reads)
                ld      (PRDEV),a           ; default PRINT# sink = disk file
                ; 🔴 D-LPTVERB: THE PRINTER COLUMN MUST BE COLD-STARTED, and the
                ; CONTROL row is what caught this. LPTPOS is plain RAM, so at
                ; power-on it holds garbage; `repl`'s R-LP16 flush fires whenever it
                ; is non-zero, so an uninitialised cell made the machine emit a
                ; spurious CR/LF to the printer on the FIRST prompt. Every printer
                ; log then read `\r\n` + the expected bytes -- including `lpr-ctl`,
                ; which exercises only OPEN"LPT:" and no new code at all. That is
                ; exactly why that control exists: the defect was in this slice's
                ; new code and showed up on a row that is not about its subject.
                ld      (LPTPOS),a          ; printer head at column 0
                ld      (FCH_ACTIVE),a      ; no channel live in the engine globals
                ; 🗑️ S10.C (2026-10-15): ARL_GETBYTE IS NO LONGER DEFAULTED HERE.
                ; It was seeded with main's fat_io_getbyte (D2), which left with
                ; the resident fatio-body.inc -- and the seed was already dead: every
                ; reader sets the vector itself before its first byte (input_common
                ; and INPUT$ through arl_set_src, the console through inp_readline /
                ; chget_getbyte, LOAD / MERGE through dsk_ascii_drive /
                ; cas_ascii_drive). Checked at every `arl_getbyte` caller, 2026-10-15.
                ; clear the per-channel mode array [0..FCH_CEIL].
                ld      hl,FCH_MODES
                ld      b,FCH_CEIL+1
ifc_zero:
                ld      (hl),a
                inc     hl
                djnz    ifc_zero
                ld      a,1
                ld      (MAXF),a            ; default ceiling = 1 (#1 always usable)
                ret                         ; (D-FLDDESC: was `jp fld_init_g`, the
                                            ; FIELD table's reset; there is no table)

; ===========================================================================
; Channel manager (Phase 2 MAXFILES) — the multi-channel substrate that retires
; the single-channel limit, WITHOUT touching the oracle-validated fat.asm engine.
;
; 🏗️ S10.E (2026-10-19): THERE IS NO SWITCH ANY MORE. What follows the next
; paragraph's first sentence is the design S10.B-S10.E dismantled: every disk
; channel is an MSX-DOS FCB in its own DSK_ENGTAB row, owned by disk.rom from
; OPEN, its record the block's +9; LOF / LOC read that FCB through H_CHIN ops
; 6 / 8. So "making a channel live" is FCH_ACTIVE := ch (the cell disk.rom's
; hooks find the row by) -- fch_select below, which hands back the mode in A
; -- and nothing is saved or loaded. (Its FCH_MODE mirror store went too,
; 2026-10-19: the three statement drivers that re-read it take A.)
; 📜 HISTORY: fat.asm kept ONE global set of streaming state (FSECTOR_BUF +
; FCH_STATE0..). Each open channel owned a context block (FCH_CTX[ch] =
; [state:FCH_STATESZ][512]) holding a saved copy; the globals always held the
; "active" channel's LIVE state. A write-back cache: FCH_ACTIVE named the live
; channel; switching to a different channel SAVED the globals to the old
; channel's ctx and LOADED the new one's. FCH_MODE/FCH_NUM mirrored the active
; channel so the read/write/PRINT# code (which read those + the globals) worked
; unchanged.
;
; Register discipline: fch_select is a store and a table read -- A and HL
; clobbered, BC / DE / IX / IY kept, no CALSLT. Statement callers still guard
; their HL text cursor.
; ===========================================================================

; fch_ctx_addr — HL = base of channel A's context block (A = 1..FCH_CEIL).
;
; D-FCH §3.2 (repack): the table is no longer AT a fixed address. It is carved
; out of the pool at MAXFILES time, immediately below the string pool's floor
; (basic/sysvars.inc §D-FCH), so the base is
;   min(HIMEM,TXTMAX) - POOLSIZE - MAXF*FCH_CTXSZ
; and this routine asks the string-heap tenant for it (op 18, sh_chan_addr).
;
; ⚠️ SITED SUB-SIDE FOR THE S-FCH-1 REASON, MEASURED NOT GUESSED: the callee
; chain it needs (strheap_varceil -> strheap_floor -> strheap_ceiling) was
; ALREADY sub-ROM, so a resident copy of the arithmetic would have bought
; nothing and cost real page-1 bytes. Resident, this is the same three stores
; and a call the old stride loop was.
; ⚠️ IX: call_strheap is a CALSLT, so every caller guards IX itself if it needs
; it (ev_ff_varptrch does; S10.E retired fch_save_active / fch_load_ctx, whose
; guard sat in fch_select). Any NEW caller must be checked against that contract.
; Clobbers A, BC, DE, IX.
fch_ctx_addr:
                ld      l,a                 ; blk+0 = the channel number (1-based)
                ld      a,18
                jp      sh_go               ; op 18: HL = the channel block address

; REFILL (D-WSZERO S16, 2026-10-16): moved here from basic/program.asm, whole and
; self-contained (entered only by label), to refill bytes the stack parameter
; block freed in front of the $73AC pin -- tools/pin_plan.py's exact fill.
; --- le_call / le_call_op: the lineedit tenant's call sequence (D-NGRAM3) ----
; Five sites drove SUBROM_IDX_LINEEDIT with the identical 14 B run --
;     ld ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_LINEEDIT
;     call subrom_call / jp c,subrom_absent_error / ld a,(LE_STATUS) / or a
; -- LIST (list.asm), the line STORE, DELETE, RENUM and AUTO (this file). 70 B in
; all; one 15 B body plus five 3 B calls is 30 B.
; 🎯 AND FOUR OF THE FIVE SET LE_OP IMMEDIATELY BEFORE IT, so `le_call_op` is a
; 3 B second ENTRY rather than a second body: those four drop their own
; `ld (LE_OP),a` for nothing. Together: **-49 B of page 1.**
;   in:  A = the LE_OP_* code (passed on to the tenant in C).
;   out: A = LE_STATUS, Z set when it is 0 (ok). Every caller branches on exactly
;        that, and `ret` preserves both. Does NOT return when the sub-ROM is
;        absent: subrom_absent_error owns that exit.
; ⚠️ `relink` below is a SIXTH site with the same prefix and is deliberately NOT
; folded in: it returns WITHOUT reading LE_STATUS, so routing it through here
; would change the A and flags its callers see (cload.asm has two plain
; `call relink` sites). 7 B, declined until that contract is measured rather
; than assumed. [[a-shared-tail-is-not-a-decision]]
le_call_op:
                ld      c,a                 ; D-WSZERO S14g-d: the op rides in C (it
                                            ; was a RAM cell, LE_OP); sc_inl1,
                                            ; subrom_call and CALSLT pass BC
                call    sc_inl1             ; D-STUBINL: D-SCCALL: tenant call + absent raise
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_LINEEDIT)
                ld      a,(LE_STATUS)
                or      a
                ret

; fch_select — make channel A the live one: FCH_ACTIVE := A (disk.rom's hooks
; find the channel's FCB row through it). A = channel (range-validated, or 0
; from fch_park: "nothing live"). out A = FCH_MODES[A], the mode -- what
; input_common, PRINT# and CLOSE test next. 🗑️ 2026-10-19: it also stored the
; mode in FCH_MODE, and those three re-read the cell (`ld a,(FCH_MODE)`, 9 B);
; both are gone -- FCH_MODE is OPEN's provisional cell only. Clobbers A, HL; keeps BC, DE,
; IX (no CALSLT). No longer a disk.rom call-back: hk_dget stores FCH_ACTIVE
; itself since S10.E (tools/gen_resident_abi.py).
; 🗑️ S10.E (2026-10-19): IT WAS A CONTEXT SWITCH. With a different channel live it
; ran fch_save_active (the sub-ROM's t_fch_save: nothing left to save since
; D-FLDDESC) and fch_load_ctx (t_fch_load: re-cache the block's address, then
; MIRROR the FCB's LOF / LOC into FAT_FILESIZE / FWR_BYTES), each a CALSLT under
; one IX guard; fch_claim was OPEN's no-load half and fch_sync_mirror the
; same-channel half. LOF / LOC ask disk.rom for the FCB's value now (H_CHIN ops
; 6 / 8), so all five are this one body. (D-FCH S-FCH-1's write-back cache --
; fch_flush_active / fch_restage over fat_detach_channel / fat_restage_channel
; in basic/fat-prim-body.inc -- had already gone with D-MODE2DEAD and S10.C.)
fch_select:
                ld      (FCH_ACTIVE),a
                call    fch_modes_ptr
                ld      a,(hl)              ; A = the mode
                ret

; 📌 PIN REFILL (S10.E, 2026-10-19): 64 B moved here from past the $73E5 pin
; (basic/program.asm) to take back the 64 B the channel switch above freed in
; front of $72D4 -- every byte removed ahead of a pinned address grows its `ds`
; pad (basic/field.asm `ds $72D4 - $`), and Joost: no growing holes. Sited AT the
; hole, so every `jr` that spans it keeps its old reach. All three are whole and
; entered only by label, with no `jr` across their edges (tools/pin_plan.py
; chunks()); their stories stay where they were.
; ret_frame: pop the top GOSUB frame. out: DE = its saved CURLINE, BC = its resume
; pointer, GSP -= GOSUB_FRAME, HL = the new GSP, and FSP is truncated back to the
; frame's recorded depth. The caller has ALREADY established that the stack is
; non-empty (R-T1). (basic/program.asm, ex_return's two arms, D-RETLN / D-FORRET.)
ret_frame:
                ld      de,(GSP)            ; DE = the read cursor
                call    ctl_get
                push    hl                  ; [saved CURLINE]
                call    ctl_get
                push    hl                  ; [resume ptr]
                call    ctl_get             ; HL = prevFSP
                ld      (FSP),hl            ; prevFSP: discards the FOR frames opened
                                            ; since this GOSUB (D-FORRET)
                ld      a,(de)              ; [6] gdelta
                inc     de
                ld      (CSP),de            ; ONE STORE FREES THE WHOLE SUBTREE
                add     a,l                 ; prevGSP = prevFSP + gdelta (7-B frame)
                ld      l,a
                adc     a,h
                sub     l
                ld      h,a
                ld      (GSP),hl
                pop     bc                  ; BC = resume ptr
                pop     de                  ; DE = saved CURLINE
                ret
; read_one_value: the READ/DATA value engine's resident stub (basic/program.asm):
; CALSLT the PAGE-0 tenant, then rebuild the (A, DE) contract from RDV_ST/RDV_VAL.
; out: A = 0 out of data / 1 item read / 2 not a number (D-READVAR); DE = the value.
read_one_value:
                call    sr_inl0             ; D-STUBINL: CF=1 iff the sub-ROM is absent
                db      low (SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_READVAL)
                ld      de,(RDV_VAL)
                ld      a,0                 ; NOT `xor a` -- subrom_call's CF is the
                ret     c                   ; test below and xor would clear it.
                ld      a,(RDV_ST)
                ret
; dl_bare: is the RUN at (HL) BARE -- nothing but ':' or the end after the 3-letter
; keyword? CF set iff so; HL preserved (basic/program.asm, the REPL's fast path).
dl_bare:
                push    hl
                inc     hl
                inc     hl
                rst    $10                ; past the 3-letter keyword
                pop     hl
                or      a
                scf
                ret     z                   ; end of line -> bare
                cp      COLON
                scf
                ret     z                   ; `RUN : ...` -> bare
                or      a                   ; anything else -> an ARGUMENT: crunch it
                ret

; oo_parse_as_chan — the "AS [#]n" clause shared by EVERY form of OPEN.
; in : HL = cursor just past the mode clause.
; out: HL past the channel expression, DE = channel (D = 0, E validated 1..MAXF).
; Never returns on a malformed clause: jumps to oo_fail_syn / oo_fail_bfn.
; Clobbers A/BC/DE/HL (eval).
;
; D-NOTOPEN2 §2d(b): this body was hand-inlined VERBATIM at THREE sites --
; oo_setmode (disk OPEN), the LPT:/CRT: device arm, and oocas_setmode (cassette).
; 47 identical bytes each, same raisers, same exit contract. Found by
; tools/clone_scout.py, not by eye; collapsing the three funds the ERR 55/58/61
; message pool this slice needs (see docs/spec-basic-gpfi-notopen-err59.md).
; ⚠️ The three callers differ ONLY in the store that precedes the clause
; (FCH_MODE / OO_DEVTYPE) and in what may follow it (LEN= for disk, a bare
; terminator for the other two) -- both stay at the call sites.
oo_parse_as_chan:
                ; "AS" is kept verbatim ASCII (not tokenised) -- match it.
                call    skip_spaces
                call    upcase
                cp      'A'
                jp      nz,oo_fail_syn
                inc     hl
                ld      a,(hl)
                call    upcase
                cp      'S'
                jp      nz,oo_fail_syn
                rst    $10     
                cp      '#'
                jr      nz,oopac_num
                inc     hl
oopac_num:
                call    eval                ; DE = channel number, HL past it
                ; validate the channel against the MAXFILES ceiling (1..MAXF).
                ; D-BADFNUM: OPEN is the ONE verb that answers 52 to channel 0 --
                ; everything else answers 59 there -- but it answers ERR 5, not 52,
                ; to `AS #256` / `AS #-1`. That last cell is the one a three-verb
                ; sample would have shipped wrong (spec §2).
                call    fch_check_d         ; D != 0 -> ERR 5; else A = E, Z <=> ch 0
                jp      z,oo_fail_bfn       ; OPEN's channel-0 exception -> ERR 52
                call    fch_check_nz        ; > MAXF -> ERR 52; else A = E
                ; 🔴 D-OPENBUSY (2026-09-29): A CHANNEL THAT IS ALREADY OPEN IS 54.
                ; `OPEN "X2.TXT" FOR OUTPUT AS #1:OPEN "X3.TXT" FOR OUTPUT AS #1`
                ; is `File already open` on the CF-3300 (scratchpad/t6enum_b8_zb.out)
                ; and was accepted here -- the second OPEN took the channel over.
                ; Here, after the number is valid and before any file work, so it
                ; covers every OPEN form (disk, LPT:/CRT:, CAS:) at one site.
                push    hl                  ; the cursor
                call    fch_modes_ptr       ; HL = &FCH_MODES[ch] (A, HL only)
                ld      a,(hl)
                pop     hl
                or      a
                ld      a,e
                ret     z                   ; free: A = E = the channel
oo_fail_54:                                 ; D-OPENSAME joins here too
                ld      e,54                ; `File already open`
                jp      oo_fail_e

; 📌 PIN REFILL (2026-10-19): 24 B moved here from past the $73E5 pin
; (basic/program.asm) to take back what this hole and FCH_MODE's dead stores
; freed in front of $72D4: fch_modes_ptr (9 B, moved IN FRONT of $6CF3 -- to
; basic/cload.asm, after autoexec_run -- to fit the sizes the tail offers),
; fch_select's FCH_MODE store, the re-reads in input_common and fdcc_disk, and
; the clears in init_filechan and fdcc_clear (3 B each). Sited AT the hole;
; whole, entered only by label, no `jr` across its edges (tools/pin_plan.py
; chunks()).
; --- onoff_decode: the shared ON | OFF | STOP sub-keyword decode -------------
; Six statements in this tree decode the same three sub-keywords into the same
; three ZTRAP states, and each one had spelled it out: `STOP ON|OFF|STOP`,
; `INTERVAL ...`, `STRIG(n) ...`, `KEY(n) ...`, `SPRITE ...`, and now `MOTOR`.
; ~19-23 B apiece for a decode that is character-for-character the same.
;
; The share was proposed as a DEFERRED funding lever (spec-traps-t5-interval
; §4.3, and again as spec-basic-missing-class §6.3) and taken instead as the
; FIRST step of the MISSING slice (S-MC-4, overridden). The reason is worth
; keeping: a reserve lever only ever gets pulled mid-overrun, when the budget is
; already spent and the only acceptable outcome is "it fits" -- which is the
; worst condition under which to restructure six live call sites.
;
;   IN:  A  = the token byte under the cursor (callers have already skipped
;             spaces; HL is left pointing AT the token, not past it -- every
;             caller consumes it itself, because each has its own guard-the-
;             cursor dance around set_state).
;   OUT: CF=1 -> matched; A = ZTS_OFF(0) / ZTS_ON(1) / ZTS_STOP(2), which is the
;                set_state argument directly (sysvars.inc: the ZTS_ values ARE
;                0/1/2, so there is no second mapping step at any call site).
;        CF=0 -> not one of the three; A = the original token, so a caller can
;                still test it (ex_stop's bare-`STOP` path needs exactly that).
;   Clobbers A, B, F. **Preserves HL and DE** -- non-negotiable: HL is the token
;   cursor at every site, and ex_strig_stmt/ex_key_stmt hold the ZTRAP entry
;   pointer in DE across this call.
;
; ⚠️ It returns "which one", NOT "is this allowed". Acceptance stays with the
; caller, which is what lets a 2-way site share a 3-way decoder: `MOTOR STOP` is
; a Syntax error (measured, spec §3.5) and that is MOTOR's own one-line `cp
; ZTS_STOP` -- not a variant of this routine. `SCF` preserves Z on the Z80, which
; is what lets each arm be cp/scf/ld/ret-z with no branch.
onoff_decode:
                ld      b,a                 ; keep the token: A is about to be the answer
                cp      OFF_TOKEN
                ld      a,ZTS_OFF
                scf
                ret     z
                ld      a,b
                cp      ON_TOKEN
                ld      a,ZTS_ON
                scf
                ret     z
                ld      a,b
                cp      STOP_TOKEN
                ld      a,ZTS_STOP
                scf
                ret     z
                ld      a,b                 ; no match: hand the token back...
                or      a                   ; ...with CF=0
                ret

; --- fch_check — a REJECTED channel number, dispositioned as the reference ---
; does (D-BADFNUM, docs/spec-basic-badfnum-channel-class.md §2a). DE = channel.
; Returns A = E (1..MAXF) or does not return at all. Clobbers A, B — the SAME
; contract fch_valid published, which is why all nine call sites already tolerate
; it. DE and HL are untouched (three callers read E afterwards).
;
; This REPLACES fch_valid, which returned a flag and left each caller to invent a
; disposition. Nine sites invented SIX (load_error, a silent no-op, ERR 52, ERR 2
; twice over, and a silent `0` from the evaluator), and the CF-3300 answers ONE
; rule with two exceptions:
;
;   D != 0 (> 255 or negative)  ERR 5   illegal function call  — all 12 verbs
;   channel 0                   ERR 59  file not open          — except CLOSE (no-op)
;                                                               and OPEN (52)
;   1 .. MAXF                   proceed to the mode checks
;   channel > MAXF              ERR 52  bad file number        — all 12 verbs
;
; ⚠️ THE `> MAXF` BOUNDARY IS MAXFILES, NOT THE CONSTANT 2. `MAXFILES=2 : PRINT
; #2,"X"` answers 59, not 52, on both machines (gate row ctl_mf2_ch2) — without
; that row "channel 2 is bad" and "channel 2 is past the ceiling" are one reading.
;
; Raising from here is safe at every site: raise_error resets SP from SAVSTK on
; BOTH the trap and the abort arm, so a caller's pushed cursor needs no pop (the
; same depth-independence LOF has relied on since S-FCH-2).

; fch_check_d — the high-byte test alone: D != 0 -> ERR 5. Otherwise A = E and
; Z <=> "channel 0", which is the ONE cell CLOSE and OPEN each answer their own
; way. Six of the nine sites used to skip this test entirely and silently
; truncate to E — that is exactly the `#256` defect (`PRINT #256` was handled as
; channel 0).
fch_check_d:
                ; A STRING channel expression is `Type mismatch` on the reference,
                ; uniformly across all 12 verbs (measured). It must be tested HERE,
                ; ahead of everything else, because a type mismatch HARD-ZEROES the
                ; expression to 0 -- so without this the channel reads as 0 and the
                ; rule above answers ERR 59 to `PRINT LOF(A$)`.
                ; 🔴 THIS WAS FOUND BY A ROW ADDED AS A CONTROL BECAUSE IT ALREADY
                ; AGREED: `EOF`/`LOF` on a string channel were `type mismatch` on
                ; both machines BEFORE this slice, and the first cut of fch_check
                ; REGRESSED them to `file not open`. The type-mismatch axis had been
                ; sampled on 3 of the 12 verbs -- the very mistake §2's sweep exists
                ; to avoid, made one axis over.
                ; ⚠️ Only four of the twelve reach eval_chan, whose check_expr_errors
                ; tail (§6) raises this one step earlier; the other eight call plain
                ; `eval` and have no such check. This is the site that covers all 12.
                ; D-PENDERR: was `ld a,(TMISMATCH)` / `jp nz,type_mismatch_error`,
                ; byte for byte. The type fault now arrives as FPERR_TYPEMM and
                ; fp_runtime_error maps it to the same ERR 13. WIDENED for the same
                ; reason and at the same price as eval_chan's: a hard-zeroed channel
                ; expression must not be read as channel 0 whatever zeroed it, so a
                ; pending div0/overflow is surfaced here too instead of derailing to
                ; ERR 59 -- the exact failure mode this site was added to stop, one
                ; fault class over. Rows p.lof.dz / p.lof.ov (spec §5.3).
                call    check_fperr_only
                ld      a,d
                or      a
                jp      nz,fchk_ifc
                ld      a,e
                or      a                   ; Z <=> channel 0
                ret
; D-DUPSPAN: an ALIAS, not a second copy -- the two instructions were
; byte-identical to interp.asm's gb_illegal, on gfx_absent's own precedent.
; The NAME and every call site survive; un-alias here to give this site a
; distinct face and nothing else moves.
; (fchk_ifc = gb_illegal: its equ is in basic/aliases-early.inc -- pasmo 0.5.3, D-PASMO053)
; fch_check — the whole rule, for the seven verbs with no channel-0 exception.
fch_check:
                call    fch_check_d
                jp      z,err_notopen_raise ; channel 0 -> ERR 59. A LEGAL channel
                                            ; number that is merely not open, which
                                            ; is why this is not simply "-> 52"
; fch_check_nz — entered directly by CLOSE and OPEN, which have already disposed
; of channel 0 themselves. Falls in from fch_check above.
fch_check_nz:
                ld      b,a
                ld      a,(MAXF)
                cp      b                   ; CF set iff ch > MAXF
                jp      c,oo_fail_bfn       ; -> ERR 52 (no FCH_MODE clear there
                                            ; since 2026-10-19: only OPEN reads
                                            ; the cell, after setting it)
                ld      a,b
                ret

; fch_do_close_ch — close channel A: if open FOR OUTPUT, append the Ctrl-Z text-EOF
; marker, flush, and stamp the directory; then mark the channel closed and release
; the engine globals. A = channel (1..FCH_CEIL, assumed open). CALSLT inside
; fat_io_* clobbers everything incl. IX/IY — the caller must guard its HL cursor.
fch_do_close_ch:
                ; A device channel (LPT:/CRT:, FCH_MODES[ch] >= LPT_MODE) owns no
                ; fat.asm context: skip fch_select (which would LDIR an uninitialised
                ; ctx block over the engine globals, corrupting any concurrently-open
                ; disk channel) and the OUTPUT flush; just clear its mode entry.
                ld      e,a                 ; keep the channel in E for fdcc_disk
                call    fch_modes_ptr
                ld      a,(hl)
                cp      LPT_MODE
                jr      c,fdcc_disk         ; mode < 5 -> disk channel (INPUT/OUTPUT)
                cp      CAS_OUT_MODE
                jr      z,fdcc_cas_out      ; 7 -> flush the final tape block + motor off
                cp      CAS_IN_MODE
                jr      z,fdcc_cas_in       ; 8 -> just stop the motor
                jr      fdcc_closed         ; LPT/CRT device channel: clear entry, done
fdcc_cas_out:
                push    hl                  ; guard FCH_MODES[ch] ptr across the flush
                call    cas_ascii_finish    ; Ctrl-Z EOF + pad the final block; the pad
                                            ; loop's 256th byte flushes it (TAPOON+256+
                                            ; TAPOOF), so the block is closed on return
fdcc_motor_off:                             ; C4 shared tail (2026-10-03): fdcc_cas_in
                call    TAPIOF              ; motor off      joins here, HL on the stack
                pop     hl
fdcc_closed:                                ; and the LPT/CRT arm here
                ld      (hl),0              ; FCH_MODES[ch] = 0 (closed)
                ret
fdcc_cas_in:
                push    hl
                jr      fdcc_motor_off      ; motor off (input channel: nothing to flush)
fdcc_disk:
                ld      a,e
                call    fch_select          ; make the channel live; A = its mode
                ; 🧭 S10.C (2026-10-15): EVERY disk mode crosses H_CHCLOSE now --
                ; INPUT too, which the CF-3300 does ($FE62 at an INPUT channel's
                ; CLOSE, s10c_hook_run.out). Its row is disk.rom's FCB since OPEN
                ; and hk_chclose's mode-1 arm writes nothing. The two `cp`s that
                ; routed INPUT past the cell are gone (-8 B); no other mode can be
                ; stored on a disk channel (1 / DOUT_MODE / 4, D-MODE2DEAD).
                ; 🗑️ D-MODE2DEAD (2026-10-07): mode 2 -- OUTPUT through main's own
                ; engine -- has not been STORED since S10.B increment 2; OPEN maps
                ; OUTPUT and APPEND to DOUT_MODE. Its arm here (Ctrl-Z through
                ; fat_io_putbyte, fat_io_close, and fdcc_fail's demote-to-INPUT on a
                ; failed flush) could not be reached; disk.rom's hoc_dout / dwr_fail
                ; carry D-DISKFULL's face now (diskfull-acceptance).
                ; Ctrl-Z, the last record, the re-date. A failure RAISES from in
                ; there (66) and leaves the channel open, marked so that the next
                ; CLOSE frees it silently -- D-DISKFULL's face, kept.
                ; 🧭 S10.D (2026-10-15): a RANDOM channel crosses the SAME cell.
                ; ⚠️ A = THE MODE AT THE CALL (fch_select's answer, untouched by the
                ; two `cp`s once above), AND disk.rom READS IT: hk_chclose_e keeps it in B, and
                ; mode 4 takes only the directory stamp -- D-PUTDIR's once-at-CLOSE
                ; entry (first cluster, size, date) from the channel's FCB row,
                ; where hk_dget keeps them. It was fdcc_rnd here: the sub-ROM's
                ; fat_dir_update over main's engine globals, which a RANDOM
                ; channel no longer fills. A failure raises from in there, the
                ; channel still open -- as fdcc_rnd's `jp c,disk_error` left it.
                call    H_CHCLOSE
                ei                          ; a CALLF returns DI (cg_back's note)
fdcc_clear:
                ; 🧭 CLOSE LEAVES THE FIELD DEFINITIONS ALONE (2026-09-01,
                ; Joost's call: match the reference). This used to
                ; `call fld_clear_chan` here, which made `LEN(A$)` read 0 the
                ; moment the file closed -- and the common idiom is read a
                ; record, CLOSE, then use the value.
                ; 📏 D-FLDCLOSE measured what the reference's surviving
                ; descriptor actually IS, and it is the more dangerous of the two
                ; possibilities: a LIVE pointer, not a stale copy. `A$` survives
                ; eight string allocations (the FIELD buffer is not in the string
                ; heap) but a later OPEN + FIELD on a channel that reuses that
                ; buffer silently rebinds it. Neither behaviour is "safe" -- this
                ; one risks a silent wrong value in a narrow case, the old one
                ; guaranteed a wrong value in a common one.
                ; ⚠️ THE OTHER `fld_clear_chan` CALLER STAYED (field_prologue): a
                ; NEW `FIELD` on a channel dropped that channel's old
                ; definitions, which is what kept FLD_SLOTS (16) from filling on
                ; the ordinary OPEN/FIELD/CLOSE/OPEN/FIELD cycle.
                ; 🏗️ D-FLDDESC (2026-10-17): BOTH ARE GONE WITH THE TABLE, and
                ; the "live pointer" above is now ours too, literally: FIELD
                ; writes the variable's own descriptor at block+9+offset, so after
                ; CLOSE it still reads the channel block's bytes (row r7 of
                ; scratchpad/flddesc_run.out: `  Z` on the CF-3300) -- and there
                ; is no slot count to fill.
                ld      a,(FCH_ACTIVE)      ; = the channel (fch_select made it active)
                call    fch_modes_ptr
                xor     a
                ld      (hl),a              ; FCH_MODES[ch] = 0 (closed)
                ld      (FCH_ACTIVE),a      ; globals no longer hold a valid channel
                ret                         ; (FCH_MODE's clear went 2026-10-19:
                                            ; only OPEN reads it, after setting it)
; fch_close_all — close every open channel (flushing OUTPUT ones). Used by bare
; CLOSE and by MAXFILES (which reinitialises the channel table). Guard HL caller-
; side (CALSLT). Clobbers everything.
fch_close_all:
                ld      b,1                 ; channel index 1..FCH_CEIL
fcla_lp:
                ld      a,b
                cp      FCH_CEIL+1
                ret     nc
                push    bc
                ld      a,b
                call    fch_modes_ptr
                ld      a,(hl)
                or      a
                jr      z,fcla_next         ; not open -> skip
                ld      a,b
                call    fch_do_close_ch
fcla_next:
                pop     bc
                inc     b
                jr      fcla_lp

; --- KILL "name" — delete a file -------------------------------------------
; Frees the file's FAT cluster chain and marks its directory entry deleted, via
; the fat.asm `fat_delete` engine routine. Accepts the same "A:"/"B:" drive prefix
; + 8.3 name as the loader verbs (parse_disk_fcb), now including 8.3 '*'/'?'
; wildcards: `KILL "*.BAK"` deletes every match. Errors (no disk / none matched /
; I-O) reuse the loader's load_error path. See basic/PROVENANCE.md §KILL.
; 🧭 D-DISKVERB (2026-09-15): THE BODY IS NOT HERE ANY MORE. It lives in
; disk.rom as `hk_kill`, reached through H_KILL -- which is what the reference
; does on all 35 of its hook cells (D-CFARCH) and what Joost directed. What is
; left is the two things only main can do: hand the handler the statement cursor,
; and decode the disposition it comes back with.
;
; ⚠️ THE CURSOR CROSSES IN RAM, AND IT REUSES FN_RESUME ON PURPOSE. `chan_gate`
; needs HL for the hook cell and clobbers DE building its return address, so
; neither register is free to carry it. FN_RESUME is the cell fname_expr writes
; the resume point into anyway, so one cell serves both directions and no new
; sysvar is claimed.
;
; ⚠️ THE GATE STAYS, AND IT IS WHAT KEEPS THE DISKLESS ANSWER RIGHT. On a machine
; with no disk ROM the cell is unclaimed, chan_gate raises ERR 5 before anything
; else happens, and no filename is ever evaluated -- the same order as before.
ex_kill:
                ld      de,H_KILL
                call    verb_run            ; A = status, HL = resume cursor,
                                            ; and FALLS THROUGH into kill_status
; The wildcard delete itself -- fat_delete finding, freeing and $E5-marking each
; match in turn -- is unchanged SOURCE, but it no longer runs where this used to
; say. 🧭 D-KILLLOCAL (disk/docs/spec-diskcode-eviction.md §6.6ay): the loop ran
; in the SUB-ROM dirverb tenant, so `hk_kill` called BACK into main to marshal on
; to it and one KILL crossed main -> disk.rom -> main -> sub.rom. disk.rom
; assembles the same shared body now, so the mount and the loop are local to the
; handler and the round trip is gone. Nothing here changed: the cursor hand-off
; and kill_status's 0/1/2 decode are the same two things main alone can do.
;
                ; D-DSKMSG (docs/spec-basic-dskmsg.md §4), R-DK1: the CF-3300
                ; answers `File not found` to a KILL that matched nothing, which
                ; is what the line below USED to say in a comment while the code
                ; said load_error. The message ships already (D-MSGSUB hosts ERR
                ; 53), so the miss now goes through df_notfound / raise_error: a
                ; real MSX error, ERR reads 53 and ON ERROR traps it.
                ;
                ; 🔴 AND THAT IS *NOT* A 0 B JUMP-TARGET SWAP, which is what the
                ; residual filed. tnt_kill used to return 0 for "not found",
                ; "mount failed" AND "I-O error" alike (fat_delete's own contract),
                ; so the swap alone would have re-pointed a disk-offline KILL at a
                ; trappable ERR 53 with no reading behind it. The tenant now
                ; separates the mount (STATUS = 2) exactly as tnt_files does, and
                ; these two lines are the head half of that: +4 B, not 0.
kill_status:                            ; D-COPY shares this decode (0/1/2)
                                        ; in: A = DISKOP_STATUS, from verb_run
                or      a
                jp      z,df_notfound       ; 0 = nothing matched -> ERR 53
                dec     a
ks_nz_diskerr:                              ; B4: save.asm's disk SAVE exit shares this tail
                jp      nz,disk_error       ; 2 = mount / DSKIO error -> the mapped code (D-DISKERR)
                jp      exec_stmt

; --- NAME "old" AS "new" — rename a file -----------------------------------
; Locate the OLD file, then overwrite its directory entry's 11-byte 8.3 name field
; with the NEW name (no FAT change — same clusters). Both names use the shared
; parse_disk_fcb (drive prefix + 8.3); "AS" is verbatim ASCII. The OLD file is
; found FIRST (recording its location in FWR_DIRSEC/FWR_DIROFF) because building
; the NEW name reuses DISK_FCB_NAME.
;
; ✅ A MISSING OLD FILE RAISES ERR 53 `File not found` SINCE 2026-08-07
; (D-DKNAME, R-DK2 — docs/spec-basic-dkname.md). This header used to read
; "Errors (no disk / old not found / I-O) reuse load_error"; the reading was
; taken on the CF-3300 and the miss got its own exit (nm_notfound below). The
; REST of that sentence stands: no disk / mount / stamp I-O still reuse
; load_error, and no row anywhere measures what the reference says there.
;
; Divergences: the no-disk / mount / I-O wording (quarantined). See
; basic/PROVENANCE.md §NAME. 🔴 THIS LINE USED TO NAME TWO MORE, BOTH NOW FALSE:
; D-NAMEEXIST (2026-09-28) added the "new name already exists" check (65, in
; hk_name, measured against the CF-3300 by scratchpad/nameexist_probe.py), and
; D-DRVNAME made pdfcb refuse a drive letter past B: with 62 (a prefix of A: or
; B: is still accepted; B: is the CF-3300's phantom drive, see D-DISKERRS).
; 🧭 D-DISKVERB2 (2026-09-15): THE BODY IS NOT HERE ANY MORE -- it is `hk_name`
; in disk/kernel.asm, reached through H_NAME, on the pattern KILL established.
; What is left is the cursor hand-off and the decode.
;
; 🎯 NAME'S THREE OUTCOMES WERE ALREADY KILL'S THREE, so this shares kill_status
; instead of keeping its own tails: nm_notfound was `jp df_notfound` (ERR 53),
; nm_fail/nm_fail2 were `jp disk_error`, success was `jp exec_stmt` -- exactly
; status 0 / 2 / 1. Only the missing-`AS` syntax error needed a fourth value, and
; it is tested here before the shared decode runs.
;
; 🔴 THE ERROR ORDER THIS VERB OWES THE REFERENCE IS UNCHANGED, and it is worth
; keeping the measurement that fixed it (D-TODOSWEEP tranche 65, 2026-08-26,
; scratchpad/sweep_tranche65.py, against the CF-3300):
;     NAME"X.DAT"AS 5   old file ABSENT   cf3300 ERR 53
;     NAME"HI.TXT"AS 5  old file EXISTS   cf3300 ERR 13
; i.e. LOOK THE OLD FILE UP FIRST, THEN EVALUATE THE NEW NAME. hk_name does them
; in that order for the same reason, and the `AS` check sits between them.
ex_name:
                ld      de,H_NAME
                call    verb_run            ; A = status, HL = resume cursor
                cp      4
                jp      z,stmt_error        ; 4 = no `AS` -> Syntax error
                jr      kill_status         ; 0 not found / 1 renamed / 2 I-O

; --- MAXFILES = n — size the multi-channel table ---------------------------
; MAXFILES sets how many file channels may be open simultaneously (the value also
; bounds every OPEN/INPUT#/PRINT#/CLOSE channel number, via fch_check). Tokenised
; as MAX ($CD) + FILES ($B7) — two reserved words, oracle-locked like OUTPUT. Like
; the reference, changing MAXFILES reinitialises the file system: every open channel
; is closed first (OUTPUT ones flushed + Ctrl-Z-stamped) and every variable is
; CLEARed. zerobas accepts 0..FCH_CEIL, which the repack build sets to the MEASURED
; reference ceiling of 15 (D-FCH §3.2: the blocks are carved out of the FRE(0) pool
; at MAXFILES time, so an unused channel costs nothing and the ceiling was free).
; The argument DOMAIN is the reference's, measured across it (D-MFDOM,
; docs/spec-basic-maxfiles-domain.md): outside int16 -> ERR 6 `Overflow`; inside
; int16 but outside 0..FCH_CEIL -> ERR 5 `Illegal function call` (negatives
; included); a fractional value TRUNCATES and is then judged on the integer
; (15.9 is accepted as 15; 2.5 becomes 2). Entry: HL on the MAX token.
; See basic/PROVENANCE.md §MAXFILES.
ex_maxfiles:
                inc     hl                  ; past MAX ($CD)
                ld      a,(hl)
                cp      FILES_TOKEN         ; "MAXFILES" = MAX + FILES; require FILES
                jp      nz,stmt_error       ; bare MAX is not a statement
                rst    $10                ; past FILES ($B7)
                cp      EQ_TOKEN            ; '=' ($EF)
                jp      nz,stmt_error
                inc     hl
                ; S-FCH-2 (first piece): the out-of-domain reject is ERR 5
                ; `Illegal function call`, as MEASURED — `MAXFILES=16` and
                ; `MAXFILES=255` both raise it on the CF-3300, read via
                ; ON ERROR/ERR rather than inferred from the wording
                ; (docs/chancost-cf3300-characterization.md §3). It used to be
                ; `syntax error` (ERR 2): the wrong CLASS, independently of where
                ; the ceiling sat.
                ;
                ; ⚠️ D-MFDOM: THE ARGUMENT COMES THROUGH eval_byte_arg, NOT `eval`.
                ; This used to be `call eval` + a hand-inlined `ld a,d / or a /
                ; jp nz,gb_illegal`, and that high-byte test could not fire for an
                ; argument OUT OF INT16: `eval`'s silent flt_to_int16 zeroes DE for
                ; those (interp.asm's own header says so), so `MAXFILES=65536` and
                ; `MAXFILES=70000` arrived here as DE=0 and were accepted as an
                ; ordinary request for ZERO channels — SILENTLY DISABLING ALL FILE
                ; I/O where the reference raises ERR 6 `Overflow`. Measured on the
                ; CF-3300 as `mfd_65536`/`mfd_70000` (both read mf0's FRE(0) on
                ; zerobas against `Overflow` on the reference), not inferred.
                ;
                ; eval_byte_arg is get_byte_arg's eval leaf and is exactly the
                ; reference rule: int16 stage first (ERR 6 outside the RANGE
                ; -32768..32767 — asymmetric, and CONFIRMED for MAXFILES on the
                ; CF-3300 by mfd_32767/32768/n32768/n32769 rather than inherited
                ; from CHR$), then 0..255 (ERR 5). It also REPLACES nine bytes with
                ; three: this slice is a NET SAVING, not a spend.
                ;
                ; The remaining ceiling test stays here because FCH_CEIL is this
                ; statement's own bound, not a byte-argument rule.
                call    eval_byte_arg       ; A = E = 0..255; ERR 6 >int16, ERR 5 else
                cp      FCH_CEIL+1
                jp      nc,gb_illegal       ; > FCH_CEIL -> ERR 5
                ; 🔴 D-MAXFTAIL: THE STATEMENT MUST END HERE, AND THE CHECK MUST
                ; COME BEFORE THE COMMIT. `MAXFILES=1 ZZ` used to execute the whole
                ; statement and only then trip over `ZZ` -- by which point
                ; `clr_done`'s CLEAR had WIPED THE USER'S VARIABLES and disarmed
                ; `ON ERROR`, so the Syntax error was UNTRAPPABLE too. Both
                ; references reject it first: measured A=42,ERR=2 on each against
                ; A=0 and no handler here (scratchpad/maxfilestail_probe.py).
                ; The body is in main.asm's low region, on oo_fail_bfn's precedent
                ; -- page 1 pays only this call.
                call    mxf_require_end
                push    de                  ; guard the requested value
                push    hl                  ; guard the text cursor across CALSLT
                call    fch_close_all       ; MAXFILES reinitialises: close everything
                pop     hl
                pop     de
                ld      a,e
                ld      (MAXF),a            ; commit the new ceiling (0..FCH_CEIL)
                ; D-FCH §3.2 / characterization §9: MAXFILES CLEARs variables
                ; UNCONDITIONALLY -- even when the value does not change (the
                ; `sem_same` row is what pins that; "clears only when it
                ; reallocates" is the natural reading and it is WRONG). It is
                ; also load-bearing here rather than merely faithful: the new
                ; ceiling MOVES the variable region's top boundary (the table is
                ; carved below the pool floor), so any surviving array would now
                ; overlap the channel table. The CLEAR is that invalidation.
                ; It runs AFTER the MAXF store so the wipe sees the new ceiling.
                ; The string-pool SIZE survives -- POOLSIZE is untouched here,
                ; which is exactly the measured `CLEAR 500 : MAXFILES=2` row.
                ;
                ; ⚠️ AND IT IS FREE, because `CLEAR`'s own tail IS this sequence:
                ; clr_done (basic/clear.asm) is `push hl / call clear_vars /
                ; call vars_reset / pop hl / jp exec_stmt` with HL = the statement
                ; cursor -- exactly our state here. Jumping to it costs the same
                ; 3 bytes the `jp exec_stmt` it replaces did. Written out inline
                ; it was 8 bytes, and page 1 had 1. (S-FCH-1's lesson a third
                ; time: the cost was SITING.)
                ; D-CLEARCLOSE (2026-10-06): `clr_wipe`, past the bare CLEAR's own
                ; close-all -- the files are closed above already.
                jp      clr_wipe

; --- MERGE "name" — merge an ASCII program from disk ------------------------
; Reads a SAVE",A"-style ASCII (line-numbered text) program file and stores each
; line into the CURRENT program (insert-or-replace by line number) — the existing
; program is KEPT, unlike LOAD. Each file line is accumulated into LINEBUF and fed
; to dispatch_line, exactly as if it had been typed: the same tokeniser + store_line
; path. Lines end at CR ($0D); LF ($0A) is ignored; a Ctrl-Z ($1A) or EOF ends the
; file. A non-blank, non-numbered line is a "Direct statement in file" error (also
; what guards against a tokenised file being read as garbage ASCII). The byte stream
; uses the global fat_io read state directly (like LOAD/BLOAD), so MERGE while a
; user file channel is open is undefined (documented). Token $B6 oracle-locked.
; Sources: MSX-BASIC language reference (MERGE merges ASCII line-numbered programs);
; the ASCII save format = line text + CR/LF, Ctrl-Z terminator. See PROVENANCE §MERGE.
; 🔴 D-MERGEXPR: MERGE'S FILENAME IS A STRING EXPRESSION, AND THIS WAS THE LAST
; VERB STILL ON THE QUOTE TEST. D-FNEXPR2/D-FILESIDE converted nine (BLOAD, LOAD,
; FILES, OPEN, KILL, NAME x2, SAVE, BSAVE) and `ex_merge` was missed: it opened
; with `cp '"' / jp nz,stmt_error` and went straight to parse_disk_fcb, with no
; fname_expr anywhere. Found by READING, in the standing review tier.
; MEASURED (scratchpad/mergexpr_probe.py, CF-3300 vs zerobas, 4 rows DIFF):
;     MERGE A$              ERR 53 File not found   <- was ERR 2 Syntax error
;     MERGE "A:"+"NOSUCH"   ERR 53                  <- was ERR 56
;     MERGE                 ERR 24 Missing operand  <- was ERR 2
;     MERGE 5               ERR 13 Type mismatch    <- was ERR 2
; The last two are the faces the deleted quote gate used to produce, and they are
; why the bare test below is explicit: `fname_expr` hands a non-string to
; els_tc_common (ERR 13, free), but NOTHING in it answers "no operand at all".
ex_merge:
                rst    $10                ; HL -> bytes after the MERGE token
                or      a
                jp      z,loc_missing       ; bare MERGE -> ERR 24 (MEASURED)
                                            ; 🔴 `loc_missing`, NOT `g8_missing`:
                                            ; the latter lives in graphics.asm and
                                            ; only exists under G8_RESIDENT, while
                                            ; ex_merge is ALWAYS assembled --
                                            ; `make switch-build-check` caught the
                                            ; first cut on exactly that. missing.asm
                                            ; already carries the ELSE arm, so this
                                            ; name is defined either way and costs
                                            ; the shipping build nothing.
                call    fname_expr          ; the filename is an EXPRESSION; HL ->
                                            ; the staged '"'-terminated copy
                ; device dispatch: "CAS:" -> tape ASCII merge; else -> disk. dev_cmp
                ; advances HL past a matched prefix, restores it on a miss (so the
                ; disk path still sees HL at the staged name's start).
                ; ⚠️ THE DISPATCH NOW RUNS ON THE STAGED COPY, not on program text --
                ; the same move do_open documents, so `MERGE A$` with A$="CAS:X"
                ; reaches the tape arm exactly as the literal does.
                ld      de,dev_cas
                call    dev_cmp
                jr      z,merge_cas         ; matched "CAS:" -> tape merge (HL past prefix)
                call    nodisk_dev          ; D-NODISKVERBS: no disk -> the tape, `d:` 56
                jr      z,merge_cas         ; (was `load error`)
                call    pdfcb_resume      ; build DISK_FCB_NAME; HL -> closing '"'
                push    hl                  ; guard the text cursor across the merge
                call    dsk_aopen           ; step 11: the DISK ROM mounts, finds and
                jr      c,mrg_ioerr         ; primes -- CF set = it said no
                call    dsk_ascii_drive     ; tokenise+store each line, bytes through
                                            ; the crossing; CF set = bad line
mrg_fin:                                    ; C4 shared tail (2026-10-03): the tape arm
                pop     hl                  ; restore the text cursor      joins here
                jp      c,dpl_direct        ; non-numbered line -> 57 "Direct statement in
                                            ; file", untrapped (D-CASDIRECT; this said so
                                            ; and raised stmt_error's Syntax error)
                ; 🔴 D-MERGERET (2026-09-12): MERGE RETURNS TO COMMAND LEVEL, and
                ; `jp exec_stmt` carried on instead -- in BOTH modes. In a program,
                ; `20 MERGE"N.BAS" / 30 POKE&HD002,55` left 55 here and 0 on the
                ; CF-3300; typed, `MERGE"N.BAS":POKE&HD002,55` did the same
                ; (scratchpad/kwdrain_cmdlevel.out, scratchpad/kwdrain_cmddirect.out).
                ; 🎯 THE MERGE ITSELF WAS NEVER WRONG: the merged line lands byte for
                ; byte on both machines and `LIST 100` agrees. Only the cursor did.
                ; `end_line_end` is the shared tail; `ex_new` is the live precedent,
                ; and its typed `NEW:POKE` reads 0 on both machines.
                jp      end_line_end
mrg_ioerr:
                pop     hl
                ; 🔴 NOT `df_or_loaderr` ANY MORE, AND THIS IS THE `A SHARED TAIL
                ; IS A LABEL, NOT A DECISION` CLASS. That tail decides between
                ; ERR 53 and a DSKIO code by reading DISKOP_OP -- and FOPEN_SEL
                ; ALIASES DISKOP_OP, so after the crossing that cell holds $41,
                ; not DISKOP_SEL_FAT_FIND, and every miss would have reported a
                ; disk error. The disk side already answered the question:
                ; DISKOP_STATUS 1 = not found, 3 = mount / I-O.
                ld      a,(DISKOP_STATUS)
                dec     a
                jp      z,df_notfound       ; 1 -> ERR 53 File not found
                jp      disk_error          ; 3 -> the mapped DSKIO code

; --- MERGE "CAS:name" — merge an ASCII program from cassette ------------------
; The tape counterpart of the disk MERGE above: read an $EA ASCII cassette file and
; store each line into the CURRENT program (insert/replace by number — the existing
; program is KEPT, NO new_prog). Reuses the M1 cassette-ASCII byte machinery: open
; the tape (TAPION), require the $EA file-type id, then cas_ascii_setup (skip header
; + prime block 1) + cas_ascii_drive (ascii_read_lines off cal_getbyte, restore +
; TAPIOF) — exactly what cas_ascii_load does, minus the new_prog. A tokenised ($D3)
; or unknown file is rejected (MERGE needs ASCII text). Clean-room: MERGE semantics
; from the MSX-BASIC language reference; format + byte source are our own M1 code.
; Entry: HL is inside the quotes, past "CAS:". Tier-3 (spec-cas-tier3-cload.md
; Item A): the name is now HONOURED — captured into CAS_WANT and located by
; cas_open_match (case-sensitive), skipping earlier non-matching files. An empty
; name (MERGE"CAS:") merges the next file, unchanged.
merge_cas:
                call    cas_capture_cut     ; -> CAS_WANT + CAS_WANT_ON; HL on '"'; a '.' ends the name (D-CASDOT)
                ; D-MERGEXPR: the name came from fname_expr's staged copy, which is
                ; ALWAYS '"'-terminated by construction, so the old "unterminated
                ; string" test here could no longer fire. The cursor resumes past
                ; the EXPRESSION, exactly as on the disk arm above.
                ld      hl,(FN_RESUME)
                push    hl                  ; guard the text cursor across the merge
                call    cas_open_match      ; find the (named) $EA file; header consumed
                jp      c,dpl_dio           ; D-CASBRK: 19, raised. mc_ioerr's disk_error
                                            ; raised the STALE disk code -- 255 on the
                                            ; diskless machine (basic_probe_casbrk pmerge)
                ld      a,(CAS_HDRID)
                cp      ASCII_ID            ; MERGE requires an ASCII ($EA) file
                jr      nz,mc_ioerr         ; tokenised / other -> cannot merge
                call    cas_ascii_setup     ; prime data block 1
                jr      c,mc_found_dio      ; D-CASPRIME: 19 in 65535, trapped
                ; NB: NO new_prog — MERGE inserts into the current program.
                call    cas_ascii_drive     ; read + tokenise + store each line; CF=bad line
                jr      mrg_fin             ; D-MERGERET: the tape arm of the same
                                            ; contract as the disk arm above. NO ROW
                                            ; -- nothing here can PLAY a tape — so it
                                            ; is changed by the disk arm's reasoning
                                            ; and named as unmeasured.
mc_ioerr:
                pop     hl
                jp      disk_error          ; D-DISKERR
; mc_found_dio -- D-CASPRIME (2026-10-11): the first data block failed to read
; (Ctrl-STOP / an I/O error) after `Found:`. The VG-8020 raises 19 TRAPPED with
; ERL 65535 -- the MERGE has left the run there (basic_probe_casrbrk's mb2); its
; search failing BEFORE `Found:` is `19 in <line>` (D-CASBRK's pmerge), and a
; later block untrapped (mb8). Ours raised the STALE disk code, 255 on the
; diskless machine, through mc_ioerr -> disk_error. DIRECTF is 0 here.
mc_found_dio:
                ld      hl,DIRECTF
                inc     (hl)                ; 0 -> 1: ERL 65535
                jp      dpl_dio             ; motor off, 19, raised

; --- ascii_read_lines — read a line-numbered ASCII (SAVE",A") program from the
; ALREADY-OPEN fat_io sequential stream, tokenising + storing each line via
; mrg_storeline -> dispatch_line (the same path as a typed line). SHARED by MERGE
; (which keeps the current program) and ASCII LOAD (whose caller cleared it via
; new_prog first). Lines end at CR ($0D); LF ($0A) is ignored; Ctrl-Z ($1A) or EOF
; ends the file. dispatch_line uses LINEBUF/TOKBUF/SL_* + the program text area, NOT
; the fat_io read state (FREAD_*/FSECTOR_BUF), so the file stream survives across it.
; Sources: MSX-BASIC language reference (ASCII program = line text + CR/LF, Ctrl-Z
; terminator); clean-room, no reference ROM read. See PROVENANCE §MERGE and
; basic/docs/spec-ascii-saveload.md §4.
;   out: CF clear = whole file stored OK; CF set = a non-blank, non-numbered line.
;
; Byte source (D2 getbyte indirection): reads go through arl_getbyte, which
; jumps through the ARL_GETBYTE RAM vector (sysvars.inc) instead of calling
; fat_io_getbyte directly. Defaulted to fat_io_getbyte at cold start
; (init_filechan), so MERGE and disk ASCII LOAD (both callers above/below) are
; byte-for-byte unchanged; cload.asm's cas_ascii_load re-points it at a TAPIN
; wrapper for a cassette ASCII load. See basic/docs/spec-cas-ascii-saveload.md §6 D2.
ascii_read_lines:
arl_newline:
                ld      hl,LINEBUF          ; start a fresh line
                ld      (MRG_PTR),hl
arl_charloop:
                call    arl_getbyte
                jr      c,arl_eofline       ; EOF -> flush any partial line, then finish
                cp      $1A
                jr      z,arl_eofline       ; Ctrl-Z soft-EOF -> finish
                cp      $0A
                jr      z,arl_charloop      ; ignore LF
                cp      $0D
                jr      z,arl_endline       ; CR -> end of this line
                ld      c,a                 ; C = the data char (survives the bounds math)
                ld      hl,(MRG_PTR)
                ld      a,l                 ; bounds: keep the last LINEBUF byte for the 0
                cp      (LINEBUF+LINEMAX-1) & $FF  ; the cap's LOW byte: unique in LINEBUF's
                jr      z,arl_charloop      ;  255 B, so EQUALITY is exact; line full ->
                                            ;  drop extra chars. (`jr nc`, an ORDER test,
                                            ;  needed a page-aligned LINEBUF; it is BUF
                                            ;  $F55E now, crossing $F600 -- D-RAMBUF.)
                ld      (hl),c
                inc     hl
                ld      (MRG_PTR),hl
                jr      arl_charloop
arl_endline:
                call    mrg_storeline       ; tokenise + store this line
                ret     c                   ; non-numbered line -> CF set (caller errors)
                jr      arl_newline
arl_eofline:
                ld      hl,(MRG_PTR)        ; flush a final line with no trailing CR
                ld      a,l
                cp      LINEBUF & $FF
                jr      z,arl_ok            ; nothing accumulated -> done
                call    mrg_storeline
                ret     c
arl_ok:
                or      a                   ; CF clear = success
                ret

; (arl_getbyte lives in basic/program.asm since D-WSZERO S16: it refills bytes the stack
; parameter block freed in front of a pinned address)

; --- dsk_aopen: open an ASCII program file THROUGH the crossing (step 11) ----
; The disk side mounts, searches the directory and primes the stream; main keeps
; the line loop and the tokeniser. `MERGE` and ASCII `LOAD` share this because on
; the reference they share everything (expansion-protocol.md §8.6a).
;   in : DISK_FCB_NAME staged by the caller (pdfcb_resume / parse_disk_fcb)
;   out: CF clear = open and primed; CF set = DISKOP_STATUS says why (1 not
;        found, 3 mount / I-O). Clobbers A/HL, as every chan_gate caller does.
; ⚠️ diskslot_test is the CALLER's job, exactly as it is for disk_prog_load: a
; diskless machine must not reach chan_gate's ERR 5 by this road.
dsk_aopen:
                ld      a,FOPEN_SEL_AOPEN
                call    fopen_cross         ; A = DISKOP_STATUS, Z iff 0 (D-CARVEFO)                   ; 0 -> Z, and CF is CLEAR here
                ret     z
                scf
                ret

; --- dsk_agetbyte: an ARL_GETBYTE source that crosses ONCE PER BYTE ----------
; 🔴 THE SELECTOR IS RE-ASSERTED ON EVERY CALL, AND IT HAS TO BE. FOPEN_SEL
; aliases DISKOP_OP, and between two byte reads main runs `mrg_storeline` --
; which reaches the SUB-ROM tokeniser, whose own marshalling uses that cell.
; disk/equates.inc's block says an arm that calls back into main must re-assert
; the selector; this is that arm, and three bytes per byte is the whole price.
; 🔬 A crossing per byte is what the reference does here: $FE8A (H.INDS) is
; entered once per byte of an ASCII LOAD or MERGE and is CLAIMED on both
; measured vendors, while the tokenised path enters it zero times (§8.6a).
;   out: A = byte, CF clear; or CF set = end of file. The contract ARL_GETBYTE's
;        other sources (fat_io_getbyte, cal_getbyte, chget_getbyte) honour.
; Preserves nothing, which that contract already allows.
dsk_agetbyte:
                ld      a,FOPEN_SEL_GETB
                call    fopen_cross         ; A = DISKOP_STATUS, Z iff 0 (D-CARVEFO)
                jr      nz,dag_eof          ; nonzero = EOF
                ld      a,c                 ; the byte -- BC crosses intact
                or      a                   ; CF clear = a byte follows
                ret
dag_eof:
                scf
                ret

; --- dsk_ascii_drive: ascii_read_lines off the CROSSING byte source ----------
; The disk twin of cas_ascii_drive (cload.asm): point ARL_GETBYTE at this
; slice's source and run the reader.
; 🗑️ S10.C (2026-10-15): THE RESTORE IS GONE, AND ITS OWN REASON SAYS WHY. It
; read "not cosmetic: INPUT #n's disk arm is still main's fat_io_getbyte because
; step 10 has not moved". That stopped being true with D-CASINP's arl_set_src --
; input_common points the vector itself before every read -- and step 10 (S10.C)
; has now moved: main has no fat_io_getbyte to put back. A tail call (-9 B).
;   out: CF from ascii_read_lines (set = a non-blank, non-numbered line).
dsk_ascii_drive:
                ld      hl,dsk_agetbyte
                ld      (ARL_GETBYTE),hl
                jr      ascii_read_lines

    IF BASICINT_PINS
; 📌 REFILL FOR D-BASICINT'S $73AC PIN (S10.C, 2026-10-15). S10.C took 23 B out of
; the stretch between the pinned $6CF3 and $73AC -- init_filechan's dead
; ARL_GETBYTE seed (6), this routine's restore (9) and fdcc_disk's mode tests (8)
; -- which would have grown basic/field.asm's `ds $73AC - $` from 2 to 25 B. Joost:
; no growing holes. So two self-contained routines from past every pin (basic/
; program.asm, no `jr` across their edges -- tools/pin_plan.py's chunk list) moved
; here: ex_new with the end_line_end it falls into (18 B) and diskslot_test (5).
; ⚠️ EXACTLY 23, NOT 25: the 2 B pin_plan reports in front of $73AC are a `jr`
; BRIDGE (lrset_common's `jr` over the pin), not a `ds` pad -- the `ds` itself
; was already 0, and a 25 B refill drove it negative (pasmo then writes an EMPTY
; image, split_islands' "image base $8000" the only sign). program.asm's copies
; are the ELSE arms; their stories stay there.
ex_new:
                ; 🔴 D-NEWARG (2026-09-28): `NEW 1` ERASED THE PROGRAM. NEW takes no
                ; argument; the VG-8020 answers `20 NEW 1` with `Syntax error in 20`
                ; and LIST still shows the program, where zerobas erased it
                ; (scratchpad/newarg_before.out; T6 batch 10, t6enum_b10.out). The
                ; check comes FIRST, before anything is cleared.
                call    stmt_bare_end       ; Z iff the statement ends here
                jp      nz,stmt_error       ; anything else: ERR 2, nothing erased
                call    clear_vars          ; NEW clears variables too (dl_new's
                                            ; own comment: MS-BASIC semantics)
                call    new_prog            ; then the stored program itself
                                            ; falls into end_line_end: ENDFLAG := 1,
                                            ; so the run loop returns to the REPL
                                            ; instead of walking erased text
end_line_end:
                ld      a,1
                ld      (ENDFLAG),a
                ret                         ; -> stage A turns THIS into `jp rp_after`
diskslot_test:
                ld      a,(DISKSLOT_OK)
                or      a
                ret
    ENDIF

; --- chget_getbyte: ARL_GETBYTE source for the CONSOLE (D-INPDCON) ---------
; `INPUT$(n)` with no `,#f` reads n characters from the KEYBOARD. That is the
; same loop the file form already runs -- sid_read's loop consumes n bytes
; into the result through this very vector -- so the console form is a SOURCE, not a
; second loop: 7 bytes here instead of a duplicate of sidr_lp.
; Source: CHGET $009F, the BIOS "wait for a character" entry (MSX2 Technical
; Handbook BIOS list); page 0, mapped throughout.
; ⚠️ IT NEVER REPORTS EOF. The file sources set CF at end-of-stream and
; sid_read's loop stops early on it; the keyboard has no end, so this always
; returns CF clear and the loop runs exactly n times -- which is the reference's
; behaviour: INPUT$(n) waits for n keys.
; ⚠️ AND IT DOES NOT ECHO. Measured on both references (kwsweep `inputdol_b`,
; `A$=INPUT$(1):PRINT"[0y";A$;"]"` with `RESPOND:Z` reads `[0yZ]` -- one Z, from
; the PRINT; an echoing INPUT$ would have put a second one before the `[`).
; CHGET does not echo, so this is the absence of code rather than code.
; out: A = the key, CF clear. HL preserved (the other sources promise it).
chget_getbyte:
                push    hl
                call    zb_chget            ; D-KEYSHIFT
                pop     hl
                or      a                   ; CF=0: never EOF
                ret

; mrg_storeline — 0-terminate LINEBUF at MRG_PTR and, if it is a numbered (or blank)
; line, hand it to dispatch_line (same tokenise + store_line path as a typed line).
;   out: CF set = a non-blank, non-numbered line (error); CF clear = stored/skipped.
; dispatch_line uses LINEBUF/TOKBUF/SL_* + the program text area — NOT the fat_io
; read state (FREAD_*/FSECTOR_BUF) — so the file stream survives across it.
mrg_storeline:
                ld      hl,(MRG_PTR)
                ld      (hl),0              ; terminate the accumulated line
                ld      hl,LINEBUF
                call    skipsp_test
                jr      z,msl_ok            ; blank line -> skip
                cp      '0'
                jr      c,msl_err
                cp      '9'+1
                jr      nc,msl_err          ; not a digit -> not a numbered line
                call    dispatch_line       ; numbered -> crunch + store (insert/replace)
msl_ok:
                or      a                   ; CF clear = ok
                ret
msl_err:
                scf                         ; CF set = direct/garbage line
                ret
