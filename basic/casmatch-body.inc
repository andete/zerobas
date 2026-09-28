; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; casmatch-body.inc — cas_open_match / cas_skip_data shared body (the
; cassette Tier-3 name-match / data-skip engine).
;
; docs/spec-eviction-g5-space.md. Extracted verbatim from basic/cload.asm so
; the SAME source fed two homes until the lean cart retired:
;   * (retired) lean 16 KB cart, inline at this
;     file's ORIGINAL position -- byte-identical to the pre-eviction build
;     (this file is a pure relocation of that exact code, nothing added/
;     removed/reordered).
;   * sub-ROM PAGE-1 tenant (sub/casmatch.asm, repack): cas_open_match
;     becomes a resident marshalling shim (basic/cload.asm's own `IF
;     branch, right where this file used to be `include`d)
;     that `subrom_call`s casmatch_tenant, which runs this body
;     unchanged and converts CF to CM_STATUS.
;
; Clean-room: our own code, extracted verbatim from basic/cload.asm (see
; that file's header for the cassette file-format provenance).

; --- cas_open_match: open the next MATCHING cassette file's header ------------
; Loops over the tape's files: TAPION each header block, read the file-type id
; (into CAS_HDRID) + the 6-char name (into CAS_HDRNAME). If CAS_WANT_ON = 0 the
; first file matches (bare CLOAD / load-next); else the name is compared BYTE-
; EXACT against CAS_WANT (case-sensitive — CF-3300-confirmed, spec §A.5). A non-
; matching file's DATA is consumed (cas_skip_data) and the next header is tried.
; Running out of tape -> the read stalls on silence and TAPIN/TAPION returns CF
; (the whole reader's end condition) -> caller reports load_error / "not found".
; On a match the header is FULLY consumed and the tape sits at the START of the
; matched file's DATA; the caller dispatches on CAS_HDRID ($D3 tokenised / $EA
; ASCII) and reads the data block(s).
;   out: CF clear = matched (CAS_HDRID set); CF set = not found / tape error.
; STATE-IN-RAM discipline (TAPIN clobbers every register): only loop COUNTERS are
; pushed across TAPIN (proven safe by ctp_skip_hdr), never a pointer.
cas_open_match:
com_next:
                call    TAPION              ; header block leader
                ret     c                   ; tape end / no file -> not found
                call    TAPIN               ; header byte 0 = file-type id
                ret     c
                ld      (CAS_HDRID),a       ; keep id for dispatch / skip
                ; read header bytes 1..15 (9 more id bytes + the 6-char name); store
                ; the LAST 6 (B = 6..1) into CAS_HDRNAME[0..5], skip the id bytes.
                ld      b,15
com_hdr:
                push    bc
                call    TAPIN
                pop     bc
                ret     c
                ld      c,a                 ; C = the header byte
                ld      a,b
                cp      7
                jr      nc,com_hdr_next     ; B >= 7 -> still an id byte -> skip store
                ld      a,6
                sub     b                   ; index = 6 - B (B = 6..1 -> 0..5)
                ld      e,a
                ld      d,0
                ld      hl,CAS_HDRNAME
                add     hl,de
                ld      (hl),c              ; store name[index]
com_hdr_next:
                djnz    com_hdr
                ld      a,(CAS_WANT_ON)
                or      a
                jr      z,com_match         ; bare form -> this file matches
                ld      hl,CAS_HDRNAME
                ld      de,CAS_WANT
                ld      b,6
com_cmp:
                ld      a,(de)
                cp      (hl)                ; byte-exact, case-sensitive
                jr      nz,com_miss
                inc     hl
                inc     de
                djnz    com_cmp
com_match:
                ld      hl,cm_s_found       ; D-CASSEARCH: the progress row
                call    cm_say
                or      a                   ; CF clear = matched
                ret
com_miss:
                ld      hl,cm_s_skip        ; D-CASSEARCH: ...before the skip, as
                call    cm_say              ; the reference orders its rows
                call    cas_skip_data       ; consume the non-matching file's data
                ret     c                   ; tape error while skipping -> fail
                jr      com_next            ; ...and try the next file

; --- cas_skip_data: consume the DATA of the current (non-matching) file so the
; next TAPION locks onto the next file's header. Format-aware on CAS_HDRID:
;   $D3 tokenised -> ONE data block: TAPION, then walk the line-link chain
;        discarding until the $0000 end-link (length-driven, exactly like
;        ctp_line, but storing NOTHING — CLINK is scratch here, the matched load
;        re-inits it).
;   $EA ASCII    -> N 256-byte blocks: cal_refill each, scan CAL_BUF for Ctrl-Z
;        ($1A); stop after the block that contains it (the ASCII soft-EOF every
;        producer puts in the last block, spec-cas-ascii-saveload §0.1). Skipping
;        has no tokenise work between blocks (it only scans for Ctrl-Z), so it
;        wants the single fixed buffer cal_refill originally gave every caller,
;        not cload.asm's double-buffered read-ahead — see csd_ascii below.
;   else -> CF (an unknown file mid-tape is corruption; do not spin).
;   out: CF clear = data consumed; CF set = tape read error.
cas_skip_data:
                ld      a,(CAS_HDRID)
                cp      BASIC_ID
                jr      z,csd_tok
                cp      ASCII_ID
                jr      z,csd_ascii
                scf                         ; unknown id -> error
                ret
; cal_refill (cal-refill-body.inc) fills "whichever buffer CAL_CURHI is NOT
; pointing at" for cload.asm's double-buffered read-ahead. This loop wants a
; SINGLE fixed target (CAL_BUF, scanned directly below) every call, which it
; gets for free by pointing CAL_CURHI at CAL_BUF2 ONCE, here, before the loop —
; csd_ascii never touches CAL_CURHI again, so every cal_refill call keeps
; targeting CAL_BUF, unchanged from before cload.asm grew a second buffer.
csd_ascii:
                ld      a,CAL_BUF2 >> 8
                ld      (CAL_CURHI),a
                call    cal_refill          ; TAPION + slurp 256 into CAL_BUF; CF = EOF/err
                ret     c
                ld      hl,CAL_BUF
                ld      b,0                 ; 256-byte scan (djnz with b=0 -> 256)
csd_asc_scan:
                ld      a,(hl)
                cp      $1A                 ; Ctrl-Z -> file complete
                jr      z,csd_ok
                inc     hl
                djnz    csd_asc_scan
                jr      csd_ascii           ; no Ctrl-Z in this block -> next block
csd_tok:
                ; NB: stops at the $0000 end-link and does NOT read the SEVEN $00
                ; bytes every CSAVE writes after it (VG-8020, CF-3300 and zerobas
                ; alike -- scratchpad/csavetail_probe.out; the old note here said
                ; "no trailing pad", sourced from our own save.asm). The next
                ; TAPION must therefore relock PAST them: its CAS_SKIP is long
                ; enough that a lock cannot complete inside them (D-CASRELOCK,
                ; tape/tape.asm). A CLOAD that reads a file leaves the same seven.
                call    TAPION              ; data block leader
                ret     c
                ld      hl,TXTBASE
                ld      (CLINK),hl          ; A_0 = saving machine text base (as ctp)
csd_tok_line:
                call    TAPIN               ; link low
                ret     c
                push    af                  ; preserve link-low (TAPIN clobbers C)
                call    TAPIN               ; link high
                jr      c,csd_tok_perr      ; must pop before leaving
                ld      b,a
                pop     af
                ld      c,a                 ; BC = saved link word L_n
                ld      a,b
                or      c
                jr      z,csd_ok            ; $0000 link -> file complete
                ld      hl,(CLINK)          ; A_n
                ld      (CLINK),bc          ; advance CLINK = L_n
                ld      a,c
                sub     l
                ld      e,a
                ld      a,b
                sbc     a,h
                ld      d,a                 ; DE = L_n - A_n = full line length
                dec     de
                dec     de                  ; DE = bytes still to discard (lineno + body)
csd_tok_disc:
                ld      a,d
                or      e
                jr      z,csd_tok_line      ; whole line discarded -> next line
                push    de                  ; guard count across TAPIN (as ctp_body)
                call    TAPIN
                pop     de
                jr      c,csd_tok_err
                dec     de
                jr      csd_tok_disc
csd_ok:
                or      a                   ; CF clear = data consumed
                ret
csd_tok_perr:
                pop     af                  ; rebalance the pushed link-low
csd_tok_err:
                scf                         ; tape read error while skipping
                ret

; --- cm_say: the tape-search progress row (docs/spec-basic-cassearch.md) ------
; Both references print one row per decision of the loop above while a tape
; search runs -- `Found:NAME` at com_match, `Skip :NAME` at com_miss, the name
; being the HEADER just read, not the name the user asked for. Measured on the
; Philips VG-8020 and the National CF-3300, which agree row for row, for all
; FOUR verbs that reach this loop: LOAD"CAS:" / RUN"CAS:", CLOAD, MERGE"CAS:"
; and OPEN"CAS:" FOR INPUT (docs/cassearch-msx1-characterization.md §1-§3).
; That is why the emit is sited HERE, in the shared search engine, rather than
; at any one verb: a verb-sited print would have to be written four times, and
; a reference silent on any one of them would have made this siting wrong. None
; is.
;
; 🔴 print_msg IS UNREACHABLE FROM HERE AND THAT IS THE POINT. It lives at $7687
; -- MAIN page 1 -- and tools/check_tenant_closure.py --page1 forbids a page-1
; sub tenant to call it. CHPUT ($00A2) is page-0 BIOS, i.e. < $4000, which a
; page-1 tenant may call and a page-0 one may not: the same reason sub/title.asm
; is a page-1 tenant, and the same edge class this body already uses for
; TAPION/TAPIN. So the two prefixes are the tenant's OWN bytes and the sink is
; BIOS.
;
;   in: HL -> a SIX-character prefix. Both prefixes are exactly six characters
;       (the reference's own spacing) and CAS_HDRNAME is exactly six bytes, so
;       ONE count-6 loop serves both halves and no terminator byte is needed.
; Clobbers AF/BC/HL -- safe at both call sites: com_match's `or a` runs AFTER
; the call so the published CF-clear contract is unchanged, and com_miss's
; cas_skip_data takes all its state from RAM (TAPIN clobbers everything anyway,
; which is the discipline this whole body is written to).
;
; The 6 name bytes are emitted VERBATIM, pad spaces included. A trailing pad
; space is indistinguishable from unwritten screen -- a CR/LF follows, so
; nothing can land beside it -- so no battery can score trimmed against padded
; (characterization §6), and trimming would only cost bytes.
cm_say:
                call    cm_six              ; the 6-char prefix
                ld      hl,CAS_HDRNAME
                call    cm_six              ; the 6-char tape header name
                ld      a,13                ; CR/LF: the row stands alone, as on
                call    CHPUT               ; the reference
                ld      a,10
                jp      CHPUT
cm_six:
                ld      b,6
cm_six_ch:
                push    bc                  ; guard the counter AND the pointer
                push    hl                  ; across the BIOS call (title-body
                ld      a,(hl)              ; st_loop's precedent)
                call    CHPUT
                pop     hl
                pop     bc
                inc     hl
                djnz    cm_six_ch
                ret
cm_s_found:     db      "Found:"
cm_s_skip:      db      "Skip :"
