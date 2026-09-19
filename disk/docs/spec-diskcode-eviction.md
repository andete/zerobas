<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — evicting the disk code from the main ROM

**Status: written 2026-09-17; five verbs moved under it (D-MKINT, D-CVMOVE,
D-DSKFMOVE, D-LRSETMOVE, D-FIELDMOVE). RE-FRAMED 2026-09-18 by the ruling in
§0.0, which replaces the denominator this spec was originally organised around.**
Ruled by Joost, 2026-09-17: *"There should probably be hardly any disk code left
in the main Rom."*

## 0.0 🏗️ THE GOVERNING EQUIVALENCE (Joost, 2026-09-18)

> *"Lets consider main + sub our replacement of reference main; the end result
> should be similar to the reference both for with disk and without disk."*

**`main.rom` + `sub.rom` TOGETHER are our replacement for the reference's BASIC
ROM. `disk.rom` is our replacement for its disk ROM.** The sub ROM is an
artefact of our size budget, not an architectural tier: nothing about a byte's
placement may depend on which of the two it landed in.

Three consequences, and they settle questions this spec previously left open:

**(1) THE CONSTRAINT REACHES `sub.rom`.** This spec used to ask whether "no disk
code in main" stopped at main or propagated. Under the equivalence it is not a
question: disk *implementation* in `sub.rom` is exactly as misplaced as disk
implementation in main. The disk-only tenants in `sub.rom` page 1 — **2.2–3.7 KB,
measured 2026-09-18, see §0.2** —
the FAT primitive engine above all — are there because `sub.rom` was the only
ROM with room in the D-DISKABI era (2026-07-19), which is a HISTORICAL
placement, not a designed one. They are in scope.

**(2) THERE IS NO DISKLESS BUILD, AND THERE MUST NOT BE ONE.** The reference
ships ONE BASIC ROM that works both with and without a disk ROM; the disk ROM's
presence is the only thing that differs. A `DISK_RESIDENT` conditional-assembly
switch producing a second main would therefore be LESS faithful, not more — and
it was recommended to Joost on 2026-09-18 before this ruling and is now
withdrawn. **The build arrangement we already have is the correct one**: the
same `main.rom` + `sub.rom` in both machines, with slot 3-1 empty for
`C-BIOS_MSX1_EU_REPACK_NODISK`. What is wrong is the CONTENT, not the build.

**(3) THE DISKLESS TARGET STOPS BEING A SEPARATE OBLIGATION.** Once every disk
implementation is behind a hook, a diskless machine behaves like the reference
for free: the cells are unclaimed, `chan_gate` raises ERR 5, and that is the
whole of it. §9's obligation becomes a CONSEQUENCE of the architecture rather
than a thing each slice must remember.
⚠️ **WHAT STAYS IN MAIN ON A DISKLESS MACHINE IS THE HOOK STUB ITSELF.** The
reference's diskless main ROM still crunches `MKS$` and answers ERR 5
(docs/spec-basic-nodisk.md §1), so ~10 B per verb of `ld hl,H_x` +
`call chan_gate` is FAITHFUL main-ROM BASIC. "No disk code" means no disk
IMPLEMENTATION; it has never meant no disk SURFACE.

🎯 **AND THE TARGET BECOMES CHECKABLE.** "Hardly any disk code" is a judgement;
*"no disk-implementation symbol is reachable in main+sub"* is an invariant a
gate can hold. That is a better end state than any byte count in §1, and
designing that gate is part of this work rather than a follow-up to it.

## 0.2 🟢 WHAT sub.rom's DISK CODE ACTUALLY COSTS — MEASURED 2026-09-18 (D-SUBDISK)

§0.0 put `sub.rom`'s disk-only tenants in scope and priced them at "~4.8 KB".
That was HAND CLASSIFICATION of label spans — my reading, never a tool's — and it
was the last unmeasured quantity this plan rested on. Main's half was already
derived (`carve_scout.py --census`: 2408 B total, 250 SHARED, 2158 PRIVATE).

`scratchpad/subdisk_census.py` computes it as a closure DIFFERENTIAL over
`check_dead_code.Spans`, which already resolves fall-through and shared-tail
edges: seed the disk-only tenants, subtract what every other tenant reaches, and
what remains is alive ONLY because of the disk.

| | bytes | spans | meaning |
|---|---|---|---|
| **LOW** | **2178 B** | 133 | minus every other tenant, INCLUDING `bload`/`save` — a strict lower bound |
| **HIGH** | **3708 B** | 221 | minus the unmixed only, i.e. `bload`/`save`'s disk arms leave too, which they would |

🔴 **IT IS A BRACKET AND NOT A NUMBER ON PURPOSE.** `bload_tenant` and
`save_tenant` serve TAPE AND DISK. Counting them as disk over-states; excluding
them subtracts the FAT code their disk arms need, which under-states. Picking one
and calling it "the" figure is precisely the hand classification this replaces.

**So sub.rom's disk cost is 2.2–3.7 KB, and the ~4.8 KB was high by 30–120 %.**

⚠️ **THE SIZE MODEL HAD A TRAP, AND A SANITY CHECK IS WHAT FOUND IT.**
`Spans.size()` is label-to-NEXT-LABEL, so it includes PADDING: summed over all of
`sub.rom` it gives 62611 B for a 32768 B ROM — **1.91×** — because a few spans sit
before the page-boundary pads (`sub_p1_ping` alone measures 16203 B). The first
cut of this measurement reported an "upper bound" of **34705 B, more than the ROM
holds**, and that impossibility is the only reason the flaw surfaced at all.
Those spans are now excluded by name, the exclusion is PRINTED rather than
silent, and `--selftest` asserts the over-count still exists — if the whole-ROM
ratio ever looks plausible, the pads have moved and the exclusion list is stale.

## 0.1 🏗️ ONE FAT12 ENGINE (Joost, 2026-09-18)

> *"we'd obviously don't want two FAT12 engines; if needed we need to
> parametrize where it has its buf"*

Costing the move surfaced that `disk.rom` already carries its own FAT12 engine
for BDOS/MSX-DOS, so BASIC's engine arriving there would make two. **That is
ruled out.** One engine serves both.

🟢 **THE TWO CONTROL BLOCKS ARE ALREADY BYTE-IDENTICAL IN LAYOUT** (read
2026-09-18 from `disk/equates.inc:123-171` and `basic/sysvars.inc:2831-2866`).
Same fields, same order, same offsets — `+0` SECPERCLUS, `+1` FATSTART, `+3`
FIRSTROOT, `+5` ROOTSECS, `+7` FIRSTDATA, `+9` CURCLUS, `+B` CLUSSEC, `+C`
FIRSTCLUS, `+E` FILESIZE, continuing identically through `FAT_DIRREM`. Only the
BASE differs: `$E4A0` (disk) against `$E9C0` (BASIC). **So parametrising the
base is a base change, not a rewrite** — the expensive-sounding half of this is
already done and nobody noticed.

🔴 **CORRECTED 2026-09-18 (D-FATENG): BOTH ENGINES HAVE TWO BUFFERS.** This
paragraph claimed the disk-side engine had ONE `SECTOR_BUF` and that the split
was BASIC's alone. It has `SECTOR_BUF` (`$E2A0`, 512 B) **and `WBUF` (`$E560`,
512 B)** — `disk/equates.inc:123,250` — exactly mirroring BASIC's `FSECTOR_BUF`
(`$E5C0`) / `FWBUF` (`$E7C0`). The data/metadata split is the SAME STRUCTURE on
both sides; only the base addresses differ. That makes unification easier than
this section assumed, not harder, and it is why §0.1a's measurement of the
reference matters for the SHAPE rather than for whether we keep two buffers.

🔬 **SO THE FIRST MEASUREMENT IS JOOST'S OWN QUESTION, AND IT IS BLACK-BOX.**
*"unless bdos actually uses the same buf as disk basic — on the reference"*
(2026-09-18). If the reference's BDOS and Disk BASIC share one sector buffer,
there is nothing to parametrise at all and OUR two-buffer split is the thing to
reconsider. **This is observable without a disassembly**: run a Disk BASIC file
operation on the CF-3300, read the candidate RAM window through the DEBUGGER,
then run a BDOS call and read the same window — if both disturb the same bytes
they share. RAM is data; reading it is the same line D-CFARCH and the hook
census already work on. ⚠️ Needs a negative control (a window neither touches)
and a positive one (a window Disk BASIC demonstrably writes), or an agreement
proves nothing [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
### 0.1a 🟢 MEASURED 2026-09-18 (D-FATBUF): THE REFERENCE KEEPS THEM SEPARATE

`scratchpad/fatbuf_probe.py`, on the National CF-3300. The probe builds its own
FAT12 disk so it knows every sector's bytes, reads a file across a cluster
boundary — forcing a chain walk with file data live — and then searches
`$8000-$FFFF` for the payload and the FAT sector in 64-byte windows.

**After the walk, FOUR regions are resident at once:**

| region | size | holds |
|---|---|---|
| `$DD77-$DE76` | 256 B | file data |
| `$E595-$E794` | 512 B | FAT sector |
| `$ED95-$EF94` | 512 B | file data |
| `$EF95-$F194` | 512 B | FAT sector |

🎯 **FILE DATA AND FAT METADATA ARE LIVE SIMULTANEOUSLY, AT DISTINCT ADDRESSES**
— and the second pair is ADJACENT: 512 B of file data at `$ED95` immediately
followed by 512 B of FAT at `$EF95`. That is the shape of a deliberate
two-buffer arrangement, not of one buffer re-read.

**So zerobas' `FSECTOR_BUF`/`FWBUF` split is NOT our invention after all.** The
choreography `basic/field.asm` documents — the record survives a chain walk
because metadata goes elsewhere — is what the reference does too. §0.1's worry
that we had invented a divergence is answered: we had not.

**What this does to the one-engine plan (§0.1):** the engine does NOT have to
collapse to a single buffer to match the reference. It has to be able to address
TWO. The parameter §0.1 asks for is therefore real, and the two control blocks
being byte-identical in layout (only the base differs) is what makes it cheap.

⚠️ **WHAT IT DOES NOT SETTLE, AND JOOST'S QUESTION WAS NARROWER THAN THIS.** He
asked whether *BDOS* shares *Disk BASIC's* buffer. This measures file-data
against FAT-metadata WITHIN Disk BASIC's own file I/O. The two extra regions
(`$DD77`, `$E595`) are unattributed — a second drive's buffers, a BDOS set, or a
cache; the probe reads WHICH BYTES ARE RESIDENT, never which routine wrote them.
Attributing them is a separate measurement and is not claimed here.
⚠️ The 256 B region is the size `LOC(1)` counts in (it reported 256 and 768),
which is consistent with a per-channel record buffer — noted as an observation,
not a conclusion.

🔴 **THE INSTRUMENT TOOK EIGHT CORRECTIONS AND EVERY FAILURE LOOKED PLAUSIBLE.**
Recorded in the probe's own docstring because the class matters more than this
result: a diff against an idle control (boot already fills the buffer), a 30-byte
directory entry that shifted the whole image, a FAT too flat to locate, a
contiguity assumption broken by scattered clusters, the CF-3300's boot date
prompt eating every line, Tcl substituting `$` out of `A$=INPUT$(...)`, a witness
that matched the screen ECHO of the line printing it, and windows sampled at 512
B against a machine that buffers in 256. **None raised an error; each produced a
clean-looking table.** The run that finally answered did so only because the
probe refuses instead of reporting — and the fix that ended it was to stop
hand-rolling injection and drive `probes/lib/omsx_repl.py`, which had already
solved all five typing defects years of this tree ago.

This is the continuation of
[spec-diskbasic-hook-rearchitecture.md](spec-diskbasic-hook-rearchitecture.md),
which settled the MECHANISM (a verb's hook points at a disk-ROM body) and took it
through phases 0–3. **That document is the mechanism; this one is the
DENOMINATOR.** It does not restate the slot model, the ABI measurement or the
phase-3 blocker; it says how much disk code is in main, what shape it is, what
each piece costs to move, and in what order.

---

## 0. The one-line target — as re-stated by §0.0

Main+sub keep the **parse**, the **error raise** and the **hook surface**.
`disk.rom` gets the **work**. Nothing that only a disk can do should occupy a
byte of main+sub.
⚠️ This section read *"a byte of main page 1"* until 2026-09-18; §0.0 is why
that was too narrow in two directions at once — it excluded `sub.rom`, and it
excluded main's low region.

---

## 1. The denominator, measured 2026-09-17 — AND SUPERSEDED

🔴 **READ §0.0 FIRST. THIS SECTION IS KEPT FOR ITS MEASUREMENT, NOT FOR ITS
FRAMING.** Under the governing equivalence the denominator is not "disk code in
main page 1" but "disk IMPLEMENTATION anywhere in main+sub", which is a larger
set and a differently-shaped one. The figures below are still the best reading
of the six files they cover; they are simply not the whole subject any more.

🔴 **AND THE CENSUS UNDER-COUNTS ITS OWN SUBJECT, THREE WAYS** (found 2026-09-18
by an independent review of this spec, each verified against the tree):

1. **`basic/fatiow-body.inc` IS MISSING FROM THE FILE LIST** although
   `basic/fat.asm:341` includes it (`fat_io_putbyte` / `fat_io_close`). A census
   whose own subject includes a file it does not list is not a denominator.
2. **`basic/files.asm` IS NOT "DISK CODE AND NOTHING ELSE".** Roughly half of
   its 1459 B is device-generic or tape code — the `LPT:`/`CRT:`/`CAS:` channel
   arms, `merge_cas`, `read_into_strscr` (whose external callers are the CONSOLE
   `INPUT`), `fname_expr`, `ex_maxfiles`, `init_filechan`, the `fch_check*`
   readers that serve EOF/LOF/LOC for every device. The sentence "six files that
   are disk code and nothing else" overclaims by about a third of the largest
   file.
3. **THE FAT LAYER IS NOT THE BULK AND NEVER WAS.** Measured 2026-09-18 from
   `build/basic-reloc.sym`: `fat.asm` + `fatio-body.inc` + `fatiocreate-body.inc`
   is ~315 B, ~394 B with the omitted `fatiow-body.inc`. That is ~16 % of the
   set. The bulk is `files.asm` (1459 B) and `field.asm` (634 B). **§6 ordered
   "the FAT layer" as the big step twice, and it was never the big step** — §6.1
   half-caught this in the course of getting the blocker wrong.

`tools/carve_scout.py --census` over the six files as originally listed —
`basic/fat.asm`, `basic/files.asm`, `basic/field.asm`,
`basic/fatio-body.inc`, `basic/fatiocreate-body.inc`, `basic/randio-body.inc`:

```
215 labels defined, 181 in page 1
**2394 B leaves page 1** if they move
  SHARED (called from outside -- must stay, or become call-backs):  250 B  (22 entries)
  PRIVATE (moves with the verb):                                   2144 B  (159 labels)
```

**Against 69 B free in main page 1 and 32 B in the low region (2026-09-17.)**
So this one direction is worth roughly thirty times everything carving has
produced in this tree, and it is the reason no other budget question needs
answering first.

⚠️ **THE BOUNDARY IS THOSE SIX FILES AND NOT A BYTE MORE.** `basic/save.asm`,
`basic/cload.asm` and the `BLOAD`/`LOAD`/`RUN` loaders are **tape AND disk** —
they dispatch on the device, so they are not disk code that can leave. Whether
their disk arms can be split out is a SEPARATE question and is not priced here.
Quoting 2394 B as "the disk code in main" without that sentence would be
overclaiming by omission.

## 2. What the destination looks like — and it is not 8415 flat bytes

```
disk free (0x00 runs >= 16 B) = 8415 B in 32 runs  (2026-09-17)
  $6ACC-$75A4  2777 B   next pin $75A5
  $5602-$5FE4  2531 B   next pin $5FE5
  $50E3-$53A6   708 B   next pin $53A7
  $75A8-$77B7   528 B   next pin $77B8
  $4EE1-$4FB7   215 B   next pin $4FB8
  $7F35-$7FD0   156 B   next pin $7FD1
```

🔴 **THE SPACE IS FRAGMENTED BY PINNED KERNEL ADDRESSES**, so "8415 B free" is
not a budget a 2144 B body can be dropped into. **2144 B fits the largest hole
(2777 B) with 633 B to spare, and nothing else does.** Any plan that assumes
flat space is wrong; a plan that lands the bulk in `$6ACC` and the leaves in the
smaller runs is the shape that fits. **Re-read `make basic-reloc`'s disk section
before every move** — the runs shift as bodies land, exactly as main's wall does.

## 3. The mechanism, corrected

The hook re-architecture spec has this; the correction below does not, because it
was made after that document was written and **its absence misled a whole slice
of work on 2026-09-17**.

* **Main → disk** is the hook: `ld hl,<cell>` + `call chan_gate`. Unclaimed → ERR
  5, trappable, which is what a diskless machine must answer.
* **Disk → main, page 0** is a plain `call`: `disk.rom` is a PAGE-1 ROM, so while
  it is mapped, page 0 still holds slot 0 and main's **low region is callable by
  absolute address**. Declared in `gen_resident_abi.py`'s CODE list, which is
  ceiling-checked to be below `__MEAS_LOW_END`.
* **Disk → main, page 1** is `calbak` — `ld iy,(EXPTBL-1) / jp CALSLT` — with the
  target in `IX`. 🔴 **IT EXISTS, AT NINETEEN CALL SITES**, reaching six page-1
  targets declared in the CALLBACK list. Its ABI is **measured two-sided**
  (D-XSLOTABI): HL/DE/BC/A cross both ways intact, and CF crosses too.
* **RAM** crosses freely: the work area is mapped throughout. Declared in the RAM
  list.

⚠️ **I TOLD JOOST THIS CALL "HAS NEVER BEEN MADE IN THIS TREE" AND THAT ITS PRICE
GATED THE CHANNEL VERBS. BOTH WERE FALSE**, and I filed the second into TODO
before checking. The source was stale prose: `gen_resident_abi.py`'s own
paragraph said its CALLBACK list was *"Empty today, and that is a statement, not
an oversight"* while the list held six names. **A PLAN BUILT ON A DOCUMENT'S
PROSE INSTEAD OF ITS DATA IS A PLAN BUILT ON WHAT WAS TRUE ONCE.**

## 4. The defect this fixes, which is not a byte count

🔴 **EVERY GATE-ONLY HOOK IS A PRESENCE TEST, AND MAIN REDOES THE WORK AFTER IT.**
Measured on `CVI`/`CVS`/`CVD` (D-CVMOVE): after the hook returned *claimed*, main
ran the entire conversion regardless — so a foreign disk ROM that claimed `H_CVI`
and computed the answer had it **overwritten on the way out**. The same shape
held for `DSKF` and holds for every cell still pointing at `hk_present`.

🎯 So each remaining verb is the **same fix**, not a fresh design: move the work
behind the hook, leave the parse and the raise in main. That is why §6's order is
a queue rather than a research programme.

## 5. Eight rules, each one paid for on 2026-09-17

1. 🔴 **`STRSCR` IS NOT A MARSHALLING BUFFER.** It is where `MKI$`/`MKS$`/`MKD$`
   stage their result, so `CVI(MKI$(258))` hands a body a string whose body IS
   `STRSCR+1`. Staging a pointer there wrote over the value being converted:
   **12 of 32 rows DIFF**, and the 20 that stayed green were the arguments that
   are not staged strings. **A ROUND TRIP IS WHERE A SHARED SCRATCH BUFFER
   ALIASES ITSELF** — and a round trip is the case these verbs exist for.
2. 🎯 **BEFORE MARSHALLING ANYTHING, ASK WHETHER IT IS ALREADY IN RAM OR ALREADY
   BELOW `$4000`.** For the CV trio it was both: the descriptor was in `STRPTR`
   and `pu_deref_body` was at `$28C1`, so the body deref'd it itself and the
   marshalling I wrote first was pure risk.
3. 🟢 **A TRIVIAL PAGE-1 HELPER SHOULD VANISH, NOT MOVE.** `flt_int_result` only
   set `FACTYP := 2`; the body does that inline and a page-1 address stopped
   being a dependency of a routine that runs in another slot. Only a substantial
   helper forces the promote-or-call-back decision.
4. ⚠️ **A REGISTER GUARD MOVES WITH THE WORK IT GUARDS.** `DSKF`'s count used to
   run main-side under its own `push iy`; it runs inside the handler now, so the
   guard had to span the GATE instead. That survives a build and dies in a probe.
5. ⚠️ **AN ARGUMENT IN A REGISTER MUST CROSS IN RAM.** `chan_gate` clobbers `DE`
   building its own return address — the first cut of D-DSKFDRV checked `DE`
   after the gate, tested `cg_back`, and made every `DSKF` answer `Bad drive
   name`, with the TIER 3 row passing because it expects a refusal.
6. 🟢 **ERROR ORDER IS OFTEN FREE.** Moving the checks above the gate is
   unobservable when both paths raise the same error — for the CV trio the
   too-short check and the unclaimed gate both raise ERR 5. **Say which two
   errors coincide**, do not assume they do.
7. ⚠️ **A NEW SECTION HEADER NEEDS A CITATION.** `make basic-reloc` refuses one
   without it. Cite the section that establishes the verb as the disk ROM's, and
   the measurement the body rests on.
8. 🔴 **THE MEASUREMENT MOVES WITH THE CODE IT GUARDS.** `DSKF`'s `drive <= 2`
   bound and the four-points-above / two-below reading that fixed it now live
   beside the check in `disk/kernel.asm`. A bound whose evidence stays behind in
   another ROM is a bound nobody can re-derive.

## 6. The order, and why it is this one

Each step is one slice: move, build, verb probe, knife, `kwsweep`, full battery,
one commit.

| # | what | state |
|---|---|---|
| 1 | `MKI$` | ✅ D-MKINT — the exemption was marshalling, not implementation; +13 B |
| 2 | `CVI` `CVS` `CVD` | ✅ D-CVMOVE — +14 B main, −38 B disk; 0/32 DIFF |
| 3 | `DSKF` | ✅ D-DSKFMOVE — +4 B main, −37 B disk; identical on all six drive points |
| 4 | `LSET` `RSET` | ✅ D-LRSETMOVE — +9 B main, −47 B disk; fldwidth 49/49 |
| 5 | `FIELD` | ✅ D-FIELDMOVE — **−23 B main, −18 B disk**; §7.6 |
| 6+ | everything below | ➡️ **RE-ORDERED BY §6.2 (2026-09-18)** |

### 6.1 🛑 THE FAT LAYER CANNOT LEAVE UNTIL THE LOADERS DO — measured 2026-09-17, AND WRONG

🔴 **THIS SECTION'S CALL-SITE LIST IS WRONG AND ITS BLOCKER IS MIS-NAMED.**
Corrected 2026-09-18; the original is kept below because the reasoning it
contains about hot-path cost is sound and only its INPUT was bad.

**(a) Three of the six "files outside" are not in main at all.**
`basic/bload-body.inc`, `basic/fat-prim-body.inc` and `basic/fat-delete-body.inc`
are `include`d only from `sub/*.asm` (`sub/bload.asm:246`, `sub/fatprim.asm:250`,
`sub/fatprim.asm:251`); `basic/main.asm` includes none of them. Their call sites
bind SUB-LOCALLY and pin nothing in main. The main-side count is **13 sites in
five files**, not 25 in six.

**(b) The list omits the caller that actually does the pinning.**
`basic/input.asm:278` — `arl_set_src` — installs `fat_io_getbyte` into the
`ARL_GETBYTE` RAM vector (`basic/sysvars.inc:1619`), and `arl_getbyte`
(`basic/files.asm:1974`) jumps through that vector **once per byte** from three
loops (`ascii_read_lines`, `read_into_strscr`, `sidr_lp`).

**(c) 🔴 AND THE COUNT HAS NOW BEEN WRONG FOUR TIMES, SO IT IS A TOOL.**
`scratchpad/fatdep_census.py` derives it from the transitive `include` closure of
`basic/main.asm` — what the main ROM actually assembles — and carries a selftest
proving the closure walks nested includes and excludes a sub-only file. Run it;
do not quote this paragraph.

| reading | figure | what was wrong |
|---|---|---|
| §6.1 as written, 2026-09-17 | 25 in six files | three of the six are `include`d only by `sub/` |
| the correction, 2026-09-18 | 13 in five | dropped `basic/files.asm` (7 sites); relayed, not re-derived |
| a hand grep, same day | 20 in five | its entry list omitted `fat_io_append` |
| **the tool** | **21 in five** | derived, with a selftest |

**And the split is what matters, not the total:**

| class | count | what it means |
|---|---|---|
| **VECTOR** | **3** | `ld hl,fat_io_getbyte` stored into `ARL_GETBYTE` — `cload.asm:852`, `files.asm:1181`, `input.asm:278`. Dispatched ONCE PER BYTE. **This is the pin.** |
| CALL | 18 | ordinary `call`/`jp`; moves with its verb or becomes a call-back |

⚠️ **AND THE FRAMING WAS WRONG TOO, WHICH IS WHY THIS LOOKED UNMOVABLE.** These
are not TAPE code depending on FAT. They are SHARED loaders that dispatch on
DEVICE, whose disk arm calls FAT — and the dispatch is three instructions:
`arl_set_src` chooses between `fat_io_getbyte` and `cas_in_getbyte`. Reading
them as a tape/disk entanglement is what produced "the FAT layer is pinned in
main".

🟢 **AND §6.2a DISSOLVES THE PIN.** The vector can hold a main-side trampoline
that crosses to `disk.rom`: one inter-slot call per byte, measured on 2026-09-18
at 0.859 ms/byte against the reference's 4.297 — **0.20×**. The per-byte vector
is exactly the case step 7 was run for, and it lands on the side that says the
crossing is affordable. What remains for steps 11/12 is placement, not price.

🎯 **SO THE BLOCKER IS NOT A CALL COUNT. IT IS A RAM VECTOR.** A page-1 address
in ANOTHER SLOT is not callable through `ARL_GETBYTE`, and that — not the number
of `call` sites — is why the byte cursors are resident. This is a sharper
statement and a more tractable one: a static call site can become a call-back,
but a per-byte indirect vector cannot become an inter-slot one at any acceptable
price. **The fix is to move the LOOP to where the cursor is, not the cursor to
where the loop is** — which is precisely what `sub/bload.asm` already does for
BLOAD, so the pattern is proven in-tree rather than proposed.

⚠️ **THE ORIGINAL TEXT FOLLOWS, FOR ITS COST REASONING ONLY. Its file list and
its "25 call sites" are superseded by (a) and (b) above.**

#### 6.1-orig (superseded 2026-09-18)

This spec listed the FAT layer as "the bulk" and put it at step 5. **That order
is wrong, and the census is what hid it**: `--census` reports a label as SHARED
by counting callers *outside the six files*, but it does not say WHO, so
"250 B shared" read as a small frontier when part of it is a hard pin.

**Six files outside the six call the FAT I/O layer directly:**

```
basic/bload-body.inc        fat_io_getbyte x8, fat_mount x1
basic/cload.asm             fat_io_open x2, fat_io_getbyte x4, fat_find x2, fat_mount x1
basic/fat-delete-body.inc   fat_find x1, fat_mount x1
basic/fat-prim-body.inc     fat_mount x1
basic/print.asm             fat_io_putbyte x1
basic/sv-diskwr.inc         fat_io_create x1, fat_io_close x1, fat_io_putbyte x1
```

🔴 **THESE ARE THE TAPE/DISK SHARED LOADERS — the exact code §1 and §11 declined
to price.** `LOAD`/`RUN`/`BLOAD`/`SAVE`/`PRINT#` dispatch on the DEVICE, so they
are not disk code that can leave; and while they stream bytes through
`fat_io_getbyte`, the layer they stream through cannot leave either. Moving it
regardless would turn 25 plain `call`s into 25 inter-slot calls on the hot path
of every disk load — at 0.156 ms each (D-XSLOTPRICE) on a machine already ~3×
slower than the reference.

🎯 **SO THE REAL STEP 5 IS A QUESTION, NOT A MOVE:** can each loader's disk arm
be split from its tape arm, so the arm and the layer move together? That is the
prerequisite, it is unpriced, and it is where the next measurement belongs —
**not** in starting a move that ends 25 calls deep in the wrong slot.
⚠️ Until it is answered, the FAT layer is **pinned in main**, and the honest
figure for what can leave today is **§1's 2394 B MINUS the FAT layer and its
frontier**, which this spec does not yet break out.

🎯 **THE SMALL VERBS FIRST IS NOT TIMIDITY.** Each one pays for the next by
freeing main page 1 — 22 B this morning, 69 B now — and each proves one more of
§5's rules against a real probe before the bulk move depends on it.

### 6.2 ➡️ THE ORDER UNDER THE GOVERNING EQUIVALENCE (2026-09-18)

Steps 1–5 were the right work and stay done. What follows them is re-ordered,
because §0.0 changed the subject and §6.1(b) changed the blocker.

**The rule that orders the rest: MOVE A LOOP TO ITS CURSOR, NEVER A CURSOR TO
ITS LOOP.** §6.1(b) is why. Every remaining step is an instance of it.

| # | what | gate on it |
|---|---|---|
| 6 | 🔬 **MEASURE: does the reference's BDOS share Disk BASIC's sector buffer?** | §0.1 — decides whether there is a parameter at all. **Nothing moves before this.** |
| 7 | 🔬 **MEASURE: does the reference cross slots per BYTE for sequential file I/O?** | §6.3 — decides whether loop duplication is required or is wasted bytes |
| 8 | the FAT engine to `disk.rom`, ONE copy, base parametrised per §0.1 | needs 6; needs a scratch build to prove the fragmented fit |
| 9 | the tokenised `LOAD` loop (`dpl_*`) **+ the stream cursor `fat_io_getbyte`** — 🔴 not "already disk-only" (§6.5) and 🛑 not sufficient alone (§6.6) | ✅ **MEASURED §6.2c**, ✅ **SCOPED §6.5**, ✅ **PORTED §6.6g**, 🏗️ **UNBLOCKED §6.6m: `H_FOPEN` ($FE5D) + a selector, ruled by Joost** |
| 10 | `OPEN`/`CLOSE` disk arms + the channel write-back manager | needs 8; 🏗️ **UNBLOCKED by §6.6m — same cell, another selector value; no longer "blocked the same way", it is the same work again** |
| 11 | `INPUT#` / `INPUT$` loop copies beside their cursor | needs 7 |
| 12 | `PRINT#` — the one consumer with no loop of its own to move | needs 7; see §6.3 |
| 13 | the `sub.rom` disk-only tenants (**2178–3708 B, §0.2**): `fatprim`, `dirverb`, `fcbname`, and BLOAD's / SAVE's disk arms | in scope only because of §0.0 |
| 14 | 🛡️ **the gate**: no disk-implementation symbol reachable in main+sub | §0.0's checkable end state |

⚠️ **STEP 13 IS WHY THIS DOES NOT FIT IN ONE PASS.** main's ~2.2 KB plus
`sub.rom`'s 2.2–3.7 KB is **4.4–5.9 KB** against `disk.rom`'s 8314 B free — but that free
space is **32 runs, largest 2712 B** (`tools/check_disk_walls.py`, 2026-09-18).
Staging is forced by fragmentation, not chosen for caution. **Every step
re-reads the walls before it starts; none of them may quote a figure from here.**

### 6.2a 🟢 STEP 7 MEASURED 2026-09-18 (D-SEQIO) — AND IT INVERTS §6.3 FOR TWO OF THE STEPS

`scratchpad/seqio_stopwatch.py`, both machines, stored-mode programs timed with
`TIME`. ⚠️ `TIME` counts VDP interrupts — **60 Hz on the Japanese CF-3300, 50 Hz
on our EU repack** — so the headline is NORMALISED against a calibration loop
each machine runs itself, in which the tick rate cancels.

| machine | cal (1000 it) | loop (512 it) | io (512 B) | per byte, cal units | per byte, ms |
|---|---|---|---|---|---|
| CF-3300 (60 Hz) | 97 | 92 | 224 | **2.66** | 4.297 |
| zerobas (50 Hz) | 249 | 244 | 262 | **0.14** | 0.703 |

🔴 **THE REFERENCE SPENDS 2.66 EMPTY-LOOP-ITERATIONS PER BYTE OF SEQUENTIAL
INPUT; WE SPEND 0.14** — normalised, so machine speed is not the cause. We are
**20× faster per byte** on a tree that is otherwise 2.5–3.8× SLOWER at
interpretation (D-SPEEDPROF). Whatever the reference does per byte is expensive:
4.3 ms is ~27× a single inter-slot crossing at D-XSLOTPRICE's 0.156 ms.

**Adding one crossing per byte to our path gives 0.859 ms/byte — still 0.20× the
reference.** So for the BASIC-visible byte verbs, a per-byte crossing is not the
catastrophe §6.3 assumed; it disappears into interpretation that is already
there.

🔴 **BUT IT SETTLES STEPS 11 AND 12 ONLY, AND NOT STEP 9.** `INPUT#`, `INPUT$`
and `PRINT#` pay a whole BASIC statement's worth of interpretation per byte, and
that is what a crossing would hide behind — it is the case this probe measures.
**The tokenised `LOAD` loop runs INSIDE the ROM with no interpreter overhead per
byte, so a crossing there is pure addition against nothing.** Its cost is not
measured here and must not be inferred from this table.

➡️ **CONSEQUENCES FOR THE ORDER:** step 11's loop duplication is **not forced**
— `INPUT#`/`INPUT$` may keep their cursor across the seam. Step 12's `PRINT#`
may cross per byte without being a regression, which removes the dilemma §6.3
left it in. Step 9 keeps its loop-to-the-cursor requirement until measured.

⚠️ **THE CONTROL'S BIAS POINTS THE SAFE WAY**: `loop` subtracts a string
ASSIGNMENT from a string-valued FUNCTION call, so a little call overhead stays
inside the I/O figure, making file I/O look DEARER than it is. That inflates
both sides and cannot manufacture the 19× normalised gap.

### 6.2b ⛔ STEP 9 IS STILL UNMEASURED, AND THE OBVIOUS METHOD DOES NOT WORK (2026-09-18)

§6.2a settled steps 11 and 12 and explicitly left step 9 open: the tokenised
`LOAD` loop runs INSIDE the ROM with no per-byte interpreter overhead for a
crossing to hide behind. `scratchpad/loadtime_probe.py` was built to close it and
**cannot**.

**Why.** The two clock reads sit either side of the `LOAD` in separate injected
lines, so the second fires on the HARNESS'S TIMETABLE, not when the work
finishes. On the CF-3300:

| | `ctl` | `load` | both equal |
|---|---|---|---|
| step = 14 s | 1678 jiffies | 1606 | the 28 s injection gap |
| step = 3 s | 360 jiffies | 307 | the 6 s injection gap |

Every configuration measures the gap; the load vanishes inside it and the
difference is jitter — **negative**, which is what the probe's `load > ctl`
control caught. Shortening `step` below the load does not rescue it: a 7.6 KB
load completes in **under 3 seconds**, already below the step the injector needs
(at 3 s the calibration case broke, its loop still running at capture).

🟢 **THE ONE FIGURE IT DID ESTABLISH, as an upper bound:** a 7603-byte tokenised
`LOAD` is **under 3 s on the CF-3300** — under ~0.39 ms/byte and plausibly far
less. That is the same order as D-XSLOTPRICE's 0.156 ms crossing, which is
precisely why step 9 cannot be decided by assertion.

➡️ **THE METHOD THAT WOULD WORK**: `LOAD"P.BAS",R` with the marker as the loaded
program's FIRST line, so the second clock read is triggered by the WORK and no
injection gap intervenes. It needs a genuinely tokenised marker line — obtained
by having the machine `SAVE` one once and padding it with the probe's REM
generator, **not** by guessing MSX token bytes.

➡️ **SUPERSEDED THE SAME DAY BY §6.2c**, which built exactly the instrument
this paragraph specified and got an answer. The diagnosis above is kept because
it is the reason the second attempt was shaped the way it was.

### 6.2c 🟢 STEP 9 MEASURED 2026-09-18 (D-LOADRUN) — §6.3 STANDS, AND IT IS NOW A NUMBER

`scratchpad/loadrun_probe.py` is the instrument §6.2b specified. Two changes make
the clock honest:

  * **`LOAD"x",R`**, with the marker as the loaded program's FIRST line — so the
    second clock read is triggered BY THE WORK and the injection gap that
    defeated `loadtime_probe` cannot intervene. The capture may fire arbitrarily
    late; the reading is TIME AS PRINTED.
  * **`TIME`, not a variable.** `scratchpad/loadtime_probe.py`'s own docstring
    concluded *"`LOAD"x",R` does not help — it clears variables too"* (that
    sentence is in the PROBE, not in §6.2b), and it was the sentence to attack: `TIME`
    is a SYSTEM cell, not a BASIC variable, so `TIME=0` before the load survives
    into the loaded program. **This is measured, not assumed** — see the
    composition control below.

Three programs, identical but for REM padding, so every FIXED cost cancels:

| machine | S (1055 B) | M (7208 B) | L (14369 B) | **ms/byte** |
|---|---|---|---|---|
| CF-3300 (60 Hz) | 51 | 62 | 81 | **0.0376** |
| zerobas (50 Hz) | 16 | 83 | 161 | **0.2178** |

🔴 **FINDING 1 — THE ANSWER TO STEP 9.** One inter-slot crossing per byte is
0.156 ms (D-XSLOTPRICE), so cursor-out-loop-left-behind costs
**0.2178 → 0.3738 ms/byte = 1.72×** our current LOAD. On a 16 KB program that is
**3.57 s → 6.12 s**. §6.3's arithmetic was exactly right (+2.6 s on 16 KB); what
it could not know was the baseline that gets added to. **§6.3 THEREFORE STANDS
FOR STEP 9 — MOVE THE LOOP, NOT THE CURSOR — AND IT NOW STANDS ON A
MEASUREMENT.** The margin is also now known and bounded: if the fit ever forces
the other arrangement, the price is 1.72×, not infinity.

🔴 **FINDING 2 — AND IT IS NOT THE EVICTION'S BUSINESS: WE ARE 5.8× SLOWER THAN
THE REFERENCE PER BYTE OF TOKENISED `LOAD`** (0.2178 vs 0.0376 ms, wall clock).
**That is not the general interpretation gap.** The probe's own delay control
prices this machine at **3.0×** the reference on a bare `FOR..NEXT` (148 jiffies
@ 60 Hz = 2.47 s against 375 @ 50 Hz = 7.50 s), consistent with D-SPEEDPROF —
and `dpl_*` is ROM code, not interpretation, so the remaining ~2× is ours.
Filed as a residual in `TODO.md`; nothing else in the tree would have found it.

🟢 **FINDING 3 — TWO DIFFERENT SHAPES, WHICH IS WHY THE DIFFERENTIAL DESIGN
EARNED ITSELF.** The reference spends **0.85 s** before the first payload byte
and we spend **0.32 s**; then it spends 1/6 of our per-byte cost. An absolute
timing of one load would have blended those two facts into a single misleading
ratio in whichever direction the chosen file size happened to point.

⚠️ **CONTROLS — each one voids the reading if it fails, and all passed:**
  * **TIME SURVIVES THE LOAD**, measured: a delay case times a bare `FOR` loop,
    a fourth case runs the same loop AND THEN loads. They must COMPOSE —
    CF-3300 199 predicted / 201 measured, zerobas 391 / 393;
  * **LINEARITY**, because a two-point differential assumes a shape it cannot
    see — a FAT walk that re-read a sector per cluster would be superlinear and
    a slope from the endpoints would look clean while understating big loads.
    The mid-size point is predicted **64.9 / measured 62** (CF-3300) and
    **83.0 / measured 83** (zerobas);
  * **the identity witness** — each program prints its own number after the
    timed line, so a failed open leaving the previous program resident cannot
    pass as a difference;
  * the large load must exceed the small one; the marker must appear at all; and
    the seed program must read back with the line numbers it was typed with.

⚠️ **REPRODUCIBLE TO THE JIFFY, AND THE ONE CHANGE BETWEEN RUNS WAS EXPLAINED.**
Adding the mid-size program to the image moved `L.BAS` two jiffies later on BOTH
machines (79→81, 159→161) while `S.BAS` did not move at all — `M.BAS` is
allocated ahead of it, so `L.BAS` starts further into the disk. That is a layout
effect the instrument is sharp enough to see, not noise.

🔬 **A FREE FINDING ON THE WAY, AND §6.2b's RULE EARNED ITSELF ON FIRST USE.**
§6.2b forbade guessing MSX token bytes, so the probe has the machine `SAVE` the
lines and reads them back out of the image. `loadtime_probe.py` had built its REM
lines as `$8F` + text; **the machine emits `$8F $20` + text** — it keeps the space
after `REM`. Both forms load, so nothing was broken, but the hand-built one was
not what the machine produces. 🟢 And both machines tokenised all five seed
lines **identically**.

### 6.3 🔴 THE ONE ARRANGEMENT THAT IS ALREADY DEAD — NARROWED BY §6.2a

🟢 **NARROWED 2026-09-18 BY §6.2a: THIS IS NOW TRUE OF STEP 9 ONLY** — and
✅ **CONFIRMED FOR STEP 9 THE SAME DAY BY §6.2c**, which measured the baseline
this paragraph was reasoning about: the crossing costs **1.72×** our current
LOAD, so the conclusion below is right and is no longer an assertion. For the
BASIC-visible byte verbs the measurement says a per-byte crossing costs 0.20× the
reference, so the paragraph below applies to the tokenised `LOAD` loop — where
there is no interpreter overhead per byte to absorb it — and not to
`INPUT#`/`INPUT$`/`PRINT#`.

**Cursors out, loops left behind** — the shape the original §6 step 5 described —
costs **one inter-slot call per byte**. At 0.156 ms (D-XSLOTPRICE) a 16 KB
tokenised `LOAD` gains ~2.6 s, on a machine already ~3× slower than the
reference. It is not a trade-off to weigh; it is ruled out, and step 7 exists to
establish whether the reference itself pays a per-byte crossing (in which case
`PRINT#`'s per-byte case in step 12 is ON-PAR rather than a defect, and steps 11
and 12 shrink).

## 6.4 🔬 STEP 8 ANALYSED 2026-09-18 (D-FATENG) — THE FIT PASSES, AND A CONSTRAINT THE SPEC NEVER NAMED

**The two engines are ONE engine, diverged.** `disk/fat.asm` (1390 lines) and
`basic/fat-prim-body.inc` (1302 lines) share **53 labels**. Comparing their code
with comments stripped:

| | identical routines |
|---|---|
| as written | **24 / 53** |
| after aliasing the buffer pairs (`SECTOR_BUF`↔`FSECTOR_BUF`, `WBUF`↔`FWBUF`, and the two write-state cells) | **35 / 53** |

So the residual difference is dominated by exactly the thing Joost named — where
the buffers are. The symbols appearing in differing lines, ranked: `FWBUF` 16,
`WBUF` 15, `FSECTOR_BUF` 15, `SECTOR_BUF` 13, then the write-state pairs
(`FWR_SECIDX`/`BDOS_WRSECIDX`, `FWR_CLUS`/`BDOS_WRCLUS`).

🟢 **THE FIT GATE PASSES.** `disk.rom` free space is 8350 B in 32 runs and the
largest usable hole is **2712 B at `$6B0D`** (`tools/check_disk_walls.py`,
2026-09-18). The BASIC engine is ~1725 B as assembled in `sub.rom`, so it fits
with ~987 B to spare. ⚠️ Arithmetic only — a scratch build is still what proves
placement, and this section does not claim otherwise.

🔴 **AND THE CONSTRAINT NOTHING IN THIS SPEC HAD NAMED: `disk/fat.asm` CARRIES
24 HARD ADDRESS PINS.** They are the M26 BDOS canonical entries — MSX-DOS calls
them by absolute address — anchored with `ds $XXXX - $, $00` padding through the
file (`k_46BA`, `k_4720`, `k_477D`, `k_4788`, `k_4793`, `k_47BE`, …;
`disk/docs/tier2-m26-spec.md`). **The file's layout is frozen**, so a shared body
cannot simply be dropped into it and nothing may be relocated across a pin.

**What still differs after aliasing** (18 routines) is not noise; it is real:
* `read_sector` — BASIC's CALSLTs out to whatever disk ROM holds the slot;
  disk's calls its own local DSKIO. **In a unified engine living in `disk.rom`
  this SIMPLIFIES to the local one** and the inter-slot call disappears.
* `nc_loop` / `fat_find` — BASIC's carries WILDCARD matching, which `FILES`
  needs and BDOS does not.
* the routines interleaved with the M26 pins, which differ by padding.

### 6.4a 🙋 THE FORK — FOR JOOST, NOT FOR ME

One engine in one ROM cannot take an ASSEMBLY-time buffer parameter: that would
instantiate it twice, which is the two-engine outcome he ruled out. So the base
must be supplied another way, and there are two ways:

**(a) SHARE ONE BUFFER PAIR — no parameter at all.** 🟢 Measured 2026-09-18: the
BASIC path never enters BDOS. Every mention of `bdos_entry` under `basic/` is a
comment saying the loader drives DSKIO `$4010` *instead* (`basic/fat.asm:10`,
`basic/sv-diskwr.inc:14`, `basic/fat-prim-body.inc:52`). The two paths do not
interleave, so they could use the same pair. ⚠️ It must be BASIC's addresses
that win: disk's `SECTOR_BUF $E2A0` overlaps BASIC's `STRSCR` (`$E26D`+255), so
BASIC cannot move to disk's. That makes it a **BDOS RAM remap**, gated by
`bdos-acceptance`, and **whether any BDOS cell is pinned by COMMAND.COM
compatibility is still undetermined.** Cost: zero bytes, zero cycles, unknown risk.

**(b) A RUNTIME POINTER — `ld hl,(DBUF)` where the code says `ld hl,SECTOR_BUF`.**
Each engine carries ~70 buffer references, of which ~24 (disk) / ~34 (BASIC) are
plain `ld rr,BUF` loads and ~15 / ~12 are `BUF+offset` forms. A plain
`ld hl,(nn)` is the SAME 3 bytes as `ld hl,nn` and costs 6 extra T-states; the
offset forms are the dear ones (a load plus an `add`). Rough size: **~60–100 B**
and a small cycle cost on every buffer access. No RAM remap, no
`bdos-acceptance` exposure.

**Recommendation: (b).** It is the literal reading of Joost's *"parametrize
where it has its buf"*, it costs bytes we have in `disk.rom` rather than risk we
cannot size, and it leaves the M26 pins untouched. (a) is strictly better if the
remap is safe — but "if" is exactly what nobody has measured, and a RAM remap
that breaks COMMAND.COM would be found by `bdos-acceptance` late and expensively.

⛔ **NOT STARTED. 1725 B of code interleaved with 24 absolute-address pins is
not a slice to begin on a guess about which parametrisation is wanted.**

## 6.5 🔴 STEP 9's SCOPE, DERIVED 2026-09-18 (D-DPLDEP) — AND THE NAME `dpl_` LIES

§6.2c settled WHY step 9 moves the loop. `scratchpad/dpldep_census.py` settles
WHAT, from the transitive `include` closure of `basic/main.asm`, and the first
thing it establishes is that **`dpl_` is not a device prefix**. `basic/cload.asm`
says so in its own header — *"🔴 dpl_err IS SHARED WITH THE WHOLE CASSETTE PATH
(do_tape_prog above, nine `jp c,dpl_err` sites)"* — so a move of "everything
spelled `dpl_*`" would put a CASSETTE tail in `disk.rom`, where a diskless build
cannot reach it at all. [[a-shared-tail-is-not-a-decision]]: the unit of decision
is the CALL SITE, never the symbol.

| symbol | in-edges | from | step 9 |
|---|---|---|---|
| `dpl_line` | 2 | DISK (incl. **fallthrough** from `disk_prog_load`) | 🟢 moves |
| `dpl_body` | 2 | DISK | 🟢 moves |
| `dpl_eof` | 4 | DISK | 🟢 moves |
| `dpl_get_store` | 3 | DISK | 🟢 moves |
| `dpl_oom_pop` | 2 | DISK | 🟢 moves |
| `dpl_nf` | 1 | DISK | 🟢 moves |
| `dpl_err` | **12** | **9 TAPE**, 3 DISK | 🔴 **STAYS** (or is duplicated) |
| `dpl_oom` | 2 | **1 TAPE**, 1 DISK | 🔴 **STAYS** (or is duplicated) |
| `dpl_link_err` | **0** | — | ⚠️ `equ ctp_link_err`, and **DEAD** |
| `dpl_err_pop` | **0** | — | ⚠️ `equ ctp_err_pop`, and **DEAD** |
| `dpl_done` | 4 | DISK | `equ load_commit_prog` — main's commit tail |

🟢 **WHAT THE MOVE BUYS, AS A RATIO.** After it, the loop's per-byte call
`fat_io_getbyte` is LOCAL to `disk.rom` (Option 2 put the engine there), so the
only crossings left are once-per-load call-backs: `load_commit_prog` on
completion, and `load_error` / `df_or_loaderr` / `new_prog` / `print_msg` on
failure. **One crossing per LOAD instead of one per BYTE** — 0.156 ms against the
2.24 s that 14369 crossings would cost on the large program §6.2c timed. That is
the whole of §6.3, expressed as the arrangement rather than the prohibition.

🔴 **AND TWO TAILS DO NOT GO.** `dpl_err` and `dpl_oom` are reached from the
cassette path and must stay in main, or be duplicated in `disk.rom`. Duplication
is the wrong default: both are once-per-FAILURE paths, so a call-back costs
nothing anyone can measure, and a second copy is bytes plus a second thing to
keep correct. **The moved loop should call back to them.**

⚠️ **THE TOOL CORRECTED ITS OWN AUTHOR TWICE, and both were in the rows rather
than the total:**
  1. **Fallthrough is an in-edge.** The first cut scanned `call`/`jp`/`jr` only
     and reported `dpl_line` with ONE in-edge — its own back-edge — which reads
     as a nearly-dead routine. It is the ENTRY POINT of the tokenised load,
     reached by fallthrough from `disk_prog_load`. [[dupspan-slice]].
  2. **A directive is not an instruction.** Adding fallthrough then produced
     FIVE edges, of which **three were false**: `dpl_done equ load_commit_prog`
     has no colon, so it read as a non-terminating code line and every label
     after an `equ` looked fallen-into. Two genuine edges remain.

➡️ **AND §6.5 IS NOT THE WHOLE SCOPE** — §6.6 re-scoped it the same day: the
six bodies above cannot travel without `fat_io_getbyte`, which is not in
`disk.rom`. Read §6.6 before acting on this section.

🔴 **A RESIDUAL THIS TURNED UP, FILED IN `TODO.md`:** `dpl_link_err` and
`dpl_err_pop` have **zero references** — D-TRUNCLOAD replaced their call sites
with `jr c,dpl_eof` and left the `equ`s behind. Worse, D-NGRAM13's 12-line
justification above `dpl_get_store` still argues about where *"the `jp
c,dpl_err_pop`"* should sit, and that instruction no longer exists anywhere.
[[a-fix-falsifies-the-justification-beside-it]] — no gate reads prose, and
`check_dead_code` does not follow `equ` aliases.

## 6.6 🛑 STEP 9 IS BLOCKED AS SCOPED — THE CURSOR IS NOT WHERE §6.5 ASSUMED (D-DPLFIT, 2026-09-18)

§6.5 scoped the move and §6.2c priced it. Attempting it turned up one blocker
that had already been lifted and one that had not. **Do not move `dpl_*` on
§6.5 alone.**

### 6.6a 🟢 THE BLOCKER THAT WAS ALREADY LIFTED

Every call-back target step 9 needs is in **main PAGE 1** — `load_commit_prog`
$67F1, `load_error` $664A, `df_or_loaderr` $6C8E, `new_prog` $75CE, `print_msg`
$776F — which `disk.rom` cannot reach by an ordinary `call`. The standing note
that *"zerobas has NEVER made a disk→BASIC inter-slot call"* is **STALE**:
`calbak` (`disk/kernel.asm:2318`) is exactly that call, and it has ~20 live sites
since D-FIELDMOVE. Verified rather than assumed — `hk_field` reaches
`field_prologue` at **$7265, main page 1**. So the mechanism exists and is
shipping.

### 6.6b 🔴 THE BLOCKER THAT IS REAL: THE STREAM CURSOR IS NOT IN `disk.rom`

`python3 scratchpad/dpldep_census.py --move` walks `disk/disk.asm`'s include
closure and answers, per out-edge, whether the move makes it free:

| out-edge | in `disk.rom`? | frequency |
|---|---|---|
| `fat_io_getbyte` | 🔴 **no** | **PER BYTE** |
| `load_commit_prog` | 🔴 no | once per load |
| `load_error`, `df_or_loaderr`, `new_prog`, `print_msg` | 🔴 no | once per failure |

🔴 **Option 2 moved the PRIMITIVE layer, not the STREAM layer.**
`fat_io_getbyte` is defined in `basic/fatio-body.inc`, which `disk/disk.asm` does
not include; only `basic/fat-prim-body.inc` travelled. **So moving `dpl_*` alone
would convert a local call into an inter-slot call PER BYTE** — precisely the
arrangement §6.3 forbids and §6.2c priced at 1.72×. The move as scoped does not
remove the crossing; it CREATES it.

➡️ **THEREFORE STEP 9 IS THE LOOP *PLUS* THE STREAM CURSOR, OR IT IS NOTHING.**
The shape is Option 2's and needs no new ruling: **one source, two ROMs** —
`fatio-body.inc` included by `disk/disk.asm` as well, exactly as
`fat-prim-body.inc` already is.

### 6.6c ⚠️ AND A TRAP UNDERNEATH IT THAT ASSEMBLES CLEAN

`fat_io_getbyte` reads its sector buffer **by hardcoded name**
(`ld de, FSECTOR_BUF`), and the two ROMs do not agree on where that is:

| | |
|---|---|
| `FSECTOR_BUF` (`basic/sysvars.inc:2831`) | **$E5C0** |
| `SECTOR_BUF` (`disk/equates.inc:123`) | **$E2A0** |
| what `fat_read_file_sector` fills | `FAT_DBUF` — *aliased per ROM* |

🔴 **`disk/basic-resident-abi.inc:25` ALSO binds `FSECTOR_BUF equ 0E5C0H`**, so
a naive port would **assemble without a single error** and read a buffer nobody
filled. This is the same class as Option 2's `FSECTOR_BUF` alias collision, one
layer up, and the fix is the same: the ported body must use the neutral
`FAT_DBUF` name, never `FSECTOR_BUF`.

### 6.6d 🟢 WHAT STAYS IN MAIN, AND WHY IT IS NOT A SECOND ENGINE

The `ARL_GETBYTE` RAM vector keeps main's copy: `basic/input.asm:278` and
`basic/files.asm:1181` store `fat_io_getbyte` into it for the ASCII path, and
**a RAM vector cannot hold a foreign-slot address** — D-FATDEP named this the
pin. The tokenised loop calls the cursor DIRECTLY, so the two paths can be served
by two assemblies of ONE source. That is Joost's 2026-09-18 ruling applied, not
bypassed: what is forbidden is two FAT engines, not one engine assembled twice.

⚠️ **THE TOOL CORRECTED ITSELF HERE TOO, AND THE GUARD IS WHY.** `--move`'s
first real run REFUSED: the include resolver had two rules (relative to the
including file, relative to the root) and pasmo uses a **third** — the Makefile
runs `pasmo -I disk` FROM THE REPO ROOT, so `disk/kernel.asm:2295`'s
`include "basic/fat-prim-body.inc"` resolves against the CWD. Without the strict
arm the shared FAT body would have been dropped silently and **every FAT
primitive would have been reported as needing a call-back** — a plausible table
from an input the tool misread. S9–S11 hold that shut, S11 against the real tree.

### 6.6e 🔴 AND THE FAT STATE IS PER-ROM, SO STEP 9 MOVES THE *STREAM*, NOT THE LOOP (2026-09-19)

§6.6b said the cursor must travel with the loop. Checking what the cursor needs
turned up the constraint underneath that:

| cell | main | `disk.rom` |
|---|---|---|
| `FAT_CURCLUS` | $E9C9 | **$E4A9** |
| `FAT_FIRSTCLUS` | $E9CC | **$E4AC** |
| `FAT_FILESIZE` | $E9CE | **$E4AE** |
| `FAT_BYTEIDX` | $E9D6 | **$E4B3** |

🔴 **The two assemblies of the engine keep two INDEPENDENT state blocks**, so a
file opened by main's `fat_io_open` cannot be read by `disk.rom`'s
`fat_io_getbyte`: the disk-side cursor would walk a cluster chain nobody had
primed. **Step 9 is therefore the tokenised LOAD stream END TO END — open, marker
peek and loop — not the loop and not even the loop plus the cursor.**

➡️ **THE SHAPE THAT FOLLOWS**, and it is smaller than it sounds because
`disk_prog_load` has only three callers (`do_load`, `do_run`, the autoexec arm):

| stays in main | crosses once | moves to `disk.rom` |
|---|---|---|
| `diskslot_test`; the `CLPTR`/`CLINK` seed (RAM, both ROMs see it) | the hook call, once per load | `fat_io_open`, the `$FF` marker peek, and the six §6.5 bodies |
| the ASCII branch — `ascii_load` **already re-opens from offset 0**, so it simply opens main-side as it does today | `load_commit_prog` on completion; `load_error`/`df_or_loaderr` on failure | |

So the hook returns one of three answers — *not found*, *not tokenised (ASCII)*,
*loaded* — and main keeps every path that is not the tokenised one.

⚠️ **IT NEEDS 6 BYTES OF NEW DISK-SIDE RAM**: `FREAD_OFF` (2 B) and `FREAD_LEFT`
(4 B), which `disk/equates.inc` does not define. 🔴 **RAM HAS NO GATE** — walk
`scratchpad/rammap_sweep.py` and then ASK THE MACHINE with `ramfree_probe.py`;
**a delta between two names is not free space** [[deffn-ramhunt-slice]].
⚠️ **AND DO NOT REUSE `BDOS_BYTESLEFT` ($E542)** merely because it holds the same
quantity: it is BDOS's cell, and D-FATBUF (§0.1a) measured the reference keeping
the BDOS and Disk-BASIC buffer sets SEPARATE. Sharing it would undo the one thing
§0.1 established by measurement.

🟢 **ONE PIECE OF THIS HAS LANDED, AND IT IS PROVABLY NEUTRAL.**
`basic/fatio-body.inc` now names its buffer `FAT_DBUF` instead of `FSECTOR_BUF`,
which disarms §6.6c's trap BEFORE the port rather than during it. In the main
build the two names are the same cell, so **all three ROMs came out
byte-identical** (`63c42493`, `7333f7f6`, `fe6084a1`, before and after) — the
control that makes a rename of this kind safe to land on its own, and the reason
this change needs no knife re-stamp.

### 6.6f 🔴 THE 6 BYTES ARE NOT BORROWABLE, AND THE MOVE DE-ENTANGLES SOMETHING (2026-09-19)

§6.6e said the port needs `FREAD_OFF` (2 B) and `FREAD_LEFT` (4 B) disk-side.
The obvious economy — bind them to main's `$E9E6`/`$E9E8`, which no disk source
claims — is **wrong, and for a reason worth writing down.**

🔴 **THOSE TWO CELLS ARE INSIDE THE PER-CHANNEL CONTEXT BLOCK.**
`basic/sysvars.inc` §"Phase 2" puts `FCH_STATE0..+FCH_STATESZ` at
**$E9C9..$E9FA**, and names its contents: the read iterator, the file meta, *"the
read stream (`FREAD_OFF`/`FREAD_LEFT`)"* and the whole write state.
`fch_save_active`/`fch_load_ctx` copy that span in and out on every channel
switch. A disk-side loader writing `$E9E6` would be writing into main's channel
staging area from another slot.

🟢 **AND THE SAME FACT IS AN ARGUMENT *FOR* THE MOVE.** Main's FAT state block
IS the per-channel context block, so **today a tokenised `LOAD` clobbers channel
state although `LOAD` is not a channel**. Running the load on `disk.rom`'s own
state ($E4A9..) takes it out of that span entirely. Step 9 is therefore a
separation-of-state improvement as well as a speed one — which §6.2c's timing
could not see.

⚠️ **SO THE 6 BYTES MUST COME FROM disk.rom's OWN RAM, AND IT IS FULL.** Every
documented region is packed, checked name by name rather than by delta:

| region | verdict |
|---|---|
| `$E4A0..$E4C1` (the disk FAT state) | packed; `$E4C2..$E541` is basic-core's `DISK_DTA` |
| `$E7E8..$E7FF` | the *"free tail"* its own comment names — **spent**, `RDBLK_RRSTART` took `$E7FD-$E7FF` |
| `$E77C..$E7E7` | `WA_SEG` hook bodies, `CONOUT_CHAR`, `PG_SV_A8`, the 48-byte interrupt stack, `INT_SP_SAVE`, `CONIN_BUF` |
| `$E560..$E75F` | `WBUF`, 512 B |

⚠️ **TWO THINGS THAT LOOKED LIKE DEFECTS AND ARE NOT** — checked, because a
map is a reading:
  * `BOOT_SV_A8`/`BOOT_SV_SEC` ($E760/$E761, `disk/init.asm`) sit on top of
    `RRND_RECSEC`/`RRND_CLUSSEC` (`disk/equates.inc`). Deliberate: the BOOT_SV
    pair is *"transient, used only during INIT's boot bridge"*. The disk ROM
    already practises documented time-division reuse.
  * `scratchpad/rammap_sweep.py` reports *"95 B $E761..$E7C0 RRND_CLUSSEC"*.
    `RRND_CLUSSEC` is **one byte**. That is the delta-is-not-size artefact the
    sweep's own header warns about — and it is why this section walked the
    declarations instead. 🔴 The sweep also reads only `.inc` files, so it never
    sees `disk/init.asm`'s ~20 declarations at all.

➡️ **TWO WAYS TO GET THE 6 BYTES, AND THE SECOND IS PROBABLY RIGHT:**
  1. **A RAM hunt** — fill a candidate window, exercise every subsystem, read it
     back (`scratchpad/ramfree_probe.py` is the template). Honest, and a probe of
     its own.
  2. **Time-division reuse of BDOS's per-call scratch**, e.g. `RDBLK_BUFPOS`
     ($E774, *"byte offset into SECTOR_BUF (word, 0..512)"* — literally
     `FREAD_OFF`'s semantics) and a `RDBLK_*` word pair. Every one of those cells
     is documented *"per-call lifetime only"* and *"dead during the DOS phase"*,
     and this is the ROM's own established discipline (see `BOOT_SV_*` above).
     ⚠️ **IT RESTS ON ONE CLAIM THAT MUST BE STATED, NOT ASSUMED: a BASIC `LOAD`
     and a BDOS random-block read cannot overlap.** That is not the same claim as
     §0.1a's, which was about BUFFERS that persist across operations, not
     per-call scratch — but it needs saying out loud before it is relied on.

### 6.6g 🟢 THE STREAM LAYER IS IN `disk.rom` (D-DPLPORT, 2026-09-19)

Step 9's first half is built. `basic/fatio-body.inc` — `fat_io_open` and
`fat_io_getbyte` — is now assembled into `disk.rom` as well, the same **one
source, two ROMs** shape Option 2 used for the primitive body.

| | |
|---|---|
| the 6 bytes of cursor state | `FREAD_OFF` → `RDBLK_BUFPOS`, `FREAD_LEFT` → `RDBLK_REQ` (`disk/init.asm`) |
| `disk.rom` free, 2026-09-19 | **8324 B in 29 runs**, from 8435 B — the gate's figure fell **111 B** |

⚠️ **THAT 111 IS NOT THE LAYER'S SIZE, AND D-BYTEREC MEASURED THE DIFFERENCE.**
The spans sum to 109 B; the gate's free-space figure fell 111 B; neither is the
other's check. Built both sides in worktrees and diffed the images:
`-111 = -103` (net `0x00` bytes) `- 8` (zeros that fell below the scan's 16 B
run threshold), and `-103 = -113` (zeros overwritten) `+ 10` (code bytes that
happen to BE `0x00` and are still counted free). The commit RELOCATED code as
well as adding it — 454 bytes differ across the image — so a span sum and a
free-space delta are not comparable here at all. The free-space figure
UNDER-counts by ignoring sub-16-byte runs and OVER-counts by reading `0x00`
inside code as free; both biases are small and both are now named.
| knife pin | re-stamped (`--all`, `--allfn`); full `kwsweep` green; **no tier row moved** |

🟢 **AND THE PREMISE NOW HOLDS, MECHANICALLY:**
`scratchpad/dpldep_census.py --move` flipped from
*"`fat_io_getbyte` IS NOT IN disk.rom's CLOSURE"* to
*"🟢 `fat_io_getbyte` IS LOCAL TO disk.rom"*. The five remaining out-edges are
all once-per-load or once-per-failure call-backs.

⚠️ **THE 6 BYTES COST NOTHING BECAUSE THEY ARE TIME-DIVIDED, AND THE INVARIANT
WAS ALREADY WRITTEN.** §6.6f found no free disk-side RAM, so the cursor state
aliases BDOS's Random-Block-Read scratch. That is not a new assumption: the
`RDBLK_*` block's own comment already says *"Only the DOS-boot path (on a
real-BIOS host) calls $27, so this never collides with the zerobas-BASIC host
buffers (which use the standard DSKIO path, not `bdos_entry`)."* A tokenised
`LOAD` is a zerobas-BASIC host operation reaching the disk through DSKIO, so it
cannot be inside a `$27` call. Same discipline as `BOOT_SV_*` over `RRND_*`.

🔴 **WHAT IS NOT DONE, STATED PLAINLY: NOTHING CALLS IT YET.** The hook
(`fat_io_open` + the `$FF` peek + the six §6.5 bodies, per §6.6e) is the second
half, and until it lands these two routines are 111 B of correct, unreferenced
code in `disk.rom`.

🔴 **AND NO GATE NOTICED THAT** — `tools/check_dead_code.py`'s *"BOTH builds"*
means **main and sub**; `disk.rom` is swept by nothing. Filed in `TODO.md`
(APPARATUS, 🤖). Discovered by walking into it, which is the only reason this
section can say it out loud instead of it being found months from now.

### 6.6h 🛑 THE HOOK HAS NO CELL: STEP 9's SECOND HALF NEEDS A MEASUREMENT FIRST (2026-09-19)

The hook was designed and then not written, because the one thing it cannot be
given is an address. **`LOAD` has no identified hook cell.** `disk/equates.inc`
names sixteen (`H_DSKF`, `H_MKI`…`H_CVD`, `H_NAME`, `H_KILL`, `H_DSKO`, `H_DSKI`,
`H_COPY`, `H_ERRP`, `H_LSET`, `H_RSET`, `H_FIELD`, `H_FILE`) and **none of them
is LOAD's**, while D-CFARCH's census counted **35** cells the reference's disk ROM
claims. Joost's standing ruling puts a disk command's body behind its hook, and
inventing the address is not an option: the clean-room line lets a cell be read
for its SLOT and IDIOM, not guessed at.

🟢 **THE DESIGN IS SETTLED AND COSTS NOTHING TO KEEP** — it is waiting only on
that address, and it came out simpler than §6.6e sketched:

| | |
|---|---|
| the hook returns | `CF=1` (claimed) and **A = a code**: 0 loaded · 1 not found · 2 not tokenised · 3 mount/I-O · 4 out of memory |
| **call-backs needed** | **NONE.** Main dispatches on A — `load_commit_prog`, `dpl_err`, `dpl_oom`, `ascii_load` all stay on main's side of the single hook call |
| main keeps | `diskslot_test`, the `CLPTR`/`CLINK` seed, and every non-tokenised path |

🟢 **AND `fat_io_find` ALREADY SOLVES THE PART THAT LOOKED HARD.** Distinguishing
*not found* from a mount/I-O fault normally needs `DISKOP_OP`, which the disk side
never writes — but `basic/fatio-body.inc` already carries a zero-byte label for
exactly this, and says so: *"D-BLNF: that is how the BLOAD tenant tells NOT FOUND
from a mount/I-O fault without a `DISKOP_OP` it never writes."* `hk_dpload` calls
`fat_mount` then `fat_io_find` and reads the two carries separately. 🟢 That also
**removes** a hazard rather than adding one: `dpl_nf`'s current header warns at
length that `df_or_loaderr` reads a `DISKOP_OP` that is stale unless the carry
came straight out of a main-side `fat_io_open`. Under the code contract nothing
reads that cell on this path at all.

➡️ **WHAT THE MEASUREMENT IS.** `scratchpad/hookid_probe.py` has the method and
its three controls (poke nothing → must not move; poke a NAMED cell → must flip
its verb; poke that same named cell → a DIFFERENT verb must NOT flip). Two things
must change before it can answer this one:
  * its `UNNAMED` list is the **old 27-cell census**; D-CFARCH corrected the
    count to 35, so the candidate set must be re-derived, not reused;
  * 🔴 **the subject destroys the instrument.** `LOAD` replaces the program that
    would print the answer. The readable case is `LOAD"<missing>"`, which raises
    **before** touching the program — but that must be *established*, not
    assumed, and it means the witness is an `ERR` trap rather than a marker the
    loaded program prints.

⛔ ~~**UNTIL THAT CELL IS NAMED, THE 111 B PORTED IN §6.6g STAY UNREFERENCED.**~~
🟢 **LIFTED BY §6.6m (Joost, 2026-09-19): the cell is `$FE5D`, named `H_FOPEN`,
and the selector comes from the program text on the `hk_files` pattern.** The
design in the table above is unchanged by the ruling — it was only ever waiting
for an address.

### 6.6i 🔧 THE INSTRUMENT FOR §6.6h EXISTS; THE RUN IS UNFINISHED (D-LOADHOOK, 2026-09-19)

`scratchpad/hookid_load.py` is built: the `POKE <cell>,201` method
`hookid_probe.py` used to answer `FIELD`, `LSET` and `RSET`, aimed at `LOAD`. It
does **not** yet have the answer, and what it has instead is worth keeping.

🟢 **IT DERIVES BOTH SIDES OF THE CANDIDATE SET RATHER THAN QUOTING THEM.** The
named cells are PARSED from `disk/equates.inc` — and that immediately corrected a
number this spec had been repeating: **17 named cells, not 16.** The claimed set
is read through the DEBUGGER, never the screen (D-CFARCH's 27-vs-35 lesson).

🔴 **ITS FIRST RUN REFUSED, AND THE REFUSAL WAS RIGHT.** The census returned
**zero** claimed cells and the probe stopped rather than concluding *"LOAD is not
hooked"* — an empty match set is not a finding
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]. Three separate
mistakes in my own scan, all in the four lines of Tcl:
  * **no boot wait.** The Tcl runs at machine CREATION; the disk ROM's INIT
    writes the hook table during boot, so the scan read a table of zeros.
    `cf3300_arch_probe.py` wraps its scan in `after time 40` for exactly this.
  * **`peek` instead of `debug read memory`.**
  * 🔴 **a stride of 5.** A cell is five bytes, but nothing promises the table
    starts aligned at `$FD9A` — stepping 5 tests one phase in five and silently
    misses the other four. Fixed to step by 1, as the working census does.

⛔ **THE RE-RUN THEN HUNG** — alive ~20 minutes past the census with **no
emulator process running** and no output. Not diagnosed. The most likely cause is
mine: two openMSX instances were competing (a stale `cf3300_arch_probe` run plus
this one) and I `kill -9`'d both mid-flight, which can leave the boot-per-case
harness waiting on something that will never arrive. **A clean re-run on an idle
machine is the next step, and it must be started from a tree with no other
emulator in flight.**

⚠️ **WHAT THE PROBE ALREADY GETS RIGHT, so the next run is not a fresh design:**
  * `LOAD"<missing>"` as the case, because `LOAD` REPLACES the running program —
    the same reason `hookid_probe.py` records MERGE as unmeasurable. Round 0
    ESTABLISHES that it raises ERR 53 with the program intact and refuses if not.
  * all three controls kept: poke nothing · poke a NAMED cell and flip ITS verb
    · poke that same cell and check a DIFFERENT verb does NOT move.
  * 🔴 **silence is scored as a CHANGE, not as an apparatus failure.** If
    un-claiming the cell drops `LOAD` onto the cassette path the machine may wait
    for tape forever; that is a reading, and its `--selftest` has the negative
    control proving silence cannot be parsed as the baseline.

### 6.6j 🔴 MEASURED: `LOAD` HAS NO HOOK CELL OF ITS OWN (D-LOADHOOK, 2026-09-19)

`scratchpad/hookid_load.py` ran end to end. All three controls passed — the
baseline raises ERR 53 with the program intact, un-claiming a NAMED cell flips
its own verb to ERR 5, and that same poke leaves the LOAD case at 53. Of **18**
candidate cells (35 claimed, read through the debugger, minus the **17** named in
`disk/equates.inc`), exactly two move `LOAD"NOSUCH.BAS"`:

| cell | `LOAD"missing"` | `OPEN"missing"` |
|---|---|---|
| `$FE5D` | 51 | **51** |
| `$FEB7` | OK (nothing happened) | **OK** |
| the other 16 | 53 | — |

🔴 **AND THE SEPARATING CASE DID NOT SEPARATE THEM.** `OPEN"NOSUCH"FOR INPUT
AS#1` raises ERR 53 for the same reason and goes through the same filename parse,
so a cell that is LOAD's own should move LOAD and leave OPEN alone. **Both cells
move both verbs, identically.** Neither is LOAD-specific: they are shared
infrastructure every disk FILE verb passes through.

⛔ **SO THERE IS NO `H_LOAD` TO INSTALL `hk_dpload` AT**, and §6.6h's plan cannot
proceed as written. This is a measurement, not a search that ran out of patience:
the candidate set was derived from the full 35-cell census and every one of the
18 was asked on its own machine.

🔴 **BUT THE HEADING OVERSTATES WHAT THE RUN CAN SUPPORT — NARROWED BY §6.6l.**
What is measured is *no candidate ON LOAD's OPEN PATH is LOAD-specific*. The
readable case is `LOAD"NOSUCH.BAS"` precisely BECAUSE it fails at the directory
search (§6.6i), so the run never reaches the DATA phase — and the data phase is
where step 9's loop lives. Cells named for that phase read "unchanged" whether
they are LOAD's or not. Read the table as a bound, not as a census of LOAD.

🔴 **IT ALSO FALSIFIES AN ASSUMPTION THE EVICTION HAS BEEN CARRYING.** Joost's
standing ruling is that a disk command's implementation belongs in `disk.rom`
behind ITS hook. That has held for every verb so far — `KILL`, `NAME`, `COPY`,
`FILES`, `LSET`/`RSET`, `FIELD` — each with a cell of its own. **`LOAD` is the
first verb measured NOT to have one.** What the ruling means for a verb that
shares its entry is a question for Joost, not one to answer by picking a cell.

➡️ **WHAT THE READINGS SUGGEST, offered as a question and not a conclusion:**
`$FEB7` un-claimed makes both verbs do NOTHING silently, which is what an entry
point looks like; `$FE5D` un-claimed leaves both raising ERR 51, which is what a
routine they both CALL looks like. If `disk.rom` is to serve the tokenised
loader, the shape would be a dispatch inside a shared cell — the way `hk_lrset`
already serves both `LSET` and `RSET` from one body via `LRSET_JUST`. ⚠️ That is
a hypothesis about the REFERENCE's architecture and needs its own measurement
before any code rests on it.

🟢 **THE PROBE IS SOUND AND ITS DIAGNOSES ARE WORTH KEEPING** — three
apparatus faults were caught by its own guards on the way here, each of which
would otherwise have produced a confident wrong answer: an empty census that
refused rather than reporting "LOAD is not hooked"; a baseline of ERR 70 (no disk
in the drive) that refused rather than measuring against the shared DSKIO layer;
and an openMSX invocation missing `set renderer none`, which blocks before the
machine starts and hangs forever. The last one now has a 180 s timeout, so a hang
names itself instead of being diagnosed by `ps`.

### 6.6k 🛑 STEP 10 IS BLOCKED THE SAME WAY, ESTABLISHED IN ONE CHECK (2026-09-19)

Step 10 moves `OPEN`/`CLOSE`'s disk arms behind their hook. **There is no
`H_OPEN` and no `H_CLOSE`** — `disk/equates.inc` names seventeen cells and
neither is among them. ~~and `$FE5D` is referenced nowhere in the tree~~
🔴 **THAT CLAUSE WAS FALSE AND IS RETRACTED — see §6.6l.** `$FE5D` is named in
four places, one of them a MEASURED TABLE nine days older than §6.6j
(`spec-diskbasic-hook-rearchitecture.md` §D-CHANHOOK, 2026-09-15). The grep
behind it asked for `H_OPEN`/`H_CLOSE` and I let its emptiness stand for a
conclusion about a different symbol. §6.6j
already measured the rest: the two cells that move `OPEN"NOSUCH"` are the two
that move `LOAD"NOSUCH.BAS"`, identically. So step 10 needs the same ruling step
9 does, and for the same reason.

⚠️ **THIS TOOK ONE GREP, NOT SIX TICKS**, which is the point of recording it.
Step 9's arc found one further constraint per tick for five ticks before any code
moved. The check that would have short-circuited it — *does this verb have a
named hook cell?* — costs nothing and now runs first.

### 6.6l 🔴 §6.6j AND §6.6k REVIEWED AND NARROWED (D-LOADREV, 2026-09-19)

An adversarial review of the two sections above — asked for holes, not for
agreement — found three, and the first is a plain error of mine. Its working is
`scratchpad/loadhook_analysis.md`; every claim below was re-verified against the
tree before being recorded here.

🔴 **(1) `$FE5D` WAS ALREADY IDENTIFIED, NINE DAYS BEFORE §6.6j MEASURED LOAD
ONTO IT.** `disk/docs/spec-diskbasic-hook-rearchitecture.md` (D-CHANHOOK,
2026-09-15) carries a measured table: of twenty unidentified cells, `$FE5D` is
the ONLY one that moves `OPEN"NOSUCH.DAT"FOR INPUT AS#1` **and** the only one
that moves `MERGE"NOSUCH.BAS"`, both ERR 70 -> ERR 51. `scratchpad/
LOOP-RESTART.md` states it outright: *"`$FE5D` is recovered (it is the cell BOTH
`OPEN` and `MERGE` arrive through)"*. So §6.6j did not discover an unexplained
cell — it added a THIRD verb, `LOAD`, to a shared cell the tree had already
named. That is a stronger result than the one recorded, and it was available
without any new measurement.
⚠️ **THE MECHANISM OF THE ERROR IS WORTH MORE THAN THE ERROR.** §6.6k grepped
for `H_OPEN`/`H_CLOSE`, found nothing, and wrote *"`$FE5D` is referenced nowhere
in the tree"* — a claim about a DIFFERENT SYMBOL than the one searched. An empty
grep is evidence about the string you typed and about nothing else.

🔴 **(2) THE INSTRUMENT IS BLIND TO THE PHASE STEP 9 ACTUALLY MOVES.**
`LOAD"NOSUCH.BAS"` is the readable case BECAUSE it raises before touching the
program (§6.6i) — it fails in the directory search. Step 9 moves the tokenised
DATA loop, which runs only after a successful open. Every candidate whose public
name belongs to the data phase therefore reads "unchanged" for a reason that has
nothing to do with whether it is LOAD's: `$FE80`, `$FE85`, `$FE8A`, `$FE99`,
`$FE9E`, `$FEA3`, `$FEAD` (`docs/spec-basic-nodisk.md`). **Seven of the eighteen
rows are uninformative, and they are the seven nearest the subject.**
⚠️ Smaller, same family: `$FEBC` never entered the candidate list because the
census requires the `F7 … C9` idiom (`scratchpad/hookid_load.py`), and
`docs/spec-basic-nodisk.md` flags that cell as an unexplained loose end.

🟢 **(3) AND LOAD IS NOT AN ANOMALY, WHICH CHANGES THE QUESTION.** The CF-3300
leaves `H.MERG`, `H.SAVE` and `H.LOPD` UNCLAIMED (`docs/spec-basic-nodisk.md`).
No per-verb cell for the program-file verbs is the reference's PATTERN, not a
quirk of `LOAD` — so steps 10, 11 and 12 meet the same wall, and §6.6k's "step 10
is blocked the same way" is the second instance of a rule rather than a
coincidence.

🙋 **SO THE RULING JOOST IS ASKED FOR IS SHARPER THAN §6.6j PUT IT.** Not *"what
do we do about a verb with no hook"* but: **does "every disk command behind ITS
hook" mean a cell of its own, or the cell the reference actually uses?** If the
latter, the shape is `$FE5D` plus a verb selector, and the pattern to copy is
`hk_files` — ONE cell, verb read from the token in program text (`disk/
kernel.asm`) — **not** `hk_lrset`, which is two cells sharing one body and is
what §6.6j reached for. ⚠️ One consequence the cost table must carry: on a
diskless machine `LOAD` has to fall through to CASSETTE, not raise ERR 5 the way
`chan_gate` does, so that surface needs a variant.

🔬 **THE DISTINGUISHING EXPERIMENT, SPECIFIED AND NOT RUN.** Breakpoint-COUNT
each claimed cell across `LOAD"S.BAS",R` vs `LOAD"L.BAS",R` (the 1055 B and
14369 B images §6.2c already built), handler doing `incr` + `cont` only — no
step, no read at the target, no register capture, so the clean-room line
(`expansion-protocol.md` §2) is not approached. Controls: `H_FILE` must count on
`FILES` and zero on `LOAD`; a cell known to scale with sectors must be SEEN to
scale, or a null result means only that the counter is blind. Outcomes: one cell
counts once and nothing scales -> shared entry with the loop inside; something
scales per sector -> stream primitives, which is a different port; per BYTE is
already excluded by §6.2c's arithmetic, since the reference cannot afford a
crossing per byte at the rate it achieves.

⚠️ **DOC DEBT THE REVIEW TURNED UP.** §6.6g prices the port at **111 B** and
`tools/deadcode-allow.txt` at **109 B**. They measure different things — a
free-space DELTA against a sum of SPANS — and the 2 B between them is
unreconciled; one check settles it and neither figure should be quoted until it
does.

### 6.6m 🏗️ RULED BY JOOST, 2026-09-19: `$FE5D` + A SELECTOR

> *"the reference is the better oracle then me, so go with FE5D + selector"*

**This settles the question §6.6l sharpened, and it settles it for the CLASS, not
for `LOAD` alone.** "Every disk command behind ITS hook" means **the cell the
reference actually uses**, not a cell of its own per verb. Where the reference
routes several verbs through one cell, so do we, and the verb is recovered from a
SELECTOR.

Three consequences, and they unblock steps 9 through 12 together:

**(1) `$FE5D` GETS A NAME FOR ITS CLASS, NOT FOR A VERB.** D-CHANHOOK already
refused to call it "OPEN's hook" — *"it is the cell both FILE-OPENING verbs route
through"* (`spec-diskbasic-hook-rearchitecture.md`) — and §6.6j added `LOAD` as
the third. It is `H_FOPEN` in `disk/equates.inc`: the cell every file-OPENING
verb arrives at. Naming it `H_LOAD` would be the narrower-than-its-class mistake
that spec already declined once.

**(2) THE PATTERN IS `hk_files`, NOT `hk_lrset`.** `hk_lrset` is TWO cells
sharing one body, with `LRSET_JUST` telling them apart — it does not solve this
problem, because here there is one cell and several verbs. `hk_files` is the
shape that does: ONE cell and a selector.
⚠️ **BUT THE SELECTOR'S SOURCE IS NOT `hk_files`'s — CORRECTED IN §6.6n.** This
paragraph first said the verb is read from the PROGRAM TEXT, the way `hk_files`
reads the token before `FN_RESUME`. That is wrong for `LOAD`, and the reason is
structural rather than incidental.

**(3) STEPS 10–12 INHERIT THE ANSWER.** §6.6l established that no per-verb cell
for the program-file verbs is the reference's PATTERN — the CF-3300 leaves
`H.MERG`, `H.SAVE` and `H.LOPD` unclaimed. Under this ruling that stops being a
blocker for each of them in turn: they route to `H_FOPEN` and add selector
values. Step 10 is no longer "blocked the same way"; it is the same work again.

⚠️ **ONE THING THE RULING DOES NOT DECIDE, AND IT IS WRITTEN DOWN RATHER THAN
ASSUMED AWAY.** §6.6j's readings suggest `$FE5D` behaves like a routine the
verbs CALL (un-claimed, all three still raise ERR 51) rather than like a verb
entry (`$FEB7`, un-claimed, makes them do nothing). If that is so, mirroring the
reference at `$FE5D` matches its CELL but not necessarily its internal SHAPE.
🟢 **That does not threaten correctness**, because zerobas owns both sides of
this interface: our main stub calls the cell and our `disk.rom` claims it and
dispatches. It bears only on how faithfully our architecture mirrors the
reference's, which is a question §6.6l's counting experiment can still answer
later, and it costs nothing to leave open.

⚠️ **AND THE DISKLESS PATH IS NOT `chan_gate`.** Every verb behind a hook so far
answers ERR 5 when the cell is unclaimed, which is what the reference's diskless
main does for `FILES`/`KILL`/`NAME`. `LOAD` is different: with no disk ROM,
`LOAD"X"` must fall through to CASSETTE. So this hook needs a gate that REPORTS
rather than RAISES, and main keeps its existing `diskslot_test` and cassette
arms behind it.

### 6.6n 🔴 THE SELECTOR CROSSES IN RAM, NOT IN THE PROGRAM TEXT (D-DPLMOVE, 2026-09-19)

§6.6m said the pattern is `hk_files` and meant it twice over: one cell with a
selector (right) and the selector read from the program text (wrong). The
correction is worth more than the fix, because it names WHEN each shape applies.

🎯 **`hk_files` CAN READ THE TOKEN BECAUSE ITS FILESPEC IS EVALUATED INSIDE THE
HOOK.** `ex_files` stages `FN_RESUME` just past the verb's own token and calls
the cell immediately; the byte in front of that cursor is therefore still
`FILES_TOKEN` or `LFILES_TOKEN`, and the evaluator runs later, on the disk side,
which is why `hk_files` pushes the selector across it on the stack.

🔴 **`LOAD` EVALUATES ITS FILENAME IN MAIN, BEFORE THE HOOK EXISTS IN THE
PICTURE.** `do_load` calls `fname_dev`, dispatches `CAS:` versus disk, and only
then reaches `disk_prog_load`. By that point `FN_RESUME` has been overwritten
with the EXPRESSION's resume point — `basic/cload.asm` reads it exactly that way
twice, for the `,R` tail — so the byte in front of it is the closing quote of the
filename, not the verb's token. Re-staging it would mean stashing the token's
address across the evaluator, which is two bytes of RAM to avoid one.

🟢 **SO THE SELECTOR CROSSES IN RAM, AND IT ALIASES `DISKOP_OP`.** That is this
tree's own idiom rather than a shortcut: `basic/sysvars.inc` already binds
`DEFT_STATUS` and `LE_STATUS` onto `DISKOP_STATUS` for mutually-exclusive
consumers. `FOPEN_SEL equ DISKOP_OP`, and the exclusion is ARGUED where the
binding is, not assumed: `DISKOP_OP` is main → SUB-ROM TENANT, while between
main writing the selector and `disk.rom` reading it there is one inter-slot call
and no tenant dispatch — the hook body needs no call-backs (§6.6h) and
`disk.rom`'s FAT engine reaches the drive through DSKIO directly. ⚠️ Written
down with it: an arm that ever DOES call back into main must re-assert the
selector afterwards, or take its own cell.

🟢 **AND IT COST NOTHING, WHICH IS WHY THE CELL WAS WORTH FINDING.** The last
free byte below the channel-context table is `DISKOP_OP` itself — the five-byte
gap at `$E9FB..$E9FF` that `basic/sysvars.inc` advertises is fully spent — so a
new cell would have had to displace something. `scratchpad/rammap_sweep.py`
(D-RAMMAP, the same day) is what made that readable at a glance instead of by
hand.

➡️ **THE GENERALISATION, for steps 10–12.** A verb whose argument is evaluated
INSIDE its hook can carry the selector in the program text; a verb whose argument
is evaluated BEFORE the hook must carry it in RAM. `OPEN`, `MERGE` and `SAVE` all
evaluate their filespec in main, so all three take the RAM route and add a value
to `FOPEN_SEL` — selector 1, 2 and 3 are reserved for them, and an unrecognised
selector already returns `CF=0`, so each arm is a local edit to one `ret nz`.

### 6.6p 🛑 `$FE5D` CANNOT BE CLAIMED, AND IT IS NOT A VERB ENTRY (D-DPLMOVE, 2026-09-19)

Step 9 was implemented under §6.6m and **backed out at the battery**. The code is
right; the CELL is not. Three measurements, each one falsifying the step before
it.

🔴 **(1) CLAIMING `$FE5D` BREAKS THE STOP TRAP.** `stop-trap-acceptance`'s
`E_rearm_under_held_key_refires` asks that the STOP trap re-fire while the key is
held: zerobas re-fires **3×** with the cell unclaimed and **1×** with it claimed,
against a threshold of 2. Three runs each way, and the pre-change ROMs pass in a
separate worktree, so this is not a flake and not pre-existing.

🔴 **(2) IT IS THE CLAIM, NOT OUR HANDLER.** With `hk_dpload` reduced to an
immediate `ret` — the cell claimed, the body doing nothing at all — the row still
fails, twice. So no amount of fixing the handler helps: a `F7 <slot> <lo> <hi>
C9` stub at `$FE5D` is by itself enough.
⚠️ The MECHANISM is not established. Nothing in C-BIOS calls `$FE5D` (it defines
the name and never references it) and neither does our main outside the call this
step added. Recorded as an open question rather than guessed at — the decision
below does not depend on it.

🔴 **(3) AND THE NAME SAYS WHY THE IDENTIFICATION WAS NEVER SAFE.** `$FE5D` is
**`H.NULO`**, which C-BIOS's public hook table documents as *"called for an
operation for file-buffer 0, in DISKBASIC"* — and `docs/spec-basic-nodisk.md`
ALREADY carried that name. It is a shared SUBSYSTEM cell, not a verb entry.
`LOAD`, `OPEN` and `MERGE` all operate on file buffer 0, so un-claiming it
disturbs all three — which is exactly the reading D-CHANHOOK and §6.6j took as
evidence that they *share an entry*. A cell every one of the subjects uses cannot
separate them; the POKE sweeps were measuring the subsystem
([[readout-blind-to-its-own-subject]] again, in a new dress).
⚠️ **§6.6l's "no per-verb cell for the program-file verbs" ALSO needs narrowing.**
The same table names `H.MERG $FE67`, `H.SAVE $FE6C`, `H.BINS $FE71` and
`H.BINL $FE76` — MERGE, SAVE, BSAVE and BLOAD each have a cell **of their own**.
What the CF-3300 does is leave several of them UNCLAIMED, which is a different
fact from their not existing, and §6.6l conflated the two.

🙋 **SO THE RULING'S PREMISE IS REOPENED, AND ONLY JOOST CAN CLOSE IT.** §6.6m
answered *"a cell of its own, or the cell the reference uses?"* with the latter,
on the understanding that `$FE5D` was that cell. It is not: it is a subsystem
hook we cannot claim without breaking an unrelated, measured behaviour. The
ruling's PRINCIPLE is untouched — mirror the reference — but the cell it was
applied to was mis-identified by me, twice, and the spec said so in a file I had
read.

🟢 **WHAT IS KEPT, ALL OF IT INERT.** The loop, the stream layer, the selector,
`chan_probe`'s design and the ABI additions are built and correct; only the
`hook_tab` row is backed out, which is a one-line change to restore. The main-ROM
side is reverted, so `LOAD` behaves exactly as it did before this step and main's
page-1 budget is unchanged. `disk.rom` carries 16 allowlisted-dead spans whose
entry states its own retirement condition, as D-DPLPORT's did.

🟢 **AND ONE REAL FIX SURVIVES ON ITS OWN MERITS.** `basic/fat-prim-body.inc`
used to gate the DSKIO error mapping out of `disk.rom` entirely, so that ROM
mapped no DSKIO failure to an MSX ERR code and wrote no `DISKOP_ERR`. It did not
matter while every disk-ROM verb reached the drive by calling BACK into main's
engine — but it is a latent defect for any verb that does not, which is the whole
direction of this eviction. The mapping is now shared by both arms.

### 6.6q 🛑 A HOOK BODY THAT USES `disk.rom`'s OWN FAT ENGINE RUNS WHILE BASIC IS LIVE — AND ITS BUFFER ALIASES MAIN'S RAM (D-RAMABI, 2026-09-19)

Found while carrying widths into the generated ABI, and it is independent of
§6.6p's cell question — it will still be true whichever cell Joost picks.

🔴 **THE PREMISE THAT IS GOING STALE.** `disk/equates.inc` and
`scratchpad/rammap_sweep.py` both rest on the same argument for why `disk.rom`
may alias main's workspace: *the standalone disk ROM only ever runs while
booting or driving MSX-DOS, NEVER while the BASIC interpreter is live.* That was
true when it was written. The hook re-architecture makes it false by
construction: `hk_kill`, `hk_files`, `hk_copy`, `hk_lrset`, `hk_field`,
`hk_dskf` and `hk_errp` all execute **during** a BASIC statement.

🟢 **IT HAS NOT BITTEN YET, AND THE REASON IS WORTH KNOWING.** Every hook body
shipped so far reaches the drive by `calbak`ing into MAIN's engine, which fills
main's own `FSECTOR_BUF` ($E5C0). None of them touches `disk.rom`'s
`SECTOR_BUF`. The aliasing is real but currently unreachable.

🔴 **STEP 9 IS EXACTLY THE CASE THAT BREAKS IT.** `hk_dpload`'s whole point
(§6.2c) is that `fat_io_getbyte` resolves LOCALLY, so it fills `FAT_DBUF`, which
in a disk build is `SECTOR_BUF equ $E2A0` — 512 bytes running to `$E49F`. Main
has live cells inside that window: `SH_START $E375`, `SH_ERR $E37E`,
`MIDS_DEST $E3E6`, `GFX_PXL $E3ED`, `GFX_CS_M2 $E3F6`, `GFX_SSIZE $E41B`, and
the string-heap/temp-pool region around them.

⚠️ **LOAD MIGHT SURVIVE IT BY ACCIDENT; STEPS 10–12 WILL NOT.** `LOAD` replaces
the program and clears variables, so a trampled string heap may not be
observable — which is the worst kind of safe, because it hides the defect.
`OPEN`/`INPUT#`/`PRINT#` run MID-PROGRAM against live strings and live graphics
state, and step 10 is the same work again by §6.6m's own argument.

➡️ **WHAT THIS ADDS TO THE STEP-9 DECISION,** whichever cell it lands on: the
disk-side stream needs a buffer that does NOT alias main's live workspace, or a
save/restore around it, or the crossing §6.2c priced. That is a THIRD option
beside §6.6p's two, and it is a measurement nobody has taken: `disk.rom` had
free space at the last reading, so a private buffer may simply be affordable.

### 6.6r 🟢 MEASURED AT LAST: `LOAD` **DOES** HAVE CELLS OF ITS OWN, AND THE REFERENCE'S LOOP IS **PER SECTOR** (D-HOOKCOUNT, 2026-09-19)

`scratchpad/hookcount_probe.py`. Two independent runs, every figure identical,
all three controls passing. This answers both open questions and it corrects
§6.6j, §6.6l and §6.6p — in the direction of *more* was knowable, not less.

🔴 **WHY EVERY EARLIER ATTEMPT FAILED, AND IT WAS THE METHOD.** `hookid_load.py`
UN-CLAIMS a cell and watches what breaks. That is a NEGATIVE probe: it reports
that something changed, never what the cell is for. Its witness is an ERROR
MESSAGE, which travels through the subsystem being broken — so `H.NULO`, which
every file-buffer-0 operation uses, moved for `LOAD`, `OPEN` and `MERGE` alike.
And because `LOAD` destroys the program that would print the answer, it could
only ever use `LOAD"<missing>"`, which dies in the directory search and never
reaches the data phase at all.
🎯 **COUNTING ENTRIES INSTEAD OF BREAKING THINGS FIXES BOTH.** A breakpoint
counter does not live in the guest, so a SUCCESSFUL load of a real file is
readable; and shared infrastructure versus a dedicated entry, indistinguishable
under un-claiming, are completely different under counting.

🟢 **(1) `LOAD` ENTERS FIVE CELLS THAT `OPEN` DOES NOT.**

| cell | `FILES` | `LOAD` small | `LOAD` large | `OPEN…FOR INPUT` |
|---|---|---|---|---|
| `$FE5D` (H.NULO) | 0 | **+1** | **+1** | **+1** |
| `$FE67` | 0 | **+1** | **+1** | 0 |
| `$FE76` | 0 | **+1** | **+1** | 0 |
| `$FED0` / `$FED5` / `$FEDA` | 0 | **+1** | **+1** | 0 |
| `$FE7B` (H_FILE, control) | **+1** | 0 | 0 | 0 |

`$FE5D` behaves exactly as §6.6p measured — shared, once each, by both verbs. But
**five cells move for `LOAD` and not for `OPEN`**, which is precisely the
question §6.6j declared unanswerable. It was unanswerable *by that instrument*.
⚠️ Suggestive, and labelled as inference rather than measurement: C-BIOS's table
calls `$FE67` H.MERG and `$FE76` H.BINL, and `LOAD` enters both while entering
NEITHER `H.SAVE $FE6C` nor `H.BINS $FE71`. A shared READ path across
LOAD/MERGE/BLOAD with the write verbs excluded explains that exactly — and means
those one-line names are narrower than the cells' real class, the same lesson
D-CHANHOOK drew about `$FE5D`.

🔴 **(2) AND THE ARCHITECTURE IS PER-SECTOR, WHICH CONTRADICTS STEP 9's DESIGN.**
`$FFCF` and `$FFD4` SCALE with program size: **+8** for the 1055 B image, **+34**
for the 14369 B one. The arithmetic is exact — 1055 B is 3 data sectors, 14369 B
is 29, a difference of **26**, and the counts differ by **26**. The residual +5
is mount traffic (boot sector, FAT, directory). It is not time-driven: `H.TIMI
$FD9F` is flat across every case, so emulated time is constant.

**So the reference crosses a hook boundary ONCE PER SECTOR during `LOAD`.**
⚠️ ~~Its sector loop is driven from OUTSIDE the hook.~~ 🔴 **THAT SENTENCE WAS AN
OVER-READING AND IS RETRACTED.** A count of 1 at the verb cell and 29 at the
sector cell is consistent with BOTH shapes: a loop inside the `$FE67` handler
calling the sector service 29 times, and a loop in main calling it 29 times
directly. Counts cannot separate them, and nothing else here does either.
🟢 **WHAT IS DETERMINED IS STILL THE THING THAT MATTERS:** a per-SECTOR hook
boundary EXISTS in the reference, and a per-BYTE one does not. So a per-sector
design is faithful and affordable — option C of D-LOADREV's analysis, priced
there at ~29 crossings ≈ 4.5 ms against a 3.57 s load — exactly as §6.2c's
arithmetic predicted. Whether the loop above that boundary sits in main or in
`disk.rom` is OURS to choose, not something this measurement dictates.

🟢 **AND IT LARGELY DISSOLVES §6.6q.** A per-sector service hands main one sector
at a time, so the disk side never holds a 512-byte buffer aliased over main's
live workspace for the duration of a load. The hazard does not need solving; the
design that created it was the wrong design.

⚠️ **WHAT IS STILL NOT KNOWN, AND THE CLEAN-ROOM LINE IS WHY.** What any of these
cells DO internally. This probe set breakpoints on addresses in the PUBLISHED
hook table ($FD9A..$FFE7 — MSX2 TH, and C-BIOS's `$C9`-fill confirms the span),
counted entries, and never peeked a cell, followed `<lo> <hi>`, single-stepped,
or captured a register. `$FFCF`/`$FFD4` sit past the last hook C-BIOS's own table
documents, so they are named here BY BEHAVIOUR — "entered once per sector during
a load" — and not by a label this project has any business asserting.

🙋 **WHAT IS NOW JOOST'S TO DECIDE** is a better-posed question than §6.6p's:
step 9 should mirror the reference's PER-SECTOR service rather than move the
whole loop. That is a different slice from the one that was built — main keeps
the tokenised loop, `disk.rom` gains a sector-read entry — and the 16 parked
spans are the wrong shape for it.

### 6.6s 🟢 ROUNDS 2 AND 3: THE PREDICTION HELD, AND `$FE67` IS THE SHARED ENTRY (D-HOOKCOUNT, 2026-09-19)

🟢 **THE PER-SECTOR CLAIM SURVIVED A FALSIFIABLE PREDICTION.** Stated before the
run: if `$FFCF`/`$FFD4` are per-sector, the MID image must land ON the line the
other two define — 15 sectors plus the 5-call mount overhead the small image
established, so **exactly +20**. It read **+20**. Three points, one line:
8 / 20 / 34 hits for 3 / 15 / 29 sectors. Two points can be fitted by anything.

🟢 **AND THE PUBLIC NAMES ARE NOW VALIDATED RATHER THAN ASSUMED.** `SAVE` moves
`$FE6C` (C-BIOS: H.SAVE) and `$FE71` (H.BINS) and nothing else does; `FILES`
moves `$FE7B` (H_FILE). Two independent confirmations that the documented table
lines up with what the counter attributes — so `LOAD` entering `$FE67` is a fact
about the machine, not a mislabelling.

🟢 **`$FFCF`/`$FFD4` IS THE GENERIC SECTOR SERVICE, BOTH DIRECTIONS.** A `SAVE`
of the same program adds **+27** on top of the identical load. Writes pay per
sector through the same cell, so it is the sector-level entry every disk
operation reaches — which is what a per-sector step 9 would be calling.

🔴 **`$FE67` IS A SHARED VERB ENTRY, AND IT IS THE ONE JOOST'S RULING DESCRIBES.**

| cell | `LOAD` | `MERGE` | `BLOAD` | `SAVE` | `OPEN` |
|---|---|---|---|---|---|
| `$FE67` (H.MERG) | **+1** | **+1** | 0 | 0 | 0 |
| `$FE76` (H.BINL) | **+1** | 0 | 0 | 0 | 0 |
| `$FE6C` (H.SAVE) | 0 | 0 | 0 | **+1** | 0 |
| `$FE5D` (H.NULO) | **+1** | **+1** | **+1** | **+1** | **+1** |

`LOAD` and `MERGE` share `$FE67`; nothing else touches it. `$FE5D` is entered by
every file verb, as §6.6p said. **So "one cell, several verbs, a selector" — the
shape Joost ruled for in §6.6m — is exactly right, and I applied it to the wrong
address.** `$FE67` is the cell that shape belongs at.

🎯 **AND THE ORDERING SETTLES ENTRY-VERSUS-CALLEE**, which §6.6j could only
guess: during a `LOAD`, `$FE67` is entered at sequence 17129 and `$FE5D` at
17131 — **the LOAD-only cell comes FIRST, then the shared file-buffer-0
machinery.** That is the signature of `$FE67` being the verb entry and `$FE5D`
something it calls, confirming §6.6j's hunch by measurement rather than by
intuition. `$FE76` follows ~100 events later, after the data phase.

🟢 **RESOLVED (D-BLOADARM, 2026-09-19): THE ZERO IS REAL, AND THE NAME IS NOT.**
Round 3's BSAVE fixture carried an all-zero payload, so `BLOAD` entering `$FE76`
zero times could equally mean *that cell is not BLOAD's* or *the fixture is
malformed and the verb died after the open* — opposite conclusions from one
number. The payload is now `$A5` (distinguishable from unwritten RAM and from
`$FF`) and the case READS IT BACK behind a `CHR$`-built marker, so the typed line
cannot be mistaken for the result. It reads **165**: the fixture is valid and
`BLOAD` SUCCEEDED.
**So `$FE76` is entered by `LOAD` and NOT by `BLOAD`**, even though C-BIOS's
table calls it `H.BINL`, *"called when doing a BLOAD command for disks"*. `BLOAD`
enters only the shared file-buffer-0 set (`$FE5D`, `$FE4E`, `$FE62`, `$FEB2`,
`$FEB7`) and has no dedicated cell among these four.

🔑 **WHICH SETTLES HOW MUCH THE PUBLISHED NAMES ARE WORTH, MEASURED AT FOUR
POINTS RATHER THAN ASSUMED:**

| cell | C-BIOS name | what the counter says |
|---|---|---|
| `$FE6C` | H.SAVE | ✅ borne out — only `SAVE` enters it |
| `$FE7B` | H_FILE | ✅ borne out — only `FILES` enters it |
| `$FE67` | H.MERG | ⚠️ PARTLY — `MERGE` does enter it, and so does `LOAD` |
| `$FE76` | H.BINL | ❌ REFUTED — `BLOAD` does not enter it; `LOAD` does |

➡️ **A documented name identifies A verb that uses the cell — not the only verb,
and in one case not the verb at all.** That is the "a name narrower than its
class" lesson D-CHANHOOK drew about `$FE5D`, now measured across four cells and
found to fail in BOTH directions. Use the names to generate hypotheses; use the
counter to settle them.

⛔ **AND NOTHING SHOULD BE INSTALLED AT `$FE67` UNTIL IT IS TESTED THE WAY
`$FE5D` WAS.** Claiming `$FE5D` broke `stop-trap-acceptance` in a way no
reasoning predicted (§6.6p) and only a full battery caught. `$FE67` must earn the
same clearance before any byte rests on it.

### 6.6t 🔴 IT WAS NEVER THE CELL: OUR DISK ROM CANNOT INSTALL AN 18th HOOK (D-FE67CLEAR, 2026-09-19)

Joost asked for the `$FE67` clearance test before choosing a shape. `$FE67`
failed it — and chasing that failure overturned §6.6p.

**THE CLEARANCE RESULT.** Claim `$FE67` with a handler that is a bare `ret`,
nothing calling it, and run the full battery: **131/132, red on
`stop-trap-acceptance`** — the same row, the same values as `$FE5D`
(`E_rearm_under_held_key_refires`, `flag` 1 against a threshold of 2).

🔴 **SO THE CAUSE IS NOT THE CELL, AND §6.6p's EXPLANATION IS RETRACTED.** That
section concluded `$FE5D` could not be claimed *because it is `H.NULO`, a
file-buffer-0 subsystem cell*. That reasoning was wrong. Three cells now fail
identically — `$FE5D`, `$FE67`, and **`$FDB3`, which no verb in the D-HOOKCOUNT
run ever enters**. A cell nothing touches breaks the same row the same way.

🎯 **IT IS THE COUNT, AND TWO SWAP TESTS PIN IT.** `hook_tab` installs
**seventeen** hooks. With an eighteenth installed the row fails; with seventeen
it passes **regardless of which seventeen**:

| build | installed | `flag` |
|---|---|---|
| baseline | 17 | **3** ✅ |
| `hk_clearance` present but its table row zeroed | 17 | **3** ✅ |
| + `$FDB3` / `$FE5D` / `$FE67` installed | 18 | **1** ❌ |
| + `$FDB3` installed, `H_MKI` row removed | 17 | **3** ✅ |
| + `$FDB3` installed, `H_DSKO` row removed instead | 17 | **3** ✅ |

The code-presence control matters as much as the swaps: `hk_clearance`'s bytes
in the ROM with the table row zeroed passes, so it is neither the image size nor
the layout shift. Only the INSTALLATION of an eighteenth stub does it.

⚠️ **THE MECHANISM IS NOT ESTABLISHED, AND IS NOT GUESSED AT HERE.** The hook
area is not corrupted: dumping `$FD9A..$FFE7` after boot and diffing baseline
against +1 shows only the new stub's own five bytes, plus four `<lo>` target
bytes of `H_NAME`/`H_KILL`/`H_COPY`/`H_FILE` shifted by exactly +5 because their
handlers moved down the ROM. The table walk is correct. Why a eighteenth
installed hook costs the STOP trap two of its three re-fires is open.

🟢 **WHAT THIS UNBLOCKS.** The obstacle is OURS, not the reference's, and it is
not about which address step 9 claims. `$FE67` remains the measured shared
`LOAD`+`MERGE` entry (§6.6s) and is still the right cell for Joost's §6.6m
shape. What has to be fixed first is the 18-hook ceiling — and one obvious
avenue is that step 9 need not ADD a row at all if it can share an existing one.

## 7. The channel trio, and the wall that is not one

`LSET`/`RSET`/`FIELD` need the channel engine: `fch_check` `$7080`,
`fch_mode_class` `$502B`, `fld_lookup` `$73B8`, `var_str_type` `$47A6`,
`req_letter` `$4093` — every one in page 1. **That is what D-VERBCLASS's "STAY
155 B" was measuring.**

🔴 **AND IT IS NOT A WALL, BECAUSE §3'S CORRECTION REMOVES IT.** Those are
call-back targets, and adding one is a single declaration in
`gen_resident_abi.py`'s CALLBACK list — which is exactly how `fat_count_free`
went in for `DSKF`. D-VERBCLASS priced a constraint from the SUB ROM's rule
("no main-page-1 escape"), and `disk.rom` is not bound by it.

### 7.1 🎚️ RULED BY JOOST 2026-09-17: THE FULL MOVE, AND SPEED WAITS

The trio is **PARSE-DOMINATED, and its work has already left main**:
`lrset_store` is a sub-ROM page-0 tenant, so the justified copy went long ago.
What `basic/field.asm`'s 576 B private actually holds is BASIC parsing —
`LSET A$="X"` is `req_letter` → `var_str_type` → `tgt_parse_fld` → `skip_eq` →
`req_operand` → `str_eval`, and `FIELD#1,20 AS N$` is an `eval` for the channel
plus an `eval` and a name resolution per field pair.

So moving the bodies faithfully — the reference's architecture, where the handler
calls back into BASIC for every expression (D-CFARCH: `FILES 5` is ERR 13, not
ERR 2) — costs roughly **five to six call-backs per statement, ~0.8–0.9 ms** at
D-XSLOTPRICE's 0.156 ms, on the verbs whose whole purpose is writing records in a
loop. Two options were put to Joost:

* **A. the full move** — up to 576 B of page 1, at that per-statement cost;
* **B. partial** — move only the non-parse work, keep the parse main-side: no
  speed cost, but the store is already gone so the byte win is small.

🎚️ **HE RULED A, VERBATIM: *"A, lets worry about speed when we reach the next
tiers"*.** That is consistent with the tier ladder — TIER 1 is the happy path
working, TIER 2 reasonable time, TIER 4 on-par speed — and with the charter:
faithful full MSX1 BASIC, which is what the reference's own architecture is.
### 7.2 🟢 THE BASELINE, TAKEN 2026-09-17 — AND IT OVERTURNS §7.1's FRAMING

[`scratchpad/lrset_stopwatch.py`](../../scratchpad/lrset_stopwatch.py), N=200,
empty loop subtracted, seconds of emulated time **per statement**:

| | CF-3300 | zerobas | |
|---|---|---|---|
| `LSET A$="X"` | 0.002593 | **0.001469** | we are 1.77× FASTER |
| `RSET A$="X"` | 0.002594 | **0.001496** | 1.73× faster |
| `FIELD#1,16 AS A$` | 0.005451 | **0.003049** | 1.79× faster |

🎯 **THE REFERENCE'S FIGURE *IS* THE PRICE OF THE ARCHITECTURE WE ARE MOVING
TO.** The CF-3300 runs these three in its DISK ROM, with the call-backs this
move adds; we run them in main with plain calls. So its column is not a target
to beat — it is what an in-disk-ROM implementation of these verbs costs, measured
on the machine that has one.

🔴 **AND THAT MAKES §7.1's OPTION A CHEAPER THAN IT WAS PRESENTED.** The estimate
put to Joost was "5–6 call-backs ≈ 0.8–0.9 ms per statement", which sounded like
a large hit — because it was compared against a statement time NOBODY HAD
MEASURED. `LSET` is 1.47 ms, so +0.8 ms is **+55%**, landing at ~2.3 ms against
the CF-3300's 2.59: still slightly FASTER than the reference. An estimate quoted
without its denominator is not half a measurement, it is a different claim.

### 7.2a 🟢 AFTER THE MOVE (D-LRSETMOVE, same day) — and the reverse direction is measured at last

| per statement | before | after | CF-3300 |
|---|---|---|---|
| `LSET A$="X"` | 0.001469 | **0.001978** | 0.002593 |
| `RSET A$="X"` | 0.001496 | **0.002023** | 0.002594 |
| `FIELD#1,16 AS A$` | 0.003049 | 0.003049 — **unchanged** | 0.005451 |

🟢 **STILL 1.31× FASTER THAN THE REFERENCE**, with three call-backs where it has
its own. And `FIELD` unchanged is the CONTROL: it had not moved, so a figure that
had shifted would have said the instrument drifted between runs rather than that
the verb did.

🎯 **+0.509 ms OVER THREE CROSSINGS = 0.170 ms PER CALL-BACK, disk→main.**
D-XSLOTPRICE measured 0.156 ms **main→disk**, and §7.1 flagged the reverse as
ASSUMED to match. It is ~9% dearer, which is now a reading rather than a guess —
and the prediction built on the old figure (+0.47 ms) came in 8% low, which is
the right direction to be wrong in but not a reason to keep estimating.

⚠️ The instrument's own first run returned NO MARKS on both machines, which is
what a watchpoint that never armed looks like AND what a program that raised
before its first POKE looks like. It was the second: the probe mounted no disk,
so `OPEN` failed at line 10. **A `control` row that needs no disk and no channel
is what separated them**, and it is row one of that probe for good.

⚠️ **AND THE COST MUST BE MEASURED, NOT CARRIED AS AN ESTIMATE.** 0.156 ms is
D-XSLOTPRICE's **main→disk** figure; the reverse direction is ASSUMED to match
and has not been measured. Time `LSET` in a loop before and after, and record the
reading — a per-statement price that only ever existed as an estimate is the kind
of figure a later slice quotes as if it had been taken.

### 7.3 The trio, sized and cut into slices (2026-09-17)

`ex_lset`..`lrset_notfld` is **`$7325`–`$739E` = 122 B**; the rest of
`field.asm`'s 576 B private is `FIELD` and the field-table machinery. So the trio
is **two or three slices, not one**, and this is the riskiest work in this spec:
a well-tested verb (`fldwidth-acceptance`, D-LRVAR) with subtle error ordering.

**What travels with the body** (defined in `field.asm`, private): `tgt_parse_fld`,
`fld_find`.
**What becomes a call-back** (page 1, defined elsewhere): `req_letter`,
`var_str_type`, `skip_eq`, `req_operand`, `str_eval`, `tgt_desc_fix`,
`fch_select`, and `lrset_store` — which stays main-side deliberately, because it
dispatches a SUB-ROM tenant and a disk→sub CALSLT is an unproven nesting this
slice should not invent.
**What is already reachable**: `pu_deref_body` (`$28C1`, low region, declared).

🟢 **A CALL-BACK MAY RAISE, AND THE TREE ALREADY RELIES ON IT.** `hk_files` calls
`fname_expr` with the note *"an EXPRESSION; may RAISE (ERR 13)"*. It is safe
because the target runs in MAIN with main page 1 mapped, so `raise_error`'s
`ld sp,(SAVSTK)` unwinds a stack whose disk-ROM frame is simply discarded — the
handler never resumes, which is the correct outcome for an error. **So
`req_operand`'s ERR 24 and `str_eval`'s ERR 13 do not need a status protocol**;
only decisions the body itself makes (`type_mismatch_error` on a non-`$` target)
do, and `DISKOP_STATUS` is that channel.

⚠️ **THE CURSOR IS THE THING TO GET RIGHT.** Every parse call-back takes and
returns `HL`, and D-XSLOTABI says `HL` crosses both ways — but the body holds the
cursor across `fld_find` and the `=` scan with two `push hl`/`pop hl` pairs
today. Those pairs are inside the handler after the move, and a push that
straddles a `calbak` is a push that straddles a CALSLT.

**Order:** (1) `LSET`/`RSET`, 122 B, proves the seam and the cursor threading;
(2) `FIELD`, whose field-list loop needs an `eval` call-back per `n AS name$`
pair; (3) the field-table machinery, which by then has no main-side callers left.

⚠️ **WHAT IS STILL OPEN IS PHASE 3'S QUESTION, NOT THIS ONE**: `OPEN`, `CLOSE`,
`INPUT`, `LINE INPUT`, `MERGE` and `MAXFILES` **have no hook cell we have
identified**, and the pattern is *point the verb's hook at a disk-ROM body*. With
no cell to point there is nothing to do. That is an ORACLE measurement — the
`hookid_chan.py` POKE sweep over the unidentified cells of the 35-cell census,
with its two controls — and it gates step 6, not steps 4 and 5.

## 7.4 🏗️ TWO RULES FOR WHERE A BODY BELONGS (Joost, 2026-09-17)

**R1 — THE CALL-BACK COUNT IS A MEASURE OF MISPLACEMENT, *AFTER* DUPLICATION.**

Joost, on seeing the trio's ten: *"if we need many callbacks from disk back to
main rom that might mean there's a design flaw?"* — and he is right, with one
correction he supplied himself: *"we have plenty of space in the disk rom...
small utilities can exist as duplicate there."* So the count that diagnoses
anything is the count **after the small helpers are duplicated**.

| body | call-backs |
|---|---|
| `MKI$`, `CVI`/`CVS`/`CVD` | 0 |
| `DSKF` | 1 |
| `KILL`, `NAME`, `FILES`, `COPY` | 1–2 (the filename expression) |
| `LSET`/`RSET` **before** duplication | ~10 |
| `LSET`/`RSET` **after** | ~2 (`str_eval`, `lrset_store`) |

🎯 **ONE OR TWO IS NATURAL; MANY MEANS THE BODY IS IN THE WRONG ROM.** The
underlying question is *does this verb need the DISK, or only the disk ROM's
EXISTENCE?* — but the count is the measurable form of it, and it must be taken
after R2 is applied or it measures the wrong thing. **My first reading of the
trio's ten concluded "misplaced, do not move" and was WRONG for exactly that
reason.**

⚠️ **DUPLICATION MEANS ONE SOURCE ASSEMBLED TWICE, NEVER A COPY.** This tree
already shares **18** `*-body.inc` files between main and `sub/`/`disk/`
(`fatio-body.inc`, `fat-prim-body.inc`, `bload-body.inc`, `fcbname-body.inc`…),
and `make shared-body-check` exists for the failure a real copy would invite:
*"a dead COPY of a live routine is worse than dead code, because it reads as the
live one while being free to drift from it."*
⚠️ **AND A HELPER IS ONLY DUPLICABLE IF ITS CLOSURE IS.** That is checkable, not
a judgement: `tools/check_tenant_closure.py` already computes exactly this for
the sub-ROM tenants. A helper whose closure stays in RAM and the low region can
be duplicated; one that reaches the evaluator cannot — which is why `str_eval`
is irreducible and the reference calls back for expressions too (D-CFEVAL).

**R1a — BEFORE CONCLUDING MISPLACEMENT, BUNDLE.** Ten call-backs is often one
step asked ten times. `LSET`'s target parse is `req_letter` + `var_str_type` +
the `$` check + `tgt_parse_fld` — **four call-backs for one logical act**, and
its RHS parse is another four. A single main-side entry per act — *parse the
target, give me the key*; *parse the RHS, give me the descriptor* — turns ten
into **three** (target, RHS, store).

🎯 **AND BUNDLING BEATS DUPLICATION WHERE BOTH APPLY.** A bundle costs a few
bytes of new main-side code and removes the fine-grained crossings outright; a
duplicate costs disk-ROM bytes and adds a second copy to keep honest. Reach for
the bundle first; duplicate what is left and genuinely local.
⚠️ **A BUNDLE IS ALSO WHAT THE REFERENCE MUST BE DOING.** Its disk ROM asks
BASIC to *evaluate an expression* once, not to *skip a space*, *test a letter*
and *look up a variable* in three crossings — which is consistent with the
CF-3300 being 1.8× slower than us rather than ten times.

⚠️ **AND IT CHANGES THE SLICE PLAN IN §7.5**: with bundling, slice 1 lands at ~3
call-backs (~0.47 ms, `LSET` ≈ 1.94 ms) and stays FASTER than the CF-3300's
2.59 ms, so the seam slice never ships a state slower than the reference and
slice 2 becomes optional rather than corrective.

**R2 — DUPLICATE THE HOT PATH, CALL BACK FOR THE ERRORS.**

A duplicate **cannot raise**: `raise_error` is main page 1. A call-back **can**,
and the tree already relies on it (`hk_files` calls `fname_expr` with *"an
EXPRESSION; may RAISE (ERR 13)"*) — it is safe because the target runs in MAIN
with main page 1 mapped, so the unwind discards the disk-ROM frame and the
handler never resumes, which is the correct outcome for an error.

🎯 So a verb's error tail becomes a call-back on a path that runs approximately
never, while the per-statement path stays local. **That is also what protects the
speed**: §7.2 measured the trio at 1.8× FASTER than the CF-3300 precisely because
it makes those call-backs and we do not; under R1+R2 we keep most of that margin
instead of trading all of it for placement.

### 7.5 So the trio is TWO slices, not one

1. **Seam first, with call-backs for everything.** The risk in this verb is the
   CURSOR THREADING and the ERROR ORDERING, not the helper placement — isolate
   it. Expect the +55%; it is temporary and Joost has ruled speed waits.
2. **Then duplication**, replacing call-backs with shared `-body.inc` includes
   one at a time, each a mechanical change against a seam already proven.

### 7.6 🔴 FIELD COST BYTES IN BOTH ROMS, AND R1 DID NOT SEE IT COMING (D-FIELDMOVE, 2026-09-18)

`FIELD` is the third and last member of the trio, and it is the first move in
this spec that makes **both** ROMs smaller-off. Measured from a clean tree on
2026-09-18:

| | main page 1 | main low region | `disk.rom` |
|---|---|---|---|
| before (`3997a9cc`) | 78 B free | 32 B free | 8368 B free |
| after | 55 B free | 32 B free | 8350 B free |

Main page 1 lost 23 B and `disk.rom` spent 18 B. Nothing was bought with those
41 bytes except the thing the slice is for: a ROM that claims `H_FIELD` now
*runs*, where before main consulted the cell and then did the statement itself.

**R1 (§7.4) does not diagnose this verb, and that is a defect in R1.** R1 reads
the CALL-BACK COUNT as the measure of misplacement. `FIELD` has TWO call-back
targets — fewer than `LSET`/`RSET`'s three — so R1 scores it *better placed*
than the verb that actually moved something. It is not. The right axis is the
**ratio of BODY to HAND-OFF**:

| verb | body in `disk.rom` | statement left in main | call-back targets |
|---|---|---|---|
| `DSKF` | the free-cluster count | the drive argument | 1 |
| `LSET`/`RSET` | ~25 B, the field-entry walk | ~97 B of parse | 3 |
| `FIELD` | ~15 B, a loop | ~300 B of parse, classify and table write | 2 |

So R1 stands as written — a HIGH count still means misplacement — but its
converse is false, and this row is the proof: **a LOW call-back count can mean
there was never a body to move.** Read the two together or neither.

⚠️ **AND THE CROSSINGS SCALE WITH THE ITEM COUNT HERE, WHICH NO EARLIER MOVE
DID.** `field_item` parses one `w AS v$`, adds it, checks the ERR 50 bound and
returns CF=1 when a comma follows, so a FIELD of N items costs 1 + N crossings
against `LSET`'s fixed 3. At the 0.170 ms measured in §7.2a, a four-field
`FIELD` pays ~0.85 ms. That is a projection from a measured per-crossing price,
NOT a measurement of `FIELD` — the stopwatch row for it is 3.049 ms pre-move
(§7.2a's control) and has not been re-taken.

🎯 **WHY IT IS STILL CORRECT.** The defect §4 names is not a byte count and was
never going to be paid for in bytes. `FIELD`'s substance is a parse, a channel
classify and a write into `FLD_TAB` — and `FLD_TAB` is MAIN's table by rule R2,
which is why `FLD_ENTSZ`/`FLD_TABEND` still appear in exactly one file. A verb
can be entirely main-shaped and still have to be *decided* in the disk ROM.

## 8. What must stay in main, and why

The 250 B frontier is not a residue to be minimised; it is the **interface**.

* **The parse.** `fname_expr`, `pdfcb_resume`, `parse_disk_fcb` — already
  call-back targets, because a filespec is a BASIC expression and only main can
  evaluate one. The reference does the same across slots (D-CFEVAL/D-CFARCH:
  `FILES 5` is ERR 13, not ERR 2).
* **The raise.** `raise_error` is page 1 and a handler must not raise across the
  call: a body returns a status and main raises. `DISKOP_STATUS` is that channel.
* **The channel table's readers.** `fch_check`/`fch_select` serve `EOF`, `LOC`,
  `LOF` — verbs that are not disk-only.
* **`init_filechan`** (30 B) runs at cold boot, before any hook is claimed.

## 9. The diskless obligation — which §0.0 turns into a consequence

`C-BIOS_MSX1_EU_REPACK_NODISK` is an official target. **Every body that moves
must leave the diskless build answering what the reference answers**, which is
ERR 5 from the hook being unclaimed — not the channel's own error, and not
silence.

🎯 **AND UNDER §0.0 THIS STOPS BEING A SEPARATE THING TO REMEMBER.** The diskless
target is the SAME `main.rom` + `sub.rom` in a machine with slot 3-1 empty —
which is exactly the reference's own arrangement, one BASIC ROM serving both
machines. So once a body is behind its hook, the diskless answer is not
something the slice must arrange: it is what an unclaimed cell already does.
The obligation below is therefore a CHECK that the move was complete, not a
second feature to build.
⛔ **AND IT IS WHY THERE MUST BE NO DISKLESS BUILD.** A `DISK_RESIDENT`
conditional-assembly switch would produce a second main that no longer contains
the unclaimed-hook paths — which would delete the only witness that those paths
answer ERR 5 correctly in the DISK build. The same-ROM diskless machine is both
the faithful arrangement and the instrument.

⚠️ **D-NODISKGAP IS THE WARNING**: `ex_lfiles` once entered PAST its gate, so a
diskless `LFILES` answered differently from a diskless `FILES`. **A body that
moves must leave exactly ONE entry, and it must be the gate.**
`make nodisk-acceptance` scores it, and its `PINNED` set is a record of
divergence — removing an entry from it is what fixing one looks like.

## 10. How each step is verified

* the verb's own oracle probe **at the byte level** — `kwsweep`'s rows are often
  `LEN`- or value-based and would pass a wrong byte ORDER (`mksd_probe.py` reads
  bytes back with `ASC`, which is what caught §5.1);
* `make kwsweep` — SUPPORTED must not move for a behaviour-preserving change;
* both knife arms re-stamped, ROM hash included;
* `make nodisk-acceptance` for §9;
* the full battery **plus the eight battery-excluded targets**, which include
  `diskbasic-acceptance`, `bdos-acceptance` and `fat-error-acceptance` — the
  three that actually exercise a disk.

## 11. What this spec does NOT claim

* It does not claim the census in §1 is the denominator. Under §0.0 the subject
  is disk IMPLEMENTATION in main+sub; §1 measures six files in main, one of
  which is half device-generic and one of whose includes it omits.
* It does not claim any byte figure in §1 or §6.2 is tool-derived. The
  per-cluster splits are HAND CLASSIFICATION from label spans. The only honest
  measurement of "disk code in main+sub" is the reachability gate at step 14,
  which does not exist yet.
* **It does not answer where the FAT engine's buffer parameter comes from, and
  §0.1 says why: the question of whether the reference even HAS two buffers is
  unmeasured.** A parametrisation chosen before step 6 would be a design built
  on an assumption about hardware nobody has read.
* It does not know the hook cells for `LOAD` / `SAVE` / `PRINT#` / `INPUT#` /
  `CLOSE`. Only `$FE5D` is measured, and it flips `OPEN` and `MERGE` TOGETHER
  (spec-diskbasic-hook-rearchitecture.md §403). Steps 9–12 each need their cell
  identified first, and the published names are not contracts we can read
  without a disassembly — so ours will be own-design behind measured cells.
* It does not claim a handler that runs a whole `LOAD` is safe as written: it
  must `ei` on entry and `di` on exit (the `bload_tenant` precedent), or TIME,
  PLAY and the traps freeze for the load's duration.
* It does not assume the order in §6.2 survives contact. Each step re-reads the
  walls before it starts.
* 🔴 **It does not claim to be right this time.** This spec has now been wrong
  about the FAT layer THREE times: once on the order (step 5 as "the bulk"),
  once on the blocker (§6.1's file list), and once on the subject (§0.0). All
  three were caught by someone re-deriving from the tree rather than reading
  this document. Do that again before building on it.
