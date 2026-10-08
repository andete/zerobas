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

widen_rhs_operand equ 0386CH
round_single_and_pack equ 033ACH
round_and_finalize equ 03358H
pu_deref_body equ 0287AH
subrom_call equ 03B62H
ARGA equ 0F06AH   ; operand A / working result, FPNUM record (18)
STRSCR equ 0E26DH   ; [len][bytes:STRMAX] staging, $E26D..$E36C
FN_RESUME equ 0E227H   ; D-FNEXPR: cursor past a filename expr (2 B)
DISKOP_STATUS equ 0E9FCH   ; tenant -> main: the disposition (1 B)
DISK_FCB_NAME equ 0E0DCH   ; +1..+11: 8.3 name field (11 bytes)
FILES_HASPAT equ 0F009H   ; FILES: 1 = a filespec pattern is in DISK_FCB_NAME (1)
FAC equ 0F7F6H   ; float accumulator = DAC: value bytes as tokenised (8)
FPERR equ 0F069H   ; runtime numeric-error flag: 0 none / 1 overflow / (1 B)
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
TXTMAX equ 0E000H   ; NOT-A-CELL: the text ceiling (= the workspace floor)
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
FCH_ACTIVE equ 0E012H   ; channel live in the engine globals, 0 = none (1)
FCH_MODES equ 0EA00H   ; 16 B ($EA00..$EA0F)
FCH_STATESZ equ 00032H   ; $E9C9..$E9FA inclusive = 50 bytes
FCH_CEIL equ 0000FH   ; repack: the MEASURED reference ceiling (§3, exactly
LPT_MODE equ 00005H   ; FCH_MODES value: channel open to the LPT: printer device
DOUT_MODE equ 00003H   ; FCH_MODES value: disk OUTPUT through disk.rom's FCB
DOUT_BLK equ 00025H   ; its row: +0..36 the FCB, +37..38 the channel's
DOUT_FLG equ 00027H   ; 265 B block, +39 flags (DOUT_RFULL / DOUT_DEAD)
DOUT_RFULL equ 00000H   ; bit: the record is full and not yet written
DOUT_DEAD equ 00001H   ; bit: a CLOSE failed; the next CLOSE frees it
main_FAT_FILESIZE equ 0E9CEH   ; main's FAT_FILESIZE -- file size in bytes (4-byte LE)
main_FWR_BYTES equ 0E9F3H   ; main's FWR_BYTES -- total bytes written so far = final file size (4-byte LE)
FMT_GEOMSEL equ 0E0F5H   ; main -> tenant: 0 = 360k, 1 = 720k (1)
FMT_RESULT equ 0E0F6H   ; tenant -> main: 0 = ok, 1 = DSKIO write error (1)
LINEBUF equ 0EB00H   ; repack: ASCII input line from the keyboard (LINEMAX B) (1 B)
SUBROM_ENTRY_BASE_P1 equ 04010H   ; sub-ROM page-1 jp-table base
SUBROM_IDX_FORMAT equ 0000AH   ; format_tenant (CALL FORMAT eviction, sub/

; --- page-1 call-back targets: reached by an INTER-SLOT call (MSX2 TH), not an absolute one ---
fname_expr equ 06E67H
pdfcb_resume equ 06E60H
dirverb_op equ 06C0EH
main_fat_mount equ 06549H   ; main's fat_mount
main_fat_find equ 0654DH   ; main's fat_find
parse_disk_fcb equ 065FFH
field_prologue equ 07293H
field_item equ 072C9H
lrset_tgt equ 0737EH
lrset_rhs equ 073A0H
lrset_finish equ 073B7H
fch_ctx_addr equ 06FF7H
disk_error equ 06C30H
read_line equ 045C5H
