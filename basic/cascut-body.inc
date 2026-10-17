; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; cascut-body.inc -- cas_capture_cut / cas_name_cut (D-CASDOT, 2026-10-17), shared
; by main (basic/main.asm, the end of the low region) and the sub-ROM BLOAD tenant
; (sub/bload.asm), like cascap-body.inc beside it: one source text, two copies.
;
; A '.' ENDS THE NAME OF A `dev:name` FILE SPEC. Measured on the VG-8020 with our
; own tapes (scratchpad/casname_probe.py -> casname_run5*.out, and
; probes/basic/basic_probe_cassave.py rows sav-cas-dot / bsv-cas-dot / csave-dot):
;   BLOAD "CAS:ABCD.EF"  finds a header "ABCD", and SKIPS a header "ABCD.E";
;   BLOAD "AB.C" (bare, diskless), OPEN "CAS:AB.C", RUN "CAS:AB.C"  find "AB";
;   SAVE "CAS:PD.X" / BSAVE "CAS:PF.X"  write the header names "PD" / "PF";
;   "CAS:ABCDEFGH.IJ"  is "ABCDEF" (the first six of the name part);
;   "CAS:.AB"  is `Bad file name` (56), before the tape moves;
;   CLOAD "AB.C" / CSAVE "PE.XY"  keep the dot: their name is raw, and they do
;   not come here.
; Harry Fox's loader asks for such a name: zerobas searched for the dotted one
; and skipped every file to the tape's end (D-TAPELOAD class B2).
; Clean-room: our own code; the rule is the black-box readings above.

; --- cas_capture_cut: cas_capture_name, then the cut -------------------------
; Same contract as cas_capture_name (HL on the closing '"').
cas_capture_cut:
                call    cas_capture_name

; --- cas_name_cut: blank CAS_WANT from its first '.' on ----------------------
; CAS_WANT is FILNAM's six name bytes (TSV_NAME too, D-TSVOVL). A '.' first is
; ERR 56. Preserves HL; clobbers A, B.
cas_name_cut:
                ld      a,(CAS_WANT)
                cp      '.'
    IF SUB_BUILD
                jr      z,cnc_bad           ; nothing before the '.': 56 (below)
    ELSE
                jp      z,pdf_badname       ; nothing before the '.': 56 (raise_error
                                            ; resets SP, so the depth does not matter)
    ENDIF
                push    hl
                ld      hl,CAS_WANT
                ld      b,6
cnc_find:
                ld      a,(hl)
                cp      '.'
                jr      z,cnc_fill
                inc     hl
                djnz    cnc_find
                pop     hl
                ret
cnc_fill:
                ld      (hl),' '            ; the '.' and the extension -> spaces
                inc     hl
                djnz    cnc_fill
                pop     hl
                ret
    IF SUB_BUILD
; The BLOAD tenant cannot raise: an error is a code in BL_STAT, which the resident
; stub raises (basic/bload.asm), and the arm returns from do_bload -- the shape of
; bl_tape_dio. Its only caller is do_bload's `call cas_capture_cut` (cas_capture_
; name has returned, the test above runs before the push, and do_bload holds
; nothing pushed there), so the word on top is the return address INTO do_bload:
; drop it, and this `ret` takes do_bload's own return. (sub/bload.asm's
; pdf_badname is bl_load_error, a `load error` that RETURNS -- jumped to from in
; here it would return into the search.)
cnc_bad:
                pop     af                  ; the return into do_bload -> discarded
                ld      a,56                ; Bad file name
                ld      (BL_STAT),a
                ret                         ; out of do_bload, as bl_tape_dio does
    ENDIF
