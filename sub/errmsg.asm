; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — errmsg.asm  (sub-hosted error-message tenant, D-MSGSUB)
; ===========================================================================
; The fourteen MSX ERR codes zerobas never RAISES but must still be able to
; PRINT -- reachable only through `ERROR n`, and worth ~227 B against a main
; page 1 that has tens. docs/spec-basic-msgsub.md.
;
; PAGE 1, not page 0, and the reason is the same one title_tenant records: the
; only outward edge is CHPUT, which is page-0 BIOS. A page-1 tenant keeps page 0
; mapped and can call it; a page-0 tenant would have the BIOS switched out from
; under it. The alternative -- calling main's own printer -- is IMPOSSIBLE from
; either page: print_string ($4673) and print_msg ($7717) are main PAGE 1, which
; is exactly what a page-1 CALSLT switches out, and check_tenant_closure --page1
; enforces that. So duplicating the emitter here is contract-forced, not a
; convenience (the same class as the standing 473 B duplication).
;
; NO MARSHALLING. The one input is ERRFLG ($F414), which raise_error has already
; written before any message resolves, and which is page-3 RAM and therefore
; visible from either island. Nothing rides in a register: `A` is NOT preserved
; across CALSLT (basic/float-arith.asm, the SQR/ATN/EXP/LOG lesson) and
; subrom_call's own CF means "sub-ROM absent", never a tenant result. That is
; also WHY this tenant must print something for EVERY input -- it has no way to
; say "not my code" -- so an unlisted code gets em_unprintable here rather than
; a status byte and a main-side fallback.
;
; 🎯 PLAIN STRINGS, NOT PHRASE-ENCODED, AND THAT IS A DECISION (spec §3.3).
; D-MSGENC measured the decoder at 44 B and msg_phrase_tab at 40 B. Duplicating
; both here would buy back roughly 20 B of literal text out of a 3 KB budget AND
; create a SECOND phrase table that a future edit to main's could silently
; desynchronise -- a drift that would corrupt message text with nothing pointing
; at the cause. Plain text costs ~14 B of emitter and cannot drift at all. The
; "duplicated print code" the sign-off approved is the nine-instruction loop at
; em_lp.
;
; ⚠️ THE TEXT IS MEASURED, NOT TRANSCRIBED. Every string below is the verbatim
; reading from docs/msgexact-msx1-characterization.md §1/§2, taken off the two
; reference machines with `ERROR n` on 2026-08-02 -- never copied from a
; published MSX-BASIC language reference, which that slice PROVED unreliable
; about exactly this (the reference table says ERR 17 is `Can't continue`; the
; machines say `Can't CONTINUE`).
;
; CLEAN-ROOM: original code. The strings are black-box readings of a running
; machine's screen, the same instrument every characterization in this tree
; uses; no reference ROM is disassembled or byte-copied. CHPUT is a published
; BIOS entry. See sub/PROVENANCE.md.
; ===========================================================================

; --- errmsg_tenant: the SUBROM_IDX_ERRMSG entry ----------------------------
; in:  ERRFLG = the MSX ERR code (1..255). No register arguments.
; out: the message body emitted through CHPUT. No CRLF and no " in <line>" --
;      main keeps both (fre_abort_low picks print_msg vs print_msg_stopcr, and
;      print_in_lineno appends the suffix), so this tenant is the BODY only,
;      exactly like print_msg_stopcr is main-side.
; Clobbers everything; CALSLT does anyway.
errmsg_tenant:
                ld      a,(ERRFLG)
                ld      hl,em_table
                ld      b,EM_ROWS
em_scan:
                cp      (hl)                ; row code -- sets Z on a hit
                inc     hl                  ; ⚠️ INC rr and LD r,(HL) do NOT touch
                ld      e,(hl)              ;    the Z flag (documented Z80), so the
                inc     hl                  ;    `jr z` below still reads the CP.
                ld      d,(hl)              ;    Advancing FIRST is what lets one
                inc     hl                  ;    walk both find and step.
                jr      z,em_print
                djnz    em_scan
                ld      de,em_unprintable   ; not one of ours -- 26..49, 65..255, and
                                            ; anything else main routes here. It
                                            ; CANNOT decline (see the header), so it
                                            ; answers with the out-of-table text.
em_print:
                ex      de,hl
em_lp:
                ld      a,(hl)
                inc     hl
                or      a
                ret     z
                push    hl                  ; guard the walk across the BIOS call
                call    CHPUT
                pop     hl
                jr      em_lp

; --- em_table: ERR code -> message. Walked linearly, EM_ROWS rows of 3 B -----
; Order is the numeric one purely for readability -- the scan is linear, so it
; carries no meaning and nothing may depend on it.
; ⚠️ EM_ROWS and this table are ONE FACT IN TWO PLACES. err_msgtab's own bound
; drifted from its table exactly this way and left ERR 25 dead for a whole arc
; (basic/interp.asm). tests/test_msgsub.py re-derives the count from the ROM and
; fails if the two disagree.
em_table:
                db      12
                dw      em_ill_direct
                db      15
                dw      em_str_too_long
                db      18
                dw      em_undef_fn
                db      19
                dw      em_device_io
                db      50
                dw      em_field_ovf
                db      51
                dw      em_internal
                db      53
                dw      em_file_notfound
                db      54
                dw      em_file_open
                db      56
                dw      em_bad_filename
                db      57
                dw      em_direct_stmt
                db      60
                dw      em_bad_fat
                db      62
                dw      em_bad_drive
                db      63
                dw      em_bad_sector
                db      64
                dw      em_file_still_open
EM_ROWS         equ     14

; The dense-range four (main's err_msgtab entries 12/15/18/19 point at
; err_subhosted for these). Both references agree on all four.
em_ill_direct:      db  "Illegal direct",0              ; ERR 12
em_str_too_long:    db  "String too long",0             ; ERR 15
em_undef_fn:        db  "Undefined user function",0     ; ERR 18
em_device_io:       db  "Device I/O error",0            ; ERR 19

; The sparse disk range. 50..59 are MAIN-BASIC messages on a real MSX1 -- the
; diskless VG-8020 answers them too, which is the measured correction to the
; "everything above 50 is the disk ROM" assumption (characterization §2). So
; 50/51/53/54/56/57 are two-reference values.
em_field_ovf:       db  "FIELD overflow",0              ; ERR 50
em_internal:        db  "Internal error",0              ; ERR 51
em_file_notfound:   db  "File not found",0              ; ERR 53
em_file_open:       db  "File already open",0           ; ERR 54
em_bad_filename:    db  "Bad file name",0               ; ERR 56
em_direct_stmt:     db  "Direct statement in file",0    ; ERR 57

; 60..64 are the DISK ROM's own, so the CF-3300 is the sole oracle: the VG-8020
; prints `Unprintable error` for all five. zerobas ships Disk BASIC in the main
; ROM and is a disk machine, so it answers as the disk reference does -- signed
; off 2026-08-02 (spec §9 Q3) as the one place this slice makes zerobas differ
; from a reference on purpose. (61 `Bad file mode` is NOT here: zerobas RAISES
; it, so it is main-resident in basic/missing.asm's rerr_sparse2 arm.)
em_bad_fat:         db  "Bad FAT",0                     ; ERR 60
em_bad_drive:       db  "Bad drive name",0              ; ERR 62
em_bad_sector:      db  "Bad sector number",0           ; ERR 63
em_file_still_open: db  "File still open",0             ; ERR 64

; The fallback, for every code main routes here that is not in the table above:
; 26..49 and 65..255. Main has its OWN copy of this text (err_unprintable, which
; ERR 23's dense entry still points at directly) -- the duplication is what buys
; the whole out-of-dense range a single main-side mechanism at ZERO page-1 bytes
; (rerr_unprintable just loads a different pointer). ERR 26 is the standing gate
; control that rides it.
em_unprintable:     db  "Unprintable error",0
