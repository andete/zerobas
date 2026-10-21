; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; filestmt.asm -- zerobas-sub2 PAGE 0: the file-channel STATEMENTS OPEN, CLOSE,
; MERGE and MAXFILES (D-P0CB slice C1, docs/spec-sub2-p0cb.md §5). Moved out of
; main page 1 (basic/files.asm, basic/grpdev.asm) on 2026-10-21. The channel
; MACHINERY stays in main -- fch_check_d / fch_check_nz, fch_modes_ptr,
; fch_do_close_ch / fch_close_all, fopen_cross and the disk.rom crossing, every
; cassette routine, fname_expr / pdfcb_resume / dev_cmp (shared with the other
; file verbs, and disk.rom calls some of them back), oo_parse_reclen (driven on
; the main image by tests/test_open_len.py) and the device-name strings, which
; main's dev_cmp reads. Only what these four statements alone reach moved.
;
; Entered through trap_tenant (sub2/trapstmt.asm), which forwards every C >= 8
; here: main's four entry labels share ONE byte, `ld c,a` in front of ex_sub2
; (basic/program.asm), so C = the statement token (exec_stmt hands every
; handler A = its token -- tests/test_stmt_dispatch.py asserts it).
;   in   HL = the cursor ON the statement token (exec_stmt's contract)
;        C  = the statement token
;   out  DE = the main address to continue at, HL = what it expects (below)
; ex_sub2 then does `push de / ret` with the stack exactly as the statement was
; entered. The continuations, and what each takes:
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
; Every other main routine is reached through p0cb (sub2/p0cb.asm) with its
; `p0_` alias from basic-resident-abi.inc; `rst $10` is this ROM's RST 10h
; (main's CHRGTR). A raise reached through p0cb never returns -- raise_error
; resets SP and runs main's error path with main's page 0 mapped -- exactly as
; the `jp` it replaces never returned; a frame this code pushed is discarded by
; the same unwind. No hook (H_xxxx) is called from here: the hooked crossings
; are inside fopen_cross / fch_do_close_ch, which run in main.
; The code is otherwise main's, statement for statement, and each arm keeps the
; original's order of checks, so the errors and their order are the ones the
; OPEN / CLOSE / MERGE / MAXFILES rows already pin. The history behind each
; check is in git (basic/files.asm before D-P0CB slice C1); what is kept here
; is the measured rule each one encodes.

; --- the dispatch -------------------------------------------------------------
file_tenant:                                ; A = C = the token (trap_tenant's head)
                cp      OPEN_TOKEN
                jr      z,fs_open
                cp      CLOSE_TOKEN
                jp      z,fs_close
                cp      MERGE_TOKEN
                jp      z,fs_merge
                cp      MAX_TOKEN
                jp      z,fs_maxfiles
                ; FALL THROUGH: no other token reaches here (main has no other stub)

; --- the shared tails -------------------------------------------------------------
fs_syntax:                                  ; oo_synerr / oo_fail_syn: stmt_error, ERR 2
                ld      ix,p0_stmt_error
                jp      p0cb                ; raises; never returns
fs_illegal:                                 ; gb_illegal: ERR 5
                ld      ix,p0_gb_illegal
                jp      p0cb
fs_badname:                                 ; pdf_badname: ERR 56
                ld      ix,p0_pdf_badname
                jp      p0cb
fs_bfn:                                     ; oo_fail_bfn: ERR 52
                ld      ix,p0_oo_fail_bfn
                jp      p0cb
fs_dio:                                     ; dpl_dio: motor off, ERR 19
                ld      ix,p0_dpl_dio
                jp      p0cb
fo_fail_ifc:                                ; LEN= out of 1..256: ERR 5 (D-RECLEN2)
                ld      e,5
fo_fail_e:                                  ; E = the ERR code
                ld      a,e
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
                ld      ix,p0_dev_cmp
                call    p0cb                ; Z + HL past the prefix iff it matched
                jp      z,fo_dev_lpt
                ld      de,p0_dev_crt
                ld      ix,p0_dev_cmp
                call    p0cb
                jp      z,fo_dev_crt
                ld      de,p0_dev_grp       ; D-OPENGRP: the graphics screen
                ld      ix,p0_dev_cmp
                call    p0cb
                jp      z,fo_dev_grp
                ld      de,p0_dev_cas
                ld      ix,p0_dev_cmp
                call    p0cb
                jp      z,fo_dev_cas
                ; D-NODISKOPEN: on a diskless machine the cassette is the default
                ; device; a `d:` name raises 56 inside nodisk_dev
                ld      ix,p0_nodisk_dev
                call    p0cb
                jp      z,fo_dev_cas
                ld      ix,p0_pdfcb_resume
                call    p0cb                ; DISK_FCB_NAME built; HL resumes in the text
                ; D-OPENWILD: a WILDCARD name is `Bad file name` (56) on the
                ; CF-3300, before any disk work
                push    hl
                ld      hl,DISK_FCB_NAME
                ld      b,11
                ld      a,'?'
fo_wild:
                cp      (hl)
                jp      z,fs_badname        ; 56
                inc     hl
                djnz    fo_wild
                pop     hl
                ld      ix,p0_skip_spaces
                call    p0cb
                cp      FOR_TOKEN
                jr      nz,fo_random        ; no FOR clause -> RANDOM (OPEN..AS #n)
                inc     hl
                ; INPUT ($85); OUTPUT = OUT + PUT; APPEND = "APP" + END (crunched)
                ld      ix,p0_skip_spaces
                call    p0cb
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
                inc     hl
                ld      a,(hl)
                cp      PUT_TOKEN
                jp      nz,fs_syntax
                inc     hl
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
                jp      c,fo_fail_ifc       ; ERR 5 (CF-3300: LEN=0/257/512)
                ; D-OPENEND: the statement must END here, before any disk work
                ; (`OPEN "X.TXT" FOR APPEND AS 1,2` is 2 even with X.TXT missing)
                ld      ix,p0_skip_spaces
                call    p0cb                ; A and HL only: DE survives
                or      a
                jr      z,fo_endok
                cp      ':'
                jp      nz,fs_syntax        ; junk after the clause: 2, nothing opened
fo_endok:
                push    hl                  ; guard the text cursor
                ld      a,(OO_RECLEN_CHAN)
                add     a,a                 ; channel * 2 (word index)
                ld      l,a
                ld      h,0
                ld      bc,FCH_RECLENS
                add     hl,bc
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; FCH_RECLENS[ch] = reclen
                pop     hl
                ld      a,(OO_RECLEN_CHAN)
                ld      e,a
                ld      d,0                 ; DE = the channel again
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
fo_storemode:
                push    hl                  ; the cursor, for fs_pop_exec
                ld      a,e
                ld      ix,p0_fch_modes_ptr
                call    p0cb                ; HL = &FCH_MODES[ch]
                ld      a,(FCH_MODE)
                ld      (hl),a              ; FCH_MODES[ch] = mode (now committed)
                ld      (OO_DEVTYPE),a      ; D-FCBHDR: what the header stamp reads
                jr      fo_hdr_tail
fo_fail:
                ; post-claim failure (DE = channel): release the slot, then the
                ; error -- never before, or the slot stays claimed (D-LOADERR).
                ; disk_error: disk.rom parked 53 for a missing file, or its DSKIO
                ; code; with none pending it prints `load error` and RETURNS.
                ld      a,e
                ld      ix,p0_fch_modes_ptr
                call    p0cb
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
                ld      ix,p0_skip_spaces
                call    p0cb
                cp      FOR_TOKEN
                jr      nz,fodv_as          ; no FOR clause -> OUTPUT (measured)
                rst     $10                 ; this ROM's RST 10h -> main's CHRGTR
                cp      OUT_TOKEN           ; OUTPUT = OUT + PUT
                jr      nz,fodv_notout      ; INPUT: Syntax error; 56 on GRP:
                inc     hl
                ld      a,(hl)
                cp      PUT_TOKEN
                jp      nz,fs_syntax
                inc     hl
fodv_as:
                call    fo_parse_as_chan    ; DE = ch
                ld      ix,p0_skipsp_test
                call    p0cb                ; only a terminator may follow (no LEN=)
                jr      z,fo_stamp_devtype
                cp      COLON
                jp      nz,fs_syntax
; fo_stamp_devtype -- D-CARVE2's shared tail of the device and cassette arms:
; HL = the cursor, E = the channel; FCH_MODES[ch] := OO_DEVTYPE.
fo_stamp_devtype:
                push    hl                  ; the cursor, for fs_pop_exec
                ld      a,e
                ld      ix,p0_fch_modes_ptr
                call    p0cb
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
                ld      ix,p0_cas_capture_cut
                call    p0cb                ; -> CAS_WANT + CAS_WANT_ON (D-CASDOT)
                ld      hl,(FN_RESUME)      ; resume in the program text
                ld      ix,p0_skip_spaces
                call    p0cb
                cp      FOR_TOKEN
                jr      nz,focas_nofor      ; CAS: needs FOR (no RANDOM cassette)
                rst     $10
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
                ld      e,56                ; Bad file name
                jp      fo_fail_e
focas_in:
                inc     hl
                ld      a,CAS_IN_MODE
                jr      focas_setmode
focas_out:
                inc     hl
                ld      a,(hl)
                cp      PUT_TOKEN
                jp      nz,fs_syntax
                inc     hl
                ld      a,CAS_OUT_MODE
focas_setmode:
                ld      (OO_DEVTYPE),a      ; the CAS mode, across the AS/#n parse
                call    fo_parse_as_chan    ; DE = ch
                ld      ix,p0_skipsp_test
                call    p0cb                ; only a terminator may follow (no LEN=)
                jr      z,focas_argsok
                cp      COLON
                jp      nz,fs_syntax
focas_argsok:
                push    de                  ; the channel
                push    hl                  ; the cursor (the tape BIOS clobbers all)
                ld      a,(OO_DEVTYPE)
                cp      CAS_OUT_MODE
                jr      z,focas_do_out
                ; FOR INPUT: find the (named) file, require $EA, prime block 1
                ld      ix,p0_cas_open_match
                call    p0cb                ; CF = tape end / I-O / Ctrl-STOP
                jp      c,fs_dio            ; D-CASBRK: 19, raised
                ld      a,(CAS_HDRID)
                cp      ASCII_ID            ; a cassette data file is an $EA file
                jr      nz,focas_ioerr
                pop     hl                  ; D-CASFCB: channel #n's own buffer
                pop     de
                push    de
                push    hl
                ld      a,e
                ld      ix,p0_cas_bufp_set
                call    p0cb
                ld      ix,p0_cas_ascii_setup
                call    p0cb                ; prime data block 1
                jp      c,fs_dio            ; D-CASPRIME: 19, raised
                jr      focas_mark
focas_do_out:
                ; FOR OUTPUT: the $EA header block now, through channel #n's buffer.
                ; TSV_NAME IS CAS_WANT (D-TSVOVL), so this copies onto itself -- kept
                ; as main had it, byte for byte (it leaves BC = 0).
                ld      hl,CAS_WANT
                ld      de,TSV_NAME
                ld      bc,6
                ldir
                pop     hl
                pop     de
                push    de
                push    hl
                ld      a,e
                ld      ix,p0_cas_bufp_set
                call    p0cb
                ld      ix,p0_cas_write_ea_header
                call    p0cb                ; TAPOON + $EA*10 + TSV_NAME + TAPOOF
                jp      c,fs_dio            ; D-CASWBRK: Ctrl-STOP -> 19, raised
focas_mark:
                pop     hl                  ; the cursor
                pop     de                  ; the channel
                jp      fo_stamp_devtype
focas_ioerr:                                ; not an $EA file: `load error`, which
                pop     hl                  ; PRINTS AND RETURNS -- a continuation
                pop     de
                ld      de,p0_load_error
                ret

; fo_parse_as_chan -- main's oo_parse_as_chan: the "AS [#]n" clause of every OPEN.
; in : HL = the cursor past the mode clause.
; out: HL past the channel expression, DE = the channel (D = 0, E in 1..MAXF),
;      A = E. Never returns on a malformed clause.
; "AS" is verbatim ASCII (not a token). OPEN is the ONE verb that answers 52 to
; channel 0, and 5 to `AS #256` / `AS #-1` (D-BADFNUM); a channel already open
; is 54 (D-OPENBUSY), checked here before any file work, for every OPEN form.
fo_parse_as_chan:
                ld      ix,p0_skip_spaces
                call    p0cb
                ld      ix,p0_upcase
                call    p0cb
                cp      'A'
                jp      nz,fs_syntax
                inc     hl
                ld      a,(hl)
                ld      ix,p0_upcase
                call    p0cb
                cp      'S'
                jp      nz,fs_syntax
                rst     $10
                cp      '#'
                jr      nz,fopac_num
                inc     hl
fopac_num:
                ld      ix,p0_eval
                call    p0cb                ; DE = the channel, HL past it
                ld      ix,p0_fch_check_d
                call    p0cb                ; D != 0 -> ERR 5; else A = E, Z <=> ch 0
                jp      z,fs_bfn            ; OPEN's channel-0 exception -> ERR 52
                ld      ix,p0_fch_check_nz
                call    p0cb                ; > MAXF -> ERR 52; else A = E
                push    hl
                ld      ix,p0_fch_modes_ptr
                call    p0cb                ; HL = &FCH_MODES[ch] (A, HL only)
                ld      a,(hl)
                pop     hl
                or      a
                ld      a,e
                ret     z                   ; free: A = E = the channel
fo_fail_54:                                 ; D-OPENSAME joins here too
                ld      e,54                ; File already open
                jp      fo_fail_e

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
                ld      ix,p0_skip_spaces
                call    p0cb
                cp      '#'
                jr      nz,fc_num
                inc     hl
fc_num:
                ld      ix,p0_eval
                call    p0cb                ; DE = the channel; HL = the cursor
                push    hl                  ; guard the cursor
                ld      ix,p0_fch_check_d
                call    p0cb                ; D != 0 -> ERR 5; else A = E, Z <=> ch 0
                jr      z,fc_done           ; channel 0 -> the one lenient no-op
                ld      ix,p0_fch_check_nz
                call    p0cb                ; > MAXF -> ERR 52
                ld      a,e
                ld      ix,p0_fch_modes_ptr
                call    p0cb                ; (preserves E)
                ld      a,(hl)
                or      a
                jr      z,fc_done           ; not open -> no-op
                ld      a,e
                ld      ix,p0_fch_do_close_ch
                call    p0cb                ; flush (if OUTPUT) + mark closed
fc_done:
                pop     hl
                ld      ix,p0_skip_comma
                call    p0cb                ; Z iff `,`
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
                rst     $10                 ; past FILES
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
                rst     $10                 ; past the MERGE token
                or      a
                jr      nz,fm_arg
                ld      ix,p0_loc_missing   ; bare MERGE -> ERR 24 (measured)
                jp      p0cb
fm_arg:
                ld      ix,p0_fname_expr
                call    p0cb                ; HL -> the staged '"'-terminated copy
                ld      de,p0_dev_cas
                ld      ix,p0_dev_cmp
                call    p0cb
                jr      z,fm_cas            ; "CAS:" -> tape merge (HL past prefix)
                ld      ix,p0_nodisk_dev
                call    p0cb                ; D-NODISKVERBS: no disk -> tape, `d:` 56
                jr      z,fm_cas
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
                jr      nc,fm_done
                ld      ix,p0_dpl_direct    ; 57 Direct statement in file
                jp      p0cb
fm_done:
                ld      de,p0_end_line_end  ; back to command level (a continuation)
                ret
fm_ioerr:
                pop     hl
                ; DISKOP_STATUS 1 = not found, 3 = mount / I-O (not df_or_loaderr:
                ; FOPEN_SEL aliases DISKOP_OP)
                ld      a,(DISKOP_STATUS)
                dec     a
                jp      nz,fs_disk_error    ; 3 -> the mapped DSKIO code
                ld      ix,p0_df_notfound   ; 1 -> ERR 53 File not found
                jp      p0cb
; --- MERGE "CAS:name": an $EA ASCII cassette file, the name honoured; NO new_prog
fm_cas:
                ld      ix,p0_cas_capture_cut
                call    p0cb                ; -> CAS_WANT + CAS_WANT_ON (D-CASDOT)
                ld      hl,(FN_RESUME)      ; resume past the EXPRESSION
                push    hl
                ld      ix,p0_cas_open_match
                call    p0cb                ; the (named) $EA file; header consumed
                jp      c,fs_dio            ; D-CASBRK: 19, raised
                ld      a,(CAS_HDRID)
                cp      ASCII_ID            ; MERGE requires an ASCII ($EA) file
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
