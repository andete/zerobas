; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; tapeprog.asm -- zerobas-sub2 PAGE 0: the TAPE PROGRAM READER of CLOAD, CLOAD?,
; LOAD "CAS:" and RUN "CAS:" (D-P0CB, the tape-loop slice, docs/spec-sub2-p0cb.md
; §5). Moved out of main page 1 (basic/cload.asm) on 2026-10-24: do_tape_prog's
; header dispatch, the tokenised ($D3) line loop (ctp_begin / ctp_line / ctp_len /
; ctp_body, D-LOADBASE's first-line scan ctp_scan) and its error shims, the end of
; the read (ctp_done / ctp_verify_done / ctp_oom), the store-or-compare point
; cas_put and the CLOAD? report (main's verify_error). Its callers are
; sub2/loadsave.asm's ls_cload / ls_load / ls_run, which `call` it directly.
;
; ⏱ THE LOOP IS REAL-TIME (TAPIN reads a moving tape) AND THAT IS WHY IT WAS LEFT
; IN MAIN BY SLICE C2. It moved after the TAPIN timing study (TODO, D-P0CB,
; 2026-10-24): CLOAD's byte loop has >= ~1270 T of slack per byte on the worst
; tape measured (openMSX's .cas playback; a VG-8020-written 2400-baud tape is
; more tolerant). The move spends, PER PROGRAM BYTE, exactly ONE p0cb round trip
; -- the TAPIN call -- and nothing else: the CLPTR / TXTCEIL bounds check reads
; the RAM cells here, and cas_put and tok_payload are this ROM's own copies.
;   ctp_body per byte, TAPIN's own body excluded, load mode, counted from the
;   instructions (nominal T, no M1 wait):
;     main (before)   256 T   (`call TAPIN` 17 T)
;     here            392 T   (`ld ix,TAPIN` 14 + `call p0cb` 17 + p0cb 43 +
;                              CLPRIM 79 = 153 T in place of the 17)
;   = +136 T per byte (+153 T counting the MSX's one M1 wait per opcode fetch).
;   Every other TAPIN of the read (the link word, the line number, the first
;   line's scan) pays the same +136 T; cas_put (99 T load, 104 T verify) and
;   tok_payload cost what they cost in main.
;
; 📏 STACK -- the loop runs NO deeper than it did. Counted from the statement's SP
; (S, ex_sub2's entry): this tenant runs at S-14 (scrstmt.asm's header: ex_sub2's
; call, sr_slot's push iy, C-BIOS's CALSLT frame), and a p0cb adds 6 B (its call,
; the old $A8, clprim's call). Before, ls_* p0cb'd main's do_tape_prog, so the
; loop ran at S-20 and entered TAPIN at S-24 (its `push de` / `push af` + the
; call). Now the loop runs at S-16 (the `call` from ls_*) and enters TAPIN at
; S-24 (its push + the p0cb frame): the same depth. cas_put is 4 B SHALLOWER
; (S-20, a local call); every other main routine -- cas_open_match, TAPION,
; TAPIOF, print_msg, and the tails cas_ascii_load / load_commit_prog / dpl_oom /
; dpl_err, which are `jp p0cb` and reuse this routine's own return address --
; runs at exactly the depth it had.
;
; WHAT STAYS IN MAIN, and is reached through p0cb:
;   TAPION / TAPIN / TAPIOF   the BIOS, by its fixed jump-table address.
;   cas_open_match    the header search (OPEN "CAS:", MERGE "CAS:" call it too).
;   cas_ascii_load    an $EA program: new_prog, then the ASCII reader
;                     (ascii_read_lines / store_line) -- long, and it stays in
;                     main so that work does not run under extra frames here.
;   load_commit_prog  the commit (relink, H.STKE), shared with the disk LOAD.
;   dpl_dio / dpl_err / dpl_oom   the failure exits, shared with the disk LOAD.
;   print_msg + err_verify   the message decoder, and the text err_msgtab[20]
;                     names (basic/missing.asm), so it cannot leave main.
;
; --- THE CF-OUT CONTRACT (D-CASTAIL, docs/spec-basic-castail.md §3.2) ---------
;   out: CF set = the load FAILED and has ALREADY reported; CF clear = loaded.
; ls_load / ls_run then return bp_ret (run NOTHING: both references print their
; message and stop); ls_cload returns either way, the line ends.
; A TAPE BIOS failure (the search, TAPION, TAPIN: an I/O error or Ctrl-STOP)
; RAISES 19 (dpl_dio, D-CASBRK) -- through p0cb it never returns, as the main
; `jp` it replaces never returned, and raise_error's SP reset discards this
; ROM's frames. The CONTENT faults (an unknown file id, CLOAD? of an $EA file)
; stay on dpl_err's printed `load error`.
; ⚠️ COVERAGE: only the search exit is scored by a row (the Ctrl-STOP abort); the
; tokenised exits are unreachable from every row in the battery (castail).
;
; TAPIN trashes every register, so the state lives in RAM (CLPTR, CLINK) and a
; count crosses a TAPIN on the stack, as it did in main.
do_tape_prog:
                ld      ix,p0_cas_open_match
                call    p0cb                ; find the (named) file; header consumed
                jp      c,fs_dio            ; tape error / Ctrl-STOP abort: 19 (D-CASBRK)
                ld      a,(CAS_HDRID)
                cp      BASIC_ID            ; tokenised BASIC -> the store/compare loop
                jr      z,ctp_data_tokenised
                cp      ASCII_ID            ; ASCII program -> cas_ascii_load
                jr      nz,ctp_bad_file     ; neither id -> unrecognised file
                ; $EA ASCII: CLOAD? verify is tokenised-only (spec §B) -> reject
                ld      a,(CAS_VERIFY)
                or      a
                jr      nz,ctp_bad_file
                ld      ix,p0_cas_ascii_load
                jp      p0cb                ; its CF is this routine's (a tail)
ctp_bad_file:                               ; main's `jp nz,dpl_err`: `load error`,
                ld      ix,p0_dpl_err       ; printed, CF set
                jp      p0cb
ctp_data_tokenised:
                ; --- data block: skip its leader tone -----------------------
                ; Like BLOAD, the program data is a SEPARATE tape block, so it
                ; needs its own TAPION to re-lock onto the data block's leader.
                ld      ix,TAPION
                call    p0cb
                jp      c,fs_dio            ; D-CASTAIL CF contract -> 19 (D-CASBRK)

                ; --- start a fresh program: store cursor at the text base ---
ctp_begin:                                  ; (tests/test_loadbase.py enters here,
                                            ;  through tests/msxtest.py's sub2 bridge)
                ld      hl,(TXTTAB)         ; D-TXTTAB: at the base as it stands
                ld      (CLPTR),hl
                ld      hl,0                ; 🔴 D-LOADBASE: A_0, the SAVING machine's
                ld      (CLINK),hl          ; text base, is NOT known -- it was assumed
                                            ; to be ours ($8001), and a program SAVEd
                                            ; with TXTTAB at $C001 loaded as garbage
                                            ; (scratchpad/txttab_saveload.out). 0 marks
                                            ; the first line, which is scanned instead

                ; --- read the program image, stopping at the $0000 end-link --
                ; The device half does NOT signal a clean end of data: once the
                ; tape block's bytes run out, TAPIN blocks on silence rather than
                ; returning CF. So we must stop reading EXACTLY when the program
                ; ends — at the $0000 link word that terminates the line-link
                ; chain — never reading a byte past it.
                ;
                ; LENGTH-DRIVEN copy. A token body legitimately contains $00 bytes
                ; (e.g. INT2 `$1C lo hi`, &H `$0C lo hi`, line-number refs), so the
                ; first $00 is NOT the line boundary. The boundary is defined by the
                ; saved link words: each link is the saving machine's absolute
                ; address of the NEXT line, so this line's full length is
                ; (this link) - (previous link) and its body length is that minus the
                ; 4-byte link+lineno header. We copy EXACTLY that many body bytes —
                ; embedded $00s included — landing precisely on the next link word.
                ;
                ; Per line: read the 2-byte link word; $0000 -> end of program.
                ; Otherwise store link word + 2-byte line number verbatim, then copy
                ; the computed body byte count. The saved links are stored as-is;
                ; relink (token-aware, in load_commit_prog) recomputes them.
ctp_line:
                ld      ix,TAPIN
                call    p0cb                ; link low
                jp      c,fs_dio            ; D-CASTAIL CF contract -> 19 (D-CASBRK)
                push    af                  ; preserve link-low: TAPIN clobbers C
                ld      ix,TAPIN
                call    p0cb                ; link high
                jr      c,ctp_link_err      ; must pop before leaving
                ld      b,a                 ; B = link high
                pop     af
                ld      c,a                 ; C = link low (restored)
                                            ; BC = saved link word L_n = A_{n+1}
                ld      a,b
                or      c
                jp      z,ctp_done          ; $0000 link -> program complete (jp:
                                            ; ctp_scan sits between, D-LOADBASE)

                ; body length = L_n - A_n - 4   (A_n = CLINK = previous link word)
                ld      hl,(CLINK)          ; HL = A_n
                ld      (CLINK),bc          ; advance CLINK = L_n for the next line
                ld      a,h                 ; D-LOADBASE: A_n = 0 is the first line,
                or      l                   ; whose length the links cannot give --
                ld      de,$FFFF            ; DE = $FFFF: scan it (flags kept)
                jr      z,ctp_len
                ld      a,c
                sub     l
                ld      e,a
                ld      a,b
                sbc     a,h
                ld      d,a                 ; DE = L_n - A_n = full line length
                dec     de
                dec     de
                dec     de
                dec     de                  ; DE = body length (incl. its $00 term)

                ; bounds: this line's header (>=4 bytes) must fit below TXTMAX
ctp_len:
                push    de                  ; guard body length across TAPIN/stores
                ld      hl,(CLPTR)
                ld      de,(TXTCEIL)        ; D-RAMCEIL: boot's ceiling, less the
                dec     de                  ;  4-byte header
                dec     de
                dec     de
                dec     de
                or      a
                sbc     hl,de
                jr      nc,ctp_oom_pop

                ; store (load) OR compare (CLOAD? verify) the saved link word via
                ; cas_put — one mode-flagged emit point (relink fixes links later).
                ld      a,c
                call    cas_put
                ld      a,b
                call    cas_put

                ; line number (2 bytes)
                ld      ix,TAPIN
                call    p0cb
                jr      c,ctp_err_pop
                call    cas_put
                ld      ix,TAPIN
                call    p0cb
                jr      c,ctp_err_pop
                call    cas_put
                pop     de                  ; DE = body length
                ld      a,d                 ; D-LOADBASE: $FFFF -> the first line,
                and     e                   ; copied up to its own $00
                inc     a
                jr      z,ctp_scan

                ; token body: copy EXACTLY DE bytes (embedded $00s and all). The
                ; per-byte path: ONE p0cb (the TAPIN), everything else local.
ctp_body:
                ld      a,d
                or      e
                jr      z,ctp_line          ; whole body copied -> next line
                push    de                  ; guard remaining count across TAPIN
                ld      hl,(CLPTR)          ; bounds check
                ld      de,(TXTCEIL)        ; D-RAMCEIL: boot's ceiling
                or      a
                sbc     hl,de
                jr      nc,ctp_oom_pop
                ld      ix,TAPIN
                call    p0cb
                jr      c,ctp_err_pop
                call    cas_put             ; store or compare the body byte
                pop     de                  ; DE = remaining count
                dec     de
                jr      ctp_body

; ctp_link_err — the second TAPIN (link high) failed with CF; AF (link-low) is on
; the stack from the push before that call.  Pop it to restore balance, then error.
ctp_link_err:
                pop     af
                jp      fs_dio              ; D-CASTAIL CF contract -> 19 (D-CASBRK)

; ctp_err_pop / ctp_oom_pop — body length / remaining count is on the stack; drop
; it before taking the shared error / out-of-memory path so the stack stays balanced.
ctp_err_pop:
                pop     de
                jp      fs_dio              ; D-CASTAIL CF contract -> 19 (D-CASBRK)
ctp_oom_pop:
                pop     de
                jr      ctp_oom

; ctp_scan -- D-LOADBASE: copy the first line's body up to its $00, passing over
; the bytes of each constant (tok_payload: a constant may hold $00), then go on
; by link deltas from CLINK = L_1. Same bounds check and errors as ctp_body.
ctp_scan:
                ld      e,0                 ; E = constant bytes still to pass
ctps_lp:
                push    de
                ld      hl,(CLPTR)          ; bounds check (as ctp_body)
                ld      de,(TXTCEIL)
                or      a
                sbc     hl,de
                jr      nc,ctp_oom_pop
                ld      ix,TAPIN
                call    p0cb
                jr      c,ctp_err_pop
                pop     de
                ld      d,a                 ; D = the byte (cas_put keeps D, E)
                call    cas_put
                ld      a,e
                or      a
                jr      z,ctps_tok
                dec     e                   ; inside a constant: any byte, $00 too
                jr      ctps_lp
ctps_tok:
                or      d                   ; A = the byte
                jp      z,ctp_line          ; its $00: the first line is done
                call    tok_payload         ; A = its constant's length (C clobbered)
                ld      e,a
                jr      ctps_lp

ctp_done:
                ld      ix,TAPIOF
                call    p0cb                ; motor off (program fully read)
                ld      a,(CAS_VERIFY)
                or      a
                jr      nz,ctp_verify_done  ; CLOAD? -> report, do NOT mutate memory
                ; the commit (end marker, PRGEND, relink, H.STKE): main's
                ; load_commit_prog, shared with the disk LOAD (dpl_done). CF clear.
                ld      ix,p0_load_commit_prog
                jp      p0cb

; --- ctp_verify_done: CLOAD? end-of-tape -> report Ok / Verify error ----------
; Verify is NON-DESTRUCTIVE: no marker, no PRGEND, no relink — CAS_VMIS holds the
; verdict. A clean CAS_VMIS = identical (silent Ok); otherwise "Verify error".
; Any real difference (including nearly all length changes — the saved link words
; are absolute addresses, so a different program layout differs byte-for-byte and
; trips CAS_VMIS during the body compare) is caught. The one gap is a tape that is
; an EXACT PREFIX of a longer in-memory program (all compared bytes equal, tape
; ends early); that is outside the verify use case (confirming a same-length
; CSAVE round-trip) and is a documented limitation (spec §B).
ctp_verify_done:
                ld      a,(CAS_VMIS)
                or      a
                ret     z                   ; no difference -> Ok (memory intact)
                ; FALL THROUGH: a byte differed -> "Verify error"
; ctp_verify_error -- main's verify_error: report a CLOAD? mismatch (memory left
; untouched). Its two callers are both here, so the `scf` reaches no one else's
; carry. The text stays main's (err_verify, which err_msgtab[20] names too).
ctp_verify_error:
                ld      hl,p0_err_verify
                ld      ix,p0_print_msg
                call    p0cb                ; D-MSGENC
                scf                         ; a mismatch is a FAILED load: CF out
                ret                         ; (docs/spec-basic-castail.md §3.2)

ctp_oom:
                ld      ix,TAPIOF
                call    p0cb                ; stop the motor before reporting
                ld      a,(CAS_VERIFY)
                or      a
                jr      nz,ctp_verify_error ; CLOAD? overrun = mismatch, do NOT wipe
                ; D-OOMTAIL: dpl_oom IS this exit's contract -- CF=1, an empty
                ; program, "Out of memory" -- shared with the disk LOAD on purpose
                ; (they are filed as mirrors, so an edit to one is an edit to both).
                ld      ix,p0_dpl_oom
                jp      p0cb

; --- cas_put: store-or-compare one program byte at CLPTR, advance CLPTR --------
; The single mode-flagged emit point of the tokenised tape reader (spec §B).
; CAS_VERIFY=0 (a real CLOAD/LOAD"CAS:"/RUN"CAS:") -> store A at CLPTR (plain
; load). CAS_VERIFY=1 (CLOAD?) -> COMPARE A against the in-memory program byte at
; CLPTR and set the sticky CAS_VMIS on any difference, WITHOUT writing (verify is
; non-destructive). CLPTR advances TXTBASE.. either way, so in verify mode it is
; exactly the in-memory comparand cursor. The program area is RAM (pages 2-3),
; mapped while this page-0 tenant runs, so no crossing is needed here.
;   in: A = the program byte just read from tape.
; Preserves B, DE; clobbers A, C, HL (BC is dead at every call site — the link
; bytes are stored before the next TAPIN, and TAPIN then trashes BC anyway).
cas_put:
                ld      c,a                 ; C = the byte
                ld      hl,(CLPTR)
                ld      a,(CAS_VERIFY)
                or      a
                ld      a,c                 ; A = the byte back
                jr      nz,cput_cmp
                ld      (hl),a              ; load mode: store the byte
                jr      cput_adv
cput_cmp:
                cp      (hl)                ; verify: compare vs the in-memory byte
                jr      z,cput_adv
                ld      a,1
                ld      (CAS_VMIS),a        ; mismatch -> sticky
cput_adv:
                inc     hl
                ld      (CLPTR),hl
                ret

                include "basic/tokpay-body.inc"   ; tok_payload (D-LOADBASE): this
                                                  ; ROM's own copy, the fourth
