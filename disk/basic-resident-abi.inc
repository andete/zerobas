; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; disk ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.
;
; Clean-room: every value below is an address inside THIS project's own
; main ROM, read out of our own build's symbol file. Nothing here is derived
; from a disassembly or byte-copy of any reference ROM.

widen_rhs_operand equ 038DCH
round_single_and_pack equ 03417H
round_and_finalize equ 033BDH
pu_deref_body equ 028C1H
ARGA equ 0F06AH   ; operand A / working result, FPNUM record (18)
STRSCR equ 0E26DH   ; $E26D: [len][bytes:STRMAX] staging
FN_RESUME equ 0E227H   ; D-FNEXPR: text cursor just past a filename
DISKOP_STATUS equ 0E9FCH   ; tenant -> main: 0 = ok (Cy=0 / Z set); nonzero =
DISK_FCB_NAME equ 0E0DCH   ; +1..+11: 8.3 name field (11 bytes)
FILES_HASPAT equ 0F009H   ; FILES: 1 = a filespec pattern is in DISK_FCB_NAME (1)
FAC equ 0F01CH   ; float accumulator: value bytes as tokenised (8)
FACTYP equ 0F01AH   ; 2=int / 4=single / 8=double (1)
FSECTOR_BUF equ 0E5C0H   ; file data / read sector buffer ($E5C0..$E7BF)
FLD_CHAN equ 0E01BH   ; FIELD/LSET/RSET: the channel being fielded (1)
LRSET_W equ 0E01DH   ; LSET/RSET: destination field width (1)
LRSET_DEST equ 0E01EH   ; LSET/RSET: destination ADDRESS of the store (2).
STRPTR equ 0E0C9H   ; pointer to the [len][bytes] descriptor (2 bytes)
DISKOP_OP equ 0E9FBH   ; main -> tenant: DISKOP_SEL_* primitive selector (1)
DISKOP_ERR equ 0E098H   ; tenant -> main: ERR code of the last DSKIO failure, 0 = none (1)
CLPTR equ 0E02BH   ; CLOAD/LOAD: store cursor into the program area (2)
CLINK equ 0E02DH   ; CLOAD/LOAD: saved link word of the current line
TXTBASE equ 08001H   ; text base (oracle: TXTTAB value after boot)
TXTMAX equ 0DB00H   ; repack: text ceiling. DETOKBUF sits immediately

; --- page-1 call-back targets: reached by an INTER-SLOT call (MSX2 TH), not an absolute one ---
fname_expr equ 06E6EH
pdfcb_resume equ 06E67H
dirverb_op equ 06C4DH
main_fat_mount equ 0641CH   ; main's fat_mount
main_fat_find equ 06420H   ; main's fat_find
parse_disk_fcb equ 065C1H
fat_count_free equ 0644FH
field_prologue equ 07265H
field_item equ 0729BH
lrset_tgt equ 07358H
lrset_rhs equ 0737AH
lrset_finish equ 07391H
