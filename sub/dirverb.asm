; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — dirverb.asm  (directory-verb I/O-body tenant)
; ===========================================================================
; The disk I/O bodies of the directory verbs KILL and NAME, evicted from the
; repack main ROM's basic/files.asm into sub-ROM PAGE 1 (docs/spec-evict-
; diskfile-cluster.md §12, Phase 2 of the disk/file cluster eviction). The
; verbs' eval/parse heads (parse_disk_fcb, the "AS" scan, DISKSLOT_OK check)
; stay MAIN-RESIDENT -- a page-1 tenant cannot reach eval/the parser -- and
; marshal their result into DISK_FCB_NAME / FWR_DIRSEC / FWR_DIROFF (page-3 RAM,
; visible from both sides) before a single subrom_call hands off to this tenant
; for the CALSLT-side sector work (spec §3 head/body split).
;
; ONE index, SELECTOR-DISPATCHED (like fatprim_tenant): DISKOP_OP picks KILL's
; delete loop vs NAME's dir-entry stamp. Both bodies call the Phase-1 FAT12
; primitives (fat_delete / read_sector / fatprim_write_sector, basic/fat-prim-
; body.inc + basic/fat-delete-body.inc, already in this sub.rom assembly)
; SUB-LOCALLY -- no nested marshalling, no subrom_call, since those primitives
; are co-resident in the tenant's own page 1. This is exactly why Phase 2 is
; cheap: Phase 1 already put the heavy sector/cluster engine here, so a verb
; body is just a short orchestration over sub-local calls.
;
; RESULT MARSHALLING. Cy cannot ride back through subrom_call/CALSLT (its own
; `or a` clears it, sub/format.asm's rule), so each body funnels its
; disposition into DISKOP_STATUS (basic/sysvars.inc); the resident head reads
; it back. The two bodies use DIFFERENT status polarity, each interpreted only
; by its OWN head:
;   * NAME_STAMP -- STATUS = 0 ok / 1 error (standard, like fatprim).
;   * KILL       -- STATUS = deleted-any flag (0 = nothing matched -> the head
;                   raises "File not found" via load_error; nonzero = ok). This
;                   mirrors basic/files.asm's ORIGINAL do_kill semantics
;                   bug-for-bug: a real I/O error mid-loop is treated (as
;                   before) as "no further match" -- fat_delete's Cy stops the
;                   loop, and success is reported iff at least one entry was
;                   freed before the error (the earlier resident build did exactly
;                   this).
;
; CLEAN-ROOM: original code (the dispatch/marshalling glue is own-design, the
; CALL FORMAT / fatprim precedent + MSX2 Technical Handbook CALSLT ABIs). The
; sector work reuses our own basic/fat.asm primitives via the shared bodies;
; KILL/NAME *semantics* trace to basic/files.asm's headers (public MSX-BASIC
; language reference + black-box CF-3300). No reference-ROM disassembly.
; ===========================================================================

; --- dirverb_tenant: the SUBROM_IDX_DIRVERB entry --------------------------
; Read DISKOP_OP (RAM, set by the resident head before subrom_call) and branch
; to the requested body. Only two ops, so a plain test beats a jp table. HL/DE
; are irrelevant on entry (both bodies read all inputs from RAM), so nothing
; needs preserving through the dispatch.
dirverb_tenant:
                ld      a,(DISKOP_OP)
                or      a
                jp      z,tnt_kill              ; DISKOP_SEL_KILL = 0
                ; fall through -> DISKOP_SEL_NAME_STAMP = 1

; --- NAME "old" AS "new": stamp the new 8.3 name over the located dir entry --
; Inputs (from the resident head): FWR_DIRSEC/FWR_DIROFF locate the OLD file's
; directory entry (the head already ran fat_mount + fat_find via the resident
; shims); DISK_FCB_NAME holds the NEW 8.3 name. Read that dir sector, overwrite
; the 11-byte name field in place, write it back. Byte-for-byte the same logic
; as basic/files.asm's do_name tail.
tnt_name_stamp:
                ld      de,(FWR_DIRSEC)
                ld      hl,FSECTOR_BUF
                call    read_sector            ; sub-local primitive body
                jr      c,dv_err
                ld      hl,FSECTOR_BUF
                ld      de,(FWR_DIROFF)
                add     hl,de                  ; HL -> the entry in the buffer
                ex      de,hl                  ; DE -> dest name field
                ld      hl,DISK_FCB_NAME       ; source = the new 8.3 name
                ld      bc,11
                ldir                           ; overwrite the 11-byte 8.3 name
                ld      de,(FWR_DIRSEC)
                ld      hl,FSECTOR_BUF
                call    fatprim_write_sector   ; sub-local (renamed) primitive
                jr      c,dv_err
                xor     a
                ld      (DISKOP_STATUS),a       ; ok
                ret
dv_err:
                ld      a,1
                ld      (DISKOP_STATUS),a       ; error -> head does load_error
                ret

; --- KILL "name": delete every matching entry ------------------------------
; Input: DISK_FCB_NAME holds the 8.3 wildcard pattern. fat_delete frees + $E5-
; marks the FIRST match per call (name_cmp honours '?'/'*'), so loop until no
; match remains. C accumulates the deleted-any flag; DISKOP_STATUS carries it
; back (0 -> the head raises "File not found").
tnt_kill:
                ld      c,0                     ; C = deleted-any flag
dvk_loop:
                push    bc
                call    fat_delete             ; sub-local primitive body
                pop     bc
                jr      c,dvk_done              ; no (further) match -> stop
                ld      c,1                     ; deleted at least one
                jr      dvk_loop
dvk_done:
                ld      a,c
                ld      (DISKOP_STATUS),a       ; deleted-any (0 = none)
                ret
