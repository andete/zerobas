; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; filestmt.asm -- zerobas-sub PAGE 0 (since D-SUB2RETIRE step 2e, 2026-11-04;
; zerobas-sub2's page 0 before that): the file-channel STATEMENTS OPEN, CLOSE,
; MERGE and MAXFILES (D-P0CB slice C1, docs/spec-sub2-p0cb.md §5 and §7). Moved out
; of main page 1 (basic/files.asm, basic/grpdev.asm) on 2026-10-21. The channel
; MACHINERY stays in main -- fch_check_d / fch_check_nz, fch_modes_ptr,
; fch_do_close_ch / fch_close_all, fopen_cross and the disk.rom crossing, every
; cassette routine, fname_expr / pdfcb_resume / dev_cmp (shared with the other
; file verbs, and disk.rom calls some of them back), oo_parse_reclen (driven on
; the main image by tests/test_open_len.py) and the device-name strings, which
; main's dev_cmp reads. Only what these four statements alone reach moved.
;
; Entered as zerobas-sub's page-0 index SUBROM_IDX_FILESTMT (19) from main's
; ex_file (basic/program.asm) through subrom_call: main's four entry labels share
; ONE byte, `ld c,a` in front of it, so C = the statement token (exec_stmt hands
; every handler A = its token -- tests/test_stmt_dispatch.py asserts it). Main
; sends no other token here. (It was zerobas-sub2's page-0 index 3,
; SUB2_IDX_TRAPS, until step 2e; SCREEN / COLOR / WIDTH / KEY, DELETE / AUTO /
; RENUM and the SAVE / LOAD family were forwarded on from it until steps 2d / 2a
; moved them to the sub ROM's page 1 with their own copies of the tails below.)
;   in   HL = the cursor ON the statement token (exec_stmt's contract)
;        C  = the statement token
;   out  DE = the main address to continue at, HL = what it expects (below)
; ex_file then does `push de / ret` (exs_tail) with the stack exactly as the
; statement was entered. The continuations, and what each takes:
;   exec_stmt      HL = the cursor          (main's `jp exec_stmt` / `jp pop_exec`
;                                            / `jp dc_finish`, which was ed_done)
;   clr_wipe       HL = the cursor          (MAXFILES' CLEAR, then exec_stmt)
;   end_line_end   nothing; its `ret` ends the line (MERGE returns to command level)
;   disk_error     nothing; raises a pending DSKIO code, else PRINTS `load error`
;                  and RETURNS -- so it is a continuation, never a p0cb call
;   load_error     nothing; prints and returns, as above
; No continuation is ever reached through p0cb: execution must not go on INSIDE
; this CALSLT.
;
; WHAT IS MAPPED: this page is the SUB ROM's (slot 3-2), main's PAGE 1 stays
; mapped, main's page 0 (the BIOS, the low region, $0038) does not. So:
;   * a main routine that is a page-1 LEAF is called directly: dev_cmp (-> main's
;     upcase) and fch_modes_ptr, each read for rst / low-region reach and pinned
;     >= $4000 by asserts in sub/sub.asm;
;   * a leaf this page already has is called locally: skip_spaces
;     (sub/readdata.asm) and upcase (sub/tkfloat.asm), the same bodies as main's;
;   * every other main routine is reached through this page's p0cb (sub/sub.asm,
;     sub2/p0cb.asm's body) with its `p0_` alias from basic-resident-abi.inc, and
;     main's CHRGTR through fs_chrgtr below -- no `rst`, which the sub build's
;     closure gate refuses (an rst here would land in THIS ROM's $0010).
; A raise reached through p0cb never returns -- raise_error resets SP and runs
; main's error path with main's page 0 mapped -- exactly as the `jp` it replaces
; never returned; a frame this code pushed is discarded by the same unwind. No
; hook (H_xxxx) is called from here: the hooked crossings are inside fopen_cross
; / fch_do_close_ch, which run in main.
; The code is otherwise main's, statement for statement, and each arm keeps the
; original's order of checks, so the errors and their order are the ones the
; OPEN / CLOSE / MERGE / MAXFILES rows already pin. The history behind each
; check is in git (basic/files.asm before D-P0CB slice C1); what is kept here
; is the measured rule each one encodes.

; --- the dispatch -------------------------------------------------------------
file_tenant:                                ; index 19: C = the token (main's ex_file)
                ld      a,c                 ; A = C
                cp      OPEN_TOKEN
                jr      z,fs_open
                cp      CLOSE_TOKEN
                jp      z,fs_close
                cp      MERGE_TOKEN
                jp      z,fs_merge
                jp      fs_maxfiles         ; MAX_TOKEN: the only other token main
                                            ; sends here

; --- the shared tails -------------------------------------------------------------
; The plain raises are `ld a,N` into fs_raise: main's gb_illegal (5), pdf_badname
; (56) and oo_fail_bfn (52) are each exactly `ld a,N / jp raise_error`.
fs_syntax:                                  ; oo_synerr / oo_fail_syn: stmt_error, ERR 2
                ld      ix,p0_stmt_error
                jp      p0cb                ; raises; never returns
fs_dio:                                     ; dpl_dio: motor off, ERR 19
                ld      ix,p0_dpl_dio
                jp      p0cb
fs_badname:                                 ; pdf_badname: ERR 56
                ld      a,56
                jr      fs_raise
fs_bfn:                                     ; oo_fail_bfn: ERR 52
                ld      a,52
                jr      fs_raise
fs_illegal:                                 ; gb_illegal: ERR 5 (also LEN= out of
                ld      a,5                 ; 1..256, D-RECLEN2)
fs_raise:                                   ; A = the ERR code
                ld      ix,p0_raise_error
                jp      p0cb
fs_pop_exec:                                ; main's `jp pop_exec`
                pop     hl
fs_exec:                                    ; main's `jp exec_stmt`
                ld      de,p0_exec_stmt
                ret
fs_disk_error:                              ; main's `jp disk_error`: a continuation
                ld      de,p0_disk_error
                ret
fs_end_line:                                ; main's `jp end_line_end`: a continuation
                ld      de,p0_end_line_end  ; (MERGE's; pgmedit.asm's until step 2d,
                ret                         ; loadsave's ls_end_line until step 2a)
; fs_chrgtr -- main's CHRGTR (`rst $10` in main) through p0cb: CHRGTR calls the
; H.CHRG hook first, so it runs with main's page 0 mapped, as it always did (sub2's
; RST 10h vector did the same). IX is NOT saved, unlike sub2's s2_chrgtr: none of
; the five sites holds anything in it. A, F, HL out as CHRGTR's; AF' clobbered.
fs_chrgtr:
                ld      ix,p0_chrgtr
                jp      p0cb

; ===========================================================================
; OPEN "name" [FOR INPUT|OUTPUT|APPEND] AS [#]n [LEN=r]   (main's ex_open/do_open)
; ===========================================================================
fs_open:
                inc     hl                  ; past the OPEN token
                ld      ix,p0_fname_expr
                call    p0cb                ; D-FNEXPR: HL -> the staged, '"'-
                                            ; terminated copy in STRSCR
                ; device dispatch, on the STAGED copy (so `OPEN A$` with A$="CAS:X"
                ; reaches the tape arm as the literal does). The names are main's
                ; data: main's dev_cmp reads (DE) with main's page 0 mapped, and the
                ; strings sit in main page 1.
                ld      de,p0_dev_lpt
                call    p0_dev_cmp          ; Z + HL past the prefix iff it matched
                jp      z,fo_dev_lpt
                ld      de,p0_dev_crt
                call    p0_dev_cmp
                jp      z,fo_dev_crt
                ld      de,p0_dev_grp       ; D-OPENGRP: the graphics screen
                call    p0_dev_cmp
                jp      z,fo_dev_grp
                call    fs_iscas            ; CAS:, or no disk at all
                jp      z,fo_dev_cas
                ld      ix,p0_pdfcb_resume
                call    p0cb                ; DISK_FCB_NAME built; HL resumes in the text
                ; D-OPENWILD: a WILDCARD name is `Bad file name` (56) on the
                ; CF-3300, before any disk work
                push    hl
                ld      hl,DISK_FCB_NAME
                ld      bc,11
                ld      a,'?'
                cpir                        ; Z iff a '?' is among the 11
                jr      z,fs_badname        ; 56
                pop     hl
                call    skip_spaces
                cp      FOR_TOKEN
                jr      nz,fo_random        ; no FOR clause -> RANDOM (OPEN..AS #n)
                inc     hl
                ; INPUT ($85); OUTPUT = OUT + PUT; APPEND = "APP" + END (crunched)
                call    skip_spaces
                cp      INPUT_TOKEN
                jr      z,fo_input
                cp      OUT_TOKEN
                jr      z,fo_output
                call    fo_is_app
                jp      nz,fs_syntax
                ld      a,3                 ; mode = APPEND
                jr      fo_setmode
; fo_is_app: Z and HL past it iff HL is at APPEND ("APP" + END, crunched)
fo_is_app:
                ld      de,fo_app_seq
fo_app_lp:
                ld      a,(de)              ; expected byte (this ROM's own data)
                cp      (hl)                ; against the line (RAM)
                ret     nz
                inc     hl
                inc     de
                ld      a,(de)
                or      a                   ; 0 terminates the sequence
                jr      nz,fo_app_lp
                ret                         ; Z
fo_app_seq:
                db      'A','P','P',END_TOKEN,0
fo_output:
                call    fs_put
                ld      a,2                 ; mode = OUTPUT
                jr      fo_setmode
fo_input:
                inc     hl
                ld      a,1                 ; mode = INPUT
                jr      fo_setmode
fo_random:
                ld      a,4                 ; mode = RANDOM (no FOR clause)
fo_setmode:
                ld      (FCH_MODE),a        ; provisional: read below only
                call    fo_parse_as_chan    ; "AS [#]n" + ceiling + busy; DE = ch
                ; the optional LEN=r clause; r in 1..256, default 256
                ld      a,e
                ld      (OO_RECLEN_CHAN),a  ; the channel, across the LEN= eval
                ld      ix,p0_oo_parse_reclen
                call    p0cb                ; DE = reclen; CF = out of range
                jp      c,fs_illegal        ; ERR 5 (CF-3300: LEN=0/257/512)
                ; D-OPENEND: the statement must END here, before any disk work
                ; (`OPEN "X.TXT" FOR APPEND AS 1,2` is 2 even with X.TXT missing)
                call    fo_term             ; junk after the clause: 2, nothing opened
                push    hl                  ; guard the text cursor
                ld      a,(OO_RECLEN_CHAN)
                ld      l,a
                ld      h,0
                push    hl                  ; DE-to-be: the channel (D = 0)
                add     hl,hl               ; channel * 2 (word index)
                ld      bc,FCH_RECLENS
                add     hl,bc
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; FCH_RECLENS[ch] = reclen
                pop     de                  ; DE = the channel again
                pop     hl
                ; D-OPENSAME: a file already open on another channel is 54, asked
                ; of disk.rom (hkk_open_check) before the claim
                push    de
                push    hl
                ld      a,FOPEN_SEL_OCHK
                ld      ix,p0_fopen_cross
                call    p0cb                ; NZ: this file is open on a channel
                pop     hl
                pop     de
                jp      nz,fo_fail_54
                ld      a,e
                ld      (FCH_ACTIVE),a      ; claim: this channel is the live one
                push    hl                  ; guard the cursor and the channel
                push    de                  ; across the crossing
                ld      a,(FCH_MODE)        ; 1 INPUT / 2 OUTPUT / 3 APPEND / 4 RANDOM
                cp      2
                jr      z,fo_create
                cp      3
                jr      z,fo_append
                cp      4
                jr      z,fo_random_setup
                ld      a,FOPEN_SEL_INP     ; S10.C: INPUT is disk.rom's (hk_finp)
                jr      fo_cross
fo_create:
                ld      a,FOPEN_SEL_MAKE    ; S10.B: OUTPUT (hk_fmake)
                jr      fo_cross
fo_append:
                ld      a,FOPEN_SEL_APND    ; S10.B: APPEND (hk_fapp)
                jr      fo_cross
fo_random_setup:
                ld      a,FOPEN_SEL_RAND    ; S10.D: RANDOM (hk_frnd)
fo_cross:
                ld      ix,p0_fopen_cross
                call    p0cb                ; A = status, 0 = open
                add     a,$FF               ; CF iff status != 0
                pop     de
                pop     hl
                jr      c,fo_fail           ; not found / dir-full / mount / I-O
                ; success: OUTPUT and APPEND are both stored as DOUT_MODE (3)
                ld      a,(FCH_MODE)
                cp      2
                jr      c,fo_storemode      ; 1 INPUT
                cp      4
                jr      nc,fo_storemode     ; 4 RANDOM
                ld      a,DOUT_MODE         ; 2 OUTPUT, 3 APPEND
                ld      (FCH_MODE),a
fo_storemode:                               ; A = the mode, now committed: the device
                ld      (OO_DEVTYPE),a      ; arms' stamp writes FCH_MODES[ch] and the
                jr      fo_stamp_devtype    ; header (D-FCBHDR) from OO_DEVTYPE
fo_fail:
                ; post-claim failure (DE = channel): release the slot, then the
                ; error -- never before, or the slot stays claimed (D-LOADERR).
                ; disk_error: disk.rom parked 53 for a missing file, or its DSKIO
                ; code; with none pending it prints `load error` and RETURNS.
                call    fs_modes_e
                xor     a
                ld      (hl),a              ; FCH_MODES[ch] = 0
                ld      (FCH_ACTIVE),a      ; no channel live
                jp      fs_disk_error

; --- OPEN "LPT:" / "CRT:" / "GRP:" : a character-device channel -------------------
; No FCB row: FCH_MODES[ch] = LPT_MODE / CRT_MODE / GRP_MODE. The FOR clause is
; OPTIONAL and means OUTPUT (D-DEVBARE, measured on the CF-3300); `FOR INPUT` is
; refused (Syntax error; 56 on GRP:); LEN= is refused by the terminator check.
; Entry: HL -> the char after the device prefix, inside the staged copy.
fo_dev_lpt:
                ld      a,LPT_MODE
                jr      fo_dev_open
fo_dev_crt:
                ld      a,CRT_MODE
                jr      fo_dev_open
; fo_dev_grp -- OPEN "GRP:" (D-OPENGRP, main's oo_dev_grp in basic/grpdev.asm).
; ONE AT A TIME: a second OPEN "GRP:" while one is open is 52 at that OPEN
; (VG-8020, round 5). The SCREEN mode is checked at PRINT #, not here. Clears
; GRP_HDR (power-on RAM is garbage; an armed header would bend the first glyph).
fo_dev_grp:
                push    hl
                ld      hl,FCH_MODES
                ld      bc,16
                ld      a,GRP_MODE
                cpir                        ; Z: a GRP: channel is already open
                pop     hl
                jp      z,fs_bfn
                ld      a,b                 ; B = 0 after a cpir that ran out
                ld      (GRP_HDR),a
                ld      a,GRP_MODE
fo_dev_open:
                ld      (OO_DEVTYPE),a      ; the device type, across the parse
fodv_fn:                                    ; skip the rest of the name to its quote
                ld      a,(hl)
                or      a
                jp      z,fs_syntax         ; unterminated string
                inc     hl
                cp      '"'
                jr      nz,fodv_fn
                ld      hl,(FN_RESUME)      ; resume in the program text
                call    skip_spaces
                cp      FOR_TOKEN
                jr      nz,fodv_as          ; no FOR clause -> OUTPUT (measured)
                call    fs_chrgtr           ; main's CHRGTR, through p0cb
                cp      OUT_TOKEN           ; OUTPUT = OUT + PUT
                jr      nz,fodv_notout      ; INPUT: Syntax error; 56 on GRP:
                call    fs_put
fodv_as:
                call    fo_as_term          ; DE = ch; only a terminator may follow
; fo_stamp_devtype -- D-CARVE2's shared tail of the device, cassette and disk arms:
; HL = the cursor, E = the channel; FCH_MODES[ch] := OO_DEVTYPE.
fo_stamp_devtype:
                push    hl                  ; the cursor, for fs_pop_exec
                call    fs_modes_e
                ld      a,(OO_DEVTYPE)
                ld      (hl),a
                ; FALL THROUGH
; fo_hdr_tail -- D-FCBHDR: stamp the channel's FCB header (VARPTR(#n)'s +0 mode,
; +4 device, +6 position) -- the FAT tenant's row 23 (sub/fatprim.asm t_fch_hdr).
;   in: E = the channel, OO_DEVTYPE = its FCH_MODES value; the cursor stacked.
; Main called fatprim_bounce, whose only addition to fatprim_op was reloading
; HL / A and a flag: pop_exec discarded all three, so fatprim_op is called direct.
fo_hdr_tail:
                ld      a,e
                ld      ix,p0_fch_ctx_addr
                call    p0cb                ; HL = the channel's block
                ld      a,DISKOP_SEL_FCH_HDR
                ld      ix,p0_fatprim_op
                call    p0cb
                jp      fs_pop_exec
fodv_notout:                                ; FOR not followed by OUTPUT
                ld      a,(OO_DEVTYPE)
                cp      GRP_MODE
                jp      z,fs_badname        ; GRP: is 56 (D-OPENGRP round 1)
                jp      fs_syntax           ; LPT: / CRT: stay Syntax error

; --- OPEN "CAS:name" FOR INPUT|OUTPUT AS #n ---------------------------------------
; A cassette sequential channel (FCH_MODES = CAS_IN_MODE / CAS_OUT_MODE). The name
; is captured into CAS_WANT and honoured (D-CASOPEN); APPEND and RANDOM are 56 on
; both references (D-NODISKOPEN), other junk after FOR is 2. The arguments are
; validated in full before any tape I/O. Entry: HL past "CAS:" in the staged copy.
fo_dev_cas:
                call    fs_cascut           ; HL back in the program text
                call    skip_spaces
                cp      FOR_TOKEN
                jr      nz,focas_nofor      ; CAS: needs FOR (no RANDOM cassette)
                call    fs_chrgtr
                cp      INPUT_TOKEN
                jr      z,focas_in
                cp      OUT_TOKEN
                jr      z,focas_out
                call    fo_is_app           ; APPEND is 56; other junk stays 2
                jp      nz,fs_syntax
                jr      fo_fail_bfname
focas_nofor:
                ; RANDOM (`AS #n`, no FOR) is 56; the AS clause is parsed first,
                ; so a bad channel there answers before the 56 (order unmeasured)
                call    fo_parse_as_chan    ; 2 unless `AS [#]n`
fo_fail_bfname:
                jp      fs_badname          ; Bad file name
focas_in:
                inc     hl
                ld      a,CAS_IN_MODE
                jr      focas_setmode
focas_out:
                call    fs_put
                ld      a,CAS_OUT_MODE
focas_setmode:
                ld      (OO_DEVTYPE),a      ; the CAS mode, across the AS/#n parse
                call    fo_as_term          ; DE = ch; only a terminator may follow
                push    de                  ; the channel
                push    hl                  ; the cursor (the tape BIOS clobbers all)
                ld      a,(OO_DEVTYPE)
                cp      CAS_OUT_MODE
                jr      z,focas_do_out
                ; FOR INPUT: find the (named) file, require $EA, prime block 1
                call    fs_casopen          ; Z iff a cassette data ($EA) file
                jr      nz,focas_ioerr
                ld      ix,p0_cas_ascii_setup ; prime data block 1 (D-CASPRIME: 19)
                jr      focas_buf
focas_do_out:
                ; FOR OUTPUT: the $EA header block now, through channel #n's buffer.
                ; TSV_NAME IS CAS_WANT (D-TSVOVL), so this copies onto itself -- kept
                ; as main had it, byte for byte (it leaves BC = 0).
                ld      hl,CAS_WANT
                ld      de,TSV_NAME
                ld      bc,6
                ldir
                ld      ix,p0_cas_write_ea_header ; TAPOON + $EA*10 + TSV_NAME + TAPOOF
                                            ; (D-CASWBRK: Ctrl-STOP -> 19)
focas_buf:                                  ; IX = the arm's tape step
                pop     hl                  ; D-CASFCB: channel #n's own buffer
                pop     de
                push    de
                push    hl
                ld      a,e
                push    ix
                ld      ix,p0_cas_bufp_set
                call    p0cb
                pop     ix
                call    p0cb                ; the step; CF = tape error / Ctrl-STOP
                jp      c,fs_dio            ; 19, raised
                pop     hl                  ; the cursor
                pop     de                  ; the channel
                jp      fo_stamp_devtype
focas_ioerr:                                ; not an $EA file: `load error`, which
                pop     hl                  ; PRINTS AND RETURNS -- a continuation
                pop     de
                ld      de,p0_load_error
                ret

; main's dev_cmp (HL = the string, DE = a device name in main): Z + HL past the
; prefix iff it matched; clobbers A, C, DE. CALLED DIRECTLY (`call p0_dev_cmp`), not
; through p0cb (D-SUB2RETIRE step 2e): main's PAGE 1 is mapped under this page-0
; tenant, and dev_cmp is a page-1 leaf whose one callee, main's upcase, is a
; page-1 leaf too -- no rst, no low-region or BIOS call (read 2026-11-04). The
; asserts beside basic-resident-abi.inc's include in sub/sub.asm refuse a build
; that moves either of them below $4000, where this page's own bytes would run
; instead (there, not here: the p0_ names are forward references in page 0, and
; pasmo 0.5.3 reads a forward alias as 0 -- D-PASMO053).
; fs_iscas -- OPEN's and MERGE's shared "is it the tape?": Z (HL past "CAS:" when
; named) -> the cassette arm; NZ -> the disk arm. On a diskless machine the
; cassette is the default device and a `d:` name raises 56 inside nodisk_dev
; (D-NODISKOPEN / D-NODISKVERBS).
fs_iscas:
                ld      de,p0_dev_cas
                call    p0_dev_cmp
                ret     z
                ld      ix,p0_nodisk_dev
                jp      p0cb
; fs_modes_e -- main's fch_modes_ptr on channel E: HL = &FCH_MODES[E] (A, HL only).
; A DIRECT jump, as dev_cmp above: fch_modes_ptr is a main page-1 leaf (an add on
; FCH_MODES, no call at all), mapped under this page-0 tenant.
fs_modes_e:
                ld      a,e
                jp      p0_fch_modes_ptr    ; (asserted page 1 in sub/sub.asm)
; fs_put -- HL on OUT: require PUT after it (OUTPUT = OUT + PUT), HL past both
fs_put:
                inc     hl
                ld      a,(hl)
                cp      PUT_TOKEN
                jp      nz,fs_syntax
                inc     hl
                ret
; fs_cascut -- the cassette name into CAS_WANT, then HL back in the program text
fs_cascut:
                ld      ix,p0_cas_capture_cut
                call    p0cb                ; -> CAS_WANT + CAS_WANT_ON (D-CASDOT)
                ld      hl,(FN_RESUME)      ; resume past the EXPRESSION
                ret
; fs_casopen -- find the (named) tape file, header consumed; Z iff it is an $EA
; (ASCII) file. Tape end / I-O / Ctrl-STOP is 19, raised (D-CASBRK).
fs_casopen:
                ld      ix,p0_cas_open_match
                call    p0cb
                jp      c,fs_dio
                ld      a,(CAS_HDRID)
                cp      ASCII_ID
                ret
; fs_chan -- `[#]n` at HL (A = (HL)): DE = n, HL past it, through fch_check_d
; (D != 0 -> ERR 5; else A = E, Z <=> channel 0). OPEN and CLOSE.
fs_chan:
                cp      '#'
                jr      nz,fsc_ev
                inc     hl
fsc_ev:
                ld      ix,p0_eval
                call    p0cb                ; DE = the channel, HL past it
                ld      ix,p0_fch_check_d
                jp      p0cb

; fo_as_term / fo_term -- the end of every OPEN form: fo_as_term parses "AS [#]n"
; first (fo_parse_as_chan's out: DE = the channel); then only end of line or `:`
; may follow (Z, A = it), else ERR 2. A, F, HL only -- DE survives.
fo_as_term:
                call    fo_parse_as_chan
fo_term:
                call    skip_spaces
                or      a                   ; Z iff the terminator (0)
                ret     z
                cp      COLON
                ret     z
                jp      fs_syntax

; fo_parse_as_chan -- main's oo_parse_as_chan: the "AS [#]n" clause of every OPEN.
; in : HL = the cursor past the mode clause.
; out: HL past the channel expression, DE = the channel (D = 0, E in 1..MAXF),
;      A = E. Never returns on a malformed clause.
; "AS" is verbatim ASCII (not a token). OPEN is the ONE verb that answers 52 to
; channel 0, and 5 to `AS #256` / `AS #-1` (D-BADFNUM); a channel already open
; is 54 (D-OPENBUSY), checked here before any file work, for every OPEN form.
fo_parse_as_chan:
                call    skip_spaces
                call    upcase              ; this page's own (sub/tkfloat.asm)
                cp      'A'
                jp      nz,fs_syntax
                inc     hl
                ld      a,(hl)
                call    upcase
                cp      'S'
                jp      nz,fs_syntax
                call    fs_chrgtr
                call    fs_chan             ; DE = the channel; Z <=> channel 0
                jp      z,fs_bfn            ; OPEN's channel-0 exception -> ERR 52
                ld      ix,p0_fch_check_nz
                call    p0cb                ; > MAXF -> ERR 52; else A = E
                push    hl
                call    fs_modes_e          ; HL = &FCH_MODES[ch] (A, HL only)
                ld      a,(hl)
                pop     hl
                or      a
                ld      a,e
                ret     z                   ; free: A = E = the channel
fo_fail_54:                                 ; D-OPENSAME joins here too
                ld      a,54                ; File already open
                jp      fs_raise

; ===========================================================================
; CLOSE [[#]n [, [#]m ...]]   (main's ex_close)
; ===========================================================================
; Bare CLOSE closes every channel. Channel 0 is the reference's ONE lenient no-op;
; #2 / #16 / #256 / #-1 raise (D-BADFNUM); a channel that is not open is a no-op.
fs_close:
                ld      ix,p0_stmt_bare_end
                call    p0cb                ; D-BAREEND: Z iff the statement ends here
                jr      z,fc_all
fc_listloop:
                call    skip_spaces
                call    fs_chan             ; DE = the channel; Z <=> channel 0
                push    hl                  ; guard the cursor (push keeps the flags)
                jr      z,fc_done           ; channel 0 -> the one lenient no-op
                ld      ix,p0_fch_check_nz
                call    p0cb                ; > MAXF -> ERR 52
                call    fs_modes_e          ; (preserves E)
                ld      a,(hl)
                or      a
                jr      z,fc_done           ; not open -> no-op
                ld      a,e
                ld      ix,p0_fch_do_close_ch
                call    p0cb                ; flush (if OUTPUT) + mark closed
fc_done:
                pop     hl
                call    skip_spaces
                cp      ','                 ; Z iff `,`
                jp      nz,fs_exec          ; the list ends: main's dc_finish (exec_stmt)
                inc     hl                  ; consume ',' and parse the next channel
                jr      fc_listloop
fc_all:
                push    hl
                ld      ix,p0_fch_close_all
                call    p0cb
                jp      fs_pop_exec

; ===========================================================================
; MAXFILES = n   (main's ex_maxfiles)
; ===========================================================================
; MAX ($CD) + FILES ($B7), two reserved words. The domain is the reference's
; (D-MFDOM): outside int16 -> 6, else outside 0..FCH_CEIL -> 5, fractions
; truncate. The statement must END before the commit (D-MAXFTAIL: `MAXFILES=1 ZZ`
; is a trappable 2 with the variables intact). Then every channel is closed and
; the variables are CLEARed -- unconditionally, even for the same value.
fs_maxfiles:
                inc     hl                  ; past MAX
                ld      a,(hl)
                cp      FILES_TOKEN         ; require FILES
                jp      nz,fs_syntax        ; bare MAX is not a statement
                call    fs_chrgtr           ; past FILES
                cp      EQ_TOKEN
                jp      nz,fs_syntax
                inc     hl
                ld      ix,p0_eval_byte_arg
                call    p0cb                ; A = E = 0..255; ERR 6 >int16, ERR 5 else
                cp      FCH_CEIL+1
                jp      nc,fs_illegal       ; > FCH_CEIL -> ERR 5
                ld      ix,p0_mxf_require_end
                call    p0cb                ; anything after it: ERR 2, nothing done
                push    de                  ; guard the requested value
                push    hl                  ; and the cursor
                ld      ix,p0_fch_close_all
                call    p0cb                ; MAXFILES reinitialises: close everything
                pop     hl
                pop     de
                ld      a,e
                ld      (MAXF),a            ; commit the new ceiling (0..FCH_CEIL)
                ld      de,p0_clr_wipe      ; a CONTINUATION: CLEAR's wipe, past its
                ret                         ; own close-all, then exec_stmt (HL)

; ===========================================================================
; MERGE "name"   (main's ex_merge)
; ===========================================================================
; An ASCII program from disk or tape into the CURRENT program. The name is a
; string EXPRESSION (D-MERGEXPR): bare MERGE is 24, `MERGE 5` is 13 (fname_expr).
; A non-numbered line is 57, untrapped (D-CASDIRECT). MERGE RETURNS TO COMMAND
; LEVEL (D-MERGERET): its continuation is end_line_end, in both arms.
fs_merge:
                call    fs_chrgtr           ; past the MERGE token
                or      a
                ld      ix,p0_loc_missing   ; bare MERGE -> ERR 24 (measured)
                jp      z,p0cb
                ld      ix,p0_fname_expr
                call    p0cb                ; HL -> the staged '"'-terminated copy
                call    fs_iscas            ; "CAS:" (HL past the prefix), or no disk
                jr      z,fm_cas            ; -> tape merge; `d:` without a disk is 56
                ld      ix,p0_pdfcb_resume
                call    p0cb                ; DISK_FCB_NAME; HL resumes in the text
                push    hl                  ; guard the cursor across the merge
                ld      ix,p0_dsk_aopen
                call    p0cb                ; disk.rom mounts, finds, primes; CF = no
                jr      c,fm_ioerr
                ld      ix,p0_dsk_ascii_drive
                call    p0cb                ; tokenise + store each line; CF = bad line
fm_fin:                                     ; the tape arm joins here
                pop     hl
                jp      nc,fs_end_line      ; back to command level (a continuation)
                ld      a,57                ; dpl_direct: 57 Direct statement in file
                jp      fs_raise
fm_ioerr:
                pop     hl
                ; DISKOP_STATUS 1 = not found, 3 = mount / I-O (not df_or_loaderr:
                ; FOPEN_SEL aliases DISKOP_OP)
                ld      a,(DISKOP_STATUS)
                dec     a
                jp      nz,fs_disk_error    ; 3 -> the mapped DSKIO code
                ld      a,53                ; df_notfound: 1 -> ERR 53 File not found
                jp      fs_raise
; --- MERGE "CAS:name": an $EA ASCII cassette file, the name honoured; NO new_prog
fm_cas:
                call    fs_cascut           ; HL past the EXPRESSION
                push    hl
                call    fs_casopen          ; MERGE requires an ASCII ($EA) file
                jr      nz,fmc_ioerr
                ld      ix,p0_cas_ascii_setup
                call    p0cb                ; prime data block 1
                jr      c,fmc_found_dio
                ld      ix,p0_cas_ascii_drive
                call    p0cb                ; read + tokenise + store; CF = bad line
                jr      fm_fin
fmc_ioerr:
                pop     hl
                jp      fs_disk_error       ; D-DISKERR
fmc_found_dio:
                ; D-CASPRIME: the first data block failed after `Found:` -- the
                ; VG-8020 raises 19 TRAPPED with ERL 65535 (DIRECTF 0 -> 1)
                ld      hl,DIRECTF
                inc     (hl)
                jp      fs_dio
