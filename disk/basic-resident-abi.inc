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

widen_rhs_operand equ 038FCH
round_single_and_pack equ 03437H
round_and_finalize equ 033DDH
pu_deref_body equ 028C1H
ARGA equ 0F06AH   ; operand A / working result, FPNUM record (18)
STRSCR equ 0E26DH   ; [len][bytes:STRMAX] staging, $E26D..$E36C
FN_RESUME equ 0E227H   ; D-FNEXPR: cursor past a filename expr (2 B)
DISKOP_STATUS equ 0E9FCH   ; tenant -> main: the disposition (1 B)
DISK_FCB_NAME equ 0E0DCH   ; +1..+11: 8.3 name field (11 bytes)
FILES_HASPAT equ 0F009H   ; FILES: 1 = a filespec pattern is in DISK_FCB_NAME (1)
FAC equ 0F01CH   ; float accumulator: value bytes as tokenised (8)
FACTYP equ 0F01AH   ; 2=int / 4=single / 8=double (1)
FSECTOR_BUF equ 0E5C0H   ; file data / read sector buffer ($E5C0..$E7BF)
FWBUF equ 0E7C0H   ; FAT/dir metadata sector buffer ($E7C0..$E9BF)
FLD_CHAN equ 0E01BH   ; FIELD/LSET/RSET: the channel being fielded (1)
LRSET_W equ 0E01DH   ; LSET/RSET: destination field width (1)
LRSET_DEST equ 0E01EH   ; LSET/RSET: destination ADDRESS of the store (2). (2 B)
STRPTR equ 0E0C9H   ; pointer to the [len][bytes] descriptor (2 bytes)
DISKOP_OP equ 0E9FBH   ; main -> tenant: DISKOP_SEL_* primitive selector (1)
DISKOP_ERR equ 0E098H   ; tenant -> main: ERR code of the last DSKIO failure, 0 = none (1)
CLPTR equ 0E02BH   ; CLOAD/LOAD: store cursor into the program area (2)
CLINK equ 0E02DH   ; CLOAD/LOAD: saved link word of the current line
TXTBASE equ 08001H   ; text base (oracle: TXTTAB value after boot)
TXTMAX equ 0DB00H   ; repack: text ceiling. DETOKBUF sits immediately
PRGEND equ 0E026H   ; addr of the $0000 end-of-program marker (2 bytes)
DSV_PTR equ 0E0EDH   ; SAVE: current source byte pointer (2)
DSV_END equ 0E0EFH   ; SAVE/BSAVE: last source byte addr, inclusive (2)
DISKSLOT_OK equ 0E0E8H   ; 1 = DISKSLOT holds a valid disk-ROM slot id (1 B)
main_FWR_DIRSEC equ 0E9F7H   ; main's FWR_DIRSEC -- logical sector holding the open file's dir entry (word)
main_FWR_DIROFF equ 0E9F9H   ; main's FWR_DIROFF -- byte offset of that dir entry within its sector (word)
COPY_SRC equ 0E080H   ; the source's 11-byte 8.3 name field
COPY_CLUS equ 0E08BH   ; the source's first cluster (word)
COPY_LEFT equ 0E08DH   ; bytes still to copy (4-byte LE)
FILES_ENTIDX equ 0E0FCH   ; FILES: dir entry index 0..15 within a sector (1)
LPTPOS equ 0EA39H   ; printer head column, 0-based (1)

; --- page-1 call-back targets: reached by an INTER-SLOT call (MSX2 TH), not an absolute one ---
fname_expr equ 06DD5H
pdfcb_resume equ 06DCEH
dirverb_op equ 06BB4H
main_fat_mount equ 063BAH   ; main's fat_mount
main_fat_find equ 063BEH   ; main's fat_find
parse_disk_fcb equ 0655FH
fat_count_free equ 063EDH
field_prologue equ 0720BH
field_item equ 07241H
lrset_tgt equ 072FEH
lrset_rhs equ 07320H
lrset_finish equ 07337H
