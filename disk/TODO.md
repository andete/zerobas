# disk/ — TODO

Two workstreams: the disk-interface ROM (`disk/`) and zerobas interpreter
extensions (`basic/`), mirroring the `tape/` + interpreter model.

## Reference machine: National CF-3300 (MSX1, JP, 1985)

The black-box oracle reference is the **National CF-3300**, a desktop Japanese
MSX1 with built-in disk drive — the cleanest genuine MSX1 disk machine in
openMSX's library.

Confirmed in openMSX:
- `<type>MSX</type>`, **TMS99X8A** VDP (true MSX1, no V9938)
- WD2793 FDC in **slot 3-1**, `connectionstyle: National` (memory-mapped
  registers), `mem base="0x4000" size="0x8000"` — architecture matches the
  plan exactly
- Single SHA1 for `cf-3300_disk.rom` — unambiguous reference
- Also has a cassette port, so the existing tape oracle path still works

Philips made no MSX1 with built-in disk (VG-8010/8020 have no disk; NMS-82xx
are MSX2). The SVI-738 variants are disqualified — they use the V9938 VDP,
making them non-standard MSX1. Sony HB-F500/F500P are MSX2. The CF-3300 is
the right reference regardless of being Japanese: file I/O behavior is
identical across regions.

ROMs needed (proprietary, source separately): `cf-3300_basic-bios1.rom`,
`cf-3300_disk.rom`.

The `connectionstyle: National` WD2793 register addresses are sourced from
open hardware documentation and the WD2793 datasheet. No disk ROM disassembly
is needed or allowed.

---

## Architecture note: internal slot, not a cartridge

On a real MSX1 with built-in disk support (NMS 8245, HB-F500, etc.) the disk
ROM lives in an **internal expansion slot** (typically slot 3-1), not in an
external cartridge slot. The FDC chip is wired directly to the motherboard at
fixed I/O ports. The BIOS boot scan finds the disk ROM's "AB" header in the
internal slot just as it finds zerobas in slot 0 page 1; cartridge slots 1 and
2 remain free for user cartridges.

Consequences for zerobas-disk:

- **Standalone ROM** — not an IPS patch on an existing ROM (unlike zerobas-tape,
  which patches C-BIOS page 0 in-place). zerobas-disk is a fresh 16/32 KB ROM
  placed in a new slot.
- **openMSX placement** — machine XML uses a `<primary slot="3"><secondary
  slot="1">` block pointing at the zerobas-disk ROM; no `<cartridgeX>` element.
- **FDC hardware** — declared as a separate FDC extension in the machine XML
  (WD2793-based, Philips/NMS-style latch + drive-select at fixed I/O ports).
  A `.dsk` image is attached to the configured drive.

## Naming convention

All sub-components of zerobas follow the `zerobas-<component>` scheme:
`zerobas-tape`, `zerobas-disk`, and any future transport or hardware layer.
This applies to the component name, its patch/ROM output filenames, and any
references in docs, scripts, and installers.

## Repository structure

zerobas-tape and zerobas-disk both live inside the zerobas repo (not as sibling
repos). zerobas-tape will be migrated in from its current standalone repo.
`src/` is renamed to `basic/` to make the three components visually symmetric:

```
zerobas/
  basic/    ← BASIC interpreter ROM (renamed from src/)
  tape/     ← zerobas-tape (migrated in)
  disk/     ← zerobas-disk (new)
  tools/
```

`install-openmsx-machine.py` simplifies: both patch paths are repo-relative,
no sibling-repo auto-detection needed. The Makefile gains `tape.ips` and
`disk.rom` targets alongside `basic.rom`.

---

## disk/ — disk-interface ROM

Goal: a clean-room MSX1 disk ROM that fills the role `tape/` fills for
cassette. Provides the physical FDC driver, FAT12 read layer, and BDOS hooks
so zerobas's `BLOAD"A:FILE"` can reach a real FAT12 disk image.

Provenance sources (all public): MSX2 Technical Handbook, WD2793 datasheet,
Philips/NMS open schematics, Microsoft FAT12 spec. No disk-ROM disassembly.
See [`PROVENANCE.md`](PROVENANCE.md) for the per-constant trace.

### TODO

- [x] **Provenance doc** — list every constant/address with source before
      writing any code; same discipline as zerobas's `PROVENANCE.md`
      ([`PROVENANCE.md`](PROVENANCE.md))
- [x] **ROM skeleton** — 16 KB ROM; MSX "AB" header; INIT vector;
      standard disk ROM entry-point stubs at fixed offsets (`+$10` DSKIO,
      `+$13` DSKCHG, `+$16` GETDPB, `+$19` CHOICE, `+$1C` DSKFMT,
      `+$1F` MTOFF)
      (`disk/disk.asm`: header + jump table verified at the exact offsets;
      stubs fail cleanly with carry set, CHOICE returns HL=0. Built via
      `make disk` → `disk.rom`, padded to 16384 bytes. Corrected the
      PROVENANCE header rows: INIT is a word at $4002, not a JP at $4003.)
- [~] **INIT** — install disk hooks in system hook RAM; set up the Drive
      Parameter Block (DPB) for a single 720 KB 3.5" drive
      (Current code installs `JP phyd_handler`/`JP dskio` at $FF3E/$FF4B and
      writes SYSTEM/$F37D → bdos_entry via `install_hook`.
      DPB / GETDPB blocked on the MSX2 TH DPB field encoding (dir mask/shift,
      total-clusters); GETDPB remains a carry-set stub.
      **NEEDS REDESIGN — oracle-contradicted (probe 3 investigation).** Observing
      the CF-3300 reference (RAM only): the real disk ROM hooks via `RST 30h`
      (CALLF) inter-slot calls with slot byte $87 at hook entries $FD9F/$FDEF/
      $FDF9/$FFA7/$FFAC — NOT at $FF3E/$FF4B, and NOT with `JP` (a `JP` can't
      cross slots). $FF4B isn't even 5-byte-aligned in the hook table, so our
      H.DSKIO address is invalid. $F37D holds a BIOS-ROM address on the
      reference, not a BDOS entry. The fix: drop the mis-addressed `JP` hooks +
      SYSTEM vector; integrate the disk ROM the standard way — its $4010 entry
      table reached via an inter-slot call. Since zerobas owns both ROMs, the
      cleanest path is for zerobas-BASIC to locate the disk-ROM slot and CALSLT
      its $4010 entries directly (ties into the boot-init item below). Real hook
      names/addresses, if we hook at all, must come from the MSX2 TH hook table.
      See disk/PROVENANCE.md §INIT. The $4010 entry table itself is correct and
      differential-confirmed (probe 2).)
- [x] **FDC driver** — WD2793 register I/O at the National memory-mapped
      register addresses; track/sector/head addressing; read-sector command and
      result-phase read; error handling (write support deferred)
      (`disk/disk.asm`: register map sourced from openMSX `NationalFDC.cc`
      ($7FB8 status/cmd, $7FB9 track, $7FBA sector, $7FBB data, $7FBC
      drive/side/motor latch); WD2793 status/command bits from the datasheet.
      `dskio` does the full DSKIO read path: logical→CHS via `div9`, per-sector
      seek+read, polled 512-byte transfer (status-reg DRQ/BUSY — IRQ/DRQ lines
      aren't wired to the Z80 per `NationalFDC.cc`), DSKIO error-code mapping,
      and one restore+retry to recover a stale Track register. `mtoff` drops the
      motor; `phyd_handler` routes to `dskio`. Writes deferred (return
      write-protected). The "Philips/NMS-style" phrasing was stale — the CF-3300
      reference is National connection style. The FDC §TBD rows in
      [`PROVENANCE.md`](PROVENANCE.md) are now resolved/sourced. End-to-end
      read is exercised once the openMSX machine config + test `.dsk` land.)
- [x] **FAT12 layer** — boot sector / BPB parse; FAT12 cluster-chain walk;
      root directory search (8.3 name, case-insensitive); sequential sector
      read for a file's data
      (`disk/disk.asm`: read-only FAT12 as internal helpers on top of the DSKIO
      core. `fat_mount` reads the boot sector and derives geometry from the BPB
      (validates 512 B/sector, then computes first-FAT / first-root / root-sector-
      count / first-data sectors); `fat_find` scans the root directory 16 entries
      per sector with a case-insensitive 8.3 compare, skipping deleted / volume /
      directory entries, and returns first cluster + file size; `fat_next_cluster`
      follows the 12-bit chain including the sector-straddle case (e.g. cluster
      682 on a full 720 KB image); `fat_open` + `fat_read_file_sector` iterate the
      chain a data sector at a time. All geometry comes from the on-disk BPB, so
      the code is geometry-agnostic. FAT12 scratch added at $E4A0–$E4BE
      (PROVENANCE §Scratch RAM). Code ends at $4359, clear of the $7FB8 FDC
      shadow. Not yet reachable — the BDOS/FCB layer (next item) calls these;
      end-to-end validation waits on the openMSX machine config + oracle probe 2.
      pasmo flags the four FAT12 entry points as "never used" until then.)
- [x] **BDOS hook** — intercept the BDOS jump vector; implement FCB-based
      `Open` ($0F), `Sequential Read` ($14), `Close` ($10); error returns per
      MSX-DOS spec
      (`disk/disk.asm`: `bdos_entry` is now a real dispatcher on the call
      number in C with the FCB pointer in DE (CP/M convention). `Open` calls
      `fat_mount` then `fat_find` on the FCB's 11-byte 8.3 name (+1..+11),
      then `fat_open`; returns A=$00 / A=$FF. `Sequential Read` delivers
      128-byte records out of the 512-byte `SECTOR_BUF`, tracking the record
      index in `BDOS_RECIDX` ($E4BF) and refilling via `fat_read_file_sector`
      when the four records are exhausted; copies each record to the DTA
      ($0080); returns A=$00 / A=$01 at EOF. `Close` returns A=$00; any other
      call returns A=$FF. The four FAT12 entry points are now reached, clearing
      pasmo's "never used" warnings on them. Code ends at $43B8, clear of the
      $7FB8 FDC shadow; ROM builds clean to 16384 bytes.
      **Divergences / simplifications:** only one file open at a time — file
      position lives in the FAT iterator + `BDOS_RECIDX`, not in the FCB extent
      (+12) / current-record (+32) fields; Sequential Read EOF granularity is
      the cluster chain, so the last record may include padding past
      `FAT_FILESIZE` (CP/M record semantics — exact byte bounding deferred).
      The exact register save/restore contract the BLOAD caller must honour is
      quarantined pending oracle probe 3 (BDOS FCB round-trip). End-to-end
      functional validation is deferred: it needs the openMSX machine config +
      a test `.dsk` + oracle probe 3 — so this lands **implemented, not yet
      oracle-confirmed**.)
- [~] **Oracle probes** (in msx-preservation repo) — black-box observation of
      BDOS return values and FCB state on a reference machine with a known
      `.dsk` image
      (`disk-spec/tools/disk_probe_dskio.py` in msx-preservation: differential
      DSKIO sector read vs the real National CF-3300 — **PASS, byte-identical**
      (sector 0 + sector 14, return codes and data). Strictly black-box: calls
      the standard $4010 DSKIO entry via CALSLT and observes only returned data
      + carry/A; the reference disk ROM is never read/disassembled.
      **Probe 3 (BDOS FCB round-trip) reframed — not a differential test.** The
      probe-3 investigation (CF-3300 RAM observation) found the reference exposes
      no CP/M FCB BDOS in Disk BASIC ($F37D → BIOS ROM, no $0005 BDOS, page 0 is
      ROM); FCB BDOS is MSX-DOS-only. Our `bdos_entry` is therefore an internal
      zerobas API, validated functionally, with no reference to differ against —
      so the real end-to-end oracle is **probe 4 (BLOAD"A:FILE",R)**, comparing
      loaded bytes + exec handoff (its read path is already differential-confirmed
      via probe 2). See disk/PROVENANCE.md §INIT and §BDOS interface.)
- [x] **openMSX machine config** — machine XML that places zerobas-disk in
      internal slot 3-1, declares an FDC extension, attaches a test `.dsk`
      image, and pairs with the existing zerobas + zerobas-tape IPS patches in
      slot 0
      (Generated by `tools/install-openmsx-machine.py --disk-rom disk.rom`,
      which now also writes `*_BASIC_DISK` variants: slot 3 expanded to 3-0 RAM
      + 3-1 `WD2793` (National connection style, `<drives>1</drives>`, our
      `disk.rom`, `mem base=0x4000 size=0x8000`) — modelled on openMSX's
      `National_CF-3300.xml`. Boot with e.g.
      `openmsx -machine C-BIOS_MSX1_BASIC_DISK -diska disk/test720.dsk`.
      **Functionally validated on openMSX** (see below) — but note this is a
      functional self-test of our ROM against our own FAT12 image, NOT the
      differential oracle vs the CF-3300 reference, whose proprietary ROMs are
      not available here.)

      **VALIDATION RESULTS (functional, openMSX 21, test720.dsk).** Driving the
      slot-3-1 routines via `CALSLT` against the real image:
      - FDC driver + FAT12 read path PASS end-to-end: `fat_mount` derives the
        BPB geometry (secPerClus 2, fatStart 1, firstRoot 7, rootSecs 7,
        firstData 14 — all matching the image); `fat_find` locates `TEST.BIN`
        (firstClus 2, size 2048); sequential `fat_read_file_sector` returns the
        correct record content across a cluster-chain hop (cluster 2→3) and
        reports clean EOF at chain end.
      - BDOS dispatcher PASS: `bdos_entry` with C=$0F (Open) → A=$00 and C=$10
        (Close) → A=$00, exercising the call-number dispatch + FCB+1 name
        extraction. SeqRead's DTA write to $0080 was NOT exercised because in
        this Disk-BASIC layout page 0 is BIOS ROM, not RAM (see finding below);
        its underlying `fat_read` path is validated above.

      **KEY FINDING — boot-scan ordering blocks the combined machine.** In the
      full `*_BASIC_DISK` machine the disk ROM INIT never runs: after boot
      `SYSTEM ($F37D)` and the `H.PHYD`/`H.DSKIO` hooks are still at C-BIOS's
      default ($C9/RET). C-BIOS scans slot 0 (zerobas-BASIC) before slot 3-1,
      and zerobas-BASIC's INIT enters its REPL and never returns, so the scan
      never reaches the disk ROM. In isolation (a disk-ROM-only C-BIOS machine,
      no BASIC patch) the disk INIT runs correctly and installs SYSTEM=$4168
      (`bdos_entry`), `H.PHYD`→`phyd_handler`, `H.DSKIO`→`dskio`. **RESOLVED** in
      the interpreter workstream (`../basic/initext.asm`, item below): zerobas-
      BASIC's INIT now scans the remaining slots and `CALSLT`s the disk ROM's INIT
      before the REPL, so on `C-BIOS_MSX1_BASIC_DISK` the disk INIT installs the
      same SYSTEM=$4168 / `H.PHYD`→$4165 / `H.DSKIO`→$4048 it does in isolation
      (`disk-spec/tools/disk_probe_init.py` PASS; differential control reads the
      C-BIOS defaults). Two related integration notes for the BLOAD work: (a) reaching disk
      entry points needs an inter-slot call (CALSLT works); (b) the BDOS DTA at
      $0080 assumes page-0 RAM (MSX-DOS), which does not hold under Disk BASIC —
      the BLOAD path should set/choose its own transfer buffer rather than rely
      on $0080.
- [x] **Makefile** — build ROM with pasmo; no patch-generation step needed
      (standalone ROM, not an IPS)
      (root Makefile `disk` target: `pasmo --bin disk/disk.asm` + `pad_rom.py`
      to 16384 bytes; `clean` removes `disk.rom`. Added with the ROM skeleton.)

---

## zerobas interpreter extensions (`basic/`)

Small delta on top of the existing [`../basic/bload.asm`](../basic/bload.asm)
once the BDOS API is stable.

### TODO

- [x] **Init disk ROMs from zerobas-BASIC's INIT** *(was the blocker, found
      during openMSX validation)* — C-BIOS scans slot 0 (zerobas-BASIC) before
      slot 3-1, and zerobas-BASIC's INIT takes over the REPL without returning,
      so the disk ROM's INIT in slot 3-1 never ran in the combined machine.
      **Done** in `../basic/initext.asm` (`init_ext_roms`, called from `init`
      before the REPL): it walks every primary slot after zerobas's own page-1
      primary and every expanded subslot, finds each `"AB"` header at $4000, and
      `CALSLT`s its INIT word at $4002 — the rest of the BIOS boot scan C-BIOS
      skipped. RDSLT/CALSLT/EXPTBL/$A8 sourced; see `../basic/PROVENANCE.md`
      §extension-ROM INIT scan. Validated end-to-end: on `C-BIOS_MSX1_BASIC_DISK`
      the disk INIT now installs SYSTEM $F37D=$4168, H.PHYD=JP $4165, H.DSKIO=JP
      $4048 (functional probe `disk-spec/tools/disk_probe_init.py`; differential
      control with the pre-scan ROM reads C-BIOS defaults). The next items below
      (disk BLOAD) are now unblocked.
- [x] **Disk filename parse in BLOAD** — extend `do_bload`'s device-string
      parser to recognise `"A:name"` / `"B:name"` (and bare `"name"` defaulting
      to drive A); extract drive letter and 8.3 filename into scratch RAM; keep
      `"CAS:"` path unchanged. NB (from validation): reach `bdos_entry` via an
      inter-slot call, and do not rely on the $0080 DTA (page 0 is BIOS ROM
      under Disk BASIC) — point the read at a buffer the BLOAD path controls.
      (`basic/bload.asm`: `do_bload` now peeks the device string non-
      destructively — full `"CAS:"` prefix → the unchanged tape path; anything
      else → the disk path (`is_disk`). The disk path reads an optional
      case-insensitive `"A:"`/`"B:"` drive prefix (bare name defaults to drive
      A), then `build_83_name` converts the filename to the 11-byte space-padded
      upper-case 8.3 field. The result lands in a scratch FCB at `DISK_FCB`
      ($E0DB, 12 bytes; `basic/sysvars.inc`): FCB+0 = drive code (CP/M / MSX-DOS
      convention 0=default/1=A/2=B — `bdos_open` ignores it today, forward-compat
      only), FCB+1..+11 = the 8.3 name. The quote-close + `,R` parse is now the
      shared `parse_close_run` (both tape and disk set RUNFLAG). **Divergences /
      judgment calls:** PARSE-ONLY — `do_disk_bload` is a labelled placeholder
      that falls through to `load_error`; the actual disk read (and passing this
      FCB to `bdos_entry` via CALSLT) is the NEXT item. 8.3 over-length / second-
      dot / empty-name is **rejected** via `load_error`, not truncated (hiding
      typos is worse). No new token — disk filenames are verbatim ASCII in the
      crunch stream, so the tokeniser is untouched and crunch stays byte-
      identical (Philips VG-8020). Validated: `disk_probe_bload_fcb.py`
      (msx-preservation) on `C-BIOS_MSX1_BASIC` (parse-only code, no disk
      hardware; breaks at the `do_disk_bload` landmark) confirms `A:TEST.BIN`→
      drive 1/`TEST    BIN`, bare `TEST.BIN`→drive 1, `B:HI.TXT`→drive 2/`HI      TXT`;
      crunch + 4 regression probes pass; `BLOAD"CAS:",R` still loads + hands off.
      See basic/PROVENANCE.md §disk-BLOAD scratch FCB.)
- [x] **Disk BLOAD execute** — open the file via BDOS FCB; read and verify
      the BSAVE header; load data bytes into RAM; close file; share `,R` handoff
      logic with the cassette path.
      **CORRECTION — the disk BSAVE header is NOT the cassette format.** The
      original wording ("10× `$D0` + 6-char name + start/end/exec — same format
      as tape") described the CASSETTE header. A BSAVE binary file *on disk* uses
      a shorter 7-byte header `[$FE][start:2 LE][end:2 LE][exec:2 LE]` immediately
      followed by the raw data — no 10×$D0 block and no filename in the body (the
      name is the directory entry). Source: MSX-BASIC file formats (MSX Wiki / MSX
      Resource Center, an allowed public MSX-BASIC language reference). Data bytes
      run start..end inclusive. See basic/PROVENANCE.md §disk BLOAD execute and
      disk/PROVENANCE.md §BDOS interface.
      (`basic/bload.asm`: `do_disk_bload` is now real. It checks `DISKSLOT_OK`
      (recorded by the INIT scan, `basic/initext.asm`), then reaches the disk
      ROM's `bdos_entry` across slots with `CALSLT` — slot id from `DISKSLOT`,
      entry address from SYSTEM $F37D. Sequence: BDOS $1A Set-DTA → a writable
      page-3 buffer `DISK_DTA` ($E4C2; the $0080 default is BIOS ROM under Disk
      BASIC and silently fails); $0F Open (DE=`DISK_FCB`, require A=$00); $14
      SeqRead streaming (a `disk_getbyte` helper pulls bytes one at a time from
      the 128-byte record, refilling via SeqRead — the 7-byte header is not
      record-aligned with the data); parse $FE + start/end/exec into the existing
      `CURPTR`/`ENDPTR`/`EXECPTR`; load bytes start..end inclusive; $10 Close. The
      `,R` exec handoff is shared with the cassette path via `load_handoff`. On
      any post-Open error the file is closed before `load_error`.
      `disk/disk.asm` gained BDOS $1A Set-DTA + a settable `BDOS_DTA` var (default
      $0080 for MSX-DOS compat). **Validated end-to-end** (openMSX,
      `disk-spec/tools/disk_probe_bload_disk.py`) on `C-BIOS_MSX1_BASIC_DISK` with
      `-diska disk/test720.dsk`: `BLOAD"A:PROG.BIN",R` lands the bytes at
      $C000..$C031, PC reaches the $C010 `JR$` landmark (handoff fired) and
      ($D000)=$5A (exec ran); plain `BLOAD"A:PROG.BIN"` loads the bytes but leaves
      ($D000) at its sentinel (no exec). Crunch byte-identical; the 4 regression
      probes, `disk_probe_init.py`, `disk_probe_bload_fcb.py`, and the
      `disk_probe_dskio.py` differential (vs CF-3300) all still pass.)
- [ ] **`LOAD"filename"`** — load a tokenized BASIC file from disk (different
      format from BSAVE binary); parse program-line format and rebuild the
      program store; needed for disk-based loader stubs
- [ ] **`RUN"filename"`** — thin wrapper: `LOAD` then `RUN`
- [ ] **Provenance entries** — document BDOS call numbers, FCB layout, and
      disk-BSAVE header format in `PROVENANCE.md`; oracle probes to confirm
      byte-identical behaviour vs reference

---

## openMSX integration (`tools/`)

- [x] **Extend `install-openmsx-machine.py`** — add `--disk-rom` option;
      generate `*_BASIC_DISK` machine variants that add the internal slot 3-1
      block and FDC extension alongside the existing zerobas + tape patches
      (`--disk-rom [ROM]` (default `disk.rom`); `expand_slot3()` rewrites the
      stock C-BIOS slot-3 RAM block into 3-0 RAM + 3-1 National `WD2793` with
      the disk ROM by absolute path; one `*_BASIC_DISK` written per MSX1 C-BIOS
      machine. The plain `*_BASIC` machines are unchanged.)
- [x] **Test disk image** — a minimal 720 KB FAT12 `.dsk` with a few BSAVE
      binaries for integration testing
      (`tools/make_test_dsk.py` builds `disk/test720.dsk` from the Microsoft
      FAT spec + ECMA-107 geometry (allowed sources; no disk-ROM bytes). It
      carries `TEST.BIN` (2048 B = two clusters = 16 records; record r filled
      with byte r+1, so a sequential read is trivially checkable and the read
      crosses a cluster-chain boundary) and `HI.TXT` (so the dir search has to
      pick the right entry). The image also carries `PROG.BIN`, a REAL on-disk
      BSAVE binary (`[$FE][start][end][exec]` + raw data; layout documented in the
      script from the MSX-BASIC file formats reference) added for the disk BLOAD
      execute item — its payload writes a landmark byte ($5A→$D000) then self-loops
      at `JR $`, with a deterministic 0..31 data tail, so the disk BLOAD probe can
      check both the loaded bytes and the `,R` exec handoff. `TEST.BIN`/`HI.TXT`
      stay raw-record content for the FAT12/BDOS layer tests; `PROG.BIN` is added
      after them so the dir search still has to pick the right entry.)
- [ ] **Valid MSX boot sector in the test image** *(found during validation)* —
      the current boot sector is filler (`EB FE 90` + zeros). A real disk machine
      reads sector 0 and *executes* its boot code (at offset $1E), so inserting
      the disk at the CF-3300's cold boot **hangs** the reference (PC stuck early).
      Our own DSKIO/FAT path is unaffected (it reads, never executes the sector),
      and oracle probes work by booting first then inserting the disk. But for a
      genuinely bootable/safe image, put valid minimal MSX boot code at offset
      $1E (the contract — CALL vs JP $C01E, expected return — must come from
      MSX2 TH, not guessed). Until then, probes must insert the disk *after* the
      reference reaches BASIC.

---

## Sequencing

```
zerobas-disk: ROM skeleton + FDC driver
          ↓
zerobas-disk: FAT12 layer + BDOS hooks
          ↓
zerobas: disk BLOAD (bload.asm extension)   ← can start once BDOS API is stable
          ↓
oracle probes confirming round-trip
          ↓
zerobas: LOAD / RUN"filename"
          ↓
openMSX integration + install script update
```

The FDC driver and FAT12 layer are the long pole; everything else is small
once those are oracle-confirmed.
