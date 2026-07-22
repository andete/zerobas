; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; casmatch-body.inc — cas_open_match / cas_skip_data shared body (the
; cassette Tier-3 name-match / data-skip engine).
;
; docs/spec-eviction-g5-space.md. Extracted verbatim from basic/cload.asm so
; the SAME source feeds two homes:
;   * lean 16 KB cart (basic/cload.asm, ROM_BASE >= $4000): inline, at this
;     file's ORIGINAL position -- BYTE-IDENTICAL to the pre-eviction build
;     (this file is a pure relocation of that exact code, nothing added/
;     removed/reordered).
;   * sub-ROM PAGE-1 tenant (sub/casmatch.asm, repack): cas_open_match
;     becomes a resident marshalling shim (basic/cload.asm's own `IF
;     ROM_BASE < $4000` branch, right where this file is `include`d for
;     lean) that `subrom_call`s casmatch_tenant, which runs this body
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
                or      a                   ; CF clear = matched
                ret
com_miss:
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
;        producer puts in the last block, spec-cas-ascii-saveload §0.1).
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
csd_ascii:
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
                ; NB: assumes the tokenised data block ENDS at the $0000 end-link
                ; (our CSAVE writes payload then TAPOOF — no trailing in-block pad),
                ; so after $0000 the next TAPION relocks on the following header.
                ; (cas_encode's single-file 16-byte pad would leave slack; the
                ; name-match gate builds skip fixtures CSAVE-faithfully.)
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
