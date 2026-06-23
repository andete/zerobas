# C-BIOS disk ROM: status and what a `cbios-disk` effort would face

A survey of where open-source MSX disk-ROM support stands, why C-BIOS has none,
and what a hypothetical clean-room disk-ROM sibling project (analogous to
[cbios-tape](https://github.com/andete/cbios-tape) and zerobas) would actually be
starting from. Compiled from the vendored C-BIOS source, its git history, the
project's status page, the msx.org development forum, and the Nextor project.

## Verdict

C-BIOS ships **no working disk ROM**. What exists in the tree is an **abandoned
2004–2005 proof-of-concept**: a *read-only* "ROM disk" with **no real floppy
controller** and **no write path**. It has been untouched in substance for ~20
years, and the gap is acknowledged and deliberately left open by the maintainers.

A `cbios-disk` effort is therefore closer to greenfield than the cassette work was,
with one structural asymmetry: **C-BIOS cannot be its own oracle** for disk (its own
`dskio` is the stub), so differential validation must target a *real* disk-ROM
machine rather than C-BIOS itself.

## What the upstream C-BIOS disk ROM actually is

`reference/cbios/disk/disk.asm` builds `cbios_disk.rom`, but its core routine is
explicitly incomplete — `; NOTE: This routine is still stubbed` sits directly above
`dskio:` ([disk.asm:253](../reference/cbios/disk/disk.asm)).

Despite the file header ("based on WD2793 FDC"), the code does **not** talk to a
floppy controller. `dskio` implements a **"ROM disk"**: sectors are served from a
disk image *appended to the disk ROM itself*, addressed through a **Konami4 mapper**
(it writes a page number to `$6000`/`$8000`/`$A000` and `LDIR`s 512 bytes per
sector). It handles multi-sector reads and the awkward page-0/1/2 load cases. On top
sits a partial BDOS jump table (`SETDTA`, `RDABS`, `DSKRST`, `CURDRV`, partial
`CONOUT`/`STROUT`, `VERIFY` as a no-op).

What it does **not** do:

- **No writing** — `dskio_write` unconditionally returns a write-protect error
  (`xor a; scf`, [disk.asm:390](../reference/cbios/disk/disk.asm)).
- **No real FDC** — no controller driver; the "disk" is a baked-in ROM image.
- Open in-code TODOs about sectors crossing a page boundary and which slot to load
  into.

So it is enough to *boot a read-only disk image baked into the ROM* as a
demonstration, not a usable disk interface.

### Timeline (from cbios/cbios git history)

| Date | Event |
|------|-------|
| 2004-12-26 | `initial diskrom implemented` |
| 2004-12-29 | hacks to make the NMS8250 disk ROM run on top of C-BIOS |
| 2005-01-08 | "ROM disk" via Konami4 mapper serving sectors from an appended image; PHYDIO→DSKIO; BDOS jump table; SETDTA/RDABS; page-1 loading |
| 2005-01-09 | partial BDOS: DSKRST, CURDRV, CONOUT, STROUT, VERIFY(noop); DRVINF table |
| 2008 / 2014 | only `$Id$`-keyword churn to `disk.asm` — no functional change |
| 2017 / 2018 | releases 0.28, 0.29, 0.29a — **no disk support added** |

All substantive disk work happened in a ~2-week burst in winter 2004–2005, then
stopped. The official status page (cbios.sourceforge.net) still states verbatim:
*"There is no cassette support yet. There is no disk support yet. There is no BASIC
yet."*

## Community status (msx.org)

Thread: *"Status of cbios development regarding disks"* (msx.org forum,
development), **March–April 2013**:

- **2013-03-26 — Manuel Bilderbeek** (lead C-BIOS maintainer), asked directly about
  disk support: *"As far as I know, no one is working on it. So, only soon if someone
  starts working on it very fast and very soon!"*
- **2013-03-27** — Vampier: *"the cbios project needs an overhaul/restart"*; Manuel:
  *"Why? It just needs work...."*
- **2013-04-19** — when a user floats reusing copyrighted BIOS code, Manuel restates
  the clean-room firewall: *"If you suggest to use code from copyrighted ROMs in
  C-BIOS, then what's the point of C-BIOS? ... the whole point of C-BIOS is not to use
  such code."* — the same discipline this repo follows (see
  [`CONTRIBUTING.md`](../../CONTRIBUTING.md)).

Notably, the user's actual request was **not** full disk-BASIC but a **minimal
bload/load/run loader** — *"few commands would be needed like: bload, defusr,
call"* — including the multi-part megaROM idiom
`bload"usas.1",r:bload"usas.2",r:...`. That is exactly the scope of this repo's
[zerobas-BASIC](../../basic/docs/feasibility.md), whose Phase 1 is
"first light: `BLOAD\"name\",R`". The community articulated this minimal-loader shape
in 2013; zerobas-BASIC is one clean-room realization of it.

## The three layers (don't conflate them)

The 2013 thread conflated "disk support" with "a loader." They are different layers,
and the open-source coverage differs per layer:

| Layer | What it is | Open-source status |
|-------|-----------|--------------------|
| Loader / interpreter | tokeniser + exec loop running `BLOAD/LOAD/RUN` | this repo's zerobas-BASIC (`basic/`, clean-room) |
| Disk **BIOS** (lower half) | FDC driver: `DSKIO`/`DSKCHG`/`GETDPB`/`PHYDIO` | **the real gap** — only the abandoned C-BIOS ROM-disk PoC |
| Disk **OS** (upper half) | BDOS, FAT filesystem, MSX-DOS | [**Nextor**](https://github.com/Konamiman/Nextor) — open since 2018, FAT16 |

A `bload/load/run` loader still needs a disk **BIOS** beneath it to read sectors, and
**Nextor** sits *above* that BIOS — it is an MSX-DOS 2.31-derived DOS kernel that
still requires a hardware **driver** (the `DSKIO`/`PHYDIO` lower half) for whatever
interface is targeted. Nextor also carries a different licence/provenance lineage
(MSX Licensing Corporation, not C-BIOS's BSD), which matters for the legal-firewall
reasoning that keeps these as separate runtime-combined components rather than
upstream merges.

## Implications for a hypothetical `cbios-disk`

1. **Closer to greenfield than the tape work.** The existing C-BIOS code is a
   read-only ROM-image fake with no controller driver and no write path — not a
   foundation to extend so much as a sketch to learn from.
2. **C-BIOS can't be its own oracle.** Unlike the BIOS and cassette differential
   probes (which validated against C-BIOS or a real machine where C-BIOS implements
   the call), C-BIOS's `dskio` is the stub. A disk probe suite would have to
   differentially target a **real disk-ROM machine** — the community-recommended
   route is using an actual machine's system+disk ROMs (e.g. Panasonic FS-A1FX) under
   openMSX.
3. **Reusable infrastructure still applies.** The openMSX harness
   ([`docs/openmsx-harness.md`](../../docs/openmsx-harness.md)), the pass/quarantine/bug
   classification, and the IPS-patch / machine-install mechanism that cbios-tape and
   zerobas use would all carry over.
4. **State-heavy contract.** The FDC contract (`DSKIO`/`DSKCHG`/`GETDPB`/`PHYDIO`) is
   more stateful than the byte-level cassette path, which raises the probe-design
   cost.

## Sources

- C-BIOS source + git history: [`reference/cbios/disk/disk.asm`](../reference/cbios/disk/disk.asm),
  `cbios/cbios` commit log (2004–2018)
- [C-BIOS Association status page](https://cbios.sourceforge.net/)
- msx.org forum: [*Status of cbios development regarding disks*](https://www.msx.org/forum/msx-talk/development/status-cbios-development-regarding-disks) (2013)
- [Konamiman/Nextor](https://github.com/Konamiman/Nextor)
- [openMSX `Contrib/README.cbios`](https://github.com/openMSX/openMSX/blob/master/Contrib/README.cbios)
