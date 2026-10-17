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

widen_rhs_operand equ 0380EH
round_single_and_pack equ 0339BH
round_and_finalize equ 03347H
pu_deref_body equ 0286FH
subrom_call equ 03ABAH
ARGA equ 0F806H   ; operand A / working result, FPNUM record (18)
STRSCR equ 0F55EH   ; = BUF ($F55E): [len][bytes:STRMAX] staging (256 B)
FN_RESUME equ 0F6BCH   ; D-FNEXPR: cursor past a filename expr (2 B) -- published TEMP2 (D-WSZERO)
DISKOP_STATUS equ 0FCAEH   ; tenant -> main: the disposition (1 B)
DISK_FCB_NAME equ 0EF49H   ; DISK-ONLY: +1..+11: 8.3 name field (11 bytes)
FILES_HASPAT equ 0F09DH   ; DISK-ONLY: FILES: 1 = a filespec pattern is in DISK_FCB_NAME (1)
FAC equ 0F7F6H   ; float accumulator = DAC: value bytes as tokenised (8)
FPERR equ 0F7B9H   ; runtime numeric-error flag: 0 none / 1 overflow / (1 B)
FACTYP equ 0F663H   ; 2=int / 4=single / 8=double (1)
FSECTOR_BUF equ 0E46AH   ; DISK-ONLY: file data / read sector buffer ($E46A..$E669)
FWBUF equ 0E66AH   ; DISK-ONLY: FAT/dir metadata sector buffer ($E66A..$E869)
STRPTR equ 0F954H   ; pointer to the [len][bytes] descriptor (2 bytes)
DISKOP_OP equ 0FCACH   ; main -> tenant: DISKOP_SEL_* primitive selector (1)
DISKOP_ERR equ 0FC9AH   ; tenant -> main: ERR code of the last DSKIO failure, 0 = none (1)
CLPTR equ 0F6EDH   ; CLOAD/LOAD: store cursor into the program area (2)
CLINK equ 0F6EFH   ; CLOAD/LOAD: saved link word of the current line
TXTBASE equ 08001H   ; text base (oracle: TXTTAB value after boot)
TXTTAB equ 0F676H   ; sysvar: pointer to the BASIC text base
TXTMAX equ 0E36AH   ; NOT-A-CELL: the text ceiling (= the workspace floor)
TXTMAX_NODISK equ 0F380H   ; NOT-A-CELL: the diskless build's text ceiling
PRGEND equ 0F6E8H   ; addr of the $0000 end-of-program marker (2 bytes)
DSV_PTR equ 0EF59H   ; DISK-ONLY: SAVE: current source byte pointer (2)
DSV_END equ 0EF5BH   ; DISK-ONLY: SAVE/BSAVE: last source byte addr, inclusive (2)
DISKSLOT_OK equ 0FB21H   ; 1 = DISKSLOT holds a valid disk-ROM slot id (1 B)
main_FWR_DIRSEC equ 0EE34H   ; main's FWR_DIRSEC -- DISK-ONLY: logical sector holding the open file's dir entry (word)
main_FWR_DIROFF equ 0EE36H   ; main's FWR_DIROFF -- DISK-ONLY: byte offset of that dir entry within its sector (word)
COPY_SRC equ 0EEEEH   ; DISK-ONLY: the source's 11-byte 8.3 name field
COPY_CLUS equ 0EEF9H   ; DISK-ONLY: the source's first cluster (word)
COPY_LEFT equ 0EEFBH   ; DISK-ONLY: bytes still to copy (4-byte LE)
FILES_ENTIDX equ 0EF63H   ; DISK-ONLY: FILES: dir entry index 0..15 within a sector (1)
LPTPOS equ 0F415H   ; printer head column, 0-based (1)
FCH_ACTIVE equ 0F733H   ; channel live in the engine globals, 0 = none (1)
FCH_MODES equ 0F71CH   ; 16 B ($F71C..$F72B)
FCH_STATESZ equ 00032H   ; $E9C9..$E9FA inclusive = 50 bytes
FCH_CEIL equ 0000FH   ; repack: the MEASURED reference ceiling (§3, exactly
LPT_MODE equ 00005H   ; FCH_MODES value: channel open to the LPT: printer device
DOUT_MODE equ 00003H   ; FCH_MODES value: disk OUTPUT through disk.rom's FCB
DOUT_BLK equ 00025H   ; its row: +0..36 the FCB, +37..38 the channel's
FCH_RECMAX equ 00100H   ; the largest record (the OPEN LEN= domain is 1..256)
DOUT_FLG equ 00027H   ; 265 B block, +39 flags (DOUT_RFULL / DOUT_DEAD)
DOUT_RFULL equ 00000H   ; bit: the record is full and not yet written
DOUT_DEAD equ 00001H   ; bit: a CLOSE failed; the next CLOSE frees it
main_FAT_FILESIZE equ 0EE0BH   ; main's FAT_FILESIZE -- DISK-ONLY: file size in bytes (4-byte LE)
main_FWR_BYTES equ 0EE30H   ; main's FWR_BYTES -- DISK-ONLY: total bytes written so far = final file size (4-byte LE)
FCH_RECLENS equ 0EE4DH   ; DISK-ONLY: 32 B ($EE4D..$EE6C). ~~$EA92..$EAFF free (110 B)~~
FCH_RECNOS equ 0EE7DH   ; DISK-ONLY: 32 B ($EE7D..$EE9C): per-channel record number
GP_RECNO equ 0F079H   ; DISK-ONLY: record number, 1-based (2 B)
GP_SEC equ 0F07BH   ; DISK-ONLY: file logical-sector index of the record (2)
GP_WITHIN equ 0F07DH   ; DISK-ONLY: byte offset of the record within its sector (0/256, 2) (2 B)
GP_CLUS equ 0F07FH   ; DISK-ONLY: current cluster during the chain walk (2)
GP_CLIDX equ 0F081H   ; DISK-ONLY: cluster steps still to walk (2)
GP_SECINCL equ 0F083H   ; DISK-ONLY: sector index within the final cluster (1)
GP_PHYS equ 0F084H   ; DISK-ONLY: resolved absolute physical sector (2)
GP_FLAGS equ 0F088H   ; DISK-ONLY: bit0 = extend (PUT allocates; GET does not) (1)
GP_RECLEN equ 0F09AH   ; DISK-ONLY: active channel's record length (word), loaded per calc
GP_SRC equ 0EE77H   ; DISK-ONLY: pass cursor into FSECTOR_BUF (2)
GP_LEFT equ 0EE79H   ; DISK-ONLY: record bytes still to move, ends $EA3E (2 B)
FCH_RDMODE equ 0F6A6H   ; current read: 0=INPUT# (stop at ','/CR), 1=LINE (1)
STRMAX equ 000FFH   ; repack build: string heap (slice-4a §8)
FMT_GEOMSEL equ 0EF61H   ; DISK-ONLY: main -> tenant: 0 = 360k, 1 = 720k (1)
FMT_RESULT equ 0EF62H   ; DISK-ONLY: tenant -> main: 0 = ok, 1 = DSKIO write error (1)
LINEBUF equ 0F55EH   ; repack: ASCII input line = the reference's BUF (LINEMAX B) (1 B)
SUBROM_ENTRY_BASE_P1 equ 04010H   ; sub-ROM page-1 jp-table base
SUBROM_IDX_FORMAT equ 0000AH   ; format_tenant (CALL FORMAT eviction, sub/

; --- page-1 call-back targets: reached by an INTER-SLOT call (MSX2 TH), not an absolute one ---
fname_expr equ 06DFEH
pdfcb_resume equ 06DF7H
main_fat_mount equ 06451H   ; main's fat_mount
main_fat_find equ 06455H   ; main's fat_find
parse_disk_fcb equ 06514H
field_prologue equ 07348H
field_item equ 072F6H
lrset_tgt equ 073C5H
lrset_rhs equ 073E8H
lrset_finish equ 07258H
fch_ctx_addr equ 06F7DH
disk_error equ 06B96H
read_line equ 045FBH
fch_close_all equ 0706CH
eval_int16_checked equ 0454AH
fch_select equ 06FB2H
raise_error equ 04326H
