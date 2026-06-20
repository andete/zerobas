# Disk ROM support plan (MSX1)

Two workstreams — a new `cbios-disk` sibling repo (hardware layer) and zerobas
interpreter extensions (language layer) — mirroring the zerobas-tape model.

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

Consequences for cbios-disk:

- **Standalone ROM** — not an IPS patch on an existing ROM (unlike zerobas-tape,
  which patches C-BIOS page 0 in-place). cbios-disk is a fresh 16/32 KB ROM
  placed in a new slot.
- **openMSX placement** — machine XML uses a `<primary slot="3"><secondary
  slot="1">` block pointing at the cbios-disk ROM; no `<cartridgeX>` element.
- **FDC hardware** — declared as a separate FDC extension in the machine XML
  (WD2793-based, Philips/NMS-style latch + drive-select at fixed I/O ports).
  A `.dsk` image is attached to the configured drive.

## Repository structure

zerobas-tape and cbios-disk both live inside the zerobas repo (not as sibling
repos). zerobas-tape will be migrated in from its current standalone repo.
`src/` is renamed to `basic/` to make the three components visually symmetric:

```
zerobas/
  basic/    ← BASIC interpreter ROM (renamed from src/)
  tape/     ← zerobas-tape (migrated in)
  disk/     ← cbios-disk (new)
  tools/
```

`install-openmsx-machine.py` simplifies: both patch paths are repo-relative,
no sibling-repo auto-detection needed. The Makefile gains `tape.ips` and
`disk.rom` targets alongside `basic.rom`.

---

## cbios-disk (new separate repo)

Goal: a clean-room MSX1 disk ROM that fills the role zerobas-tape fills for
cassette. Provides the physical FDC driver, FAT12 read layer, and BDOS hooks
so zerobas's `BLOAD"A:FILE"` can reach a real FAT12 disk image.

### Provenance sources to establish first

- MSX2 Technical Handbook: disk ROM interface (standard entry-point offsets),
  hook addresses (`H.DSKIO` `$FF4B`, `H.PHYD` `$FF3E`), BDOS call numbers,
  FCB layout, slot architecture
- WD2793 FDC datasheet (public; the most common MSX1 built-in disk controller)
- Philips/NMS FDC port mapping — open hardware schematics (NOT from ROM
  disassembly)
- Microsoft FAT12 specification (public)
- No disassembly of any existing disk ROM (Sony, Philips, Panasonic)

### TODO

- [ ] **Provenance doc** — list every constant/address with source before
      writing any code; same discipline as zerobas's `PROVENANCE.md`
- [ ] **ROM skeleton** — 16 or 32 KB ROM; MSX "AB" header; INIT vector;
      standard disk ROM entry-point stubs at fixed offsets (`+$10` DSKIO,
      `+$13` DSKCHG, `+$16` GETDPB, `+$19` CHOICE, `+$1C` DSKFMT,
      `+$1F` MTOFF)
- [ ] **INIT** — install `H.DSKIO` / `H.PHYD` hooks in system hook RAM; set
      up the Drive Parameter Block (DPB) for a single 720 KB 3.5" drive
- [ ] **FDC driver** — WD2793 register I/O at the Philips/NMS-style port
      addresses; track/sector/head addressing; read-sector command and
      result-phase read; error handling (write support deferred)
- [ ] **FAT12 layer** — boot sector / BPB parse; FAT12 cluster-chain walk;
      root directory search (8.3 name, case-insensitive); sequential sector
      read for a file's data
- [ ] **BDOS hook** — intercept the BDOS jump vector; implement FCB-based
      `Open` ($0F), `Sequential Read` ($14), `Close` ($10); error returns per
      MSX-DOS spec
- [ ] **Oracle probes** (in msx-preservation repo) — black-box observation of
      BDOS return values and FCB state on a reference machine with a known
      `.dsk` image
- [ ] **openMSX machine config** — machine XML that places cbios-disk in
      internal slot 3-1, declares an FDC extension, attaches a test `.dsk`
      image, and pairs with the existing zerobas + zerobas-tape IPS patches in
      slot 0
- [ ] **Makefile** — build ROM with pasmo; no patch-generation step needed
      (standalone ROM, not an IPS)

---

## zerobas interpreter extensions (this repo)

Small delta on top of the existing `src/bload.asm` once cbios-disk's BDOS API
is stable.

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

## openMSX integration (this repo, `tools/`)

- [ ] **Extend `install-openmsx-machine.py`** — add `--disk-rom` option;
      auto-detect cbios-disk ROM next to this repo (sibling `cbios-disk/`
      dir); generate `*_BASIC_DISK` machine variants that add the internal
      slot 3-1 block and FDC extension alongside the existing zerobas + tape
      patches
- [ ] **Test disk image** — a minimal 720 KB FAT12 `.dsk` with a few BSAVE
      binaries for integration testing

---

## Sequencing

```
cbios-disk: ROM skeleton + FDC driver
          ↓
cbios-disk: FAT12 layer + BDOS hooks
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
