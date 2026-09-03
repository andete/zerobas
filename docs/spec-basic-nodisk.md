# D-NODISK — the diskless build target, and what it measures

**Status:** target and gate shipped 2026-09-03; **8 divergences pinned, not
fixed.** **Gate:** `make nodisk-acceptance`
(`probes/basic/basic_probe_nodisk.py`). **Probe that found it:**
`scratchpad/nodisk_probe.py`.

## 0. The decision

> **Joost, 2026-09-03:** *"the diskless zerobas should be an official build
> target and any disk related thing should be validated on both."*

It came out of a question about `D-MKSD`: shouldn't the disk-only keywords live
in `disk.rom` behind a hook, as on real hardware? Both halves of that turned out
to be measurable.

## 1. The keyword table belongs in the MAIN ROM — measured

Pointing `kwsweep`'s crunch layer at the **diskless** VG-8020
(`--disk-machine Philips_VG_8020 --layer crunch`), all five MK/CV words crunch
`SAME` as zerobas: the VG-8020 tokenises `MKS$` to `FF AF` **with no disk ROM
present**.

So on real MSX the main BASIC ROM owns the crunch table and the disk ROM supplies
only the **implementation**, through hooks. That is exactly why a diskless
machine tokenises `MKS$` happily and *then* answers `Illegal function call`.
D-MKSD's `kwtable.inc` entries sit where the reference puts them.

## 2. The implementation does not — and it is reachable

`disk/disk.asm`'s own header: zerobas-BASIC reaches the file layer through the
BDOS `SYSTEM` vector with `CALSLT`, *"NOT through the H.\* / HPHYD chain; HPHYD
exists for FOREIGN hosts"*. `disk.rom` is a **storage provider** with no
BASIC-extension hook at all, so every disk verb is implemented BASIC-side.

⚠️ **The first draft of this finding called that unobservable**, since every
installed machine carried `disk.rom`. The decision above makes it reachable, so
it was measured instead.

| row | vg8020 (oracle) | zb-nodisk |
|---|---|---|
| `LEN(MKS$(1.5))` | ERR 5 | `4` |
| `LEN(MKD$(1.5))` | ERR 5 | `8` |
| `CVS(MKS$(1.5))` | ERR 5 | `1.5` |
| `LEN(MKI$(258))` | ERR 5 | `2` |
| `CVI(MKI$(258))` | ERR 5 | `258` |
| `DSKF(0)` | ERR 5 | `0` |
| `CVI("AB")` | ERR 5 | `16961` |
| `ASC(MKI$(1))` | ERR 5 | `1` |
| 🟢 `PRINT 1+1` / `LEN("ABC")` | identical | identical |
| 🟢 `EOF(1)` / `LOF(1)` | ERR 59 | ERR 59 |

**8 DIFF / 12.**

🎯 **The shape is sharper than "disk verbs leak": it is exactly the disk verbs
that need NO MEDIUM.** `EOF`/`LOF` want a channel and already raise; the
conversion functions and `DSKF` compute an answer, so they answer. Those two
green rows are what turn a vague suspicion into a precise one.

🔴 **And it is not new with D-MKSD** — `MKI$`, `CVI` and `DSKF` show it too. This
is the standing architecture, not something that slice broke.

## 3. The target

`C-BIOS_MSX1_EU_REPACK_NODISK`: the same merged main ROM and sub-ROM, slot 3-1
**empty**, nothing else changed — the hardware shape of the VG-8020 oracle.
`tools/install-repack-machine.py --no-disk` writes it, and **`make
repack-machine` installs both**, so neither machine can go stale against the
other.

## 4. Why the divergences are PINNED rather than tolerated

The gate records each divergent row's exact `(oracle, nodisk)` pair. A gate that
merely *allowed* these rows would stay green through a regression **and** through
a fix — and this project has been bitten by the second: a filed row that quietly
stops diverging is the `CVI` shape that `tools/filed-row-known.txt` opens on.
Pinning makes the gate go red when the answer **changes in either direction**,
which is what makes it a measurement rather than a permission slip.

⚠️ **Rows needing a live disk are excluded by construction.**
`OPEN`/`FILES`/`KILL`/`NAME` return the fixture's `load error` on a diskless
machine — an unreadable cell, not a divergence. Counting them would have inflated
this finding by a third.

## 5. The architectural target (decided 2026-09-03)

> **Joost:** *"not only should diskless match vg8020 and withdisk the cf, the
> implementation of the disk related keywords should probably be in the disk rom
> (there's holes, plenty of space) and work via the officially documented
> hooks."*

So the shape is the reference's own: **the main ROM keeps the keyword TABLE**
(§1 measured that this is faithful) and the **bodies move into `disk.rom`,
reached through the published MSX BASIC expansion hooks**. A diskless zerobas
then matches the VG-8020 *because the code is not there* — which is how the
reference gets it right — rather than by a presence guard bolted onto verbs that
are still present.

### 5.1 🔴 The space figure in §5 of this document's first draft was WRONG

It said `disk.rom` was "16384 B with a **2-byte** trailing free run", and
concluded the move was "not obviously a space win". That was a **trailing** scan,
which cannot see interior holes. Re-measured 2026-09-03 by scanning for interior
fill runs:

| fill | runs ≥ 16 B | total | largest |
|---|---|---|---|
| `0x00` | 32 | **9012 B** | 3420 B at `$2849` (mapped `$6849`), 2531 B at `$1602` (`$5602`) |
| `0xFF` | 0 | 0 | — |

Main page 1 was **164 B** free the same day. The move is a **large** space win —
roughly 55× the room — and the number that priced it out was an instrument error
of exactly the kind this project keeps filing against other people's figures.

⚠️ Not all 9012 B are necessarily available: the disk ROM has pinned
fixed-offset entry points and stub bodies at known addresses. A real figure needs
a **disk-ROM wall check**, which does not exist — `make basic-reloc` reports the
main and sub walls only. The two large runs are the candidates.

### 5.2 The hook set must be sourced, not recalled

⚠️ The hook names and addresses must come from a **published source** (MSX
Technical Handbook / MSX Assembly Page) and be cited into `PROVENANCE.md` — not
written from memory.

🎯 **And they are measurable without any document.** Diff the hook RAM region
between the VG-8020 (no disk ROM) and the CF-3300 (disk ROM): the entries that
differ **are** the hooks disk BASIC installs. That is an observation of an
interface boundary — the same class as the already-published `HPHYD` → `DSKIO`
vector this project documents — and needs no disassembly. Do it first, then match
it against the published list; agreement between an independent measurement and
the documentation is worth more than either alone.

### 5.3 Scope

A multi-slice migration, and the gate orders it: the **no-medium verbs the gate
already pins** (`MKI$` `MKS$` `MKD$` `CVI` `CVS` `CVD` `DSKF`) first, then the
channel verbs. Each slice must leave `make nodisk-acceptance` green **with its
pins moved** — a fixed row that keeps its old pin is precisely the failure mode
§4 built that gate to catch.
