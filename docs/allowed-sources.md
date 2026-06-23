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
file rates the concrete documents and maps each to the **MSX generation(s)** it serves.

## The one governing test

Documentation may be used only where it specifies a **published / standard
interface the original was built to conform to** — never where it reveals a
reference implementation's *internals*. Internal behaviour that appears in no
published spec is reverse-engineered knowledge of protected code, and stays
forbidden even after it has been laundered into a wiki, a forum post, or an
annotated "documentation" file.

## Two axes: quality ≠ admissibility

Each source is rated on **two independent** scales. They are not the same question,
and collapsing them hides risk (a meticulous disassembly is *high quality* yet
**inadmissible**; a hobbyist demo is *low quality* yet **admissible** within tight
conditions). The firewall's strength is exactly this separation: **high
information-quality can never promote an inadmissible source** — "but the Red Book
is *accurate*" is a non-argument.

**Quality (Q)** — how authoritative / close to silicon:

- **A** — primary spec, no provenance risk: manufacturer silicon datasheets /
  manuals, vendor-neutral standards, and this project's own black-box oracle.
- **B** — official platform documentation (ASCII handbooks / specs) or a clean
  reimplementation used for *facts*; authoritative, minor caveat (one step from
  silicon, or facts-only, or needing a pin / translation).
- **C** — usable *within a stated scope*; provenance- or licence-caveated.

**Admissibility (Adm)** — clean-room safety, and the *single binding condition*
that keeps it clean:

- **Clean** — usable as-is; no provenance condition (the document *is* the spec the
  silicon conforms to).
- **Scoped** — usable only for the **published interface**, never the protected
  implementation behind it.
- **Conditional** — usable only under explicit, load-bearing conditions (licence
  firewall, corroboration-only, original-work-only).
- **✗** — forbidden. Listed at the end so the line is unambiguous.

## Generation legend

`1` MSX1 · `2` MSX2 · `2+` MSX2+ · `R` Turbo-R · `all` every gen · `disk`
disk-equipped machines. zerobas is **MSX1-scoped today**; the `2`/`2+`/`R` rows
are catalogued for *future* work and are not in scope until the charter says so.

---

## Hardware silicon datasheets

For every chip here the analysis is the same and trivial: **the datasheet *is* the
spec the silicon conforms to**, so it is the legitimate, safe clean-room source even
though we reimplement the chip's behaviour — there is no reference implementation to
launder around, the chip *is* the reference.

| Source | Q | Adm | Gen | Scope / caveat |
|--------|:-:|:---:|-----|----------------|
| **Z80 CPU User Manual** (Zilog) | A | Clean | 1·2·2+·R | full instruction / timing spec; we don't even reimplement the Z80 |
| **R800 User's Manual** (ASCII Corp, Systems Division, 1991) | A | Clean | R | the **official** ASCII R800 manual: instruction set (Z80 superset + `MULUB`/`MULUW`), registers, internal extension registers, interrupts, DMA, timings. Digitised from authentic scans (grauw `resources/cpu/r800_users_manual.php`); the online transcription may be **incomplete** → prefer the scans. Third-party "undocumented-R800 / timing" compilations are RE → ✗ |
| **TMS9918A data manual** (Texas Instruments) | A | Clean | 1 | SCREEN 0–3, sprite engine, VRAM / registers |
| **Yamaha V9938 "MSX-VIDEO" Technical Data Book** (Aug 1985) | A | Clean | 2 | SCREEN 4–8 + the command (blitter) engine |
| **Yamaha V9958 MSX-VIDEO Technical Data Book / Application Manual** | A | Clean | 2+·R | SCREEN 10–12, YJK. Official Yamaha doc, scanned original + OCR on grauw (`resources/video/yamaha_v9958.pdf`) |
| **AY-3-8910 PSG datasheet** (General Instrument) | A | Clean | 1·2·2+·R | base `SOUND` / `PLAY` |
| **Yamaha YM2413 (OPLL) Application Manual** | A | Clean | 2+·R, + FM-PAC on any | MSX-MUSIC |
| **Yamaha Y8950 (MSX-AUDIO) datasheet** | A | Clean | cart / some 2 | MSX-AUDIO (FM + ADPCM). **Not niche** — a staple of the MSX demoscene / homebrew audio; a first-class sound source |
| **i8255 PPI datasheet** (Intel) | A | Clean | 1·2 | keyboard / PSG / slot-select port lines. *(An Intel silicon datasheet — same class as the chips above, not a handbook.)* |

## Disk / DOS / filesystem

| Source | Q | Adm | Gen | Scope / caveat |
|--------|:-:|:---:|-----|----------------|
| **MB8877A datasheet** (Fujitsu) | A | Clean | disk | the CF-3300's **actual** FDC (WD179x-family-compatible) — the **primary** for the FDC register interface. *(Audit: reconcile the "WD2793" naming in disk.asm / disk-PROVENANCE; register interface identical, behaviour unaffected — oracle-validated byte-identical to the CF-3300.)* |
| **WD2793 FDC datasheet** (Western Digital) | A | Clean | disk | **secondary / compatibility cross-check** — the WD179x-family reference the driver was first written against; no longer "the chip" now the real FDC (MB8877A) is pinned |
| **ECMA-107** | A | Clean | disk | **primary** FAT12 on-disk structures — vendor-neutral, no licence shadow |
| **Microsoft FAT specification** | A | Clean | disk | corroboration only; defer to ECMA-107 (the MS doc carries a long-filename patent penumbra, irrelevant to short-name FAT12 but not worth standing near) |
| **MSX-DOS 2.20 specs** (ASCII: Program / Function / Command / System) | B | Scoped | 2·2+·R | the DOS2 *function* interface only — **not** the DOS1 in-ROM kernel; does **not** unblock the `$4030` DOS-boot wall (disk/docs/provider-oracle-scope.md §8.12) |
| **Nextor Driver Development Guide** | C | Conditional | disk (DOS) | the documented DPB / driver contract **only where it is corroborated by an official ASCII handbook** (the DPB layout is). Nextor's ABI is itself partly RE'd from the original disk ROM → Nextor-*only* internals not in any official spec are ✗; never Nextor code |

## System handbooks (official ASCII platform docs)

The admissibility verdict for every handbook is the *same sentence*: the **published
interface the original conforms to, never the protected implementation behind it**.

| Source | Q | Adm | Gen | Scope / caveat |
|--------|:-:|:---:|-----|----------------|
| **MSX Technical Data Book** (ASCII / Microsoft) | B | Scoped | 1 | the official **MSX1** hardware + software spec — the gen-1 counterpart of the MSX2 TH (the "MSX1 handbook"). Published BIOS entry points + sysvars; never treat an incidental internal detail as spec. grauw `resources/system/msxtech.pdf` |
| **MSX2 Technical Handbook** (ASCII; Konamiman's public English translation) | B | Scoped | 1·2 | the practical anchor. **B, not A**: documents the *standard interface* with **known gaps** — it omits the disk-ROM `$4022+` kernel region. That omission is the documented **edge of the map**: it is *why* `$4030` is walled, not a deficiency to route around |
| **MSX-BASIC reference** — Tech Data Book software section + a manufacturer **MSX-BASIC Programming Reference Manual** (e.g. Sony, Internet Archive) | B | Scoped | 1 | the user-visible *language* contract (keywords, functions, errors, file formats) — not interpreter internals. Pins the previously-vague "public MSX-BASIC language reference" |
| **MSX Datapack** (ASCII) | B | Scoped | 1 | comprehensive official reference; Japanese-only (translation caveat) — stay on the interface line |
| **MSX2 Datapack** (ASCII) | B | Scoped | 2 | as above, Japanese |
| **MSX Turbo-R Technical Handbook** (ASCII) | B | Scoped | R | official; Japanese |

## Tooling / project-internal

| Source | Q | Adm | Gen | Scope / caveat |
|--------|:-:|:---:|-----|----------------|
| **This project's own black-box oracle** | A | **Clean *iff* black-box** | 1 (current ref machines) | observed input→output behaviour. Gold standard — *the discipline is the methodology*: inputs in, outputs out, never read/disassemble a reference ROM or proprietary binary (BIOS, BASIC ROM, disk-ROM, MSXDOS.SYS, COMMAND.COM). The instant you disassemble, it flips to ✗ |
| **National CF-3300 schematic** (open hardware) | B | Clean | 1 | FDC wiring / register-window facts — hardware = facts, not code; **still to pin** — lead: MSX service-manual repos (hansotten file-hunter "Manuals and Guides", elektrotanya). The FDC is the Fujitsu **MB8877A** |
| **C-BIOS source** (BSD-2) | B | Conditional | 1·2 | a **peer clean-room reimplementation**, not an authority. Use for *facts* (published sysvar addresses / memory map) only. The binding condition is **clean-room independence** (we don't lift its code/expression even though BSD-2 would permit it, so our reimplementation stays our own), not the licence |
| **openMSX source** (GPL) | C | Conditional | all | hardware *register / port facts* only. **GPL is the binding condition**: code/expression must never enter this BSD-2 tree — only non-copyrightable facts, and even those are corroboration (openMSX's model is itself partly RE'd) cross-checked against the datasheet |
| **MSX Assembly Page** (`map.grauw.nl`) — split three ways | — | — | all | **(1) hosted manufacturer PDFs** (V9958, YM2413, Y8950, R800 manual) → **A / Clean**, the PDF's own provenance; **(2) grauw's own compiled interface notes** → **C / Scoped**, standard interfaces only, corroborate against the TH; **(3) hosted disassemblies / RE'd system listings** → **✗** |
| **komkon MSX docs** (`fms.komkon.org`) | C | Scoped | 1·2 | published hook / sysvar *address tables* (facts) only — not RE-derived routine-behaviour text |
| **own design** | — | — | — | original authorship by this project; not an external source |

## Conditional, low-tier

| Source | Q | Adm | Gen | Scope / caveat |
|--------|:-:|:---:|-----|----------------|
| **Open-sourced third-party MSX software** (demos, homebrew, games released under an open licence by their authors) | **C (low)** | Conditional | any (per the target) | Categorically **safer** than the BIOS/BASIC ROM — it is *application* code on top of the platform, **not** the reference implementation zerobas reimplements, so reading it is not "reading the thing we clone." Usable **only** as a non-authoritative *worked example* of how a **documented public hardware interface** (VDP / PSG / MSX-AUDIO registers, BIOS-entry usage) is exercised — to corroborate the A-grade datasheet/oracle, never to replace them. **Hard conditions, all required:** (1) **author's original work only** — if it embeds anything lifted from a proprietary ROM (BIOS font, BASIC token tables, ripped routines / sound / graphics data), that part is forbidden exactly as the ROM is; (2) **techniques/facts, not code** — understand it, write our own; honour its licence; never copy source; (3) **not for BIOS / BASIC / DOS *behaviour*** — a demo does not document those interfaces and the oracle is both better and safer there |

---

## ✗ Forbidden (never a source)

**High information-quality does not promote any of these** — that is the entire point
of rating quality and admissibility separately.

- the **MSX Red Book** and any other BIOS/ROM **disassembly published as a book or doc**;
- **any** reference BIOS / BASIC-ROM / disk-ROM disassembly;
- the bytes of any proprietary system binary (reference ROM, MSXDOS.SYS, COMMAND.COM)
  read as anything other than an **oracle** (identical inputs in, observed outputs out);
- the **MSX Wiki, MSX Resource Center**, and other community reverse-engineering
  compilations — where they restate a published interface, cite that published source
  instead; where they reveal proprietary internals, they are out.
