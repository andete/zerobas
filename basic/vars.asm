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

; --- var_str_type: does the name at (HL) carry a `$` suffix? -----------------
; in:  HL = cursor at the first name char (a letter). HL is NOT advanced.
; out: A = 1 if a `$` suffix follows the identifier (string variable), else 0.
;      CF = the A==1 condition is also reflected (set iff string). Clobbers A.
; Walks the identifier (letters/digits) to the first non-identifier char and
; tests it for `$`. Used by LET / PRINT / the factor layer to choose the string
; path before delegating the real advance to var_name_key.
var_str_type:
                push    hl
vst_walk:
                ld      a,(hl)
                call    is_ident_cont
                jr      nc,vst_suffix
                inc     hl
                jr      vst_walk
vst_suffix:
                cp      '$'
                jr      z,vst_yes
                pop     hl
                xor     a                   ; not a string (A=0, CF clear)
                ret
vst_yes:
                pop     hl
                ld      a,1
                scf                          ; string (A=1, CF set)
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

; --- string-variable store (own-design; see PROVENANCE.md) -----------------
; Parallel to the numeric var_find/get/set, but over STRTAB, whose entries are
; [name0][name1][len][bytes:STRMAX]. The same 2-char key (BC) identifies a string
; variable; the `$` suffix (handled by the caller) is what selects this store
; instead of the numeric one, so `A` and `A$` are independent (as in MSX-BASIC).

; --- str_find: locate the string entry for key BC --------------------------
; out: CF set  -> found,     HL = entry address (name0 field).
;      CF clear -> not found, HL = first free slot (or STREND if full).
; Clobbers A, DE, HL (BC preserved).
str_find:
                ld      hl,STRTAB
sf_lp:
                ld      a,h                 ; end of the string table?
                cp      high STREND
                jr      nz,sf_test
                ld      a,l
                cp      low STREND
                jr      z,sf_full
sf_test:
                ld      a,(hl)              ; name0
                or      a
                jr      z,sf_free           ; empty slot -> not found
                cp      b
                jr      nz,sf_next
                inc     hl
                ld      a,(hl)              ; name1
                dec     hl
                cp      c
                jr      z,sf_hit
sf_next:
                ld      de,STRENTSZ
                add     hl,de
                jr      sf_lp
sf_hit:
                scf
                ret
sf_free:
                or      a
                ret
sf_full:
                or      a
                ret

; --- str_get_key: BC = key -> HL = descriptor [len][bytes...] ----------------
; Returns HL pointing at the entry's len byte (a valid [len][bytes] descriptor).
; If the variable is unset, returns HL -> STR_EMPTY (a len-0 descriptor), so the
; caller always has a printable/copyable value. Clobbers A, DE, HL (BC kept).
str_get_key:
                call    str_find
                jr      nc,sgk_empty
                inc     hl
                inc     hl                  ; HL -> len field (+2) = descriptor
                ret
sgk_empty:
                ld      hl,STR_EMPTY        ; len-0 descriptor (uninitialised = "")
                ret
STR_EMPTY:      db      0                   ; a shared empty-string descriptor

; --- str_set_key: BC = key, DE -> source descriptor [len][bytes...] ----------
; Copy the source string (len-prefixed at DE) into the key's slot, allocating a
; new slot if needed. Length is clamped to STRMAX (own-design truncation; no
; heap growth). If the table is full the assignment is silently dropped.
; Clobbers A, DE, HL (BC kept). DE may point into STRTAB itself (var-to-var copy
; A$=B$); the copy is forward and the destination is a different slot, so a plain
; LDIR is safe (a self-copy A$=A$ writes identical bytes).
str_set_key:
                push    de                  ; str_find clobbers DE — guard the source ptr
                call    str_find
                pop     de                  ; DE = source descriptor (restored)
                jr      c,ssk_store         ; existing slot
                ld      a,h                 ; not found: free slot or full?
                cp      high STREND
                jr      nz,ssk_new
                ld      a,l
                cp      low STREND
                ret     z                   ; table full -> drop
ssk_new:
                ld      (hl),b              ; write the name into the free slot
                inc     hl
                ld      (hl),c
                dec     hl
ssk_store:
                ; HL = entry name0 field; DE = source descriptor. LDIR copies
                ; (HL)->(DE), so the COPY needs HL=source, DE=dest: we read the
                ; length here, then swap the roles before the LDIR.
                inc     hl
                inc     hl                  ; HL -> dest len field
                ld      a,(de)              ; source length (DE = source descriptor)
                cp      STRMAX+1
                jr      c,ssk_len_ok
                ld      a,STRMAX            ; clamp to STRMAX
ssk_len_ok:
                ld      (hl),a              ; store the (clamped) length at the dest
                inc     hl                  ; HL -> dest bytes
                inc     de                  ; DE -> source bytes
                or      a
                ret     z                   ; zero-length -> done
                ld      c,a
                ld      b,0                 ; BC = byte count
                ex      de,hl               ; LDIR copies (HL)->(DE): HL=source, DE=dest
                ldir
                ret

; --- clear_vars: empty the numeric AND string tables (called at INIT / RUN) --
; Zero name0 of every slot (a 0 name0 = empty). Clearing the whole numeric
; region keeps it tidy; for strings, zeroing each entry's name0 marks it free.
; Clobbers A, BC, HL.
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
                ; clear the string store: name0 = 0 in every slot
                ld      hl,STRTAB
                ld      b,STRSLOTS
cv_str:
                ld      (hl),0              ; name0 = free
                ld      de,STRENTSZ
                add     hl,de
                djnz    cv_str
                jp      fld_init            ; also reset the random-access field table
