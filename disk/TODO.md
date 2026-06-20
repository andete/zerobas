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
- [~] **INIT** — install `H.DSKIO` / `H.PHYD` hooks in system hook RAM; set
      up the Drive Parameter Block (DPB) for a single 720 KB 3.5" drive
      (Hook installation done: H.PHYD/$FF3E → phyd_handler, H.DSKIO/$FF4B →
      dskio, SYSTEM/$F37D → bdos_entry, via `install_hook` helper.
      DPB / GETDPB blocked: the directory-mask, directory-shift, and
      total-clusters encoding in the MSX2 TH DPB layout are ambiguous without
      the TH text — oracle probe 2 (DSKIO sector-read) must confirm them.
      GETDPB remains carry-set stub. bdos_entry stub returns A=$FF.)
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
- [ ] **BDOS hook** — intercept the BDOS jump vector; implement FCB-based
      `Open` ($0F), `Sequential Read` ($14), `Close` ($10); error returns per
      MSX-DOS spec
- [ ] **Oracle probes** (in msx-preservation repo) — black-box observation of
      BDOS return values and FCB state on a reference machine with a known
      `.dsk` image
- [ ] **openMSX machine config** — machine XML that places zerobas-disk in
      internal slot 3-1, declares an FDC extension, attaches a test `.dsk`
      image, and pairs with the existing zerobas + zerobas-tape IPS patches in
      slot 0
- [x] **Makefile** — build ROM with pasmo; no patch-generation step needed
      (standalone ROM, not an IPS)
      (root Makefile `disk` target: `pasmo --bin disk/disk.asm` + `pad_rom.py`
      to 16384 bytes; `clean` removes `disk.rom`. Added with the ROM skeleton.)

---

## zerobas interpreter extensions (`basic/`)

Small delta on top of the existing [`../basic/bload.asm`](../basic/bload.asm)
once the BDOS API is stable.

### TODO

- [ ] **Disk filename parse in BLOAD** — extend `do_bload`'s device-string
      parser to recognise `"A:name"` / `"B:name"` (and bare `"name"` defaulting
      to drive A); extract drive letter and 8.3 filename into scratch RAM; keep
      `"CAS:"` path unchanged
- [ ] **Disk BLOAD execute** — open the file via BDOS FCB; read and verify
      the BSAVE header (10× `$D0` + 6-char name + start/end/exec — same format
      as tape); load data bytes into RAM; close file; share `,R` handoff logic
      with the cassette path
- [ ] **`LOAD"filename"`** — load a tokenized BASIC file from disk (different
      format from BSAVE binary); parse program-line format and rebuild the
      program store; needed for disk-based loader stubs
- [ ] **`RUN"filename"`** — thin wrapper: `LOAD` then `RUN`
- [ ] **Provenance entries** — document BDOS call numbers, FCB layout, and
      disk-BSAVE header format in `PROVENANCE.md`; oracle probes to confirm
      byte-identical behaviour vs reference

---

## openMSX integration (`tools/`)

- [ ] **Extend `install-openmsx-machine.py`** — add `--disk-rom` option;
      generate `*_BASIC_DISK` machine variants that add the internal slot 3-1
      block and FDC extension alongside the existing zerobas + tape patches
- [ ] **Test disk image** — a minimal 720 KB FAT12 `.dsk` with a few BSAVE
      binaries for integration testing

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
