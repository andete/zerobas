<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# Allowed-sources catalogue (rated)

This is the **detailed, per-document** companion to the allowed-sources policy in
[`../README.md`](../README.md) (the firewall: the governing test + the category
list) and the per-component logs ([`../disk/PROVENANCE.md`](../disk/PROVENANCE.md),
[`../basic/PROVENANCE.md`](../basic/PROVENANCE.md),
[`../tape/PROVENANCE.md`](../tape/PROVENANCE.md)). The README states the rules; this
file rates the concrete documents by **quality** and maps each to the **MSX
generation(s)** it serves, as a working reference for current and future work.

## The one governing test

Documentation may be used only where it specifies a **published / standard
interface the original was built to conform to** — never where it reveals a
reference implementation's *internals*. Internal behaviour that appears in no
published spec is reverse-engineered knowledge of protected code, and stays
forbidden even after it has been laundered into a wiki, a forum post, or an
annotated "documentation" file.

## Quality scale

- **A** — primary spec, no provenance risk: manufacturer silicon datasheets /
  manuals, vendor-neutral standards, and this project's own black-box oracle.
- **B** — official platform documentation (ASCII handbooks / specs) or a clean
  reimplementation used for *facts*; authoritative, minor caveat (a handbook one
  step from silicon, or facts-only, or needing a pin / translation).
- **C** — usable *within a stated scope*; provenance- or licence-caveated
  (community compilations → standard interfaces only, never internals; GPL →
  facts only; open third-party software → corroboration only).
- **✗** — forbidden (disassembly / RE compilation). Listed at the end so the line
  is unambiguous.

## Generation legend

`1` MSX1 · `2` MSX2 · `2+` MSX2+ · `R` Turbo-R · `all` every gen · `disk`
disk-equipped machines. zerobas is **MSX1-scoped today**; the `2`/`2+`/`R` rows
are catalogued for *future* work and are not in scope until the charter says so.

---

## CPU

| Source | Q | Gen | Scope / caveat |
|--------|:-:|-----|----------------|
| **Z80 CPU User Manual** (Zilog) | A | 1·2·2+·R | full instruction / timing spec |
| **R800 User's Manual** (ASCII Corp, Systems Division, 1991) | A | R | the **official** ASCII R800 CPU manual: instruction set (Z80 superset + `MULUB`/`MULUW`), registers, internal extension registers, interrupt modes, DMA, timings. Digitised from authentic manual scans (grauw `resources/cpu/r800_users_manual.php`); the online transcription may be **incomplete** — prefer the scans. Third-party "undocumented-R800 / timing" compilations are RE → ✗. (The MSX Turbo-R Technical Handbook, B, remains a secondary official source.) |

## VDP / graphics

| Source | Q | Gen | Scope / caveat |
|--------|:-:|-----|----------------|
| **TMS9918A data manual** (Texas Instruments) | A | 1 | SCREEN 0–3, sprite engine, VRAM/registers |
| **Yamaha V9938 "MSX-VIDEO" Technical Data Book** (Aug 1985) | A | 2 | SCREEN 4–8 + the command (blitter) engine |
| **Yamaha V9958 MSX-VIDEO Technical Data Book / Application Manual** | A | 2+·R | SCREEN 10–12, YJK. Pinned: official Yamaha doc, scanned original + OCR on grauw (`resources/video/yamaha_v9958.pdf`, `…_ocr.pdf`) |

## Sound

| Source | Q | Gen | Scope / caveat |
|--------|:-:|-----|----------------|
| **AY-3-8910 PSG datasheet** (General Instrument) | A | 1·2·2+·R | base `SOUND` / `PLAY` |
| **Yamaha YM2413 (OPLL) Application Manual** | A | 2+·R, + FM-PAC on any | MSX-MUSIC |
| **Yamaha Y8950 (MSX-AUDIO) datasheet** | A | cart / some 2 | MSX-AUDIO (FM + ADPCM). **Not niche** — a staple of the MSX demoscene and homebrew audio; a first-class sound source |

## Disk / DOS / filesystem

| Source | Q | Gen | Scope / caveat |
|--------|:-:|-----|----------------|
| **MB8877A datasheet** (Fujitsu) | A | disk | the CF-3300's **actual** FDC (a WD179x-family-compatible chip) — the precise primary for the FDC interface. *(Audit: reconcile the "WD2793" naming in disk.asm / disk-PROVENANCE; the command/status register interface is identical, so behaviour is unaffected — oracle-validated byte-identical to the CF-3300.)* |
| **WD2793 FDC datasheet** (Western Digital) | A | disk | the WD179x-family reference (compatible command/status interface) the driver was written against |
| **Microsoft FAT specification** | A | disk | FAT12 structures |
| **ECMA-107** | A | disk | vendor-neutral twin of the FAT spec |
| **MSX-DOS 2.20 specs** (ASCII: Program / Function / Command / System) | B | 2·2+·R | the DOS2 *function* interface — **not** the DOS1 in-ROM kernel (does **not** unblock the `$4030` DOS-boot wall, see disk/docs/provider-oracle-scope.md §8.12) |
| **Nextor Driver Development Guide** | C | disk (DOS) | the documented DPB / disk-driver *contract* only — never Nextor code |

## System / BIOS / handbooks

| Source | Q | Gen | Scope / caveat |
|--------|:-:|-----|----------------|
| **MSX Technical Data Book** (ASCII / Microsoft) | B | 1 | the official **MSX1** hardware + software specification — the gen-1 counterpart of the MSX2 TH (this is the "MSX1 handbook"). grauw `resources/system/msxtech.pdf` |
| **MSX2 Technical Handbook** (ASCII; Konamiman's public English translation) | B | 1·2 | the practical anchor reference. **B, not A**: it documents the *standard interface* (with known gaps — it omits the disk-ROM `$4022+` kernel region), not silicon |
| **MSX-BASIC reference** — the MSX Technical Data Book software section + a manufacturer **MSX-BASIC Programming Reference Manual** (e.g. Sony, on Internet Archive) | B | 1 | the user-visible language contract (keywords, functions, errors, file formats). Pins the previously-vague "public MSX-BASIC language reference" |
| **MSX Datapack** (ASCII) | B | 1 | comprehensive official reference; Japanese-only (translation caveat) |
| **MSX2 Datapack** (ASCII) | B | 2 | as above, Japanese |
| **MSX Turbo-R Technical Handbook** (ASCII) | B | R | official; Japanese |
| **i8255 PPI datasheet** (Intel) | A | 1·2 | keyboard / PSG / slot-select port lines |
| **C-BIOS source** (BSD-2) | B | 1·2 | system-variable *addresses* / facts only — not code/expression (BSD-2 attribution if ever copied) |
| **MSX Assembly Page** (`map.grauw.nl`) | C\* | all | standard interfaces only; corroborate internals against the TH. \*When it merely **hosts a manufacturer PDF** (YM2413, Y8950 …), that PDF keeps its own **A** rating |
| **komkon MSX docs** (`fms.komkon.org`) | C | 1·2 | published hook / sysvar *address tables* (facts) only — not RE-derived routine-behaviour text |

## Tooling / project-internal

| Source | Q | Gen | Scope / caveat |
|--------|:-:|-----|----------------|
| **This project's own black-box oracle** | A | 1 (current ref machines) | observed input→output behaviour. Gold standard — *provided it stays black-box*: never read/disassemble a reference ROM or a proprietary binary (BIOS, BASIC ROM, disk-ROM, MSXDOS.SYS, COMMAND.COM) |
| **National CF-3300 schematic** (open hardware) | B | 1 | FDC wiring / register-window facts; **still to pin** — lead: MSX service-manual repositories (hansotten file-hunter "Manuals and Guides", elektrotanya). The FDC is the Fujitsu **MB8877A** |
| **openMSX source** (GPL) | C | all | hardware *register / port facts* only — never code (GPL must not enter this BSD-2 tree) |
| **own design** | — | — | original authorship by this project; not an external source |

## Conditional, low-tier

| Source | Q | Gen | Scope / caveat |
|--------|:-:|-----|----------------|
| **Open-sourced third-party MSX software** (demos, homebrew, games released under an open licence by their authors) | **C (low) — corroboration only** | any (per the target) | Categorically **safer** than the BIOS/BASIC ROM — it is *application* code on top of the platform, **not** the reference implementation zerobas reimplements, so reading it is not "reading the thing we clone." Usable **only** as a non-authoritative *worked example* of how a **documented public hardware interface** (VDP / PSG / MSX-AUDIO registers, BIOS-entry usage) is exercised — to corroborate the A-grade datasheet/oracle, never to replace them. **Hard conditions, all required:** (1) **author's original work only** — if the program embeds anything lifted from a proprietary ROM (BIOS font, BASIC token tables, ripped ROM routines / sound / graphics data), that part is forbidden exactly as the ROM is; (2) **techniques/facts, not code** — understand it, write our own; honour its licence; never copy source; (3) **not for BIOS / BASIC / DOS *behaviour*** — a demo does not document those interfaces and the oracle is both better and safer there |

---

## ✗ Forbidden (never a source)

- the **MSX Red Book** and any other BIOS/ROM **disassembly published as a book or doc**;
- **any** reference BIOS / BASIC-ROM / disk-ROM disassembly;
- the bytes of any proprietary system binary (reference ROM, MSXDOS.SYS, COMMAND.COM)
  read as anything other than an **oracle** (identical inputs in, observed outputs out);
- the **MSX Wiki, MSX Resource Center**, and other community reverse-engineering
  compilations — where they restate a published interface, cite that published source
  instead; where they reveal proprietary internals, they are out.
