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

🔴 **THAT EXCLUSION WAS WRONG AND IS WITHDRAWN (2026-09-03) — see §11.**
This section used to read: *"Rows needing a live disk are excluded by
construction. `OPEN`/`FILES`/`KILL`/`NAME` return the fixture's `load error` on a
diskless machine — an unreadable cell, not a divergence. Counting them would have
inflated this finding by a third."* Every clause of that is false.

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

### 5.2.1 ✅ The hook set, MEASURED — 35 slots

`scratchpad/hookdiff_probe.py` reads the published system-hook region
`$FD9A..$FFE7` on both references and diffs it. 42 five-byte slots differ, and
they fall into two clearly distinct shapes:

| shape | vg8020 (no disk) | cf3300 (disk) | count |
|---|---|---|---|
| **installed hook stub** | `C9 C9 C9 C9 C9` (five `RET` — unclaimed) | `F7 87 <addr-lo> <addr-hi> C9` | **35** |
| not that shape | `FF`/`00` patterns | `C9`/`FF` patterns | 7 |

`F7` is `RST 30h` (the inter-slot call), `87` the slot byte, then a 2-byte target
and a `RET` — the documented MSX hook-installation stub. The 35:

```
$FD9F $FDEF $FDF9 $FDFE $FE08 $FE12 $FE17 $FE21 $FE26 $FE2B $FE30 $FE35 $FE3A
$FE3F $FE44 $FE49 $FE4E $FE58 $FE5D $FE62 $FE71 $FE76 $FE7B $FE80 $FE85 $FE8A
$FE99 $FE9E $FEA3 $FEAD $FEB2 $FEB7 $FEFD $FFA7 $FFAC
```

🟢 **THE MEASUREMENT PASSED A CONTROL NOBODY PLANTED.** `$FFA7` is in that list —
and `disk/disk.asm`'s own header already says it *"installs the standard HPHYD
($FFA7) -> DSKIO inter-slot hook"*. So the diff independently rediscovered the one
hook this project already documents, with exactly the expected signature.
`$FD9F` (H.TIMI, which `keytrap.asm` and `playsvc.asm` already use) is in it too.
Two known hooks recovered from a blind diff is what says the other 33 are real.

⚠️ **THE 7 OTHERS ARE NOT CLAIMED AS HOOKS.** Six (`$FFCA`–`$FFE3`) show `FF`/`00`
patterns on one side and `C9`/`FF` on the other — uninitialised RAM differing by
boot history, not installed stubs. `$FEBC` reads `33 33 C3 1D 6F` and needs its
own look. Counting all 42 would have overstated the set by a fifth.

### 5.2.2 ✅ Names attached — 35 of 35, from a grade-B source

Source: the **MSX2 Technical Handbook** appendix (Konamiman's public English
translation, <https://www.konamiman.com/msx/msx2th/th-ap.txt>) — grade **B /
Scoped** in `docs/allowed-sources.md`, an interface table, no code. The join was
done **in code from the probe output**, not transcribed by hand.

🟢 **THREE IN-REPO CONTROLS, ALL MATCHING**, checked before believing any row:
`$FD9F` = H.TIMI (`basic/sysvars.inc`: `H_TIMI equ $FD9F`), `$FFA7` = H.PHYD
(`disk/disk.asm`: *"the standard HPHYD ($FFA7) -> DSKIO inter-slot hook"*), and
`$FFCA` = the expanded-BIOS call, which `sysvars.inc` calls H.BEXT — same address
and meaning, different name between the two sources, worth knowing.

**Every one of the 35 measured stubs is a named hook, and every one is
disk-related** (plus H.TIMI, which a disk ROM legitimately chains for drive-motor
timeout, and H.ERRP for error display):

```
$FD9F H.TIMI   $FDEF H.DSKO   $FDF9 H.NAME   $FDFE H.KILL   $FE08 H.COPY
$FE12 H.DSKF   $FE17 H.DSKI   $FE21 H.LSET   $FE26 H.RSET   $FE2B H.FIEL
$FE30 H.MKI$   $FE35 H.MKS$   $FE3A H.MKD$   $FE3F H.CVI    $FE44 H.CVS
$FE49 H.CVD    $FE4E H.GETP   $FE58 H.NOFO   $FE5D H.NULO   $FE62 H.NTFL
$FE71 H.BINS   $FE76 H.BINL   $FE7B H.FILE   $FE80 H.DGET   $FE85 H.FILO
$FE8A H.INDS   $FE99 H.LOC    $FE9E H.LOF    $FEA3 H.EOF    $FEAD H.BAKU
$FEB2 H.PARD   $FEB7 H.NODE   $FEFD H.ERRP   $FFA7 H.PHYD   $FFAC H.FORM
```

🎯 **AND EVERY VERB THIS GATE ALREADY PINS HAS ITS OWN DEDICATED HOOK.** There is
nothing to invent:

| verb | hook | verb | hook |
|---|---|---|---|
| `MKI$` | `H.MKI$` `$FE30` | `CVI` | `H.CVI` `$FE3F` |
| `MKS$` | `H.MKS$` `$FE35` | `CVS` | `H.CVS` `$FE44` |
| `MKD$` | `H.MKD$` `$FE3A` | `CVD` | `H.CVD` `$FE49` |
| `DSKF` | `H.DSKF` `$FE12` | | |

⚠️ **`$FEBC` (H.POSD) IS A LOOSE END, NOT A CLOSED ONE.** The table names it a
hook, but the CF-3300 holds `33 33 C3 1D 6F` there — not the `F7 87 … C9`
inter-slot stub every other claimed hook uses. Either it is claimed by a
different mechanism (a bare `JP`, valid only while the disk ROM is mapped) or the
5-byte read is misaligned at that slot. It is excluded from the 35 and flagged;
it is **not** silently counted either way.

⚠️ **24 table entries are NOT claimed by this disk ROM** — `H.SETS` `H.IPL`
`H.CMD` `H.ATTR` `H.SETF` `H.MERG` `H.SAVE` `H.RSLF` `H.SAVD` `H.FPOS` `H.DEVN`
`H.GEND` `H.RUNC` `H.CLEAR` `H.LOPD` `H.STKE` `H.ISFL` `H.OUTD` `H.CRDO`
`H.DSKC` `H.DOGR` `H.PRGE` `H.ERRF` (and `H.POSD` above). The hook AREA is
bigger than what Disk BASIC 1.0 uses, so "the hook exists" does not mean "the
reference uses it" — a distinction that matters when deciding what zerobas must
install.

🔴 **AND ROUND 1 OF THIS DIFF WAS 90% BLIND WHILE PRINTING A VERDICT.** It read
64 bytes per chunk — 128 hex characters into a 40-column screen — so nine of ten
chunks per side matched nothing, and it still reported "3 hooks claimed" off an
almost entirely absent table. The probe now names unread cells as unread and
refuses to let a hook count be read past them.

### 5.3 Scope

A multi-slice migration, and the gate orders it: the **no-medium verbs the gate
already pins** (`MKI$` `MKS$` `MKD$` `CVI` `CVS` `CVD` `DSKF`) first, then the
channel verbs. Each slice must leave `make nodisk-acceptance` green **with its
pins moved** — a fixed row that keeps its old pin is precisely the failure mode
§4 built that gate to catch.


## 6. The calling convention — settled from C-BIOS and our own precedent

The Technical Handbook documents the hook **layout** but not how a caller learns
a hook was *handled*. That convention is not observable in the reference without
tracing inside its ROM, which this project does not do — so it was answered from
sources that are permitted and, as it turns out, already in this tree.
**Joost's suggestion:** *"we can look in the c bios code to see how they handle
hooks."*

**1. The layout is confirmed three ways.** The Technical Handbook gives
`RST 30H (0F7H) / byte data / addr-lo / addr-hi / RET (0C9H)`; my hook diff
measured `F7 87 <lo> <hi> C9` on all 35 claimed slots; and `disk/init.asm`
already *writes* exactly those five bytes for `HPHYD`.

**2. An unclaimed hook is `RET` with the flags untouched.** C-BIOS's hook-area
init `$C9`-fills `$FD9A..$FFE7` — stated in this project's own C-BIOS patch
(`cbios-repack/key-trap-hook.patch`: *"still inside the span the hook-area init
`$C9`-fills ($FD9A..$FFE7), so it defaults to `ret` with CF undisturbed"*) and
independently measured: all seven target slots read `C9C9C9C9C9` on **both**
zerobas builds.

**3. 🎯 AND ZEROBAS ALREADY HAS THE SIGNALLING CONVENTION.** `H_ZKEY`, the KEY-trap
seam this project added to C-BIOS, contracts exactly:

> `CF=1` → swallow this delivery entirely … `CF=0` → expand `FNKSTR[A]` as before

That works *because* an unclaimed hook is a `RET` that leaves CF alone. So the
migration adopts the project's **own established convention** rather than
inventing one, and rather than guessing at the reference's internals:

| | |
|---|---|
| main ROM | clear CF, `CALL <hook>`, `jr c` = handled; fall through = raise ERR 5 |
| with `disk.rom` | the stub inter-slot-calls the body, which returns `CF=1` |
| diskless | the slot is `RET`; CF stays clear; ERR 5 — **correct by absence** |

⚠️ This is **own-design signalling over a published layout**, and it is recorded
as such. The observable contract is what must match the reference (works with a
disk, ERR 5 without); how our two ROMs talk to each other between those points is
ours, because the reference's internal answer is not available without
disassembly.

## 7. Slice 1 — fully specified, nothing left to guess

| verb | hook | verb | hook |
|---|---|---|---|
| `MKI$` | `H.MKI$` `$FE30` | `CVI` | `H.CVI` `$FE3F` |
| `MKS$` | `H.MKS$` `$FE35` | `CVS` | `H.CVS` `$FE44` |
| `MKD$` | `H.MKD$` `$FE3A` | `CVD` | `H.CVD` `$FE49` |
| `DSKF` | `H.DSKF` `$FE12` | | |

* **Install:** extend `disk/init.asm`'s `init:` — it already captures
  `HOOK_SLOT` on entry and writes one such stub; this adds seven more.
* **Bodies:** into `disk.rom`'s interior holes. ✅ **`tools/check_disk_walls.py`
  shipped 2026-09-03 and `make basic-reloc` now prints five regions, not four** —
  so this figure comes from a tool rather than from anyone's memory, which is the
  project's own standing rule and exactly what the "2-byte" error broke.
  Measured: **9012 B in 32 runs**, largest **3420 B at `$6849`** bounded by the
  pin at `$75A5`.
  🎯 **AND A RAW BYTE COUNT WOULD STILL HAVE BEEN THE WRONG NUMBER.** This is a
  provider ROM with **69 pinned entry addresses**, each reached by
  `ds $XXXX - $, $00`, so nearly all the fill is the gap *before* the next pin —
  every hole's usable room equals its fill length exactly, and a body must fit
  before that pin. The check reports room-before-pin per hole for that reason.
  ⚠️ It is a **readout, not a new guard**: overrun was already caught, because a
  negative `ds` makes pasmo emit an empty image and `tools/pad_rom.py` refuses
  it. What was missing was the number.
* **Main side:** `str_mkf` (`basic/strvar.asm`) and `ev_ff_cv` (`basic/expr.asm`)
  lose their bodies and gain a hook call each — the space win, and the reason the
  two were factored into shared bodies in D-MKSD in the first place.
* **Gate:** `make nodisk-acceptance` must stay green **with its pins moved** —
  `k.mks` etc. become `ERR 5` on `zb-nodisk`, matching the oracle. A fixed row
  that keeps its old pin is exactly what §4 built that gate to catch.


## 8. 🔴 THE SPACE ARGUMENT IS WITHDRAWN — the destination has room, the *source* does not

Written 2026-09-03, before any Z80 was cut, from reading the call graph the
migration would have to break.

§5.1 corrected a wrong disk-ROM figure (2 B → 9012 B) and concluded the move was
"a **large** space win — roughly 55× the room". **The 9012 B is right and the
conclusion is wrong**, because it prices the *destination* and the binding
constraint is the *source*.

### What actually pins the verbs to main page 1

A body living in `disk.rom` executes with `disk.rom` mapped at `$4000-$7FFF`, so
it can reach **main's low region** (page 0 still holds slot 0) but **not main
page 1**. Marking each line of `str_mkf` by what it reaches:

| calls | region | movable? |
|---|---|---|
| `eval`, `str_eval_no`, `strscr_desc` | main **page 1** | ❌ never |
| `widen_rhs_operand`, `round_single_and_pack`, `round_and_finalize` | main **low** | ✅ |

Same shape for `ev_ff_cv`: `ev_sp`, `ev_f_empty`, `ev_f_ifc`, `cvi_tmm`,
`str_eval_ix` are page-1-bound; only `flt_int_result` and `pu_deref_body` (low)
and the final `ldir` are not.

**So the parse/marshalling half cannot move at all**, which is also why the
reference must call its hooks *after* evaluating the argument — the main ROM owns
the tokeniser and the evaluator.

### The arithmetic

Measured from `build/basic-reloc.sym` and the instruction sequences:

| | |
|---|---|
| `str_mkf` total body | **72 B** (of which the coercion+copy tail ≈ **35 B** is movable) |
| `ev_ff_cv` parse+checks | **61 B**, page-1 bound; its float tail ≈ **15 B** movable |
| movable, both trios | **≈ 50 B** |
| hook-call cost added back | ≈ 6 B at each shared call site + ≈ 4 B per entry stub to select the hook → **≈ 18 B per trio** |
| **net for main page 1** | **≈ break-even**, perhaps ~15 B recovered |

### What this changes

* **The migration is still worth doing** — but for **faithfulness**, which was the
  actual directive ("diskless should match vg8020"), *not* for space.
* **Any pitch of it as a page-1 relief valve is retracted.** Main page 1 was
  164 B free on 2026-09-03 and would stay about there.
* The 9012 B in `disk.rom` remains genuinely free — it is simply not reachable by
  *this* code. It stays available for anything whose call graph is low-region or
  self-contained.

🎯 **The lesson is the one this project keeps re-filing: a number that is correct
about one side of a question can still answer the wrong question.** The trailing
scan was an instrument error; this was worse, because the instrument was right
and the *inference* was not.

## 9. ✅ D-MKHOOK — the mechanism, proved on one verb

**The first BASIC-extension hook zerobas has ever claimed**, and the first it has
ever *called*: `HPHYD` was installed for foreign hosts and never invoked here, so
the round trip — main page 1 → a RAM `CALLF` stub → `RST 30h` across slots →
`disk.rom` → back — was entirely unproven. `MKI$` is the smallest verb that
proves it.

| | vg8020 (oracle) | zb-disk | zb-nodisk |
|---|---|---|---|
| `LEN(MKI$(258))` | ERR 5 | ` 2 ` | **ERR 5** ✅ |
| `ASC(MKI$(1))` | ERR 5 | ` 1 ` | **ERR 5** ✅ |
| `CVI(MKI$(258))` | ERR 5 | ` 258 ` | **ERR 5** ✅ |

Three rows left the pinned set (8 → 5) and are now scored as ordinary agreeing
rows, so the gate enforces that they stay fixed. `k.cvi` moved because its
*argument* is `MKI$` — **`CVI` itself is not hooked yet**, and `v.cvistr`
(`CVI("AB")`) is the row that still measures `CVI` alone. It is still pinned.

**No regression on the disk side:** `scratchpad/mksd_probe.py` is 0 DIFF / 32.

**Cost: main page 1 164 → 146 B** (−18 B) to gate one verb, which is §8's
arithmetic playing out exactly as predicted — gating costs main-side bytes and
this migration buys faithfulness, not space.

`install_hook` was factored out of `disk/init.asm` into the free corridor, because
the pad before the `$41EF` pin is **25 B** and one inline install had already spent
all of it — a second overran, pasmo emitted an empty image, and `pad_rom.py`
refused it exactly as its own header describes. Nine bytes per hook now, not 25.

### 9.1 Knives — 2/2, after three faults in the harness

```
K-MH1  disk/init.asm no longer INSTALLS H.MKI$   zb-disk loses k.cvi k.mki v.mkifld  PASS
K-MH2  hk_mki returns CF CLEAR instead of set    zb-disk loses k.cvi k.mki v.mkifld  PASS
```

K-MH1 proves the **install** is load-bearing; K-MH2 proves the **CF convention**
carries the answer, not merely the presence of a stub — same visible outcome,
reached by a completely different route.

🔴 **Three harness faults on the way, none in the fix**, and the third is the
worst kind:

1. **The comparison ran backwards.** `zb-disk` *should* differ from the diskless
   oracle at base; killing the hook makes it **stop** differing. Looking for
   newly-differing rows found nothing and failed both arms on a correct fix.
2. **`os.utime(+1)` on restore left files dated in the future**, so the next arm's
   plant looked *older* than the ROM and `make` skipped it → INERT. That stamp was
   the fix for the *previous* knife set; it broke the one after it.
3. 🔴 **Stamping the plant forward too made the source permanently newer than the
   built ROM, so `omsx_preflight` REFUSED to measure — and the scorer read that
   refusal page as "agrees on everything" and reported all 8 rows moving.** The
   preflight did its job; the harness ignored it. The scorer now returns `None` on
   a run with no verdict line, and the mtime games are gone entirely: the arms
   **delete the ROMs** and let `make` rebuild.


## 10. ✅ D-MKHOOK COMPLETE — all seven verbs, and the diskless build is faithful

Batched in one cycle on Joost's suggestion (*"once we know the move to disk rom
works, can't we move all others in one go, saving test time?"*). Safe here for a
specific reason: **the gate has one row per verb**, so a batched change still
localises its own failure — batching costs nothing in diagnosis.

| | vg8020 (oracle) | zb-disk | zb-nodisk |
|---|---|---|---|
| all 8 verb rows | ERR 5 | answers | **ERR 5** |
| `EOF` / `LOF` controls | ERR 59 | ERR 59 | ERR 59 |
| plain-BASIC controls | identical | identical | identical |

**`nodisk-acceptance` pins: 8 → 0.** The diskless build now matches the VG-8020
on every row this probe measures, and the disk build is unchanged
(`mksd_probe` 0 DIFF / 32).

🔴 **AN EMPTY PIN SET IS THE STRICTEST STATE THIS GATE HAS**, not the weakest.
Every row is now scored against the oracle, so any regression is a plain failure
with no pin to hide behind — and a *new* disk verb that answers on a diskless
build lands as a red row rather than as an entry someone must remember to add.

### 10.1 What it cost, plainly

**Main page 1: 164 → 75 B free.** Eighty-nine bytes to gate seven verbs. §8
predicted "roughly break-even" for a migration that *moved bodies*; this slice
moved none, so it is pure overhead — and the overhead is real:

| step | page 1 free |
|---|---|
| before | 164 B |
| `MKI$` alone (the spike) | 146 B |
| + `MKS$`/`MKD$` (shared gate) | 124 B |
| + `CVI`/`CVS`/`CVD` + `DSKF` | **75 B** |

⚠️ **75 B is tight**, and the next page-1 slice has to reckon with it. The
conversions themselves could still follow into `disk.rom` (§8: ~50 B movable),
which would claw back most of the MK/CV gate cost — but that is a separate slice
that must justify itself, not a rider on this one.

### 10.2 Two design notes

**The hook address cannot travel in a register.** `eval` (MK) and the expression
evaluator (CV) both own `IX` as their token cursor and clobber it, so the address
is *selected at the gate* from the width already in `C` — no new RAM cell, and
the three widths 2/4/8 are exactly the three verbs in each trio.

**Calling through `HL` needs no helper.** The hook cell is
`F7 <slot> <lo> <hi> C9`, so pushing a return address and `jp (hl)` runs the
inter-slot call and lands on it; unclaimed, the cell is a bare `ret` and lands
there immediately with `CF` untouched. Six bytes.

⚠️ **Both gates sit AFTER the operand and the `)`**, so a malformed call still
reports its own syntax error first — which is what both references do *with* a
disk. A gate must not reorder errors it was not asked to change. The diskless
behaviour of a *malformed* call is unmeasured on the reference and is not claimed
here.

### 10.3 Knives — 4/4, and two of them are the batch's own argument

```
K-MH1  init installs NOTHING              zb-disk loses all 8 rows      PASS
K-MH2  hk_present returns CF CLEAR        zb-disk loses all 8 rows      PASS
K-MH3  drop H_CVS from the table          zb-disk loses k.cvs ONLY      PASS
K-MH4  drop H_MKS from the table          zb-disk loses k.cvs + k.mks   PASS
```

K-MH1/2 re-prove the mechanism at seven verbs. 🎯 **K-MH3 and K-MH4 are the pair
that matters**: dropping `CVS` does *not* take `MKS$`, while dropping `MKS$` takes
both (`k.cvs` builds its argument with `MKS$`). A blanket presence check would
have moved both arms identically. That asymmetry is what proves the selection is
genuinely per-verb.

### 10.4 The `$41EF` pad decided this code's shape twice in one day

Seven inline installs need 45 B; the pad before that pin is **31 B**, so it
overran and pasmo emitted an empty image — caught by `pad_rom.py`, exactly as its
header describes. The installs are now a table-driven loop in the free corridor
and `init.asm` costs **one call**. The first overrun, hours earlier, is what moved
`install_hook` there in the first place.

⚠️ And one self-inflicted repair: a `str.replace` of `install_hook:` matched the
string inside that routine's **own comment header** first, mangling the comment
into code. Anchor on the label, not on prose that names it.


## 11. 🔴 The channel verbs were never unreadable — the exclusion is withdrawn

§4 and §10 both said `OPEN`/`FILES`/`KILL`/`NAME` return "the **fixture's**
`load error` on a diskless machine — an UNREADABLE cell, not a divergence", and
§4 went further: counting them "would have inflated this finding by a third".

**`load error` is zerobas's own message.** The machine prints it and carries on —
a following `PRINT"C"` still answers `C`. Traced directly:

| | `PRINT"A":FILES` |
|---|---|
| vg8020 (diskless) | `A` then `Illegal function call in 10` |
| zb-nodisk | `A` then **`load error`** |
| zb-disk (no floppy) | `A` then `load error` |

So the cell was always readable, and these were always divergences: the oracle
**refuses because the verb does not exist without a disk ROM**, while zerobas
**runs the verb and fails on the medium**. Four rows the gate had been blind to,
now scored and pinned:

| row | oracle | zb-nodisk | hook (named, unclaimed) |
|---|---|---|---|
| `h.files` | ERR 5 | `load error` | `H.FILE` `$FE7B` |
| `h.kill` | ERR 5 | `load error` | `H.KILL` `$FDFE` |
| `h.name` | ERR 5 | `load error` | `H.NAME` `$FDF9` |
| `h.open` | **ERR 2** | `load error` | — see below |

⚠️ **`h.open` is a different class** and is pinned as characterisation, not as a
hook candidate: the oracle answers **Syntax error**, because `FOR OUTPUT` is not
parseable at all without Disk BASIC. That is a keyword-surface question, which no
handler hook fixes.

🎯 **The lesson is the ordinary one, and it is about confidence rather than
cleverness.** "I do not recognise this output" and "the instrument failed" look
identical until you look — and I asserted the second twice, once with an argument
about how much it would have *inflated* the finding. An unreadable cell must be
**proved** unreadable. The probe's own scorer carried the same premise (it
treated the string `load error` as an apparatus failure); that rule is gone, and
only a genuinely absent capture counts as unreadable now.

**Cost of fixing them:** page 1 is at **75 B** free (2026-09-03) and each verb
gate has run 7–12 B, so hooking the three real candidates is affordable but would
leave very little. That is the next slice's problem, and it should be weighed
against moving conversions into `disk.rom` (§8) to buy the room back first.


## 12. ✅ D-CHANHOOK — FILES / KILL / NAME, and page 1 is now the constraint

The three divergences §11 uncovered are closed. `FILES`, `KILL` and `NAME` go
through `H.FILE $FE7B`, `H.KILL $FDFE` and `H.NAME $FDF9`; a diskless build
answers **ERR 5** like the oracle, and the disk build is unchanged.

**`nodisk-acceptance`: 16 rows, PASS, 1 pin** — `h.open`, held as
characterisation because the oracle answers *Syntax error* (`FOR OUTPUT` is not
parseable without Disk BASIC), which no handler hook fixes.

### 12.1 What it cost, and why this is now the binding constraint

| step | page 1 free |
|---|---|
| before the whole migration | 164 B |
| after the seven no-medium verbs | 75 B |
| after `FILES`/`KILL`/`NAME` | **39 B** |

🔴 **39 B is the tightest page 1 has been, and the next slice cannot ignore it.**
One shared `chan_gate` helper was used rather than three inline gates precisely
because of this — 6 B per verb instead of 12.

⚠️ **The obvious relief is blocked.** §8 identified ~50 B of conversion tail that
could move into `disk.rom`, and with the gates already paid for that would now be
**pure recovery** rather than break-even. But it does not work today: **the disk
ROM has no main-ROM ABI bridge.** `sub/basic-resident-abi.inc` is generated for
the sub-ROM alone, so `disk/*.asm` cannot see `ARGA`, `STRSCR`, `FAC` or the
float-arith entries. Building the equivalent for `disk.rom` — a generated include
plus a staleness check, mirroring `tools/gen_resident_abi.py` /
`check_resident_abi.py` — is the prerequisite, and it is a slice of its own.

### 12.2 A regression the gate caught that review did not

The first cut clobbered **HL — the statement cursor** — to load the hook address,
and all three verbs began answering ERR 2 **on the disk build**. Nothing about the
diskless side changed, so a probe that only looked at the target would have
called it a success.

🎯 **The `zb-disk` column is what caught it**, and it is in the table for exactly
this reason: a change aimed at the diskless build must leave the disk build
alone, and only a row that watches both can say so. Fixed with `push hl`/`pop hl`
(2 B per verb).


## 13. ✅ D-DISKABI — the bridge, and the first body actually living in `disk.rom`

§12.1 named the blocker: `disk.rom` had **no main-ROM ABI bridge**, so the verb
bodies could not follow their hooks. It has one now, and it is witnessed by a
real consumer rather than built on speculation.

**The bridge.** `disk/basic-resident-abi.inc`, generated per build from
`build/basic-reloc.sym` by the *same* `tools/gen_resident_abi.py` the sub-ROM
uses — a **profile**, not a fork, so the two cannot drift. `make
diskrom-abi-check` is the standing assert; `patch-freshness-check` now covers it
as `abi-disk` too, because this gate's own header records that the sub-ROM copy
was **stale in HEAD across 11 commits** before it was covered.

* **Code symbols are ceiling-checked** exactly as the sub list is: `disk.rom` is
  a page-1 ROM, so main's low region is callable and main page 1 is not.
* **RAM symbols are exempt from that ceiling**, and the exemption is the point —
  work-area cells live above `$8000` and are always mapped; applying the
  page-0-resident test would reject every one. They go through the bridge anyway
  so that a *sysvar move* cannot leave `disk.rom` writing the old address.

**The consumer.** `hk_mkfloat` — `MKS$`/`MKD$`'s round-and-pack now runs **inside
`disk.rom`**, the first disk-verb body actually to live there rather than merely
be gated from there. Everything crosses in RAM (width in `STRSCR`, value in
`FAC`/`FACTYP`, result back into `STRSCR`), because `CALSLT` preserves almost
nothing.

**Page 1: 39 → 61 B free** — 22 B recovered.

### 13.1 Two register mistakes, both caught by measurement

🔴 **`widen_rhs_operand` cannot move, because for an integer argument it reads
`DE`** — a register `CALSLT` does not preserve. Moving it broke `MKS$(0)`,
`MKS$(1)`, `MKD$(7)` and `MKS$(3%)` while **every float argument stayed green**,
because only the int path reads a register. `mksd_probe`: 5 DIFF. It stays
main-side; the hook receives `ARGA`, which is RAM.

🔴 **Then the repair went in after `HL` already held the hook address** and
clobbered it — 24 DIFF on the next measurement, controls included. The widen now
runs *before* hook selection. Two ordering bugs in one small block, both found by
running it rather than by reading it.

⚠️ **So the recovery is 22 B, not the 37 B the first (broken) build reported.**
The first number was measured on a ROM that did not work.

### 13.2 A gate this broke that had nothing to do with it

Selecting the profile from the output path reddened **`patch-freshness-check`**,
which regenerates into a **temp directory** to diff against the tracked copy —
that path carries no `sub/` or `disk/` hint, so selection refused it. An explicit
`--profile=` now wins over the path. Textbook "correct by its own rule, breaks a
different invariant", and the battery is what said so.
