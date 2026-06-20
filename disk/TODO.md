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
- [x] **INIT** — publish the BDOS entry point via the SYSTEM sysvar; decide the
      Drive Parameter Block (DPB) question
      (**RESOLVED.** INIT now only writes `SYSTEM ($F37D) → bdos_entry` and seeds
      the default DTA ($0080), then RETs. The mis-addressed `JP phyd_handler` /
      `JP dskio` hooks at $FF3E/$FF4B were **removed as oracle-contradicted dead
      code** — along with the now-unused `phyd_handler` shim, the `install_hook`
      writer, and the `H_PHYD`/`H_DSKIO` equs. Two reasons they had to go: (a)
      oracle-contradicted — the CF-3300 reference (RAM observation, probe-3
      investigation) hooks via `RST 30h` (CALLF) inter-slot calls with slot byte
      $87 at hook entries $FD9F/$FDEF/$FDF9/$FFA7/$FFAC, NOT at $FF3E/$FF4B and NOT
      with `JP` (a `JP` can't cross slots); $FF4B isn't even 5-byte-aligned in the
      hook table; (b) functionally dead — zerobas is a standalone BASIC, not Disk
      BASIC, so it never drives the H.* chain. zerobas reaches the file layer
      through the **SYSTEM-vector BDOS entry**, located via $F37D and called across
      slots with CALSLT (slot id from the INIT scan in `basic/initext.asm`). That
      path is now **differentially oracle-confirmed byte-identical vs real MSX-DOS
      1** (`disk_probe_bdos.py`), and the underlying $4010 DSKIO read is
      differential-confirmed vs the CF-3300 (`disk_probe_dskio.py`, probe 2).
      **GETDPB decision:** `getdpb` ($4016) stays an **intentional carry-set stub**
      — the DPB is a Disk-BASIC/MSX-DOS structure, zerobas's self-contained FAT12
      path (`fat_mount`) derives all geometry from the BPB directly and never calls
      $4016, and the MSX DPB field encoding (dir mask/shift, total-cluster encoding)
      is not cleanly sourceable clean-room. De-quarantined: documented as a sourced
      design decision, not a blocked item. `disk_probe_init.py` updated to assert
      SYSTEM only (refreshed `EXP_BDOS` for the code shift). See disk/PROVENANCE.md
      §INIT and §DPB.)
- [x] **FDC driver** — WD2793 register I/O at the National memory-mapped
      register addresses; track/sector/head addressing; read-sector AND
      write-sector command + result-phase read; error handling
      (`disk/disk.asm`: register map sourced from openMSX `NationalFDC.cc`
      ($7FB8 status/cmd, $7FB9 track, $7FBA sector, $7FBB data, $7FBC
      drive/side/motor latch); WD2793 status/command bits from the datasheet.
      `dskio` does the full DSKIO read path: logical→CHS via `div9`, per-sector
      seek+read, polled 512-byte transfer (status-reg DRQ/BUSY — IRQ/DRQ lines
      aren't wired to the Z80 per `NationalFDC.cc`), DSKIO error-code mapping,
      and one restore+retry to recover a stale Track register. `mtoff` drops the
      motor; `phyd_handler` routes to `dskio`. The "Philips/NMS-style" phrasing
      was stale — the CF-3300 reference is National connection style. The FDC
      §TBD rows in [`PROVENANCE.md`](PROVENANCE.md) are now resolved/sourced.
      **WRITE SUPPORT NOW IMPLEMENTED** — `dskio_write` mirrors the read loop
      (count loop + `div9` CHS) and calls the new `fdc_write_phys`/
      `fdc_write_data`: drive/side/motor latch, Type-I seek, then the WD2793
      **Write Sector** command (`CMD_WRITE = $A0`, single record, normal data
      mark — WD2793 DS) and a polled 512-byte transfer (poll `FDC_STATUS` DRQ,
      write each byte to `FDC_DATA`), then result-phase status. Write-protect /
      write-fault (status bit 6 $40) → DSKIO code 0 (no retry); NOTRDY→2,
      RNF→8, CRC→4, LOST→12, `B` = sectors-not-written, exactly like the read
      path. **Differential oracle PASS** (`disk_probe_write.py`, msx-preservation):
      our write to a /tmp scratch image round-trips through our read path, persists
      across a reboot, and is read **byte-identical by the genuine National CF-3300**
      disk ROM. This is the physical sector-write primitive only; FAT12/BDOS write
      logic is a later workstream. disk.rom 16384, 7 baseline warnings (`ST_WP`
      now used); basic.rom byte-identical.)
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
      **Probe 3 (BDOS FCB round-trip) — now a PASSED differential vs real
      MSX-DOS 1.** The CF-3300 disk ROM runs Disk BASIC and exposes no CP/M FCB
      BDOS ($F37D → BIOS ROM, no $0005 BDOS, page 0 is ROM), so the reference for
      the FCB layer is **MSX-DOS**, not the CF-3300 disk ROM. That differential
      now exists and passes: `disk-spec/tools/disk_probe_bdos.py` reads the same
      `ORACLE.BIN` through Open → 17× SeqRead → Close on real MSX-DOS 1.03 (booted
      on `National_CF-3300` from a user-supplied DOS system disk; a tiny `.COM` is
      injected + auto-run via AUTOEXEC.BAT, since hijacking PC at the prompt
      re-enters the non-reentrant console BDOS) and on our `bdos_entry` via CALSLT
      — Open result, all 16 records, the EOF code, and Close are **byte-identical**.
      Strictly black-box (BDOS results + delivered bytes only; MSXDOS.SYS /
      COMMAND.COM never read or disassembled). **Scope: NARROW** — `ORACLE.BIN` is
      an exact cluster multiple (clean EOF) and the FCB extent/current-record fields
      are not differenced; the **FULL** differential is the follow-up below.
      Probe 4 (BLOAD"A:FILE",R) remains the interpreter-glue oracle (loaded bytes +
      exec handoff; read path differential-confirmed via probe 2). See
      disk/PROVENANCE.md §INIT and §BDOS interface.)
- [x] **FULL BDOS differential vs MSX-DOS 1** *(follow-up to the narrow probe)* —
      tighten `bdos_entry` to MSX-DOS FCB semantics and extend `disk_probe_bdos.py`
      to a 2-file differential (cluster-multiple + sub-record-EOF) plus FCB-field
      capture.
      (**PART A — sub-record EOF bounding: DONE, byte-identical.** `bdos_seqread`
      now bounds the record stream by the true file size: Open seeds
      `BDOS_BYTESLEFT` ($E542, 4-byte LE) from `FAT_FILESIZE`; each Sequential Read
      delivers n = min(128, BYTESLEFT) real bytes followed by 128−n bytes of $00,
      code $00, decrementing the counter, and returns EOF ($01) once it hits 0.
      **MSX-DOS partial-record padding turned out to be $00 zero-fill** — oracle
      observation captured by `disk_probe_bdos.py` PART A on real MSX-DOS 1.03
      reading a 1500-byte `ORACLE2.BIN` (last record = 92 real + 36 × $00),
      confirmed *actively* zeroed by pre-filling the DTA with $FF and seeing the
      tail still read $00 (so not Ctrl-Z/$1A, not stale). The probe diffs all 12
      delivered records (incl. the partial) + every A-code byte-for-byte: **PASS,
      byte-identical** ref==ours. The original 2048-byte cluster-multiple case
      still PASSes byte-identical too.
      **PART B — FCB-field mutations: OBSERVED + DOCUMENTED divergence, not chased.**
      `disk_probe_bdos.py` PART B captures the 37-byte FCB on both machines after
      Open / 2 SeqReads / Close and reports a per-field compare. **Matched
      (byte-identical ref==ours):** drive (+0) and the 8.3 name (+1..+11) — the
      fields a reasonable FCB caller reads. **Documented intentional divergences
      (reported, never failed):** extent (+12), record-count (+15), alloc-map
      (+16..31), current-record (+32) — MSX-DOS advances this internal bookkeeping;
      zerobas leaves it $00 because its ONLY `bdos_entry` callers (BLOAD/LOAD/RUN)
      read A + the DTA and never an FCB field, so matching it has no functional
      value (would be a clean-room rabbit hole). The probe's PASS/FAIL hinges on
      PART A data+codes + the matched fields, not the divergences.
      disk.rom rebuilt 16384 / 8 baseline warnings; basic.rom byte-identical.
      Re-ran the whole disk suite (`init`, `dskio` differential vs CF-3300,
      `bload_disk`, `load_disk`, `run_disk`, `bload_fcb`) + crunch + the four basic
      regression probes — all green; the EOF tightening did NOT regress BLOAD/LOAD/
      RUN (they stop at the BSAVE end / $0000 link before EOF). See
      disk/PROVENANCE.md §BDOS interface.)
- [x] **BDOS WRITE FILE API + FAT12 write-back substrate** — implement the FCB
      WRITE subset a `SAVE`/`BSAVE"A:FILE"` path needs and the FAT12 write-back
      layer underneath, differential-confirmed vs real MSX-DOS 1.
      (`disk/disk.asm`: `bdos_entry` now also dispatches **Create ($16)**,
      **Sequential Write ($15)**, and a write-flushing **Close ($10)** (the read
      Close behaviour is preserved). Create finds/makes a root-dir slot and writes
      a fresh entry (name, attribute **$00** — oracle-corrected to match MSX-DOS,
      which does NOT set the archive bit — zeroed size/cluster, date/time $0000).
      Sequential Write buffers a 128-byte record from the DTA into `SECTOR_BUF` and
      flushes a full 512-byte sector when the buffer fills, allocating/extending the
      cluster chain. Close flushes the partial final sector (zero-padded), then
      stamps the dir entry's true first cluster (+26) and byte count (+28). The
      FAT12 write-back substrate (new helpers): **`fat_alloc_cluster`** (sector-by-
      sector free-cluster scan → claim first $000, mark $FFF EOC), **`fat_write_fat_
      entry`** (12-bit pack — the inverse of `fat_next_cluster`'s unpack, incl. the
      512-byte straddle — synced to **all** FAT copies per `BPB_NUMFATS`),
      **`fat_dir_create`** / **`fat_dir_update`**, and **`fat_flush_data_sector`**.
      The file DATA accumulates in `SECTOR_BUF`; the FAT/dir METADATA helpers use an
      independent 512-byte `WBUF` so a cluster scan or dir stamp never disturbs the
      in-flight data sector. New write-position scratch at $E546.. + numFATs/secPerFAT
      cache + `WBUF` $E560 (disk/PROVENANCE.md §Scratch RAM). disk.rom 16384 / 7
      baseline warnings (no new "never used"); basic.rom **byte-identical**.
      **DIFFERENTIAL ORACLE PASS** (`disk-spec/tools/disk_probe_fwrite.py`,
      msx-preservation, on /tmp scratch copies only — never a committed image):
      (1) **functional** — Create + 11× Sequential Write (1408 B = 11 records, a
      sub-sector, sub-cluster size exercising a partial final sector + cluster hop +
      multi-FAT sync) + Close, read back through our own bdos_open/seqread
      byte-identical with correct size + EOF; (2) **cross-machine** — genuine MSX-DOS
      1 (National_CF-3300, ORACLE.COM auto-run via AUTOEXEC) Opens + SeqReads the
      file OUR ROM wrote byte-identical (our FAT chain + dir entry are valid to real
      MSX-DOS); (3) **structural** — the same name+content file written by OUR ROM vs
      by an MSX-DOS WRITER.COM on separate images: byte-identical DATA (each walked
      via its OWN chain) + identical dir entry excluding date/time (+22..25) and the
      free-list-dependent first cluster. **Intentional divergences:** date/time
      stamp = $0000 (no RTC — documented, not fabricated); truncate-if-exists
      orphans the old chain (loader-create subset, quarantined). All 14 disk +
      basic regression probes + crunch still PASS; crunch byte-identical. See
      disk/PROVENANCE.md §BDOS WRITE interface + §FAT12 write-back layer + §Oracle
      probe 6.)
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
- [x] **`LOAD"filename"`** — load a tokenized BASIC file from disk (different
      format from BSAVE binary); parse program-line format and rebuild the
      program store; needed for disk-based loader stubs
      (`basic/cload.asm`: `do_load` now peeks the device string non-destructively
      — a full `"CAS:"` prefix → the unchanged cassette path (`do_tape_prog`),
      anything else → the disk path. The disk path restores the filename start
      from the stack, parses the FCB via the new shared `parse_disk_fcb`
      (factored out of `do_bload`'s `is_disk`, reused by both), then
      `parse_close_run`, then `disk_prog_load`, then `jp run_prog` iff `,R`.
      `disk_prog_load` (reusable, callable by the next `RUN"filename"` item)
      checks `DISKSLOT_OK`, Set-DTA→`DISK_DTA`, Open (require A=$00), requires the
      leading **`$FF` tokenised-BASIC marker** (`BASIC_DISK_ID`, new in
      `basic/sysvars.inc`; source: MSX-BASIC file formats — MSX Wiki / MSX
      Resource Center, the same allowed reference class the `$FE` BSAVE marker
      came from; DISTINCT from `$FE`), then streams the `[link][lineno][tokens][00]`
      line-link image into `TXTBASE` via `disk_getbyte` — mirroring
      `do_tape_prog`'s `ctp_line`/`ctp_body`/`ctp_done` — stopping at the `$0000`
      end-link (authoritative; mid-line EOF ⇒ `load_error`), closing the file,
      and `relink`-ing. No new keyword token (`LOAD` already exists), so crunch
      stays byte-identical.
      `tools/make_test_dsk.py` now also writes `PROG.BAS` (a real on-disk
      tokenised program: `$FF` + the line-link image of `10 POKE &HD002,123`,
      byte-identical to the typed-in crunch). **Divergences / judgment calls:**
      the streamed body-store loop is NOT token-aware (it stops the body at the
      first `$00`) — a pre-existing `do_tape_prog` limitation inherited verbatim;
      the fixture encodes `123` as the 1-byte `INT1` form ($0F $7B), not the `&H`
      16-bit form ($0C $7B $00), to avoid an embedded `$00` in the body, so it is
      a faithful exercise of the shared loop (a token-aware streamed copy is
      deferred and would equally fix `do_tape_prog`). Validated end-to-end
      (openMSX, `disk-spec/tools/disk_probe_load_disk.py`) on
      `C-BIOS_MSX1_BASIC_DISK` with `-diska disk/test720.dsk`:
      `LOAD"A:PROG.BAS"` rebuilds the relinked store at `$8001` byte-identical and
      does NOT auto-run; `LOAD"A:PROG.BAS",R` rebuilds the store AND runs it
      (`($D002)`=$7B). Crunch byte-identical; the four regression probes,
      `disk_probe_init.py`, `disk_probe_bload_fcb.py`, `disk_probe_bload_disk.py`
      and the `disk_probe_dskio.py` differential (vs CF-3300) all still pass. See
      `basic/PROVENANCE.md` §disk LOAD.)
- [x] **`RUN"filename"`** — thin wrapper: `LOAD` then `RUN`
      (`basic/interp.asm` + `basic/cload.asm`: a `RUN_TOKEN` case was added to the
      executor's statement dispatch (next to `LOAD_TOKEN`→`ex_load`) →
      `ex_run`→`do_run`. `RUN"file"` has a `"` right after RUN (not a delimiter),
      so `program.asm`'s direct-mode `dl_cmd` does NOT consume it — it tokenises
      to `RUN_TOKEN` + the quoted filename verbatim and reaches the executor with
      no handler, which this case now provides; the bare-RUN / RUN<lineno>
      direct-mode path is untouched. `do_run`: `skip_spaces`; if the next char is
      `"` → `RUN"A:name"` (disk load+run): `inc hl` past the quote, `parse_disk_fcb`
      + `parse_close_run` (consume closing quote, tolerate a stray `,R`),
      `disk_prog_load` (the SAME reusable routine `LOAD"name"` uses — load logic is
      NOT duplicated), then `jp run_prog`; otherwise (bare RUN / RUN<lineno>)
      `jp run_prog` to run the stored program from the start, ignoring any line
      number (matching the existing bare-RUN semantics). No new keyword token
      (`RUN_TOKEN`=$8A already exists); the disk filename is verbatim ASCII in the
      crunch stream, so the tokeniser is untouched and crunch stays byte-identical.
      **Oracle-confirmed:** `RUN"A:PROG.BAS"` crunches as `8A 22 41 3A 50 52 4F 47
      2E 42 41 53 22 00` (`RUN_TOKEN` + the quoted filename kept verbatim, no
      line-number conversion, no new token), byte-identical vs the Philips VG-8020
      (`basic_probe_crunch.py`, ALL PASS). **Validated end-to-end** (openMSX,
      `disk-spec/tools/disk_probe_run_disk.py`, new) on `C-BIOS_MSX1_BASIC_DISK`
      with `-diska disk/test720.dsk`: `RUN"A:PROG.BAS"` rebuilds the relinked store
      at `$8001` byte-identical (it LOADED) AND runs it (`($D002)`=$7B — it RAN);
      both assertions pass. Crunch byte-identical; the four regression probes,
      `disk_probe_init.py`, `disk_probe_bload_fcb.py` (its `do_disk_bload` landmark
      address refreshed for the code shift this item caused), `disk_probe_bload_disk.py`,
      `disk_probe_load_disk.py` and the `disk_probe_dskio.py` differential (vs the
      CF-3300 reference) all still pass. See `basic/PROVENANCE.md` §disk RUN.
      **Divergences:** none beyond reusing the inherited not-token-aware streamed
      body store (a pre-existing `do_tape_prog`/`disk_prog_load` limitation, see
      §disk LOAD); the test fixture avoids embedded `$00` so the shared loop is
      faithfully exercised.)
- [x] **Provenance entries** — document BDOS call numbers, FCB layout, and
      disk-BSAVE header format in `PROVENANCE.md`; oracle probes to confirm
      byte-identical behaviour vs reference
      (Audit/consolidate/close item — items 2–4 already documented their
      constants inline, so this verified, consolidated, and closed. **Audit
      result:** every constant the TODO names is present and `sourced` — BDOS
      call numbers $0F/$10/$14/$1A (basic/PROVENANCE.md §disk BLOAD execute +
      disk/PROVENANCE.md §BDOS interface), FCB layout (+0 drive code, +1..+11
      8.3 name, matching disk-ROM `fat_find`; §disk-BLOAD scratch FCB + §FCB
      layout), the `[$FE][start][end][exec]` disk-BSAVE header (§disk BLOAD
      execute), the `$FF` tokenised-BASIC marker (§disk LOAD), the cross-slot
      `CALSLT $001C` / `DISKSLOT` / SYSTEM `$F37D` mechanism, the DTA-in-page-3
      rationale, and the `DISK_FCB`/`DISK_DTA`/`DISKSLOT` scratch placement. No
      missing or under-sourced constant; nothing newly quarantined. **Added** to
      basic/PROVENANCE.md a consolidated `§disk BLOAD / LOAD / RUN surface` index
      (a map + constants table tying the four sections together) and an honest
      three-tier **oracle-confirmation status** statement: tier 1 = the DSKIO read
      path is differential-confirmed byte-identical vs the real CF-3300
      (`disk_probe_dskio.py`); tier 2 = the FCB BDOS layer + BLOAD/LOAD/RUN paths
      are validated FUNCTIONALLY on openMSX (no FCB-BDOS reference exists — Disk
      BASIC exposes none), NOT differentially; tier 3 = crunch is byte-identical
      vs the Philips VG-8020. The inherited first-`$00` line-link truncation limit
      (shared with `do_tape_prog`) is documented where the LOAD/RUN provenance
      lives (§disk LOAD Divergences, re-summarised in the new index). Fixed one
      stale cross-reference (§BDOS Set-DTA → §BDOS interface Set-DTA rows). Docs-
      only: both ROMs byte-identical to the pre-edit build (`cmp` clean,
      16384 bytes each); crunch oracle ALL PASS vs Philips VG-8020; disk probe
      suite green. **The whole "zerobas interpreter extensions" section is now
      complete.**)

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
- [x] **Valid MSX boot sector in the test image** *(found during validation)* —
      the old boot sector was filler (`EB FE 90` + zeros at $1E..). A real disk
      machine reads sector 0 into $C000..$C0FF and *CALLs* the boot code at $C01E,
      so the all-$00 area was a NOP slide that ran off the rails — cold-booting the
      CF-3300 with that image **wedged** the reference (PC frozen at $002E, SP
      corrupted to $0026).
      (**Contract sourced from MSX2 TH §3 (MSX-DOS, boot procedure), verbatim**:
      "the contents of the boot sector (logical sector #0) is transferred to C000H
      to C0FFH … when the top of the transferred sector is neither EBH nor E9H,
      DISK-BASIC is invoked. The routine at C01EH is called with CY flag reset.
      Normally, since code 'RET NC' is written to this address, nothing is carried
      and the execution returns." So: load $C000–$C0FF; entry $C01E; reached by
      **CALL** (stub must RET, not JP); first call has **CY reset**; byte 0 must be
      $EB/$E9 for the boot code to be reached; the documented data-disk default is
      **`RET NC`**. **Own-design stub** (`tools/make_test_dsk.py` `_write_boot_code`,
      byte-level comments + the TH citation): `$1E: D0` `RET NC` (the documented
      default — CY reset ⇒ returns to BASIC) + `$1F: C9` `RET` (belt-and-braces
      unconditional return); keeps `$EB $FE $90` at 0–2 and `$55 $AA` at $1FE. This
      is the documented instruction, not a copied boot sector — see
      [`PROVENANCE.md`](PROVENANCE.md) §Boot sector boot code. **FAT geometry
      untouched**: bytes 0–29 and the FAT/dir/data are byte-identical; only
      $1E/$1F differ. **Cold-boot-safe, oracle-verified** (`disk_probe_boot.py`,
      msx-preservation, on the genuine National CF-3300): AFTER the fix PC reaches
      BASIC (ROM/RAM, moving, SP ~$C1xx) and a screenshot shows the Disk-BASIC
      "Enter date" prompt; the synthesised BEFORE/filler image wedges at $002E. The
      probe asserts both. Whole disk probe suite (`dskio` differential vs CF-3300
      incl. sector 0, `bdos` vs MSX-DOS, `init`, `bload_disk`, `load_disk`,
      `run_disk`, `bload_fcb`) + crunch + the 4 regression probes all still PASS;
      basic.rom + disk.rom byte-identical to before (this item touches only
      tools/make_test_dsk.py + the .dsk + the new probe + docs).)

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
