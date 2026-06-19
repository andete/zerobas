; vars.asm — integer variable store.
;
; 26 single-letter variables A..Z, each a 16-bit integer, held in a fixed
; page-3 RAM table (VARTAB). This is the minimal store the PEEK/POKE slice
; needs: a READ-style target and operands for expressions. No strings, arrays,
; or multi-character names (a stored-program milestone can extend this).
;
; Clean-room: original code. Variable *semantics* (a named 16-bit cell) follow
; the public MSX-BASIC language reference; the table layout is our own choice
; (see PROVENANCE.md). No disassembly.

; --- var_addr: name in A -> HL = address of its 2-byte slot -----------------
; Case-folds the name. Clobbers A, BC, HL. Caller guarantees A is 'A'..'Z' or
; 'a'..'z'.
var_addr:
                call    upcase
                sub     'A'                 ; 0..25
                add     a,a                 ; *2 bytes/slot (<=50, fits 8 bits)
                ld      c,a
                ld      b,0
                ld      hl,VARTAB
                add     hl,bc
                ret

; --- var_get: name in A -> DE = value --------------------------------------
; Clobbers A, BC, HL.
var_get:
                call    var_addr
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ret

; --- var_set: name in A, value in DE -> stored -----------------------------
; var_addr does not touch DE, so the value survives. Clobbers A, BC, HL.
var_set:
                call    var_addr
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

; --- clear_vars: zero the whole table (called once at INIT) ----------------
; Clobbers A, B, HL.
clear_vars:
                ld      hl,VARTAB
                ld      b,VARCOUNT*2
cv_loop:
                ld      (hl),0
                inc     hl
                djnz    cv_loop
                ret
