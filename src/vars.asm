; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; vars.asm — integer variable store (multi-character names).
;
; Each variable is a 16-bit integer held in a dynamically-allocated table of
; 4-byte entries: [name0][name1][value:2]. Names are significant to two
; characters (public MSX-BASIC language reference): `name0` is the first letter,
; `name1` the second name char (letter or digit) or 0 for a single-char name.
; Any 3rd+ name characters and a trailing type-suffix (`% ! # $`) are consumed
; but ignored, so e.g. `SCORE`, `SC` and `SCX` all map to key (`S`,`C`). A name0
; of 0 marks the first free slot; lookup of an unset variable yields 0 (MSX
; auto-initialises numerics to 0).
;
; Phase 1 grew this from the single-letter A..Z store. zerobas is still
; integer-only: there are no string variables, arrays, or floats yet.
;
; Clean-room: original code. Variable *semantics* (a named 16-bit cell, 2
; significant characters, default 0) follow the public MSX-BASIC language
; reference; the table layout is our own choice (see PROVENANCE.md). No
; disassembly.

; --- is_ident_cont: CF set if A is an identifier continuation char ----------
; (a letter 'A'..'Z'/'a'..'z' or a digit '0'..'9'). A preserved.
is_ident_cont:
                call    is_letter           ; letter -> CF set, A preserved
                ret     c
                cp      '0'
                jr      c,iic_no
                cp      '9'+1
                jr      nc,iic_no
                scf                          ; digit -> CF set
                ret
iic_no:
                or      a                    ; CF clear
                ret

; --- var_name_key: parse a variable name at (HL) -> key in BC ---------------
; in:  HL = cursor at the first name char (guaranteed a letter).
; out: B = name0 (upcased), C = name1 (upcased letter / digit, or 0). HL is
;      advanced past the whole name + any type-suffix char. Clobbers A.
; In the crunched stream a name's letters are already upcased and its digits are
; kept verbatim (see the tokeniser's identifier path), so this walks plain ASCII.
var_name_key:
                ld      a,(hl)
                call    upcase
                ld      b,a                 ; name0
                inc     hl
                ld      c,0                 ; name1 default (single-char name)
                ld      a,(hl)
                call    is_ident_cont
                jr      nc,vnk_suffix       ; only one char
                call    is_letter
                jr      nc,vnk_dig2
                call    upcase
vnk_set2:
                ld      c,a                 ; name1
                inc     hl
vnk_more:
                ld      a,(hl)              ; consume (ignore) any 3rd+ chars
                call    is_ident_cont
                jr      nc,vnk_suffix
                inc     hl
                jr      vnk_more
vnk_dig2:
                ld      a,(hl)              ; digit second char, verbatim
                jr      vnk_set2
vnk_suffix:
                ld      a,(hl)              ; optional type suffix, consumed/ignored
                cp      '%'
                jr      z,vnk_eat
                cp      '!'
                jr      z,vnk_eat
                cp      '#'
                jr      z,vnk_eat
                cp      '$'
                ret     nz
vnk_eat:
                inc     hl
                ret

; --- var_find: locate entry for key BC -------------------------------------
; out: CF set  -> found,     HL = entry address.
;      CF clear -> not found, HL = first free slot (or VAREND if table full).
; Clobbers A, HL (BC preserved).
var_find:
                ld      hl,VARTAB
vf_lp:
                ld      a,h                 ; reached the end of the table?
                cp      high VAREND
                jr      nz,vf_test
                ld      a,l
                cp      low VAREND
                jr      z,vf_full
vf_test:
                ld      a,(hl)              ; name0
                or      a
                jr      z,vf_free           ; empty slot -> not found
                cp      b
                jr      nz,vf_next
                inc     hl
                ld      a,(hl)              ; name1
                dec     hl
                cp      c
                jr      z,vf_hit
vf_next:
                ld      a,VARENTSZ
                add     a,l
                ld      l,a
                jr      nc,vf_lp
                inc     h
                jr      vf_lp
vf_hit:
                scf                          ; HL = entry start, CF set
                ret
vf_free:
                or      a                    ; CF clear, HL = free slot
                ret
vf_full:
                or      a                    ; CF clear, HL = VAREND (table full)
                ret

; --- var_get_key: BC = key -> DE = value (0 if unset) ----------------------
; Clobbers A, HL (BC preserved).
var_get_key:
                call    var_find
                jr      nc,vgk_zero
                inc     hl
                inc     hl                  ; HL = value field
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ret
vgk_zero:
                ld      de,0
                ret

; --- var_set_key: BC = key, DE = value -> stored (allocates if new) ---------
; A new variable is written into the first free slot (name + value). If the
; table is full the assignment is silently dropped. Clobbers A, HL (BC, DE kept).
var_set_key:
                call    var_find
                jr      c,vsk_store         ; found existing entry
                ; not found: HL = free slot (or VAREND if full)
                ld      a,h
                cp      high VAREND
                jr      nz,vsk_new
                ld      a,l
                cp      low VAREND
                ret     z                   ; table full -> drop
vsk_new:
                ld      (hl),b              ; write the name into the free slot
                inc     hl
                ld      (hl),c
                dec     hl
vsk_store:
                inc     hl
                inc     hl                  ; HL = value field
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

; --- var_get / var_set: single-letter compatibility shims ------------------
; A = name (one char). Map to key (upcased name, 0) — identical to the key a
; 1-char name produces via var_name_key, so single-letter variables set here are
; fully interoperable with multi-character ones. Used by FOR/NEXT and READ, whose
; loop/target variables are single-letter. var_set preserves DE (the value).
var_get:
                call    upcase
                ld      b,a
                ld      c,0
                jp      var_get_key
var_set:
                call    upcase
                ld      b,a
                ld      c,0
                jp      var_set_key

; --- clear_vars: empty the table (called once at INIT) ---------------------
; Zero name0 of every slot (a 0 name0 = empty), which is enough; clearing the
; whole region keeps it tidy. Clobbers A, BC, HL.
clear_vars:
                ld      hl,VARTAB
                ld      bc,VARSLOTS*VARENTSZ
cv_loop:
                ld      (hl),0
                inc     hl
                dec     bc
                ld      a,b
                or      c
                jr      nz,cv_loop
                ret
