; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — dirverb.asm  (DSKO$ / DSKI$ raw-sector tenant)
; ===========================================================================
; 🔴 THE NAME IS HISTORY NOW, AND SAYING SO IS CHEAPER THAN A RENAME. This
; file held the disk I/O bodies of the DIRECTORY verbs -- KILL, NAME, COPY,
; FILES and LFILES -- evicted from the repack main ROM into sub-ROM PAGE 1
; (docs/spec-evict-diskfile-cluster.md §12, Phase 2). **Every one of them has
; since moved on into `disk.rom`**, where the reference keeps them and where
; Joost ruled they belong (*"we do as the reference does"*):
;   * NAME's dir stamp   -- D-NAMESTAMP, spec-diskcode-eviction.md §6.6aw
;   * KILL's delete loop -- D-KILLLOCAL,  §6.6ay
;   * COPY, both halves  -- D-COPYLOCAL,  §6.6az
;   * FILES / LFILES     -- D-FILESLOCAL, §6.6ba
; Each move deleted a THREE-ROM ROUND TRIP: the disk-ROM handler used to call
; BACK into main purely so main could `subrom_call` on to this tenant, whose
; bodies then ran FAT primitives `disk.rom` has had of its own since steps
; 9/11/12 of §6.2.
;
; ⚠️ WHAT IS LEFT IS NOT A DIRECTORY VERB AT ALL: DSKO$ and DSKI$, one raw
; sector between (DSKBUF_PTR) and sector FWR_DIRSEC, no mount and no BPB. They
; stay because they are called from MAIN (`dirverb_op`), not from a disk-ROM
; hook -- there is no hook cell for them to follow, so the round trip the four
; verbs above were paying does not exist here.
; ➡️ RESIDUAL, FILED NOT DONE: the tenant, its file, its `dirverb_op` veneer
; and SUBROM_IDX_DIRVERB all still carry the directory-verb name. Renaming them
; is a mechanical change across the sub-ROM index, the resident ABI and main's
; veneer, and it is not free -- so the name is documented here rather than half
; changed.
;
; RESULT MARSHALLING, unchanged: Cy cannot ride back through subrom_call/CALSLT
; (its own `or a` clears it, sub/format.asm's rule), so the body funnels its
; disposition into DISKOP_STATUS (basic/sysvars.inc) and the resident head reads
; it back. `dsk_status` turns the primitive's Cy into $FF/0 for that head.
;
; CLEAN-ROOM: original code (the dispatch/marshalling glue is own-design, the
; CALL FORMAT / fatprim precedent + MSX2 Technical Handbook CALSLT ABIs). The
; sector work reuses our own basic/fat.asm primitives via the shared bodies;
; DSKO$/DSKI$ semantics trace to basic/files.asm's headers (public MSX-BASIC
; language reference + black-box CF-3300). No reference-ROM disassembly.
; ===========================================================================

; --- dirverb_tenant: the SUBROM_IDX_DIRVERB entry --------------------------
; Read DISKOP_OP (RAM, set by the resident head before subrom_call) and branch
; to the requested body. TWO ops now, a plain `cp`/`jp` chain: a jump table would
; cost more than it replaces. HL/DE are irrelevant on entry (both bodies read
; every input from RAM), so nothing needs preserving through the dispatch.
;
; ⚠️ THE OLD WARNING HERE IS RETIRED WITH ITS SUBJECT. It said DISKOP_OP is
; read AGAIN deep inside the FILES body -- that it is the SINK and LAYOUT
; selector as well as the dispatch key, and must survive the whole listing. That
; is still true of the code, but the code is `hkf_body` in disk/kernel.asm now,
; and the warning travelled with it. Nothing on THIS path reads DISKOP_OP after
; the dispatch.
dirverb_tenant:
                xor     a
                ld      (DISKOP_ERR),a      ; D-DISKERR: no DSKIO failure pending yet
                ld      a,(DISKOP_OP)
                cp      DISKOP_SEL_DSKO
                jp      z,tnt_dsko              ; 4 -> DSKO$ (D-DSKIO)
                cp      DISKOP_SEL_DSKI
                jp      z,tnt_dski              ; 5 -> DSKI$
                ; 🔴 SIX OF THE EIGHT OPS ARE NO LONGER SERVED HERE, AND THE
                ; BARE FALL-THROUGH WENT WITH THE FIRST OF THEM. Selector 1
                ; (NAME_STAMP) D-NAMESTAMP §6.6aw · selector 0 (KILL) D-KILLLOCAL
                ; §6.6ay · selectors 6 and 7 (COPY) D-COPYLOCAL §6.6az · selectors
                ; 2 and 3 (FILES/LFILES) D-FILESLOCAL §6.6ba. Each body runs on
                ; disk.rom's OWN FAT now, so its dispatch arm is gone and the op
                ; lands on the error tail rather than silently running whatever
                ; happens to follow -- which is what the fall-through did.
                ; ⚠️ fat_delete STAYS in this assembly: the fatprim tenant
                ; publishes it as DISKOP_SEL_FAT_DELETE.
                ; 🎯 TWO ARE LEFT, DSKO$ AND DSKI$, and they are not going
                ; anywhere: both are called from MAIN rather than from a disk-ROM
                ; hook, so there is no round trip to delete.
                jp      dv_err

; --- dv_err: the unrecognised-op tail ---------------------------------------
; ⚠️ THE HEADER THAT STOOD HERE DESCRIBED NAME'S DIR STAMP, whose body
; D-NAMESTAMP deleted (§6.6aw) -- it was left orphaned above a label that is not
; its subject, which is how a comment block outlives the code it explains. Every
; op this tenant no longer serves lands here.
dv_err:
                ld      a,1
                ld      (DISKOP_STATUS),a       ; error -> head does load_error
                ret

; --- DSKO$ / DSKI$: one sector between (DSKBUF_PTR) and sector FWR_DIRSEC ------
; D-DSKIO, docs/spec-basic-dskio.md §3. The head parsed drive and sector; the
; buffer is whatever DSKBUF_PTR names (FWBUF -- the DIRECTORY/RAW tier, NOT the
; open channel's FSECTOR_BUF; written at disk-ROM init, D-ALIASWCELL).
; No mount and no BPB: a raw sector needs neither, and the reference reads
; sector 9999 without complaint. STATUS = 0 ok, $FF = DSKIO error.
tnt_dsko:
                call    dsk_regs
                call    fatprim_write_sector    ; sub-local primitive body
                jr      dsk_status
tnt_dski:
                call    dsk_regs
                call    read_sector             ; sub-local primitive body
dsk_status:
                sbc     a,a                     ; CF -> $FF, clear -> 0
                ld      (DISKOP_STATUS),a
                ret
dsk_regs:
                ld      de,(FWR_DIRSEC)         ; the sector
                ld      hl,(DSKBUF_PTR)         ; the buffer
                ret


