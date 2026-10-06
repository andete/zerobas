; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; islands.asm -- BASIC code placed in C-BIOS's own alignment padding.
; ===========================================================================
; MAKING ROOM IN MAIN, lever B (TODO.md; Joost 2026-09-25: *"We need to come up
; with other ways to make room. Clearly reference fits everything in 32k"*, then
; *"B first, then A"*). C-BIOS pads to pinned addresses with `ds`; those runs
; are zero in OUR merged image, in the SAME slot as main, and always mapped with
; it. Each island below is one such run, confirmed in the C-BIOS source:
;   $1AF5..$1BBE  src/main.asm:3091 `ds $1bbf - $` -- pad up to the font
;                 (was $1AF2 until cbios-repack patch #7, D-LINTTBWRAP, 2026-10-06)
;                 (was $1ADB until cbios-repack patch #6, D-CTRLKEYS, 2026-10-05)
;                 ($1ACF until cbios-repack patch #4, D-HOMEKEY, added 12 bytes
;                 to C-BIOS's key_ascii before it: the pad now starts 12 later)
;   $0160..$01FF  src/main.asm:620  `ds $0200 - $` -- pad up to jump_table
; tools/split_islands.py cuts these bytes out of pasmo's image and
; tools/build_mainrom.py overlays them, REFUSING any byte outside those ranges or
; onto a non-zero C-BIOS byte.
; CLEAN-ROOM: original code (moved unchanged from basic/initext.asm). The two
; ranges come from the C-BIOS SOURCE -- a BSD-2 peer implementation this project
; already patches (cbios-repack/, docs/allowed-sources.md grade B) -- never from
; a reference ROM. No disassembly.
; ⚠️ WHAT MAY LIVE HERE: main code/data entered only by call/jp (no fallthrough
; in or out, no `jr` across the gap -- pasmo refuses those loudly), not imported
; by the sub-ROM or disk.rom ABIs, and not needed while page 0 is switched away
; from the main slot (a sub-ROM PAGE-0 tenant cannot reach it).
; ===========================================================================

; --- island 1: before the font ($1AF5..$1BBE, 202 B usable) -----------------
; D-LINTTBWRAP (2026-10-06): cbios-repack/linttb-scroll.patch adds 3 bytes to
; chput_esc_m, before the font pad: this island starts 3 B later than $1AF2.
; D-CTRLKEYS (2026-10-05): cbios-repack/ctrl-keys.patch puts 23 bytes in
; key_ascii, BEFORE the font pad, so the pad -- and this island -- start 23 B
; later than D-HOMEKEY's $1ADB. rn_undefined moved to island 2 to make room.
                org     $1AF5

; try_init_slot -- boot-time: does the slot in A carry an "AB" ROM, and if so
; CALSLT its INIT. From basic/initext.asm, unchanged. Better here than in page 1:
; the CALSLT into the cartridge's page-1 INIT runs from page 0, which the switch
; never touches.
try_init_slot:
                ld      (SCAN_SLOT),a
                ld      hl,$4000
                call    rdslt_scan
                cp      'A'
                ret     nz
                ld      hl,$4001
                call    rdslt_scan
                cp      'B'
                ret     nz
                ld      hl,$4002
                call    rdslt_scan
                ld      (SCAN_INIT),a       ; INIT entry, low byte
                ld      hl,$4003
                call    rdslt_scan
                ld      (SCAN_INIT+1),a     ; INIT entry, high byte
                ld      hl,(SCAN_INIT)
                ld      a,h
                or      l
                ret     z                   ; INIT vector $0000 -> nothing to call
                ; inter-slot call to the extension ROM's INIT (it installs its
                ; hooks / SYSTEM vector and returns).
                ld      a,(SCAN_SLOT)
                ld      (SCAN_IY+1),a       ; CALSLT reads the slot from IYh
                ld      iy,(SCAN_IY)
                ld      ix,(SCAN_INIT)
                call    CALSLT
                ; Record this external AB ROM's slot id for cross-slot BDOS calls
                ; from BLOAD (it CALSLTs the disk ROM's bdos_entry). On the
                ; combined machine the disk ROM is the only external AB ROM the
                ; scan reaches, so its slot is unambiguous; a multi-ROM setup
                ; would need per-ROM tracking (last-one-wins here — documented
                ; limitation, PROVENANCE.md §disk-ROM slot capture).
                ld      a,(SCAN_SLOT)
                ld      (DISKSLOT),a
                ld      a,1
                ld      (DISKSLOT_OK),a
                ret


; init_ext_roms -- the boot-time extension-ROM scan (from basic/initext.asm,
; unchanged): every primary/secondary slot after ours, CALSLT each "AB" ROM's
; INIT via try_init_slot above. Runs once, with interrupts off, at power-on.
init_ext_roms:
                xor     a
                ld      (DISKSLOT_OK),a     ; no disk-ROM slot recorded yet
                ld      (SUBSLOT_OK),a      ; no zerobas-sub slot recorded yet (subrom S2b)
                di                          ; slot switching must be uninterrupted
                in      a,(PSLTREG)         ; primary slot select register
                rrca
                rrca
                and     $03                 ; A = our page-1 primary slot
                inc     a                   ; begin one past ourselves (scan order)
                ld      (SCAN_PRIM),a
ier_ploop:
                ld      a,(SCAN_PRIM)
                cp      4
                jr      nc,ier_done         ; primaries (mine+1)..3 all scanned
                ; expanded primary?  EXPTBL[prim] bit 7
                ld      hl,EXPTBL
                ld      e,a
                ld      d,0
                add     hl,de
                bit     7,(hl)
                jr      z,ier_single
                ; expanded: scan secondaries 0..3
                ld      b,0                 ; B = secondary slot
ier_sloop:
                ld      a,(SCAN_PRIM)
                ld      c,a                 ; C = primary
                ld      a,b
                add     a,a
                add     a,a                 ; secondary << 2  (into bits 3-2)
                or      c                   ; | primary
                or      $80                 ; expanded-slot flag
                push    bc                  ; try_init_slot / CALSLT clobber BC
                call    try_init_slot
                call    try_sub_slot        ; also record a CD sub-ROM here (3-2; subrom S2b)
                pop     bc
                inc     b
                ld      a,b
                cp      4
                jr      c,ier_sloop
                jr      ier_pnext
ier_single:
                ld      a,(SCAN_PRIM)       ; slot id = primary (no expanded flag)
                call    try_init_slot
ier_pnext:
                ld      hl,SCAN_PRIM
                inc     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
                jr      ier_ploop
ier_done:
                call    sub_int_install     ; install the page-0 EI trampoline if a
                                            ; sub-ROM was recorded (subrom trampoline)
                call    play_install        ; install the PLAY servicer H.TIMI seam
                                            ; (audio Slice 3; H.TIMI is C9-free here)
    IF TRAPS_T3
                call    zkey_install        ; install the KEY-trap fn-key hook (traps T3;
                                            ; H_ZKEY is C9-filled by C-BIOS's hook init)
    ENDIF
                call    trap_init           ; interrupt-traps T1: zero the ZTRAP table so
                                            ; garbage boot RAM can't look like an armed
                                            ; trap. Under the boot DI (below); the H.TIMI
                                            ; poll installed just above fast-outs anyway
                                            ; until TRAPENA is set. (traps.asm)
                ei
                ret

; try_init_slot: if slot A carries an "AB" header, CALSLT its INIT entry.
; in: A = slot id. The slot id and INIT address live in RAM (SCAN_SLOT /
; SCAN_INIT) because RDSLT destroys AF/BC/DE between reads.
; try_init_slot -- MOVED to basic/islands.asm (MAKING ROOM lever B, 2026-09-25):
; it now lives in C-BIOS's own padding before the font, in page 0, and is still
; reached by the two `call try_init_slot` sites above.

; rdslt_scan: A = RDSLT(slot=(SCAN_SLOT), addr=HL). RDSLT preserves HL, so the
; caller sets HL; the slot id is reloaded from RAM each call (RDSLT clobbers it).
rdslt_scan:
                ld      a,(SCAN_SLOT)
                jp      RDSLT               ; tail call: RDSLT's RET returns to caller

; --- D-ISLDATA2 (2026-10-03): pure-DATA blocks into the font island ---------------
; (five blocks, 58 B, when it landed; space plan B-7 took fmt_menu_text out to
; disk.rom on 2026-10-04 -- four blocks, 41 B, now.)
; Same rules as the $0160 block: absolute `ld` readers only. `rn_in` became an
; equ alias of in_msg in basic/program.asm (both were " in ",0).
; rn_undefined -- MOVED to island 2 (D-CTRLKEYS, 2026-10-05): island 1 lost
; 23 B to the CTRL arm in C-BIOS's key_ascii. Same readers, same rules.
; fmt_menu_text WAS here (D-ISLDATA2) until space plan B-7 (C6-FORMAT,
; 2026-10-04) moved CALL FORMAT's menu into disk.rom's hk_format, text and all.
tkf_ref32767:
                db      3,2,7,6,7           ; signed 16-bit ceiling
tkf_ref65535:
                db      6,5,5,3,5           ; unsigned 16-bit ceiling
tkf_ref32768:
                db      3,2,7,6,8           ; negative magnitude ceiling (-32768)
in_msg:         db      " in ",0
brk_msg:        db      "Break",0           ; repack: " in " moved into print_in_lineno

    IF $ > $1BBF
                db      ISLAND_BEFORE_FONT_OVERRAN_1BBF__IT_WOULD_OVERWRITE_THE_FONT
    ENDIF

; --- island 2: before C-BIOS's internal jump table ($0160..$01FF, 160 B) -----
                org     $0160

; chrgtr -- RST 10h, the PUBLISHED MSX BIOS CHRGTR (MAKING ROOM lever A, Joost
; 2026-09-25 "B first, then A"; docs: the MSX2 Technical Handbook's BIOS table).
; Contract: calls H.CHRG, then INC HL and skips spaces; A = the character at HL;
; Z set at end of statement (00 or ':'); CF set on a digit '0'..'9'; else NZ/NC.
; 🔴 C-BIOS's own routine behind $0010 is NOT this contract: it reads (HL) and
; THEN increments, returning HL PAST the character. Ours is the published one,
; and it is also exactly zerobas's `inc_skip` plus the flags -- so the 50 internal
; `call inc_skip` sites (none reads Z/C before setting them; scratchpad/
; rst_scout.py) become 1-byte `rst $10`, and USR machine code gets a real CHRGTR.
chrgtr:
                call    H_CHRG              ; the published hook (a RET by default)
cgt_lp:
                inc     hl
                ld      a,(hl)
                cp      ' '
                jr      z,cgt_lp
                cp      ':'                 ; end of statement -> Z
                ret     z
                or      a                   ; end of line -> Z (and NC)
                ret     z
                cp      '0'
                jr      c,cgt_nd
                cp      '9'+1               ; a digit -> CF
                ret     c
cgt_nd:
                or      a                   ; anything else: NZ, NC
                ret

; outdo -- RST 18h, the PUBLISHED MSX BIOS OUTDO (MAKING ROOM lever A, step 3).
; Contract: calls H.OUTD, then outputs A to the CURRENT output channel; every
; register preserved. zerobas's `pchar` already IS that (screen, file, LPT:,
; CRT: or CAS: by PRDEST/PRDEV, all four pairs and the flags kept), so the 13
; `call pchar` sites become 1-byte `rst $18`.
; 🔴 C-BIOS's own $0018 only calls H.OUTD, and its boot points H.OUTD at
; `chput` -- the hook IS its output. Calling the hook AND pchar would print every
; character twice, so the merge also patches C-BIOS's boot to leave H.OUTD a
; RET (`ld a,$c3` -> `ld a,$c9` at $1037, below), as on the published machine.
; A is saved around the hook as C-BIOS saves it: a hook may clobber it.
outdo:
                push    af
                call    H_OUTD              ; the published hook (a RET by default)
                pop     af
                jp      pchar

; ttypos_col -- TTYPOS as the reference keeps it (D-ADDR29 N set, 2026-09-25).
; C-BIOS's CHPUT ends `ld a,(CSRX) / ld (TTYPOS),a`, a 1-BASED cursor mirror;
; the VG-8020's TTYPOS is BASIC's 0-BASED print column (scratchpad/
; nset_probe.py: PRINT"ABC"; -> 3 there, 4 here). The merge replaces only the
; `ld a,(CSRX)` at $11CF with a call to this, and C-BIOS's own store that
; follows it writes the corrected A. chput_exit pops AF, so flags are free.
ttypos_col:
                ld      a,(CSRX)
                dec     a
                ret

; --- D-ISLDATA2 (2026-10-03): six more pure-DATA blocks, 61 B, to the brim --
; Each is read by exactly the absolute `ld hl/de,<label>` sites its source file
; still carries; none is a `jr` target, none is fallen into, nothing in sub/ or
; disk/ names any of them, and no test decodes them by image offset. Order here
; is free. The `IF $ > $0200` guard below is what refuses an overrun.
; The precedence table: LOOSEST first, `db token, dw leaf`, $00-terminated.
; EQV sits looser than XOR only because something had to; the two are measurably
; indistinguishable (see the header), so this is a free choice, not a claim.
logtab:
                db      IMP_TOKEN
                dw      lg_imp
                db      EQV_TOKEN
                dw      lg_eqv
                db      XOR_TOKEN
                dw      lg_xor
                db      OR_TOKEN
                dw      lg_or
                db      AND_TOKEN
                dw      lg_and
                db      0                   ; terminator -> drop to ev_not
; The single-numeric-argument $FF selectors, for the cpir set test above. Order is
; free. Repack-only, like the scan that reads it.
ev_ff_argtab:
                db      PEEK_TOKEN          ; $97
                db      VPEEK_TOKEN         ; $98
                db      INP_TOKEN           ; $90
                db      EOF_TOKEN           ; $AB
                db      LOF_TOKEN           ; $AD
                db      LOC_TOKEN           ; $AC  (D-LOC)
                db      DSKF_TOKEN          ; $A6
                db      POS_TOKEN           ; $91  (cursor cluster; arg DISCARDED)
                db      LPOS_TOKEN          ; $9C  (D-LPTVERB; arg DISCARDED too)
    IF I1_RESIDENT
                db      STICK_TOKEN         ; $A2  (input devices, slice I1)
                db      STRIG_TOKEN         ; $A3
    ENDIF
    IF I2_RESIDENT
                db      PDL_TOKEN           ; $A4  (input devices, slice I2)
                db      PAD_TOKEN           ; $A5
    ENDIF
ev_ff_argtab_len equ    $ - ev_ff_argtab
; --- evmc_total_tab: <selector token>, <low byte of the sub-ROM entry> ------
; The five rows carry what used to be five stub headers. All are COMPUTE-ONLY
; tenants (they leave FAC correct but touch neither FACTYP nor DE), so
; evmc_dispatch does the shared FACTYP:=8 + flt_to_int16 refresh for all of them.
evmc_total_tab:
                db      ATN_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_ATN) & $FF
                db      SIN_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SIN) & $FF
                db      COS_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_COS) & $FF
                db      TAN_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_TAN) & $FF
                ; RND's argument VALUE is read by fp_rnd itself (ignored when
                ; positive, consumed as mant14 when negative) -- nothing here
                ; interprets it, so RND collapses with the other four.
                db      RND_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_RND) & $FF
; --- autoexec_name: the upcased 11-byte 8.3 name we probe for on cold start ---
; "AUTOEXEC" (8) + "BAS" (3) = exactly 11 non-space characters -- no padding
; needed (see disk/docs/autoexec-bas-spec.md §3 point 2).
autoexec_name:  db      "AUTOEXECBAS"
fmt_name:       db      "FORMAT"
prompt_text:
                db      "ZB",13,10,0
; rn_undefined -- from island 1 (D-CTRLKEYS, 2026-10-05): pure data, absolute
; `ld` readers only, exactly as in its D-ISLDATA2 home.
rn_undefined:   db      "Undefined line ",0

    IF $ > $0200
                db      ISLAND_BEFORE_JUMPTABLE_OVERRAN_0200__IT_WOULD_OVERWRITE_CBIOS
    ENDIF

; --- islands 3 and 4: C-BIOS gap 1 around the tape bodies (space plan A3) ------
; C-BIOS src/main.asm:631 pads `ds $0D01 - $` from the end of debug.asm up to its
; pinned compat ISR-exit tail at $0D01 ("Hacker" jumps to $0D02, Star Force calls
; $0D0E). zerobas's tape bodies take $09EE..tape_end of that run; what is left is
; $09D9..$09ED (21 B, island 3) and $0CC9..$0D00 (56 B, island 4).
; ⚠️ That pad is C-BIOS's deliberate "wrong jumper" slide (src/main.asm:631-633,
; "put RET instruction there"): a stray jump into $0CC9..$0D00 used to slide to
; the RET at $0D01. With island 4 filled, only the bytes after the table still
; slide. No published contract names those addresses; recorded here, not hidden.
; Both islands hold DATA only (read by an absolute `ld hl,<label>` in main page 1,
; never by a page-0 tenant), and tools/build_mainrom.py now REFUSES a tape image
; ending past island 4's start -- the non-zero-overlap check alone would let a
; growing tape silently replace a table's $00 bytes.
; (Space plan A3, docs/plan-main-rom-space-2026-10.md: C2-GAP1's islands, DT-2's
; tables -- DT-2 no longer fit islands 1/2 once A2/DT-3 had filled them.)
                org     $09D9
fperr_to_err:
                db      6                   ; FPERR 1: overflow (err_overflow, program.asm's
                                            ; own string, dl_overflow -- REUSED byte-for-byte)
                db      11                  ; FPERR 2: division by zero (err_fp_divzero)
                db      5                   ; FPERR 3: illegal function call -- math pack
                                            ; slice 1b SQR(x<0)/LOG, and the deferred
                                            ; ASC domain check (ev_f_ifc). A REAL ENTRY
                                            ; since D-MSGEXACT: it was a `db 0` placeholder
                                            ; while FPERR=3 was intercepted upstream to get
                                            ; a LOWERCASE message. Same ERR 5, same string
                                            ; as FPERR=8 now -- knife K3 cuts this slot.
                db      2                   ; FPERR 4: syntax error (D-F2-3 empty
                                            ; parenthesised/argument expression; reuses
                                            ; stmt_error's own ERR-2 table entry)
                db      9                   ; FPERR 5: subscript out of range -- arrays
                                            ; slice-1 (§4.1 #3/#8): index out of range, or
                                            ; wrong dimension count
                db      7                   ; FPERR 6: out of memory (DIM/auto-dim OOM via
                                            ; ary_errmap). A REAL ENTRY since D-MSGEXACT --
                                            ; was a `db 0` placeholder while FPERR=6 was
                                            ; intercepted upstream to get the CAPITALISED
                                            ; message; that is now the only spelling.
                db      10                  ; FPERR 7: redimensioned array -- arrays
                                            ; slice-1 (§4.1 #4): a second DIM of a live array
                db      5                   ; FPERR 8: illegal function call -- arrays
                                            ; slice-1 (§4.1 #9): negative subscript; arrays'
                                            ; OWN reference-verbatim capitalised
                                            ; "Illegal function call" (basic/arrays.asm
                                            ; err_illegal_fn_arr; §9.5 pins the array error
                                            ; surface oracle-exact, unlike the lowercase
                                            ; shared FPERR=3 SQR/LOG keep) -- ERR-5's table
                                            ; entry still points at THAT string, not FPERR=3's
                db      16                  ; FPERR 9: string formula too complex -- arrays
                                            ; slice-4a (docs/spec-basic-arrays-slice4a-
                                            ; string-heap.md §6/§11): temp-descriptor stack
                                            ; overflow (basic/str-engine.asm err_too_complex,
                                            ; low region)
                db      13                  ; FPERR 10: type mismatch -- a string function
                                            ; given a NON-string arg (LEN(5)/ASC(5)/VAL(5));
                                            ; ev_f_tmm (expr.asm) defers this via FPERR=10.
                                            ; Same ERR-13 table entry type_mismatch_error uses.
    IF CLEARPOOL
                db      14                  ; FPERR 11 (= FPERR_STROOM, sysvars.inc):
                                            ; OUT OF STRING SPACE -- the string heap could
                                            ; not allocate, which with the D-CLP partition
                                            ; ON means the pool `CLEAR n` sized ran out.
                                            ; ⚠️ Deliberately NOT FPERR=6/ERR 7: an ARRAY
                                            ; that will not fit is out of MEMORY, and the
                                            ; probe's oos-vs-oom row pins the two apart.
                                            ; Unlike 3 and 6 this needs no special case in
                                            ; fp_runtime_error -- ERR 14 has exactly one
                                            ; message (err_out_of_str, str-engine.asm) and
                                            ; flows through the generic err_msgtab lookup.
    ENDIF
                db      24                  ; FPERR_MISSOP (sysvars.inc, D-MISSOP): MISSING
                                            ; OPERAND -- a factor was REQUIRED and the
                                            ; statement ended instead (end of line, ':', or
                                            ; a byte that cannot start one). Deferred by
                                            ; ev_f_err, expr.asm. ⚠️ THIS `db` MUST FOLLOW
                                            ; the CLEARPOOL block, not sit inside it: the
                                            ; table is DENSE and FPERR_MISSOP's value moves
                                            ; with the switch (12 with CLEARPOOL, 11
                                            ; without), which is why the equ lives beside
                                            ; FPERR_STROOM rather than being a literal.
                db      15                  ; FPERR_STRLONG (= FPERR_MISSOP+1, sysvars.inc,
                                            ; D-STRLONG): STRING TOO LONG -- a `+` fold whose
                                            ; combined length exceeds STRMAX. sh_append used
                                            ; to clamp it to 255 and return that; both
                                            ; references raise here instead. Same DENSE-table
                                            ; caveat as the entry above: this `db` must stay
                                            ; LAST, because FPERR_MISSOP moves with CLEARPOOL
                                            ; and this code is defined relative to it.

    IF $ > $09EE
                db      ISLAND3_OVERRAN_09EE__IT_WOULD_OVERWRITE_THE_TAPE_BODIES
    ENDIF

                org     $0CC9
; --- err_msgtab: MSX ERR code (1..25) -> message string (docs/spec-basic- --
; error-handling-s2a-packet.md §2/(a)). Every code's message is stored ONCE
; (this table replaces the old FPERR-indexed fre_msgtab AND every direct
; site's own `ld hl,msg`); holes (12/14/15/18/19/20/21/22 -- not yet raised by
; any S2a site) point at the code-23 "unprintable error" string, same as an
; out-of-table `ERROR n` argument (raise_error, above). The capitalised
; arrays-arc strings (err_subscript/err_redim/err_mem_arr/err_illegal_fn_arr)
; stay separate from the lowercase shared strings, unmerged (spec-basic-
; arrays §9.5) -- their codes (9/10/7/5) just index this table at their own
; entries, same string, no new copy.
err_msgtab:
                dw      err_subhosted       ; 1: next without for
                dw      err_syntax          ; 2: syntax error
                dw      err_subhosted       ; 3: return without gosub
                dw      err_subhosted       ; 4: out of data
                dw      err_illegal_fn_arr  ; 5: illegal function call (arrays' own
                                            ; capitalised string; §9.5 keep)
                dw      err_subhosted       ; 6: Overflow. D-MSGMIGRATE: sub-hosted
                                            ; (em_overflow) -- and it only became
                                            ; migratable when dl_overflow's float arm
                                            ; was FIXED to store ERRFLG at all. Until
                                            ; then this code had one ERRFLG-keyed reader
                                            ; and one that was not keyed on anything.
                dw      err_mem             ; 7: out of memory (program.asm err_mem;
                                            ; err_stack aliases it -- program.asm)
                dw      err_subhosted       ; 8: undefined line number (zerobas's own
                                            ; "undefined line" wording, spec-basic-error-
                                            ; handling.md §4)
                dw      err_subscript       ; 9: subscript out of range (arrays' own
                                            ; capitalised string; §9.5 keep)
                dw      err_redim           ; 10: redimensioned array (arrays' own
                                            ; capitalised string; §9.5 keep)
                dw      err_subhosted       ; 11: division by zero
                dw      err_subhosted       ; 12: Illegal direct. D-MSGSUB: the text
                                            ; lives in the sub-ROM tenant, keyed on
                                            ; ERRFLG. Still not RAISED by any zerobas
                                            ; site -- `ERROR 12` is the only way here --
                                            ; but it no longer prints the wrong thing.
                dw      err_subhosted       ; 13: type mismatch
    IF CLEARPOOL
                dw      err_out_of_str      ; 14: out of string space (D-CLP; was a
    ELSE                                    ; hole until the pool could raise it)
                dw      err_unprintable     ; 14: out of string space (hole)
    ENDIF
                                            ; hole until the pool could raise it)
                dw      err_subhosted       ; 15: String too long (D-MSGSUB, sub-hosted;
                                            ; not raised by any zerobas site)
                dw      err_too_complex     ; 16: string formula too complex
                dw      err_subhosted       ; 17: can't continue
                dw      err_subhosted       ; 18: Undefined user function (D-MSGSUB,
                                            ; sub-hosted; not raised -- DEF FN's own
                                            ; slice would be the raiser)
                dw      err_subhosted       ; 19: Device I/O error (D-MSGSUB, sub-hosted).
                                            ; The load_error family unification that would
                                            ; RAISE it is still its own later item
                                            ; (S1 §9.1) -- this fixes the TEXT only.
                dw      err_verify          ; 20: Verify error. 🎯 D-MSGEXACT: this was a
                                            ; HOLE pointing at "unprintable error" while
                                            ; cload.asm's own err_verify -- already the
                                            ; reference's exact `Verify error`, measured
                                            ; 2026-08-02 on a real CLOAD? mismatch -- sat
                                            ; right there on a separate path. Repointing
                                            ; costs 0 B and is the whole fix: `ERROR 20`
                                            ; now says what the tape path has always said.
                dw      err_no_resume       ; 21: no resume (D-ERR21, docs/spec-basic-
                                            ; err21-no-resume.md -- was a hole until the
                                            ; run loop could raise it: falling off the
                                            ; END of the program while still owing a
                                            ; RESUME. The string and e21_no_resume both
                                            ; live in basic/arrays.asm's low region;
                                            ; this entry also gives `ERROR 21` the right
                                            ; message, which it did not have)
                dw      err_subhosted       ; 22: RESUME without error (raised by
                                            ; raise_error_forced, below)
                dw      err_unprintable     ; 23: unprintable error (self; ERROR n with
                                            ; an out-of-table code, or any hole above)
                dw      err_subhosted       ; 24: missing operand. The table used to stop
                                            ; at 23, so this code -- ALREADY raised by
                                            ; graphics.asm g8_missing and time.asm
                                            ; tm_err24 -- printed "unprintable error" on
                                            ; every site that used it. Found by LOCATE,
                                            ; which is the third: `LOCATE` bare reads
                                            ; `Missing operand` on the reference and read
                                            ; `unprintable error` here. Adding the entry
                                            ; fixes all three at once. raise_error's own
                                            ; range test moved from `cp 23` to `cp 24`
                                            ; with it -- the table bound and that test are
                                            ; one fact in two places.
                dw      err_subhosted       ; 25: line buffer overflow (D-LINEMAX R-2 --
                                            ; the crunched body exceeded TOKMAX_BODY=314).
                                            ; Same two-places-one-fact pair -- and the
                                            ; SECOND place did NOT move when this entry
                                            ; landed: `cp 24` stayed, so this entry was
                                            ; two bytes of DEAD TABLE and `ERROR 25` read
                                            ; `unprintable error` for the whole of
                                            ; D-LINEMAX. Fixed 2026-07-29 (`cp 24` ->
                                            ; `cp 25`, zero bytes). It went unnoticed
                                            ; because the ONLY raiser of 25 -- program.asm
                                            ; dl_overflow -- deliberately bypasses this
                                            ; table (see its header), so linemax-acceptance
                                            ; was green throughout. MEASURED on the
                                            ; VG-8020 before landing: `ERROR 25` ->
                                            ; `Line buffer overflow`, `ERROR 26` ->
                                            ; `Unprintable error` (so 25 IS the bound).

    IF $ > $0D01
                db      ISLAND4_OVERRAN_0D01__IT_WOULD_OVERWRITE_THE_CBIOS_COMPAT_TAIL
    ENDIF

; --- the RST 10h vector: $0010 `jp chrgtr` (was C-BIOS's `jp $10FF`) ---------
; tools/build_mainrom.py PATCH_RANGES allows exactly these 3 bytes, and only
; while the base still holds C-BIOS's `C3 FF 10`.
                org     $0010
                jp      chrgtr

; --- the RST 18h vector: $0018 `jp outdo` (was C-BIOS's `jp $111B`) ---------
                org     $0018
                jp      outdo

; --- C-BIOS's CHPUT stores CSRX-1 into TTYPOS, not CSRX -----------------------
; $11CF is C-BIOS's `ld a,(CSRX)` just before `ld (TTYPOS),a` (src/chput.asm,
; "CSRX -> TTYPOS"). PATCH_RANGES refuses unless it reads 3A DD F3.
                org     $11CF
cbios_chput_ttypos:                         ; a root: C-BIOS enters it (PATCH_ROOTS)
                call    ttypos_col

; --- C-BIOS's boot leaves H.OUTD a RET, not `jp chput` -----------------------
; $1037 is C-BIOS's `ld a,$c3` before `ld (H_OUTD),a` (src/main.asm, "set up
; hook"); only its operand byte changes. PATCH_RANGES refuses unless it is $C3.
                org     $1038
                db      $C9
