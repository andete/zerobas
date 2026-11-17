# Disk ROM entries + MSX-DOS 1 BDOS — per-entry CONTRACT inventory (2026-11-17)

D-DISKCONTRACT's queue, the disk-side twin of [bios_contract_inventory.md](bios_contract_inventory.md).
A read-only agent read the gate sources (no ROM, nothing run); the headline finding was then
VERIFIED by hand (`probes/disk/omsx_session.py:51`). (inf) = inferred, not read.

## 🔴 Headline: most BDOS / disk-ROM comparisons do not run on the shipped machine

`disk_probe_diff.py`'s "ours" is `OURS_MACHINE = os.environ.get("ZEROBAS_OURS_MACHINE",
"National_CF-3300_ZEROBASDISK")` -- our disk.rom under the **CF-3300's own BIOS**, not
`C-BIOS_MSX1_EU_REPACK_DISK`. No Makefile recipe sets the variable for bdos-acceptance,
dskfmt-acceptance or fmtdos-acceptance (dskfmt depends on repack-machine yet captures on the
CF-3300 host); diskbasic's GET(RDBLK) row likewise. The only C-BIOS-side bdosx check is
`bdos-cbios-selfcheck`: not an `*-acceptance` target (only a .PHONY entry), ours-vs-ours (not
the reference), defaulting to `C-BIOS_MSX1_EU_BASIC_DISK` (the lean machine; stale (inf)), and
without dskfmt / fmtdos.

On the repack machine against the reference / pinned values: bdosunop, p1dta, p1vec, strout,
dosdate, dosbasic, phydio (diskbasic) vs the CF-3300; p1multi, seqmix, lstout pinned; biosl
b8save vs the VG-8020 + NMS 1200 (another disk ROM).

## Comparing gates

bdos-acceptance (`probes/disk/disk_bdos_acceptance.py`, CF-3300 host): every capture diffs a
RAM block the program filled; live CPU registers are only noted; registers snapped as
A/B/C/D/E/H/L (8 B per record) -- **F never**.

| code | exerciser | diffs |
|---|---|---|
| BX | bdosx.asm | FSIZE FOPEN RDSEQx2 SETRND RDBLK WRBLK FCLOSE: regs, final FCB, 3x128 B |
| BX2 | bdosx2.asm | CPMVER LOGIN STIME GTIME VERIFY DSKRST CONST CONIN DIRIN INNOE DIRIO-in (drained) DIRIO-out: regs |
| BX3 | bdosx3.asm | FMAKE WRSEQx9 FCLOSE FOPEN RDSEQ FREN FDEL FOPEN-miss RDRND WRRND RDABS WRABS: regs, FCB, buffers, a sector (FREN L, FOPEN-miss H/L excused) |
| BX0 | bdosx0.asm | TERM0 by callseq: each call's INPUTS (30 hits); screen run skipped |
| BX4 | bdosx4.asm | WRSEQ on a full disk: registers only |
| BX5 | bdosx5.asm | FMAKE on a full directory x2, FOPEN: regs, FCB |
| BX6 | bdosx6.asm | RDRND / WRRND past EOF, FCLOSE, re-FOPEN: regs, FCB, buffer (RDRND L excused) |
| BX7 | bdosx7.asm | FREN onto an existing name: regs, FCB (H/L excused) |
| BX8 | bdosx8.asm | WRSEQ x12: FCB after the writes and after FCLOSE |
| BX9 | bdosx9.asm | CURDRV SELDSK0 ALLOC0 SFIRST/SNEXT CONOUT FMAKE/WRZER/FCLOSE AUXOUT, unused $1C-$20 $25 $29: regs |
| BUF | bufinx.asm | BUFIN "AB"+CR: the buffer only |
| AUX | auxinx.asm | AUXIN: A |
| DENT | dskent.asm | MTOFF Cy; DSKCHG Cy+B (x2); GETDPB Cy + 32 B DPB |
| DCHG | dskchg.asm | DSKCHG Cy+B after 0/1/3/10 s idle, + DPB |
| WZ | wrzer.asm | WRZER vs WRRND over $CC-filled clusters: each A |
| D1-D7 | dosl/*.asm | d1con, d2type, d3copy, d4dir, d5rendel, d6rand, d7sort: A, sums, FCB fields, DTA, counts |

Other: UN bdosunop (via $F37D on repack: SETDTA DSKRST FOPEN FCLOSE SEQREAD on bad FCBs; all A,
37 B x4 FCBs, root entries 0..1 of the image); SM seqmix (zerobas, pinned CF-3300 values); RB
diskbasic GET(RDBLK) (CF-3300 host); WB diskbasic PUT(WRBLK) (image: dir size, cluster, FAT
chain, data); WA wrblkalt (two FCBs alternating; sizes / content, not cluster numbers); PD p1dta;
PV p1vec; ST strout (text PRESENT on both, not a screen diff); DD dosdate; DB dosbasic; LS lstout
(zerobas only, pinned `LP!\r\n`); FM dskfmt (CHOICE string, DSKFMT A/Cy/B, sectors 0..7, a BDOS
round trip; choices 1-4; CF-3300 host); FD fmtdos (MSX-DOS `format` via $4025: whole image
outside the boot code; choices 1, 4); PH phydio (1 sector: Cy A B checksum); PM p1multi (2-sector
read from page 1, pinned); B8 biosl b8save (vs the VG-8020 + NMS 1200).

In no gate: disk_probe_dskio.py (`make probe` only), disk_probe_write.py, verifyx.asm,
rndfcb.asm, setrnd_char.asm, lstoutx.asm on the CF-3300.

## Gaps, ranked (harm to a .COM program / a ROM on C-BIOS without BASIC)

1. **The comparisons run on the wrong host** (headline): CHPUT / CHGET / H.TIMI / $F340 / the
   page-1 slot state seams behind them are unchecked on the shipped machine.
2. **Disk errors never compared at DSKIO / BDOS level** -- DSKIO's Cy / A codes (0 write-protect,
   2 not ready, 4 CRC, 6 seek, 8 RNF, 10 write fault, 12 other) / B; a .COM or $F37D caller's
   error path (DISKVE $F323, Abort/Retry/Ignore). Only BASIC-level wprotect / geteject /
   nodiskerr.
3. **DSKIO direct**: no direct WRITE against the CF-3300; B on multi-sector only pinned; other
   media only in FM.
4. **$F37D's own dispatch** (`bdos_tab`, disk/kernel.asm: bb_conout, bb_dirio, bb_version,
   bb_dskrst, bb_setrnd): only FOPEN / FCLOSE / SEQREAD / SETDTA / DSKRST (UN), FMAKE / WRBLK /
   RDBLK (B8, other ROM), SM (pinned) compared; the rest via $F37D (inf) never.
5. **Console behaviour**: CONOUT / DIRIO-out / CONIN echo / BUFIN echo / STROUT screens never
   diffed; control codes, tab, Ctrl-P/C/S, BUFIN editing; **DIRIO input with a key waiting**.
6. Function numbers > $30 never called ($6F, the DOS2 probe (inf)).
7. DSKCHG "changed" (B=$FF after a swap) / error path; GETDPB other media.
8. Drive B (phantom drive) never compared.
9. Disk-image side effects mostly invisible (FMAKE/FDEL/FREN raw bytes, FAT copy 2; disk full
   only WRSEQ, registers only).
10. Registers / flags excused or never compared (F everywhere; ALLOC IX/IY).
11. SDATE / STIME invalid input (A=$FF) -- STIME's range check not implemented (likely live).
12. VERIFY's effect (verifyx in no gate).
13. One geometry (720 KB test.dsk) for the BDOS.

## Faults in tools/entry_table.py (disk / BDOS tables)

- BDOS: probes issuing BDOS calls as Python-assembled bytes are not credited (bdosunop_acceptance,
  disk_probe_seqmix); `_differential_scripts` credits any script importing disk_probe_bdos (for
  fat12_add) as "vs reference" (LSTOUT reads yes via a zerobas-only probe); the `ld c,N` scan
  misses table / loop calls; zerobas-only (LS, SM) and other-ROM (B8) gates count as CF-3300
  comparisons.
- Disk-ROM rows: the name still matched with re.I (CHOICE credited via a lowercase `choice`
  variable); DSKIO credited to subrom via `ld ix,$4010` (a sub-ROM ping); missed: fmtdos for
  DSKFMT / CHOICE, phydio / biosl / dskio / wprotect / geteject for DSKIO.
- Pinned rows: $5552 is SDATE; $607B tied to CPMVER by a comment; $4257 label `?`; $4217 an equ
  line (rdslt_h); $47B9 / $7FD1 / $7F7C / $7FC0 are pads / zerobas-internal; $4022 / $5E10 BASENT,
  $4025 FORMAT, $44F4 choice, ... read "no BDOS function named"; $4030 has no row.

## Per entry -- disk-ROM published entries

| entry | answer | compared by | gap |
|---|---|---|---|
| $4010 DSKIO | Cy, A err, B left, data, disk | FM, PH, PM, B8 | direct write vs CF-3300; error codes; B multi; geometries; CF-3300 host |
| $4013 DSKCHG | Cy, B 1/0/FF, A err, DPB | DENT, DCHG (idle) | real swap; errors; drive B |
| $4016 GETDPB | Cy, DPB | DENT ($F9) | other media; errors; drive B |
| $4019 CHOICE | HL string / 0 | FM, FD | -- |
| $401C DSKFMT | Cy, A, the disk | FM, FD (via $4025) | error paths; FM reads sectors 0..7 only |
| $401F MTOFF | motor off | DENT (Cy) | the motor state (low value) |
| $4022 BASENT / $4025 FORMAT | -- | DB / FD | not credited |
| $4030 work area | HL | none | no row |

## Per entry -- BDOS $00-$30 (condensed)

Compared on the CF-3300 host by BX* / D* unless noted. Notable gaps: TERM0's screen; CONIN /
CONOUT / DIRIO / STROUT / BUFIN screens and control keys; LSTOUT never vs the CF-3300; DIRIO input
with a key; DSKRST's DTA reset; SELDSK E=1; FDEL / FREN raw directory bytes; WRSEQ / WRRND /
WRBLK / FMAKE on a full disk (FCB, image); ALLOC IX/IY; SETRND via $F37D; GDATE only two dates;
SDATE / STIME invalid input; VERIFY's effect; RDABS / WRABS multi-sector and errors.
