; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; play.asm — the PLAY statement's RESIDENT stub (audio arc, Slice 2a).
;
;   PLAY "mml"[,"mml"[,"mml"]]     parse up to three MML voice strings
;
; PLAY splits (spec docs/spec-basic-audio-play-slice2a.md §3/§4): the heavy MML
; PARSER is a page-1 sub-ROM tenant (play_parse_tenant, SUBROM_IDX_PLAY_PARSE);
; this resident stub only evaluates the up-to-three string arguments and marshals
; each voice's (body pointer, length) into that voice's VCB, then hands off with a
; single subrom_call. The tenant parses each string into its VOICxQ ring buffer and
; sets MUSICF last; Slice 2a has NO live drain (the interrupt servicer is Slice 3),
; so PLAY returns immediately after the parse.
;
; Marshalling is faithful (Q2): each voice's MML (ptr,len) go into the standard MSX
; VCB fields VCXPTR/VCXLEN (basic/sysvars.inc), and AUDIO_VMASK (reusing DISKOP_OP
; -- audio and disk are never in flight together) carries the voices-present mask.
; IY runs along the three VCBs (VCBA/VCBB/VCBC, VCB_STRIDE apart); C carries the
; current voice's mask bit (1/2/4), B the voice count for the 3-voice cap.
;
; Clean-room: original code. PLAY *syntax* (comma-separated per-voice MML strings)
; is the public MSX-BASIC language reference; the work-area layout is the MSX2
; Technical Handbook (also reserved by our target C-BIOS). No disassembly.
;
; Entry: ex_play, HL on the PLAY token. Repack-only (the tenant it drives is page-1,
; which only the repack build reaches); PLAY is dispatched, not resident.
ex_play:
                inc     hl                  ; past the PLAY token
                xor     a
                ld      (AUDIO_VMASK),a     ; no voices present yet
                ld      iy,VCBA             ; IY = running VCB base (voice 0)
                ld      bc,$0001            ; B = voice count 0; C = voice-0 mask bit
                ; Each voice is a REQUIRED string expression (empty "" is allowed),
                ; commas separate voices. A numeric operand is a Type mismatch
                ; (PLAY 5), and PLAY"","E" is fine -- both still as the old header
                ; said and as basic_probe_play.py confirmed.
                ; 🔴 BUT ITS OTHER HALF WAS WRONG, AND D-PLAYOP MEASURED IT
                ; (docs/spec-basic-playop.md, 11 rows x 3 machines). The header
                ; used to say "a bare comma / MISSING OPERAND is a Syntax error
                ; -- matching the VG-8020". The bare comma is; the missing
                ; operand is NOT. `PLAY` and `PLAY:PRINT1` are ERR 24 `Missing
                ; operand` on BOTH references and were ERR 2 here. One citation
                ; was carrying two claims and only one of them had been run.
                ; 🎯 AND THE SPLIT IS THE ORDINARY ONE: a required slot that ENDS
                ; where a value was needed is 24; an EMPTY operand terminated by
                ; ',' is 2 (D-MISSOP's rule, docs/spec-basic-missop.md §5).
                ; ⚠️ pl_voice IS A LOOP -- `jr pl_voice` below re-enters it after
                ; every comma -- so each test here has TWO entry conditions, the
                ; first voice and a subsequent one. Both were measured and both
                ; answer the same way: `PLAY"A",` and `PLAY"A",:PRINT1` are 24,
                ; `PLAY"A",,"C"` is 2. Reading the sites as four INSTRUCTIONS
                ; would have missed that they are seven ROWS.
pl_voice:
                call    skip_spaces
                or      a                   ; a separator / EOL where a string is
                ; +1 B each, and that is CHEAPER THAN A TRAMPOLINE HERE. D-PAINTMISS
                ; reasoned the opposite way and was right for its own case: with
                ; FOUR `jr` sites, four `jp z,loc_missing` costs +4 B against a 3 B
                ; `ep_missing: jp loc_missing`. With TWO sites it is +2 B against 3,
                ; so the arithmetic inverts below four. loc_missing is `equ
                ; g8_missing` in the shipping build and a real body in the
                ; !G8_RESIDENT arm, so both switch arms still assemble.
                jp      z,loc_missing       ; required slot ENDS here -> ERR 24
                cp      COLON
                jp      z,loc_missing       ; `PLAY:` likewise -> ERR 24
                cp      ','
                jr      z,pl_syntax         ; bare comma (PLAY ,"E") -> Syntax error,
                                            ; measured 2 on both references at BOTH
                                            ; entry conditions -- this one does NOT move
                push    bc                  ; str_eval clobbers BC (voice count + bit)
                call    str_eval            ; STRPTR -> [len][ptr]; VALTYP=1; CF=1 ok;
                pop     bc                  ;   HL advanced past the operand
                jr      nc,pl_typeerr       ; not a string form (numeric) -> Type mismatch
                push    hl                  ; save the line cursor
                ld      hl,(STRPTR)         ; HL = descriptor address
                ld      a,(hl)              ; A = string length
                ld      (iy+VCX_VCXLEN),a
                call    pu_deref_body       ; HL = string body address (A preserved)
                ld      (iy+VCX_VCXPTR),l
                ld      (iy+VCX_VCXPTR+1),h
                pop     hl                  ; restore the line cursor
                ld      a,(AUDIO_VMASK)
                or      c                   ; mark this voice present
                ld      (AUDIO_VMASK),a
                ; after a string, an optional ',' introduces the next voice
                call    skip_spaces
                cp      ','
                jr      nz,pl_dispatch      ; no separator -> argument list done
                inc     hl                  ; consume the ',' separator
                ld      de,VCB_STRIDE
                add     iy,de               ; IY -> next voice's VCB
                rlc     c                   ; next voice's mask bit (1->2->4)
                inc     b
                ld      a,b
                cp      3
                jr      nc,pl_syntax        ; a 4th voice string -> Syntax error
                jr      pl_voice
pl_syntax:
                ld      a,2                 ; Syntax error. D-PLAYOP: NOT "missing/bad
                                            ; voice operand" any more -- a MISSING one is
                                            ; ERR 24 at loc_missing above. What is left
                                            ; here is the EMPTY operand before a ','
                                            ; (`PLAY,"E"`, `PLAY"A",,"C"`) and the 4th
                                            ; voice string, both measured 2 on both
                                            ; references. The 4th-voice site is the one
                                            ; TODO.md marked UNMEASURED and told nobody
                                            ; to assume: it is 2, and it stays.
                jp      raise_error         ; via raise_error so ON ERROR can trap it (the
                                            ; VG-8020 traps this; stmt_error would not)
pl_dispatch:
                call    check_expr_errors   ; surface a deferred string error (FPERR/TMISMATCH)
                push    hl                  ; save the statement cursor -- CALSLT clobbers HL
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_PLAY_PARSE
                call    subrom_call         ; CF=1 iff the sub-ROM is absent (no call made)
                pop     hl                  ; restore cursor so exec_stmt chains the next stmt
                jp      c,pl_absent
                ld      a,(AUDIO_STATUS)    ; tenant result (RAM; subrom_call's CF is absence)
                or      a
                jp     nz,pl_parse_err     ; nonzero = the ERR code the tenant chose
                jp      exec_stmt           ; PLAY returns immediately; chain the next stmt
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to tm_raise,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
pl_parse_err    equ     tm_raise
pl_typeerr:
                ld      a,13                ; Type mismatch (a PLAY argument was not a string)
                jp      raise_error
; D-DUPSPAN: an ALIAS, not a second copy -- the two instructions were
; byte-identical to interp.asm's gb_illegal, on gfx_absent's own precedent.
; The NAME and every call site survive; un-alias here to give this site a
; distinct face and nothing else moves.
pl_absent       equ     gb_illegal  ; defensive: merged ROM always ships the tenant
