; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; format.asm — CALL FORMAT (initialise a blank FAT12 filesystem on the disk).
;
;   CALL FORMAT          (or the abbreviation _FORMAT)
;
; A real MSX CALL FORMAT is interactive: it asks "Drive name? (A,B)" and then offers
; the disk ROM's CHOICE menu of geometries (on the National CF-3300: 1-side / 2-sides
; / ±double-track — 360 KB up to 720 KB). zerobas-disk targets drive A only, so it
; skips the drive prompt, but it DOES prompt a minimal geometry menu: "1=360K 2=720K"
; read via the REPL line editor (do_format, below) — the two supported FAT12 layouts
; (media $F9/720 KB and media $FD/360 KB). Any drive argument typed after the verb is
; parsed-past and ignored.
;
; zerobas-BASIC owns the FAT12 logic and drives the standard $4010 DSKIO read+write
; (basic/fat.asm's resident layer; since the eviction below, the write primitive
; itself is sub/format.asm's sub-local copy), so it lays the filesystem down
; ITSELF — a fresh boot sector (BPB)
; + two FAT copies + an empty root directory via write_sector — without needing
; zerobas-disk's DSKFMT (a stub). This is the Phase-1.5 "BASIC owns the filesystem"
; model applied to formatting.
;
; GEOMETRY IS PARAMETERISED. All geometry lives in descriptor tables (GEOM_720K,
; GEOM_360K); the format logic reads their fields, with no hardcoded constants. The
; menu selection just picks which descriptor to hand the routine — the routine itself
; does not change. A further geometry is a new descriptor + a menu line.
;
; Clean-room: original code. The CALL token ($CA) is oracle-locked to the VG-8020
; crunch. The BPB *geometry* (512 B/sec, 2 sec/clus, 1 reserved, 2 FATs, 112 root
; entries, 1440 sectors, media $F9, 3 sec/FAT) is the standard 720 KB FAT12 layout
; (Microsoft FAT spec / MSX2 TH), confirmed field-for-field against a black-box
; National CF-3300 "2 sides, double track" format. The boot-CODE region and OEM name
; are zerobas' OWN (not copied from any ROM) — the one documented divergence from a
; byte-identical CF-3300 format. No disassembly. See basic/PROVENANCE.md §CALL FORMAT.
;
; REPACK EVICTION (docs/spec-evict-call-format.md, funding error-handling S2b): the
; sector-build/write BULK (everything past the menu — clear/stamp/boot-write, the
; geometry helpers, the GEOM_* tables) straddles both main-BASIC page-1 (console I/O)
; and the page-0 BIOS (write_sector -> CALSLT), so it can't be a single-shape sub-ROM
; tenant (playbook §3). The design is a SPLIT: this file keeps the dispatch + the
; interactive menu RESIDENT (console I/O is page-1 main, trivially resident); the
; bulk moves to a sub-ROM PAGE-1 tenant (sub/format.asm format_tenant) that carries
; its own sub-local CALSLT write path. The bulk's CODE is shared verbatim via
; basic/format-body.inc (the c3fc2d8 printusing.asm pattern).

; --- ex_call / _<name> — extended-statement dispatch -----------------------
; HL -> the CALL token (ex_call) or the '_' char (ex_call_us). Only CALL FORMAT is
; supported; any other name errors.
ex_call:
                inc     hl                  ; past the CALL token
                jr      exc_name
ex_call_us:
                inc     hl                  ; past '_'
exc_name:
                call    skip_spaces
                call    fmt_match_format    ; CF set if (HL) == "FORMAT"
                jp      nc,stmt_error       ; unsupported CALL extension
                ; 🔴 THE REFERENCE REJECTS EVERY TAIL — MEASURED, NOT ASSUMED
                ; (D-FMTTAIL, docs/spec-basic-fmttail.md). On the National
                ; CF-3300 `CALL FORMATX`, `CALL FORMATFOO`, `CALL FORMAT X` and
                ; `_FORMAT("A:")` are ALL `Syntax error`, raised BEFORE the
                ; format prompt appears. So the name must END the statement and
                ; CALL FORMAT takes no argument at all.
                ; What was here swallowed everything up to ':'/EOL, which made a
                ; TYPO silently FORMAT THE DISK: `CALL FORMATX` wiped it where
                ; the reference refuses. It was also quote-blind, so
                ; `_FORMAT("A:")` stopped at the colon INSIDE the quotes (the
                ; D-DATACOLON class).
                ; ⚠️ COLON MUST STILL PASS: `CALL FORMAT:PRINT 1` is accepted on
                ; both references, so this requires end-of-STATEMENT, not
                ; end-of-line. That row is why the test is not a bare `or a`.
                call    skip_spaces         ; returns A = (HL) -- no reload
                or      a
                jr      z,exc_go
                cp      COLON
                jp      nz,stmt_error
exc_go:
                push    hl                  ; save the statement-end cursor (CALSLT clobbers)
                call    do_format
                pop     hl
                jp      c,load_error        ; format I/O error (or, repack: the tenant
                                            ; absent/reporting an error — folded into
                                            ; Cy by do_format below, spec §4)
                jp      exec_stmt

; fmt_match_format — CF set iff the 6 chars at (HL) are "FORMAT" (case-insensitive);
; HL is advanced past them on a match. Clobbers A, B, DE, HL.
fmt_match_format:
                ld      de,fmt_name
                ld      b,6
fmf_lp:
                ld      a,(de)
                ld      c,a
                ld      a,(hl)
                call    upcase
                cp      c
                jr      nz,fmf_no
                inc     hl
                inc     de
                djnz    fmf_lp
                scf                         ; matched
                ret
fmf_no:
                or      a                   ; CF clear -> no match
                ret
fmt_name:       db      "FORMAT"


; --- do_format — interactively pick a geometry, then write a fresh filesystem ----
;   out: Cy = 0 ok; Cy = 1 = no disk / write error (repack: OR the sub-ROM tenant
;        is absent, spec §4 — same disposition class as any other format I/O error).
; A real CALL FORMAT lets you choose the disk geometry; with two geometries there now
; IS something to choose, so zerobas prompts a minimal 1=360K / 2=720K menu (its own —
; zerobas-disk's CHOICE offers none) and reads the answer via the REPL line editor.
; The MENU stays resident (console I/O is main-BASIC page-1); the build/write engine
; past the choice is dispatched to the sub-ROM page-1 tenant (sub/format.asm
; format_tenant),
; marshalling just the 1-byte geometry selector through RAM (FMT_GEOMSEL).
do_format:
                ld      a,(DISKSLOT_OK)
                or      a
                jr      nz,fmt_menu
                scf                         ; no disk -> error
                ret
fmt_menu:
                ld      hl,fmt_menu_text
                call    print_string
                call    read_line           ; LINEBUF <- the typed choice (echoed)
                ld      a,(LINEBUF)
                cp      '1'
                jr      z,fmt_sel_360
                cp      '2'
                jr      z,fmt_sel_720
                jr      fmt_menu            ; invalid -> re-prompt (like the CF-3300 '?')
fmt_sel_360:
                xor     a                   ; A = 0 -> 360k (format_tenant's GEOM select)
                jr      fmt_dispatch
fmt_sel_720:
                ld      a,1                 ; A = 1 -> 720k
fmt_dispatch:
                ld      (FMT_GEOMSEL),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FORMAT
                call    subrom_call         ; CF=1 iff the sub-ROM is absent (no call made).
                                            ; No live pointer to guard here: exc_go already
                                            ; saved HL (the token cursor) before `call
                                            ; do_format`, and IX is not otherwise live.
                ret     c                   ; absent -> Cy=1 (do_format's own error contract;
                                            ; exc_go folds it into the same load_error as a
                                            ; real DSKIO error, spec §4)
                ld      a,(FMT_RESULT)      ; the tenant's DSKIO disposition (RAM, not CF --
                                            ; subrom_call's CF is claimed by the absence
                                            ; signal, spec §4)
                or      a
                ret     z                   ; tenant ok -> Cy=0 (subrom_call already cleared
                                            ; it on a completed call)
                scf                         ; tenant reported a write error -> Cy=1
                ret
; fmt_menu_text has its own copy here (resident); a second copy lives INSIDE
; basic/format-body.inc, at its original position between fmt_boot and
; fmt_geom_byte (see that file) -- format-body.inc is sub-ROM-only
; in the repack build (sub/format.asm), not included resident here, so the menu
; needs its own text. Same 17 bytes, no functional difference.
fmt_menu_text:  db      "1=360k 2=720k? ",0
