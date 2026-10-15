#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S9, groups G6 / G3 / G2+G1 / G4: the disk-only cells made disk-only.
Each edit is anchored on exact text and refuses unless it matches exactly once."""
import sys

def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)} for {old[:60]!r}")
    open(path, "w").write(s.replace(old, new))

# G6: the two diskless DISKOP_ERR reads go through se_pending (3 B <-> 3 B, seg C)
edit("basic/files.asm", """seq_end:
                ld      a,(DISKOP_ERR)
""", """seq_end:
                call    se_pending          ; D-WSZERO S9: 0 without a disk ROM
""")
edit("basic/files.asm", """disk_error:
                ld      a,(DISKOP_ERR)
""", """disk_error:
                call    se_pending          ; D-WSZERO S9: 0 without a disk ROM
""")
# G3 + G6 + G2: the gated helpers, all in seg F (past every pin), after fld_lookup
edit("basic/field.asm", """fld_lookup:
                call    fld_find            ; CF set -> HL -> entry
""", """fld_lookup:
                call    diskslot_test       ; D-WSZERO S9: no disk ROM, no FIELD --
                ret     z                   ; CF=0 (the `or a`): not fielded
                call    fld_find            ; CF set -> HL -> entry
""")
edit("basic/field.asm", """                scf                         ; fielded
                ret

; (fat_rand_open / fat_rand_put / fat_rand_get""", """                scf                         ; fielded
                ret

; --- D-WSZERO S9 (2026-10-15): the disk-only cells, made disk-only in fact -----
; FLD_TAB and DISKOP_ERR are the disk machine's: on a diskless one no FIELD can
; exist and no DSKIO can fail. But a string-variable read walked the table
; (fld_lookup, above) and NEW / RUN / CLEAR re-wrote it, and a tape INPUT # past
; the end read the error cell -- so when the diskless ceiling rises over them
; (S15) a program's own bytes there would be read as fields and error codes. Each
; reader now asks diskslot_test first. They live here, past the $73E5 pin: the
; segments ahead of the pins have no free byte (tools/pin_plan.py).
; se_pending: A = the DSKIO failure code pending, 0 without a disk ROM. Z/NZ unset.
se_pending:
                call    diskslot_test
                ret     z                   ; A = 0: nothing pending
                ld      a,(DISKOP_ERR)
                ret
; fld_init_g: fld_init on a machine with a disk ROM, nothing without one.
fld_init_g:
                call    diskslot_test
                ret     z
                jp      fld_init

; (fat_rand_open / fat_rand_put / fat_rand_get""")
edit("basic/vars.asm", "                jp      fld_init            ; also reset the random-access field table\n",
     "                jp      fld_init_g          ; also reset the random-access field table (disk only)\n")
edit("basic/files.asm", "                jp      fld_init            ; empty the random-access field table\n",
     "                jp      fld_init_g          ; empty the random-access field table (disk only)\n")
# G1: VALTYP's write-only store goes; its 3 B pay for the post-scan fld_init_g
edit("basic/strvar.asm", """str_eval_ok:
                ld      a,1
                ld      (VALTYP),a
                scf
""", """str_eval_ok:
                ld      a,1                 ; (VALTYP's store went in D-WSZERO S9:
                                            ; nothing read it, in any image)
                scf
""")
edit("basic/interp.asm", """                call    init_ext_roms       ; run the boot-scan INITs C-BIOS skips
                ; D-KEYSTR (2026-09-10)""", """                call    init_ext_roms       ; run the boot-scan INITs C-BIOS skips
                ; D-WSZERO S9: the FIELD table is the disk machine's, and only HERE
                ; is DISKSLOT_OK known -- clear_vars and init_filechan above ran
                ; fld_init_g on power-on DRVINF. A disk machine is initialised now.
                call    fld_init_g
                ; D-KEYSTR (2026-09-10)""")
# G4: ERASE's key slide over FLD_TAB, disk only (sub page 0, no pins)
edit("sub/arrays.asm", """aer_fldfix:
                or      a
                sbc     hl,de               ; HL = stride (SRC - DST)
""", """aer_fldfix:
                ld      a,(DISKSLOT_OK)     ; D-WSZERO S9: no disk ROM, no field
                or      a                   ; table to slide (the caller keeps
                ret     z                   ; BC/DE/HL; A and the flags are free)
                or      a
                sbc     hl,de               ; HL = stride (SRC - DST)
""")
print("ok")

# G5 (LRSET_JUST from the token, ex_on_key across the $73AC pin) was applied
# by hand-anchored edits in the session; see TODO D-WSZERO S9.
