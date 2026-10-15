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

widen_rhs_operand equ 03857H
round_single_and_pack equ 03397H
round_and_finalize equ 03343H
pu_deref_body equ 0284CH
subrom_call equ 03B4DH
ARGA equ 0F806H   ; operand A / working result, FPNUM record (18)
STRSCR equ 0F55EH   ; = BUF ($F55E): [len][bytes:STRMAX] staging (256 B)
FN_RESUME equ 0F6BCH   ; D-FNEXPR: cursor past a filename expr (2 B) -- published TEMP2 (D-WSZERO)
DISKOP_STATUS equ 0EE39H   ; tenant -> main: the disposition (1 B)
DISK_FCB_NAME equ 0EF49H   ; +1..+11: 8.3 name field (11 bytes)
FILES_HASPAT equ 0F09DH   ; FILES: 1 = a filespec pattern is in DISK_FCB_NAME (1)
FAC equ 0F7F6H   ; float accumulator = DAC: value bytes as tokenised (8)
FPERR equ 0F7B9H   ; runtime numeric-error flag: 0 none / 1 overflow / (1 B)
FACTYP equ 0F09EH   ; 2=int / 4=single / 8=double (1)
FSECTOR_BUF equ 0E46AH   ; DISK-ONLY: file data / read sector buffer ($E46A..$E669)
FWBUF equ 0E66AH   ; DISK-ONLY: FAT/dir metadata sector buffer ($E66A..$E869)
FLD_CHAN equ 0EEC5H   ; FIELD/LSET/RSET: the channel being fielded (1)
LRSET_W equ 0EEC7H   ; LSET/RSET: destination field width (1)
LRSET_DEST equ 0EEC8H   ; LSET/RSET: destination ADDRESS of the store (2). (2 B)
STRPTR equ 0EF36H   ; pointer to the [len][bytes] descriptor (2 bytes)
DISKOP_OP equ 0EE38H   ; main -> tenant: DISKOP_SEL_* primitive selector (1)
DISKOP_ERR equ 0EF06H   ; tenant -> main: ERR code of the last DSKIO failure, 0 = none (1)
CLPTR equ 0F6EDH   ; CLOAD/LOAD: store cursor into the program area (2)
CLINK equ 0F6EFH   ; CLOAD/LOAD: saved link word of the current line
TXTBASE equ 08001H   ; text base (oracle: TXTTAB value after boot)
TXTTAB equ 0F676H   ; sysvar: pointer to the BASIC text base
TXTMAX equ 0E36AH   ; NOT-A-CELL: the text ceiling (= the workspace floor)
TXTMAX_NODISK equ 0ECF8H   ; NOT-A-CELL: the diskless build's text ceiling
PRGEND equ 0F6E8H   ; addr of the $0000 end-of-program marker (2 bytes)
DSV_PTR equ 0EF59H   ; SAVE: current source byte pointer (2)
DSV_END equ 0EF5BH   ; SAVE/BSAVE: last source byte addr, inclusive (2)
DISKSLOT_OK equ 0EF55H   ; 1 = DISKSLOT holds a valid disk-ROM slot id (1 B)
main_FWR_DIRSEC equ 0EE34H   ; main's FWR_DIRSEC -- logical sector holding the open file's dir entry (word)
main_FWR_DIROFF equ 0EE36H   ; main's FWR_DIROFF -- byte offset of that dir entry within its sector (word)
COPY_SRC equ 0EEEEH   ; the source's 11-byte 8.3 name field
COPY_CLUS equ 0EEF9H   ; the source's first cluster (word)
COPY_LEFT equ 0EEFBH   ; bytes still to copy (4-byte LE)
FILES_ENTIDX equ 0EF63H   ; FILES: dir entry index 0..15 within a sector (1)
LPTPOS equ 0EE76H   ; printer head column, 0-based (1)
FCH_ACTIVE equ 0EEBEH   ; channel live in the engine globals, 0 = none (1)
FCH_MODES equ 0EE3DH   ; 16 B ($EE3D..$EE4C)
FCH_STATESZ equ 00032H   ; $E9C9..$E9FA inclusive = 50 bytes
FCH_CEIL equ 0000FH   ; repack: the MEASURED reference ceiling (§3, exactly
LPT_MODE equ 00005H   ; FCH_MODES value: channel open to the LPT: printer device
DOUT_MODE equ 00003H   ; FCH_MODES value: disk OUTPUT through disk.rom's FCB
DOUT_BLK equ 00025H   ; its row: +0..36 the FCB, +37..38 the channel's
DOUT_FLG equ 00027H   ; 265 B block, +39 flags (DOUT_RFULL / DOUT_DEAD)
DOUT_RFULL equ 00000H   ; bit: the record is full and not yet written
DOUT_DEAD equ 00001H   ; bit: a CLOSE failed; the next CLOSE frees it
main_FAT_FILESIZE equ 0EE0BH   ; main's FAT_FILESIZE -- file size in bytes (4-byte LE)
main_FWR_BYTES equ 0EE30H   ; main's FWR_BYTES -- total bytes written so far = final file size (4-byte LE)
FMT_GEOMSEL equ 0EF61H   ; main -> tenant: 0 = 360k, 1 = 720k (1)
FMT_RESULT equ 0EF62H   ; tenant -> main: 0 = ok, 1 = DSKIO write error (1)
LINEBUF equ 0F55EH   ; repack: ASCII input line = the reference's BUF (LINEMAX B) (1 B)
SUBROM_ENTRY_BASE_P1 equ 04010H   ; sub-ROM page-1 jp-table base
SUBROM_IDX_FORMAT equ 0000AH   ; format_tenant (CALL FORMAT eviction, sub/

; --- page-1 call-back targets: reached by an INTER-SLOT call (MSX2 TH), not an absolute one ---
fname_expr equ 06E14H
pdfcb_resume equ 06E0DH
main_fat_mount equ 06468H   ; main's fat_mount
main_fat_find equ 0646CH   ; main's fat_find
parse_disk_fcb equ 06522H
field_prologue equ 072E2H
field_item equ 07318H
lrset_tgt equ 073CDH
lrset_rhs equ 073EFH
lrset_finish equ 07406H
fch_ctx_addr equ 06F9EH
disk_error equ 06BAAH
read_line equ 045FBH
fch_close_all equ 0709EH
