; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; bload-body.inc — the BLOAD verb body (dispatch + tape load + the disk name).
; ===========================================================================
; Home:
;   * the sub-ROM PAGE-1 tenant (sub/bload.asm, SUBROM_IDX_BLOAD) — evicted there
;     in the repack build to free main page-1 space (docs/spec-traps-t3-key.md
;     §7.6). The fcbname-body.inc precedent, one level larger. That is its only
;     home: no other ROM includes this file.
; 🏗️ D-ROMSIZE step 1 (2026-10-19): THE DISK LOAD LEFT FOR disk.rom (hk_dpbload,
; disk/kernel.asm), reached through H_FOPEN with FOPEN_SEL_BLOAD -- the cell the
; CF-3300's BLOAD enters. For a disk name this body builds DISK_FCB_NAME and
; answers BL_STAT = FOPEN_SEL_BLOAD; main (basic/bload.asm) makes the crossing.
; With it went this body's calls into the sub-ROM's FAT engine, its last users.
;
; Every name it calls resolves on the tenant's side:
;   parse_disk_fcb / bl_upcase — sub-local clones co-located in sub/bload.asm
;     (the resident originals must STAY resident regardless: they have external
;     callers, so they are not evicted, only copied). The tenant binds
;     parse_disk_fcb's two rejects, pdf_baddrive and pdf_badname, to 62 / 56 in
;     BL_STAT (sub/bload.asm), which main raises -- the resident copy's codes.
;   bl_load_error — sub-local in the tenant, where it does TAPIOF + ERRMARK + sets
;     BL_STAT and rets, with the SAME stack behaviour, so control flow is unchanged
;     and the resident stub does the reporting once on the way out.
;   bl_tape_dio — 19 for a failed tape search / read (D-CASBIN, D-CASRBRK).
;   (bl_notfound / bl_badmode -- 53 / 61, the disk path's raised codes -- are
;     disk.rom's since 2026-10-19: hk_dpbload answers them in DISKOP_STATUS.)
;   The ,R exec jump is MAIN's (basic/bload.asm load_handoff): it CALLs into the
;     loaded program, so it must NOT run inside the tenant's CALSLT -- that would
;     leave main page 1 switched out. The tenant returns normally.
;
; TAPIN/TAPION/TAPIOF are BIOS calls; main page 0 stays mapped while a page-1
; tenant runs, so they are reachable from both sides unchanged.
;
; CLEAN-ROOM: extracted verbatim from our own basic/bload.asm; provenance for the
; BSAVE formats is unchanged (basic/PROVENANCE.md).
; ===========================================================================


do_bload:
                ; --- parse: <name expression> [ ,R ] -----------------------
                ; ✅ D-FNEXPR2: the opening `call bl_skip_spaces` / `cp '"'` /
                ; `jp nz,bl_load_error` / `inc hl` gate is GONE. HL arrives (via
                ; BL_PTR) already pointing at a staged, '"'-terminated copy of
                ; the evaluated filename, because `str_eval` lives in main page 1
                ; and cannot be called from inside a page-1 tenant -- see the
                ; resident stub in basic/bload.asm. Everything below is unchanged:
                ; the dispatch and parse_disk_fcb walk (HL) exactly as before and
                ; neither cares where the bytes came from.
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                ; Peek for the literal "CAS:" prefix. Match it verbatim and
                ; non-destructively decide; only commit to the tape path once
                ; the full prefix matched, so a name like "CASE.BIN" falls
                ; through to the disk path cleanly.
                push    hl                  ; remember filename start
                ld      de,dev_cas          ; compare device name to "CAS:"
parse_dev:
                ld      a,(de)
                or      a
                jr      z,is_tape           ; matched all of "CAS:" -> tape
                ld      c,a                 ; expected (uppercase) char
                ld      a,(hl)              ; typed char
                call    bl_upcase              ; case-insensitive (typed may be lower)
                cp      c
                jr      nz,is_disk          ; prefix mismatch -> disk path (out of jr range)
                inc     hl
                inc     de
                jr      parse_dev
is_tape:
                pop     af                  ; discard saved filename start
                ; The `,R` / `,S` / `,offset` tail is ALREADY parsed: main's
                ; pcr_bload (basic/bload.asm) did it before calling in, because
                ; the offset needs `eval` (D-BLOADOFS). RUNFLAG / VRAM_FLAG /
                ; BL_OFS are set.
                ld      a,(VRAM_FLAG)
                or      a
                jp      nz,bl_load_error       ; ,S VRAM-from-tape not supported here
                ; 🔴 D-CASBIN (2026-10-08): THE TAPE IS SEARCHED, BY NAME AND TYPE, AS
                ; EVERY OTHER TAPE VERB SEARCHES IT. This read the FIRST file's header,
                ; never looked at the name, and refused a non-binary file with an
                ; untrappable `load error` -- so `BLOAD"CAS:X"` on a tape holding a
                ; binary Y first LOADED Y, silently (VG-8020: skips Y, loads X;
                ; probes/basic/basic_probe_casbin.py `bnn`). Now: the name into
                ; CAS_WANT (cascap-body.inc, shared with main), bit 6 = binary, and
                ; the sub-local matcher -- which leaves the tape at the DATA block.
                call    cas_capture_cut     ; (D-CASDOT: a . ends the name) HL past "CAS:" (or the bare diskless name)
                ld      hl,CAS_WANT_ON
                set     6,(hl)              ; BLOAD wants $D0
                call    cas_open_match      ; Found:/Skip : rows, as the reference
                jp      c,bl_tape_dio       ; I/O error / Ctrl-STOP: 19, as D-CASBRK

                ; --- data block: skip its tone, then read the 6-byte header --
                call    TAPION              ; sync block 2 (data)
                jp      c,bl_tape_dio       ; D-CASRBRK: Ctrl-STOP / I/O -> 19, raised

                ; spec-bload-r.md §1: start(LE), end(LE), exec(LE) -- into
                ; CURPTR, ENDPTR, EXECPTR, six contiguous bytes (sysvars.inc).
                ; 🔴 D-CASRBRK: THESE SIX READS IGNORED CF. A Ctrl-STOP in them
                ; returned garbage, BLOAD loaded the tape to a garbage range and
                ; the screen came back as noise (basic_probe_casrbrk's bb2; the
                ; VG-8020: `19 in 15`). A loop that tests it is 18 B smaller.
                ld      hl,CURPTR
blh_lp:
                push    hl                  ; TAPIN trashes every register
                call    TAPIN
                pop     hl
                jp      c,bl_tape_dio       ; Ctrl-STOP / I/O -> 19, raised
                ld      (hl),a
                inc     hl
                ld      a,l
                cp      low (EXECPTR + 2)
                jr      nz,blh_lp
                call    bl_apply_ofs        ; D-BLOADOFS: + BLOAD's ,offset

                ; --- load loop: bytes start..end inclusive, verbatim --------
                ; spec-bload-r.md §2. State lives in RAM because TAPIN trashes
                ; all registers on every call.
load_loop:
                call    TAPIN
                jp      c,bl_tape_dio       ; D-CASRBRK: Ctrl-STOP in the data -> 19
                ld      hl,(CURPTR)
                ld      (hl),a              ; store the byte
                ld      de,(ENDPTR)
                ld      a,h
                cp      d
                jr      nz,load_next        ; high bytes differ -> more to do
                ld      a,l
                cp      e
                jr      z,load_done         ; cur == end -> last byte stored
load_next:
                inc     hl
                ld      (CURPTR),hl
                jr      load_loop

load_done:
                jp      TAPIOF              ; motor off; its `ret` ends the tape load
                ; ✅ D-CASOFS2X (2026-10-19): this was `call TAPIOF` and FELL INTO
                ; bl_apply_ofs, adding BL_OFS a SECOND time after the data (to
                ; CURPTR, ENDPTR and EXECPTR), so `BLOAD"CAS:X",R,ofs` ran exec +
                ; 2 x ofs. Measured (scratchpad/casofs_probe.py, our own tape): the
                ; VG-8020 runs exec + ofs. The tail call is the same 3 bytes; the
                ; header's single bl_apply_ofs above is the only add now, as on the
                ; disk path (disk.rom's hk_dpbload).

; bl_apply_ofs -- D-BLOADOFS: add BL_OFS (main's pcr_bload) to the header's
; start, end and exec, wrapping at 16 bits, as the CF-3300 does to all three.
bl_apply_ofs:
                ld      de,(BL_OFS)
                ld      hl,(CURPTR)
                add     hl,de
                ld      (CURPTR),hl
                ld      hl,(ENDPTR)
                add     hl,de
                ld      (ENDPTR),hl
                ld      hl,(EXECPTR)
                add     hl,de
                ld      (EXECPTR),hl
                ret

; (load_handoff -- the tenant's do-nothing `ret` for the ,R tail, with a resident
; `jp (hl)` arm from the lean-cart days -- is GONE, 2026-10-19: its one caller was
; the disk path's `jp load_handoff`, which left with the disk load. The ,R hand-off
; was always main's (basic/bload.asm load_handoff / lh_back, the $6CF3 pin's
; continuation); RUNFLAG and EXECPTR reach it in RAM.)

; ===========================================================================
; Disk path: build the 8.3 name, then hand the load to MAIN, which crosses to
; disk.rom.
;
; On entry to is_disk: the top of the stack holds the filename start (the
; char after the opening quote), and HL points partway through the prefix
; comparison (it must NOT be trusted — restore from the stack). DE was
; pointing into dev_cas (don't care).
;
; FCB convention (CP/M / MSX-DOS, MSX2 TH): drive code 0=default, 1=A, 2=B.
; The 11-byte 8.3 name field is space-padded ($20), upper-cased. See
; basic/sysvars.inc DISK_FCB and PROVENANCE.md §disk-BLOAD scratch FCB.
is_disk:
                pop     hl                  ; HL = filename start (staged copy)
                ; D-NODISKVERBS (2026-10-07): with no disk the CASSETTE is the
                ; default device (VG-8020), and a drive name is 56. Main's
                ; nodisk_dev cannot be called from here (main page 1 is switched
                ; out), so the rule is restated: the tape path never reads the
                ; name (TAPION takes the next file).
                ld      a,(DISKSLOT_OK)
                or      a
                jr      nz,isd_disk
                inc     hl
                ld      a,(hl)
                cp      ':'
                jr      nz,isd_tape
                ld      a,56                ; Bad file name -- main raises it
                ld      (BL_STAT),a
                ret
isd_tape:
                dec     hl                  ; D-CASBIN: back to the name's FIRST char --
                                            ; is_tape now reads the name (the `cp ':'`
                                            ; above stepped one past it)
                push    hl                  ; is_tape drops the saved name start
                jp      is_tape
isd_disk:
                ; 🏗️ D-ROMSIZE step 1 (2026-10-19): THE LOAD IS disk.rom's NOW. This
                ; was `jr do_disk_bload` -- mount, find, the $FE header, the offset
                ; and the data loop, here, over the sub-ROM's own copies of
                ; fat-prim-body.inc's read half and fatio-body.inc: the LAST disk
                ; verb on this ROM's FAT engine. The CF-3300's BLOAD enters $FE5D
                ; once, as LOAD does (disk/docs/spec-diskcode-eviction.md §6.6ab /
                ; §8.2), so the tenant builds the name and answers BL_STAT =
                ; FOPEN_SEL_BLOAD; main crosses H_FOPEN with it (basic/bload.asm)
                ; and disk.rom's hk_dpbload runs that loop over its own FAT.
                ; The tail was parsed by main's pcr_bload (D-BLOADOFS).
                call    parse_disk_fcb      ; DISK_FCB_DRV + DISK_FCB_NAME; a bad drive
                                            ; or name files 62 / 56 and returns HERE
                ld      hl,BL_STAT
                ld      a,(hl)
                or      a
                ret     nz                  ; 62 / 56: main raises it; nothing is read
                ld      (hl),FOPEN_SEL_BLOAD ; a disk file, its name built: main loads
                ret                         ;  it through disk.rom

                include "basic/pdfcb-body.inc"

; (do_disk_bload .. disk_load_fin -- the disk load: mount, find, the $FE marker,
; the six header bytes, the offset, the data into RAM or through WRTVRM, with
; bl_notfound's 53 and bl_badmode's 61 -- MOVED to disk.rom on 2026-10-19 as
; hk_dpbload (disk/kernel.asm), the same exits in the same order.)
