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

> 📘 **§§6.6r–§6.6aa ARE THE WORKING RECORD, WRITTEN AS THE MEASUREMENTS WERE
> MADE, AND SEVERAL CORRECT EARLIER ONES.** The consolidated, retraction-checked
> description of how `LOAD` works on the reference is
> **`disk/docs/expansion-protocol.md` §8** — read that first, and come here for
> the instrument, the controls and the history of each claim.

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
✅ **ANSWERED SINCE, BY §6.6u:** the caller's return address settles it — the
loop is INSIDE the disk ROM. The retraction was right and the original hunch was
too; what was missing was an instrument that could tell them apart.
🟢 **WHAT IS DETERMINED IS STILL THE THING THAT MATTERS:** a per-SECTOR hook
boundary EXISTS in the reference, and a per-BYTE one does not. So a per-sector
design is faithful and affordable — option C of D-LOADREV's analysis, priced
there at ~29 crossings ≈ 4.5 ms against a 3.57 s load — exactly as §6.2c's
arithmetic predicted. Whether the loop above that boundary sits in main or in
`disk.rom` is OURS to choose, not something this measurement dictates.

🔴 **THE FOLLOWING PARAGRAPH IS WITHDRAWN BY §6.6u.** Its premise is that MAIN
keeps the loop and the disk side is a one-sector-at-a-time service. Measured, the
reference does the opposite, so the hazard is back — and it is the price of the
faithful shape, not an argument against it. The analysis is kept because the
conditional it states is still true: IF main kept the loop, §6.6q would go away.
🟢 ~~**AND IT LARGELY DISSOLVES §6.6q.**~~ A per-sector service hands main one sector
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

🔴 **RETRACTED BY §6.6v — `$FE67` IS UNCLAIMED, SO IT IS NOT AN ENTRY AT ALL.**
Reading the cell's bytes shows a bare `C9`: main calls it and it returns. The
counts below are real and the INFERENCE from them is not, because a hook nobody
claimed and a real crossing are both "entered once". Joost's `$FE5D` stands.
🔴 ~~**`$FE67` IS A SHARED VERB ENTRY, AND IT IS THE ONE JOOST'S RULING DESCRIBES.**~~

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

🔴 **THE NEXT PARAGRAPH'S INFERENCE IS CORRECTED BY §6.6u: ORDER IS NOT NESTING.**
`$FE5D`'s caller is measured to be MAIN page 1, so it is a main-side step in the
same statement, NOT something the disk-side handler calls. The CONCLUSION —
`$FE67` is the verb entry — survives, on §6.6u's evidence rather than on this.
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
| `$FE76` | H.BINL | ⚠️ REFINED by §6.6v — it marks the BINARY-FORMAT program path: tokenised `LOAD` enters it, ASCII `LOAD` does not, and neither does `BLOAD` |

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

> 🟢 **ITS CONCLUSION IS WITHDRAWN BY §6.6af (2026-09-20).** The analysis
> below is kept intact — inverted, not deleted — because it is what made the
> right next move findable. Its own closing advice, *doubt the row first*,
> was taken and was correct: `E_rearm_under_held_key_refires` reads RED on
> the UNMODIFIED ROM at 15 of 20 timing configurations, so it cannot carry
> the claim in this heading. **An 18th hook is not known to be a problem.**

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

🔴 **AND THEN THE "CEILING" ITSELF FAILED TO SURVIVE A MECHANISM CHECK — SO IT
IS PARKED, NOT BELIEVED.** Counting hook ENTRIES on OUR machine while running the
failing row's own program, 16-hook build against 18-hook build:

| cell | 16 hooks | 18 hooks |
|---|---|---|
| `$FD9A` / `$FD9F` (the 60 Hz interrupt pair) | 12981 | **12981** |
| `$FDA4` | 375 | **375** |
| `$FDC2` | 153 | **153** |
| `$FDB3` (the 18th hook itself) | 0 | **0** |

**Nothing ever enters the extra hook, and every cell that IS entered has an
identical count.** Same work, same interrupt total, same run length. The only
mechanical story — that a claimed cell costs a full inter-slot call where an
unclaimed one costs a bare `RET` — is therefore dead, and no other mechanism is
in hand.

⛔ **SO "OUR DISK ROM CANNOT INSTALL AN 18th HOOK" IS NOT A FINDING AND MUST NOT
BE TREATED AS ONE.** What exists is a CORRELATION, consistent across nine builds
(five red at 18 installed, four green at 16 or 17, the set of cells irrelevant)
with NO mechanism and with the machine demonstrably doing identical work. A
correlation that survives every discriminating test but explains nothing is far
more likely to be a property of the MEASUREMENT than of a Z80.
➡️ The honest next step, whenever someone returns to it, is to doubt
`E_rearm_under_held_key_refires` before doubting the hardware: it scores 3
against a threshold of 2 where the reference scores 122, so it is a
one-step-from-red metric, and what it counts is re-fires inside a fixed window.
Establish what makes IT move before attributing anything to hook installation.

🟡 **WHAT SURVIVES, AND IT IS THE PART THAT MATTERS FOR STEP 9:** claiming a
cell — ANY of three tried — reproducibly turns that row red, and the code-only
control (handler assembled in, table row zeroed) stays green. Whatever the cause,
installing a new hook currently trips an acceptance row, and that is a real
obstacle to step 9 at ANY address. `$FE67` remains the measured shared
`LOAD`+`MERGE` entry (§6.6s) and is still the right cell for Joost's §6.6m shape.
➡️ And the cheap way round is unchanged and now looks better than chasing this:
**step 9 need not ADD a row at all** — sharing an existing one leaves the
installed set untouched and sidesteps the whole question.

### 6.6u 🟢 MEASURED: MAIN HANDS `LOAD` OVER ONCE AND THE DISK ROM OWNS THE WHOLE SECTOR LOOP (D-LOADPROTO, 2026-09-19)

🏗️ **JOOST, 2026-09-19:** *"as long as we don't fully know how e.g. `LOAD`
works on the reference, we can't implement it properly."* That reframes step 9
from a shape Joost has to RULE on into a shape that can be MEASURED, and this is
the measurement. `scratchpad/loadproto_probe.py`, three identical runs.

🎯 **THE METHOD, AND IT IS ONE STEP PAST D-HOOKCOUNT.** At a breakpoint on a
hook cell the Z80 has not yet executed the cell's first byte, so the word at
`(SP)` is the return address into WHOEVER CALLED THE HOOK. Classify that address
by its page and that page's selected slot and the caller's ROM falls out:
`$0000-$3FFF` slot 0 = main page 0, `$4000-$7FFF` slot 0 = main page 1,
`$4000-$7FFF` slot 3-1 = the disk ROM. 🔴 **The slot is what makes this work at
all** — `$4000-$7FFF` is main page 1 AND the disk ROM, so an address alone
cannot tell them apart, and the probe's selftest carries that exact pair as a
negative control.

🔴 **FOUR CONTROLS, ALL GREEN IN EVERY RUN.**

| | control | result |
|---|---|---|
| K1 | `H.TIMI $FD9F`'s caller is known a priori to be the BIOS interrupt handler in **main page 0** | classified MAIN-P0, 2244/2244 |
| K2 | the arming window must cover the WHOLE verb: each sector cell's delta must equal D-HOOKCOUNT's | **8 each** (3-sector image), **34 each** (29-sector image) |
| K3 | the `quiet` case types no verb, so `$FE67` never fires and the trace must be EMPTY | 0 events |
| K4 | the disk ROM must actually be observed selected into page 1 | slot 3-1 seen |

🟢 **(1) THE SECTOR LOOP RUNS INSIDE THE DISK ROM.** Every entry to the
per-sector service has its caller in the **disk ROM**, at both sizes:

| image | data sectors | sector-service entries | callers |
|---|---|---|---|
| S (1055 B) | 3 | 16 | **DISK 16 / MAIN 0** |
| L (14369 B) | 29 | 68 | **DISK 68 / MAIN 0** |

Three data sectors and twenty-nine give the same verdict, so this is the shape of
the loop and not an artefact of a file that fits somewhere special. **This is the
sentence §6.6r had to RETRACT, now settled by measurement rather than by
preference:** a count of 1 at the verb cell and 29 at the sector cell was
consistent with a loop in main and with a loop in the disk ROM; the caller region
separates them, and it is the disk ROM.

🟢 **(2) AND A SECOND, INDEPENDENT LINE AGREES.** All 16 (and all 68) sector
entries sit at a stack depth BELOW the verb entry's. Caller region and stack
depth are different quantities and could have disagreed; they do not.

🔴 **(3) THE HEADLINE IS A NEGATIVE: THE DISK ROM IS NEVER SEEN CALLING BACK
INTO MAIN AT EITHER PUBLIC INTER-SLOT ENTRY DURING A LOAD.** ⚠️ §6.6v shows this
must be read exactly as scoped — it bounds the two public entries, not every
route back into main, and a ROM can page slots itself with `out ($a8)`. Both public inter-slot entries were trapped for the whole verb
— `$0030` (RST 30h / CALLF) and `$001C` (CALSLT). The disk side makes **8**
outward calls through CALSLT and **every one of them targets its own slot**;
there is no disk→main crossing at either entry, at either file size. The 8 do
not scale with sectors (8 at 3 sectors, 8 at 29), so they are mount traffic, not
per-sector work.

🔴 **CORRECTED BY §6.6v: THE CELL NAMED IN THE NEXT PARAGRAPH IS WRONG.**
`$FE67` holds a bare `C9` — main calls it and it returns, and nothing crosses
there. The HANDOVER SHAPE below is right and the ADDRESS is not: the crossing is
at `$FE5D`, which is claimed and which every file verb enters. An entry count
cannot tell an offered extension point from a crossing, which is why this section
picked the wrong cell.
➡️ **SO THE REFERENCE'S `LOAD` PROTOCOL IS ONE HANDOVER, NOT A CONVERSATION:**
main (page 1) calls ~~`$FE67`~~ **`$FE5D`** once, control crosses to the disk ROM,
and the disk ROM runs mount, directory search and the entire sector loop on its
own side before returning. Main is not driving the transfer.

🔴 **(4) WHICH CORRECTS §6.6s, AND THE ERROR WAS READING ORDER AS NESTING.**
§6.6s took `$FE67` at sequence 17129 and `$FE5D` at 17131 as "the LOAD-only cell
comes first, then the shared machinery ... the signature of `$FE67` being the
verb entry and `$FE5D` something it calls." **`$FE5D`'s caller is MAIN page 1**,
as is `$FE76`'s. They are main-side steps in the same statement, not callees of
the disk-side handler. Ordering constrains nothing about who calls whom; only the
return address does. 🎯 The conclusion `$FE67` IS the verb entry survives — it
is the cell main calls, and the crossing happens there — but it survives on this
evidence, not on §6.6s's.

🔴 **AND THIS PUTS §6.6q BACK.** §6.6r retired the buffer-aliasing hazard on the
grounds that "a per-sector service hands main one sector at a time, so the disk
side never holds a 512-byte buffer aliased over main's live workspace for the
duration of a load." That relief was premised on MAIN keeping the loop. The
reference does the opposite, so a faithful step 9 **does** hold disk-side buffer
state across the whole transfer while a BASIC statement is live, and
`SECTOR_BUF $E2A0..$E49F` still overlaps `SH_START $E375`, `SH_ERR $E37E`,
`MIDS_DEST $E3E6`, `GFX_PXL $E3ED`, `GFX_CS_M2 $E3F6`, `GFX_SSIZE $E41B` and the
string heap. **The hazard is not dissolved; it is the price of the faithful
shape**, and it has to be solved rather than designed around.

🙋 **WHAT THIS DOES AND DOES NOT DECIDE FOR STEP 9.** It removes the A-vs-B
question from Joost's plate: the reference is **B** — one cell, the whole loop
below it. It does NOT clear the obstacle §6.6t parks: claiming a new hook cell
still reddens `stop-trap-acceptance`, so the "share an existing row" route stays
the cheap way in. And it does not price the move.

⚠️ **WHAT IS STILL NOT KNOWN.** The register contract at the crossing — what
main puts in which register before calling `$FE67`, and what it expects back.
That is the next thing a faithful implementation needs and the next thing this
instrument can be pointed at. Also unmeasured: whether `SAVE` and `MERGE` have
the same shape, and whether the 8 mount-time CALSLTs are DSKIO or something else.

🔴 **CLEAN ROOM.** Registers, one word of RAM (the stack top) and the
slot-select state only — the same surface `disk/docs/expansion-protocol.md` §7
already operates on ("reading the live Z80 register file / system work areas").
No ROM byte was read, no hook cell's `<lo> <hi>` was followed, nothing was
single-stepped into ROM, nothing was disassembled. The report prints REGIONS and
counts and deliberately never prints a reference-internal address.

### 6.6v 🔴 AN ENTERED CELL IS NOT A CROSSING — `$FE67` IS A BARE `RET`, AND JOOST'S `$FE5D` RULING WAS RIGHT AFTER ALL (D-CROSSABI, 2026-09-19)

`scratchpad/crossabi_probe.py`, seven cases, two runs agreeing on every control
and every shape. It set out to measure the REGISTER CONTRACT at §6.6u's crossing
and found there is no crossing at that cell.

🔴 **THE PRECONDITION FAILED, AND THE FAILURE IS THE RESULT.** A claimed hook
cell holds `F7 <slot> <lo> <hi> C9`; an unclaimed one holds a bare `C9`. Reading
the five bytes of every published slot after boot (§2 permits exactly this — slot
and idiom, nothing followed) gives **35 of 118 slots CLAIMED**, identical across
all seven cases:

| cell | | state |
|---|---|---|
| `$FD9F` | H.TIMI | CLAIMED |
| `$FFA7` | HPHYD | CLAIMED |
| `$FDEF` | HDSKO | CLAIMED |
| **`$FE5D`** | **H.NULO** | **CLAIMED** |
| **`$FE76`** | **H.BINL** | **CLAIMED** |
| `$FE67` | §6.6u's "verb entry" | 🔴 **unclaimed — bare `RET`** |
| `$FE6C` | H.SAVE | 🔴 **unclaimed — bare `RET`** |
| `$FFCF` / `$FFD4` | the per-sector service | 🔴 **unclaimed — bare `RET`** |

🎯 **SO AN ENTRY COUNT CANNOT LOCATE A CROSSING, AND THAT IS THE LESSON.**
BASIC calls its hook cells unconditionally to offer an extension the chance to
act. An offered cell nobody took and a real inter-slot handover are **both
"entered once"** under a breakpoint counter. Every cell D-HOOKCOUNT ranked, and
every conclusion §6.6s and §6.6u drew about WHICH cell matters, rests on a
measurement that is blind to the distinction. Four of them are no-ops.

🟢 **A SECOND WITNESS AGREES, AND IT IS NOT DERIVED FROM THE BYTES.** Trapping
both ends of each cell — offset 0 and the trailing `C9` at offset 4, both RAM
addresses in the published table — gives an asymmetry that follows from the claim
state without being read off it:

| cell | entries / exits | reading |
|---|---|---|
| `$FE5D` | 1 / 1 in all six verb cases | a call-and-return crossing |
| `$FE76` | 1 / 0 (tokenised `LOAD` only) | entered, never returns through the cell |
| `$FE67` | 1 / 0 | its `C9` at offset 0 returns before offset 4 is reached |
| `$FE6C` | 1 / 0 | the same |

🔑 **WHICH RESTORES JOOST'S §6.6m RULING AND RETRACTS MY CORRECTION OF IT.** He
ruled *"the reference is the better oracle then me, so go with FE5D + selector"*.
§6.6s moved that to `$FE67` on the strength of an entry count. **`$FE5D` is the
claimed cell, it is the one every file verb enters, and it is the only one that
pairs.** One cell, several verbs, therefore necessarily a selector — exactly the
shape he ruled for, at the address he named. The cell has now moved twice and the
reason it moved wrongly is this section's first paragraph.

⚠️ **`$FE76` IS ABOUT THE FORMAT, NOT THE VERB — WHICH PARTLY REHABILITATES A
NAME §6.6s MARKED REFUTED.** It is entered by `LOAD` of a TOKENISED file and NOT
by `LOAD` of an ASCII file (the probe loads the same bytes under two names, and a
third file in ASCII form, so this is separated rather than inferred), not by
`MERGE`, not by `SAVE`, not by `BLOAD`. "H.BINL — binary load" describes the
BINARY-FORMAT program path, which is a better fit than either "BLOAD's cell" or
"refuted".

🟢 **AND ONE REGISTER IS IDENTIFIED BY CONTENT.** At `$FE76`, `IY` points at
the file name in padded 8.3 directory form — the dump reads `S       BAS` and
`L       BAS` and tracks the file being loaded. Identified by what is THERE, not
by matching a work-area name this tree does not have a table for.

✅ **ANSWERED BY §6.6w:** the selector is not in RAM and not a verb — `DE`
carries an open MODE (`1` input, `2` output, `$80` for `SAVE`) and `HL` the file
buffer. `LOAD`, `MERGE` and `BLOAD` are indistinguishable at this cell.
🔴 **BUT `$FE5D` CARRIES NO PER-FILE ARGUMENT IN THE REGISTERS.** `AF`, `BC`,
`DE`, `HL`, `IX` and `IY` at its entry are **invariant across all four loads** —
including between two files with the SAME BYTES and different names, and between
a 3-sector and a 29-sector file. `HL` points at a fixed structure whose contents
are identical case to case. **So the selector and the arguments travel in RAM,
not in the register file**, and finding them is the next measurement.

🔴 **THE PARAGRAPH BELOW IS RETRACTED BY §6.6aa.** `$FE76` is NOT entered
between `$FE5D`'s entry and its exit — that ordering came from this probe
printing `ins + outs`, i.e. every entry before every exit by CATEGORY, and I read
it as a time order. A timestamped run puts `$FE76` after the crossing closes, and
the `$A8` trace shows page 1 going MAIN → DISK → MAIN with no excursion. There is
no hand-back to explain. The scoping advice in it is still correct and is kept.
⚠️ **AND §6.6u'S CROSSING-DIRECTION BULLET MUST BE READ AS WRITTEN.** It says no
disk-side call into main was observed *at either public inter-slot entry*, and
that remains true. It is not the same as "no return into main happens": `$FE76`
is entered, with `MAIN-P1` on top of stack, BETWEEN `$FE5D`'s entry and its exit.
Two readings fit — the disk side returned control to main by a route that is not
`$0030` or `$001C` (a ROM can page slots itself with `out ($a8)`), or `$FE76` is
reached by a `jp` so its top-of-stack is a caller's caller, the limit D-LOADPROTO
named up front. 🔼 **The discriminator is cheap and unrun:** watch `$A8` writes
inside the window, the idiom `scratchpad/cf_trace.py` already carries.

🟢 **WHAT §6.6u KEEPS.** Its central finding does not depend on claim state:
every per-sector entry's CALLER is in the disk ROM, at 3 data sectors and at 29,
so the disk ROM owns the sector loop and step 9's shape is still the whole-loop
move. What changes is WHERE main hands over — `$FE5D`, not `$FE67` — and that the
per-sector cells are the disk ROM's own unclaimed extension points rather than a
boundary anything crosses.

🔴 **CLEAN ROOM.** Registers, RAM (hook cells, the stack top, and whatever a
register points at) and slot-select state. No ROM byte read, no hook target
followed, nothing single-stepped into ROM, nothing disassembled; a register
holding a reference-internal address is reported as a PAGE, and the probe refuses
to name a slot it did not sample.

### 6.6w 🔑 THE CROSSING CARRIES AN OPEN **MODE**, NOT A VERB SELECTOR (D-SELECTOR, 2026-09-19)

§6.6v left one question: the registers at `$FE5D` are invariant across four
loads, so what tells the disk side which operation it is serving? Two
measurements answer it — `scratchpad/selector_probe.py` (a RAM differential at
the crossing) and an extension to `scratchpad/crossabi_probe.py` (the register
comparison §6.6v never made).

🔴 **FIRST, A CANDIDATE THAT LOOKED PERFECT AND IS NOT THE ANSWER.** Dumping
`$E000..$FFFF` at the `$FE5D` breakpoint across cases and subtracting —
verb-dependent MINUS name-dependent MINUS size-dependent — leaves three runs. Two
are the typed input line, identified by CONTENT (they spell `LOAD"`, `MERGE`,
`SAVE"`, `OPEN"`). The third is a single byte at **`$F41F`**:

| verb | `$F41F` | our own `basic/sysvars.inc` |
|---|---|---|
| `LOAD` | `$B5` | `LOAD_TOKEN equ $B5` |
| `MERGE` | `$B6` | `MERGE_TOKEN equ $B6` |
| `SAVE` | `$BA` | `SAVE_TOKEN equ $BA` |
| `OPEN` | `$B0` | `OPEN_TOKEN equ $B0` |

It is the statement's BASIC token, and our equates — oracle-sourced from a
VG-8020 by crunching keywords, a different machine by a different method — agree
at all four points. A one-byte code, perfectly verb-dependent, file-independent,
live at the instant of the crossing. **And it is not what the disk side reads.**
A `read_mem` watchpoint on it reports **13 reads, every one with PC in MAIN
(3 in page 0, 10 in page 1), and ZERO inside the `$FE5D` window** — identical in
`LOAD` and `MERGE`. It is main's own record of the statement it is executing.
🎯 **This is the check §6.6t's parked correlation did not have.** A byte that
tracks the verb across four values with independent confirmation of its meaning
is exactly the kind of evidence that gets shipped as a finding. Asking *who reads
it* cost one run and refuted it.

➡️ **AND WITHIN THAT BAND THERE IS NO OTHER CANDIDATE.** Verb-dependent,
file-independent, and not the input line — the set is that one byte. So the
selector is not in the work area the disk side could consult.

🔑 **SECOND: IT IS IN `DE`, AND IT IS A MODE RATHER THAN A VERB.** §6.6v compared
registers across four cases that were all LOADs, so it could only ever answer
"does a register carry the FILE". Asked across VERBS, `DE` separates them:

| case | `DE` |
|---|---|
| `LOAD` | `$0001` |
| `MERGE` | `$0001` |
| `BLOAD` | `$0001` |
| `OPEN … FOR INPUT` | `$0001` |
| `OPEN … FOR OUTPUT` | `$0002` |
| `SAVE` | `$0080` |

🔬 **A PREDICTION WAS STATED BEFORE THE RUN AND IT SCORED HALF.** Fitted to the
first three points, the hypothesis was *"`DE` carries read-versus-write"*, which
predicts `BLOAD` = `$0001`, `OPEN FOR INPUT` = `$0001` and **`OPEN FOR OUTPUT` =
`$0080`**. The read half HELD across three new points. ❌ **The write half is
REFUTED:** `OPEN FOR OUTPUT` reads `$0002`, not `SAVE`'s `$0080`. `DE` is an
open-MODE code — `1` for input, `2` for output, `$80` for `SAVE` — which is
exactly what a cell named *"an operation for file-buffer 0"* would take.

🟢 **`HL` IS THE BUFFER.** `$DC65` for every program verb and `$DD6E` for
`OPEN`'s channel — machine RAM addresses, so they are quotable. `AF` is invariant
across every verb; `BC`, `IX` and `IY` vary without an interpretation this
measurement can support, and are left unclaimed rather than guessed.

🔴 **WHICH QUALIFIES §6.6m'S SHAPE, THE DAY AFTER §6.6v RESTORED IT.** Joost
ruled for *"one cell, several verbs, a selector"*. The cell is right and the
selector is not there: **`LOAD`, `MERGE` and `BLOAD` are INDISTINGUISHABLE at the
crossing** — same cell, same `DE`, same `HL`. The reference does not pass a verb.
It opens file buffer 0 in a MODE, and the verb-level difference is carried by
WHICH OTHER CLAIMED CELL is entered (`$FE76` for the tokenised-program path,
§6.6v) and by what main does around the call.
➡️ **For step 9 that is cheaper than a selector, not dearer:** the shared entry
needs a mode byte, not a verb dispatch, and the per-verb work stays where it
already is.

⚠️ **WHAT IS STILL OPEN.** `$0080` for `SAVE` against `$0002` for `OPEN FOR
OUTPUT` is unexplained — two writes, two codes. And `BC`/`IX`/`IY` are unread.
Neither blocks the shape.

🔴 **CLEAN ROOM.** RAM and registers at a breakpoint on a RAM address in the
published hook table. No ROM byte read, no hook target followed, nothing
single-stepped into ROM, nothing disassembled. A register value is printed only
when it cannot be a reference-internal address — a scalar below `$0100`, or a
pointer into RAM; anything in page 0 or 1 is reported as differing and no more.

### 6.6x 🟢 THE INPUT SURFACE IS 38 CELLS, AND 36 OF THEM ARE SHARED BY READ AND WRITE (D-DISKREAD, 2026-09-19)

§6.6w measured what main HANDS the disk side at `$FE5D`. This measures what the
disk side FETCHES for itself once control has crossed — the other half of the
input contract, and the surface a faithful `disk.rom` would have to read the same
way. `scratchpad/diskreads_probe.py`.

🎯 **THE METHOD.** A `read_mem` watchpoint over `$F380..$FFFF`, armed between
the `$FE5D` entry breakpoint and its exit at cell+4, recording each read's
address and the REGION its reader's PC falls in, then keeping the reads whose
reader is the DISK ROM. Addresses are deduplicated, so the result is a SET with a
hit count rather than a transcript.

🔴 **SEVEN CONTROLS, ALL GREEN.** The watchpoint fires (15.0 M times in the
band, so silence would have been a fault and not a finding); reads occur both
inside the window (3436) and outside (15.0 M), so the "during the crossing"
qualifier is earned; the reader classifier produces three distinct regions, so no
row is a tautology; **SP at the crossing is OUTSIDE the band**, so these are
work-area reads and not push/pop traffic wearing a work-area address; the log
ceiling was NOT reached, so the set is complete rather than a prefix; the quiet
case produces nothing; and **two runs of one case give an identical hit map**, so
a cell present in one verb and absent in another is a difference between the
VERBS.

🟢 **THE ANSWER: 38 DISTINCT CELLS FOR `LOAD`, 36 FOR `SAVE`, 36 OF THEM
SHARED.** `LOAD` adds exactly two (`$F5BE` and `$FCAE`, one read each) and `SAVE`
adds none. Both verbs make **480** disk-side reads in the band.

| cells | `LOAD` | `SAVE` | what the bytes say |
|---|---|---|---|
| `$F568..$F574` (13 B) | ×25 | ×25 | identical in both verbs and both files — **not** the argument |
| `$F864..$F870` (13 B) | ×48 | ×46 | 🔑 **the file name**: `..S       BAS` / `..T       BAS` |
| `$F85F..$F861` (3 B) | ×3 | ×3 | — |
| `$FB21..$FB22`, `$FB29` | ×63, ×45 | ×63, ×45 | read repeatedly through the transfer |
| `$FCC4`, `$FCC8` | ×96 each | ×97 each | the hottest pair |
| `$FD73..$FD74` | ×102 | ×104 | a word, read repeatedly |
| `$F5BE`, `$FCAE` | ×1 each | — | the only `LOAD`-only cells |

🔑 **AND TWO INDEPENDENT MEASUREMENTS MEET.** §6.6w recorded `BC = $F871` at the
crossing for `LOAD`, `MERGE` and `SAVE` — **exactly one past the end of the
`$F864..$F870` name block** this probe finds the disk side reading. Neither
measurement knew about the other: one compared registers across verbs, the other
watched memory reads and rendered their contents. The name is identified by what
is THERE, not by a work-area label this tree has no table for.

⚠️ **`$F568..$F574` IS NOT THE ARGUMENT, THOUGH IT LOOKS LIKE A NAME FIELD.**
Its 13 bytes are IDENTICAL for `LOAD"S.BAS"` and `SAVE"T.BAS"`, so whatever it
holds does not track the file. It is read 25 times either way and is left
uninterpreted rather than guessed — the same discipline `$F41F` earned in §6.6w.

⚠️ **SCOPE, STATED SO THE NUMBER IS NOT OVER-READ.** This is the SHARED WORK
AREA only. The disk ROM's own private RAM below `$F380` is excluded BY DESIGN:
that is its internal state, not the interface. "38 cells" is the size of the
boundary, not of everything the disk side touches.

🔎 **AND A NOTE FOR §6.6v'S OPEN QUESTION.** Inside the window the readers are
DISK (480), RAM (876 — the inter-slot stubs) and **MAIN-P0 (2080)**, with **no
MAIN-P1 reads at all**. Main page-0 code running during the crossing is fully
explained by the 60 Hz interrupt handler, which lives there — so "main code runs
inside the window" is NOT by itself evidence that the disk side handed control
back. The `$A8` discriminator is still the thing that would settle it.

🔴 **CLEAN ROOM.** RAM addresses, RAM contents and the slot-select state, at a
breakpoint on a RAM address in the published hook table. No ROM byte read, no
hook target followed, nothing single-stepped into ROM, nothing disassembled. PC
is never printed — only the region it falls in.

### 6.6y 🟢 THE RETURN DIRECTION — AND PART OF THE PROTOCOL RUNS FROM RAM (D-DISKWRITE, 2026-09-19)

§6.6w measured what main hands over, §6.6x what the disk side fetches. This is the
return direction, asked as two deliberately redundant questions:
**(a)** what does the disk ROM WRITE during the crossing, and **(b)** what has
CHANGED by the time main gets control back. `scratchpad/diskwrites_probe.py`.

🔴 **THEY ARE NOT THE SAME SET, AND THAT IS THE POINT.** A cell the disk side
writes and then restores appears in (a) and not in (b). A cell changed by a
writer in another region appears in (b) and not in (a). Reporting one alone would
silently pick a side.

| | `LOAD` | `SAVE` |
|---|---|---|
| (a) cells the DISK ROM wrote | **22** (22 writes — each cell exactly once) | **16** (16 writes) |
| (b) cells CHANGED across the crossing | **34** | **11** |
| in both | 13 | 9 |
| written by DISK, unchanged on return | 9 | 7 |
| changed, not written by DISK | 21 | 2 |

🔑 **AND IT RESOLVES THE BLOCK §6.6x DELIBERATELY LEFT UNNAMED.**
`$F568..$F574` was read 25 times during the crossing with contents identical
across verbs AND files, so §6.6x refused to call it the argument. It is an
**OUTPUT**: the disk side writes all 13 bytes, and across the crossing it goes
from stale (`".` …) to **`.S       BAS`** for `LOAD"S.BAS"` and **`.T       BAS`**
for `SAVE"T.BAS"`. It was read so often because it is written and then re-read.
🎯 **So the two 13-byte blocks are an input/output PAIR:** main supplies the name
at `$F864..$F870` (§6.6x, with `BC = $F871` one past it) and the disk side
publishes a resolved copy at `$F568..$F574`. Both are drive byte + 8.3 name + one
trailing byte.

🔴 **AND PART OF THE PROTOCOL EXECUTES FROM RAM.** The classifier reports three
writer regions inside the window — DISK, MAIN-P0 and **RAM** — and RAM is not
incidental: `$F5B3..$F5BD` (eleven of the twelve bytes of a THIRD copy of the
name, which reads `.S       BAS` on return) plus `$F5C2`, `$F5C4` and
`$F5CA..$F5CD` are written by code whose PC is in pages 2-3. The disk ROM itself
wrote only `$F5B2`, the byte before them. ⚠️ **What that RAM-resident code IS is
not measured and is not guessed here** — only that it is neither the disk ROM
page nor main ROM. It matters for step 9 because a faithful implementation may
need RAM-resident code of its own, and nothing in this project's design has
assumed that.

🟢 **THE INTERRUPT ACCOUNTS FOR THE REST, AND IT WAS PREDICTED.** `$FC9E` and
`$FCA2` change in BOTH verbs and are written only from MAIN page 0 — `$FC9E` is
the documented JIFFY timer, and §6.6x had already noted that main page-0 activity
during the window is explained by the 60 Hz handler living there. A prediction
made in the previous section, borne out here without being fitted to it.

🔴 **EIGHT CONTROLS, ALL GREEN — AND ONE OF THEM IS THE INSTRUMENT'S OWN
HONESTY.** 🆕 **K17: every cell whose content changed has a recorded writer —
zero orphans, in both verbs.** If a cell had changed with no writer logged, the
watchpoint would have a blind spot, half (a) would be incomplete, and every "the
disk side does not write this" reading would be unfounded. It is the control that
licenses the (a)-versus-(b) comparison at all. The others are carried from
D-DISKREAD: the watchpoint fires (327 k writes in the band), writes occur inside
(1267) and outside (326 k) the window, three distinct writer regions, SP outside
the band, the ceiling not reached, the quiet case empty, and **two runs of one
case agreeing in BOTH halves**.

⚠️ **SCOPE, as in §6.6x.** The SHARED work area `$F380..$FFFF` only. The disk
ROM's private RAM below `$F380` is excluded by design — internal state, not
interface.

🔴 **CLEAN ROOM.** RAM addresses, RAM contents and the slot-select state, at
breakpoints on RAM addresses in the published hook table. No ROM byte read, no
hook target followed, nothing single-stepped into ROM, nothing disassembled. PC
is never printed — only the region it falls in.

### 6.6z 🔑 THE RAM-RESIDENT CODE IS LOCATED, SIZED AND DATED — THE DISK ROM INSTALLS IT AT BOOT (D-RAMCODE, 2026-09-19)

§6.6y found that part of the crossing executes from RAM and deliberately did not
guess what it was. `scratchpad/ramcode_probe.py` locates it.

🎯 **AN EXECUTION DETECTOR, NOT A DATA-ACCESS ONE.** `openmsx-probing-toolbox.md`
§1 records that a `read_mem` watchpoint fires on the Z80 OPCODE FETCH as well as
on data reads, and that PC at that moment is the executing instruction. So
`wp_last_address == PC` selects FETCHES and rejects data reads. The earlier
probes recorded PC at data accesses, which only ever sampled instructions that
happened to touch the watched band; this samples execution itself.

🔴 **TWO CONTROLS WITH KNOWN ANSWERS ARE WHAT MAKE THE REST READABLE.** `$FE5D`
holds `F7` and every probe in this arc has watched it execute — it IS in the
executed set. `$F864..$F870` is the name block the disk side READS and never runs
(§6.6x) — it is ABSENT. One would catch a detector that misses fetches, the other
one that passes data reads. Plus: the quiet case executes nothing, two runs give
an identical set, and the ceiling was not reached.

🟢 **FIVE CLUSTERS OF RAM CODE, ALL BELOW `$F380`.**

| range | span | distinct | fetches | |
|---|---|---|---|---|
| `$F1D9..$F1E1` | 9 B | 5 | **582** | the hottest |
| `$F1F4` | 1 B | 1 | 2 | |
| `$F255..$F2A3` | **79 B** | 18 | 45 | the largest |
| `$F365..$F36B` | 7 B | 4 | 196 | |
| `$F38C..$F399` | 14 B | 10 | 520 | 🔑 matches the stub `scratchpad/cf_trace.py` found empirically and labelled CLPRIM |

Plus execution inside the published hook table itself, which is expected and is
its own confirmation: `$FD9A..$FDA3` (the interrupt pair), `$FE5D` once, and
`$FFCF..$FFD4`. ⚠️ Clusters bridge gaps of up to 16 B — operands are fetched as
data and a `jr` skips forward, so a strict run would shatter one routine into
fragments. The spans are therefore an upper bound on extent, not a measured
routine size.

🔑 **AND THIS IS WHY THE EARLIER PROBES COULD NOT SEE IT.** §6.6x and §6.6y watch
`$F380..$FFFF`. Every one of these clusters is BELOW that. They reported a writer
whose region was RAM and could not say where it lived, because the region was all
they sampled.

🔴 **WHO INSTALLS THE 79-BYTE BLOCK, AND WHEN.** Watching writes to
`$F255..$F2A3` from reset:

| writer | writes | first | last |
|---|---|---|---|
| MAIN-P0 | 158 | t=0.3723 | t=0.3737 |
| MAIN-P1 | 3 | t=1.1911 | t=1.1924 |
| **DISK** | **158** | **t=3.7983** | **t=3.8034** |

79 distinct cells in ONE contiguous run, and 158 = 2 × 79 — each side writes the
whole block twice. 🎯 **The crossing itself is at t=164.0254 and the LAST write to
the range is at t=3.8034 — 160 emulated seconds earlier.** So the block is
installed once, during boot, and is **not** rebuilt per call. That timing is
measured rather than inferred: the probe logs the crossing's own timestamp
precisely so "t=3.8 looks like boot" did not have to be an assumption.

➡️ **WHAT THIS OBLIGES STEP 9 TO.** The reference's disk ROM writes **79 bytes of
RAM-resident code at boot**, and code in that block runs during a file operation.
No design in this project has assumed RAM-resident code at all. It is not a large
number, but it is a NEW KIND of cost — RAM, not ROM — and `wall-assertion-check`
covers ROM only, so nothing would have caught its absence.

⚠️ **WHAT IS NOT MEASURED.** The other four clusters' installers and install
times; whether any of the five is shared with non-disk BIOS function; and what
any of this code DOES.

🔴 **CLEAN ROOM, AND THE LINE IS TIGHTER HERE THAN ANYWHERE ELSE IN THIS ARC.**
Code sitting in RAM is reference ROM content that has merely been RELOCATED, so
reading its bytes would be reading the reference. This section reports an address
RANGE, a SIZE, the REGION of each writer and the emulated TIME. Not one byte of
that code was read, disassembled or single-stepped.

### 6.6aa 🔴 THE OPEN QUESTION WAS AN ARTEFACT OF MY OWN PRINT ORDER (D-SLOTSW, 2026-09-19)

§6.6v left one thing open and §6.6x/§6.6y carried it forward: *"`$FE76` is entered
with `MAIN-P1` on top of stack BETWEEN `$FE5D`'s entry and its exit"*, with two
candidate explanations — a return into main by a non-public route, or a `jp` so
the top-of-stack is a caller's caller. **Neither is needed. `$FE76` is not inside
the window at all.**

🔴 **WHERE THE CLAIM CAME FROM.** `scratchpad/crossabi_probe.py` printed its
events as `ins + outs` — every ENTRY before every EXIT, whatever the machine
actually did. I read a control-flow ordering out of a list I had myself
concatenated by category. The probe never measured that ordering and never
claimed to.

🟢 **WHAT A TIMESTAMPED RUN SHOWS.** `scratchpad/slotswitch_probe.py` logs in
true time order: the crossing opens, the crossing shuts, and **`$FE76` is entered
at t=165.1181 with the window already SHUT**, page 1 selected to MAIN. An
ordinary main-side step after the crossing returns — nothing to explain.

🔑 **AND AN INDEPENDENT INSTRUMENT AGREES.** Watching writes to port `$A8`
inside the window, the page-1 selection changes exactly three times:
**`0-0` → `3-1` → `0-0`** — MAIN, then the DISK ROM, then MAIN again. **Zero
`DISK → elsewhere → DISK` excursions.** The disk ROM is paged in once, stays for
the whole crossing, and is paged out at the end. Nothing hands control to main
ROM page 1 mid-crossing, by any route, public or not.
The `$A8` writers inside the window are MAIN-P0 (208) and RAM (104) — the
interrupt handler and the inter-slot trampolines, both of which switch slots and
restore them, which is why they do not register as excursions.

🔴 **FOUR CONTROLS, INCLUDING A KNOWN-ANSWER PAIR.** At the crossing's entry
page 1 must read MAIN — §6.6v measured main page 1 as the caller — and it does;
page 1 must be selected to the disk ROM somewhere inside the window, because
§6.6u measured the disk ROM running the sector loop there — and it is. One arm
would catch a decode that is wrong in each direction. The quiet case records
nothing, and two runs give an identical sequence.
⚠️ The first run failed the MAIN arm because openMSX renders a NON-EXPANDED
slot's secondary as the literal `X` and the readout said `0-X`. The control was
right and the formatter was wrong — a fact already recorded once in this arc and
re-broken here.

⚠️ **WHAT THIS DOES NOT SAY.** `$A8` traffic proves which ROM is VISIBLE, not who
is executing; an inter-slot trampoline switches slots too. The verdict is stated
in terms of page-1 visibility, which is what was measured.

➡️ **SO §6.6v'S OPEN ITEM IS CLOSED AND THE ANSWER IS "NO HAND-BACK".** The
crossing is one handover, control stays on the disk side for its whole duration,
and `$FE76` is a main-side step that follows it. §6.6u's "no disk→main crossing at
either public inter-slot entry" needed no widening after all — but it stays
scoped as written, because visibility and execution are different claims.

### 6.6ab 🔑 `DE` IS THE MSX OPEN-MODE CODE, AND `$0080` BELONGS TO EXACTLY ONE VERB (D-MODECODE, 2026-09-19)

§8.9 left open why `SAVE` passes `$0080` where `OPEN…FOR OUTPUT` passes `$0002` —
two writes, two codes. Ten verbs through `scratchpad/crossabi_probe.py` settle the
first half and sharpen the second.

🔴 **A PREDICTION WAS STATED BEFORE THE RUN AND SCORED 1 OF 3.** §8 had already
shown that FORMAT is carried by WHICH CELL is entered (`$FE76`, the binary-format
program path), so the prediction was that `DE` is a mode code and ASCII-ness is
carried elsewhere:

| case | predicted | measured | |
|---|---|---|---|
| `OPEN…FOR APPEND` | `$0008` | **`$0008`** | ✅ hit |
| `BSAVE` | `$0080` | **`$0002`** | ❌ miss |
| `SAVE"…",A` | `$0080` | **`$0002`** | ❌ miss |

🟢 **THE HIT COMPLETES A SET.** Adding random access (`OPEN "f" AS #n`, which has
no `FOR` clause) gives **all four classic MSX open-mode codes**, measured:

| `DE` | mode | verbs that pass it |
|---|---|---|
| `$0001` | INPUT | `LOAD`, `MERGE`, `BLOAD`, `OPEN…FOR INPUT` |
| `$0002` | OUTPUT | `OPEN…FOR OUTPUT`, **`BSAVE`**, **`SAVE"…",A`** |
| `$0004` | RANDOM | `OPEN "f" AS #n` |
| `$0008` | APPEND | `OPEN…FOR APPEND` |
| `$0080` | — | **tokenised `SAVE`, and nothing else** |

🔴 **AND THE MISSES ARE WHAT PRODUCED THE RIGHT MODEL, AGAIN.** `$0080` is NOT
"a write" — three other writes use `$0002`. It is NOT "binary" — `BSAVE` writes a
binary image through plain OUTPUT. It is NOT "not-ASCII" in any general sense —
`BLOAD` reads binary through plain INPUT. Among ten operations it is used by
**exactly one**: the tokenised program `SAVE`. Bit 7, disjoint from the low mode
bits, for the single operation that does not open an ordinary channel.
⚠️ **WHAT `$0080` MEANS IS NOT DETERMINED BY THESE TEN POINTS** and is not named
here. What IS determined is the shape: a four-value mode code plus one out-of-band
value, and the out-of-band one is the tokenised save.

🟢 **TWO MORE REGISTERS FIRM UP ON THE WIDER SET.** `HL` partitions cleanly and
now across ten verbs rather than six: **`$DC65` for every program verb**
(`LOAD`/`MERGE`/`SAVE`/`SAVE,A`/`BLOAD`/`BSAVE`) and **`$DD6E` for every `OPEN`
channel** (INPUT/OUTPUT/APPEND/RANDOM). And `BC` is identified for one verb by
correspondence with an input I chose: for `BSAVE"X.BIN",&HD000,&HD00F` it reads
**`$D000`** — the start address as typed. For the name-taking program verbs it is
`$F871`, one past the name block (§6.6x). `AF` remains invariant across every
verb; `IX` is still uninterpreted.

🔴 **AND ONE CASE FAILED FIRST, WHICH IS WHY THE PROBE NOW SHOWS ITS SCREEN.**
`OPEN…FOR APPEND` on a file that does not exist is an error, and the erroring run
reported `$FE5D` entered and never returning through the cell — **exactly the
signature of a genuine one-way handover** (§6.6v's `$FE76`). Seeding `Z2.DAT` onto
the image made it pair, which confirms the cause by construction. The probe now
prints enough of each case's screen that a failure is visible rather than
inferred, and flags any case whose screen contains an error word. Without that,
a failed case contributes a register row that looks exactly like data.

### 6.6ac 🔑 FOUR OF THE FIVE RAM CLUSTERS ARE THE DISK ROM'S; THE FIFTH IS THE BIOS'S (D-RAMCODE round 2, 2026-09-19)

§6.6z traced the installer of the 79-byte block and left the other four
unmeasured (§8.9). `scratchpad/ramcode_probe.py` phase 2 now watches **all five
ranges under ONE boot** — so the install times are directly comparable rather than
read off five timelines that only happen to start alike — and the run is repeated.

| cluster | span | writers, in time order | disk-installed? |
|---|---|---|---|
| `$F1D9..$F1E1` | 9 B | MAIN-P0 ×18 @0.380 · **DISK ×18** @3.797–6.911 | ✅ |
| `$F1F4` | 1 B | MAIN-P0 ×2 @0.380 · **DISK ×2** @3.797–6.911 | ✅ |
| `$F255..$F2A3` | **79 B** | MAIN-P0 ×158 @0.372 · MAIN-P1 ×3 @1.191 · **DISK ×158** @3.798 | ✅ |
| `$F365..$F36B` | 7 B | MAIN-P0 ×14 @0.368 · **DISK ×20** @3.802–14.003 | ✅ |
| `$F38C..$F399` | 14 B | MAIN-P0 ×42 @0.368–0.619 · MAIN-P1 ×14 @1.189 | ❌ **no DISK writer at all** |

🔑 **AND THE ONE THE DISK ROM DOES NOT WRITE IS EXACTLY THE ONE INDEPENDENTLY
IDENTIFIED AS BIOS INFRASTRUCTURE.** §6.6z noted that `$F38C..$F399` matches the
stub `scratchpad/cf_trace.py` located empirically and labelled CLPRIM — the
inter-slot call primitive. Two measurements that knew nothing of each other agree:
one found the range by matching an old probe's note, the other found it by being
the only cluster with no disk-side writer.

➡️ **SO THE DISK ROM'S RAM OBLIGATION IS FOUR CLUSTERS AND ~96 B OF SPAN**
(9 + 1 + 79 + 7), not the ~110 B across five that §6.6z's list implied. The 14-byte
inter-slot stub is the BIOS's and a faithful `disk.rom` inherits nothing for it.

🟢 **EVERY CLUSTER IS INSTALLED BEFORE THE CROSSING AND NONE IS REBUILT PER
CALL.** The crossing is at t=164.0254; the latest write to any cluster is
t=14.0034. ⚠️ Two clusters are written more than once during boot — `$F1D9` and
`$F1F4` up to t≈6.91, `$F365` up to t≈14.00 — so "installed at INIT" is too
narrow: the disk side touches them again later in the boot sequence. What is
measured is that all of it precedes the first file operation by a wide margin.

🔴 **CONTROLS.** Two runs agree on every cluster's writers and counts. A
per-cluster POSITIVE arm refuses to read an unwritten range as "never installed"
— it would be a watchpoint that did not fire, and these must not print the same
way (silence is not evidence). The crossing's own timestamp is logged, so
"before the crossing" is a comparison and not an assumption about when typing
starts.

🔴 **CLEAN ROOM.** Ranges, sizes, writer regions and emulated times only. Not
one byte of any cluster was read, disassembled or single-stepped — code sitting in
RAM is relocated reference content, and reading it would be reading the reference.

### 6.6ad 🔑 `IX` IS A VERB-FAMILY SELECTOR, AND IT QUALIFIES §8.2 (D-IXFAM, 2026-09-20)

`IX` was the last unnamed item in §8.9. It had printed `differs` in every case,
which says only that its value sits in page 0 or 1. **"Differs across the set" was
the wrong question.** Grouping the ten verbs by EQUAL VALUE — which prints no
address and is therefore safe for a page-1 register — asks the decisive one.

🟢 **`IX` TAKES EXACTLY THREE VALUES, ALL IN PAGE 1, AND THEY PARTITION THE VERBS
BY FAMILY:**

| class | verbs |
|---|---|
| BASIC-program file | `LOAD`, `MERGE`, `SAVE`, `SAVE"…",A` |
| `OPEN` channel | `OPEN…INPUT` / `OUTPUT` / `APPEND` / `RANDOM` |
| binary image | `BLOAD`, `BSAVE` |

Invariant across files (the four-load arm already showed that), identical across
two runs, and page 1 at that instant is MAIN (§6.6aa measured the page-1 selection
as `0-0` at the crossing's entry). **So `IX` is a main-ROM page-1 pointer chosen by
verb family.** ⚠️ What it points AT is inside the reference's ROM and was not
read; "a per-family vector" is the obvious reading and is NOT asserted here.

🔴 **AND THIS QUALIFIES §8.2's "THERE IS NO VERB SELECTOR".** That sentence rests
on `LOAD`, `MERGE` and `BLOAD` arriving with the same cell, the same `DE` and the
same `HL` — all three still true. But two registers DO separate `BLOAD` from
`LOAD`/`MERGE`:

| register | classes over the ten verbs | separates `BLOAD`? |
|---|---|---|
| `HL` | 2 — program-file vs channel | ❌ shares with `LOAD`/`MERGE` |
| `DE` | 5 — the open-mode codes (§6.6ab) | ❌ shares (`$0001`) |
| **`IX`** | **3 — by family** | ✅ binary image is its own class |
| **`BC`** | **4** | ✅ `$0000` for `BLOAD`, the start address for `BSAVE` |

➡️ **The precise statement is narrower and stronger than §8.2's:** **no measured
register separates `LOAD` from `MERGE`** — they are identical in `AF`, `BC`, `DE`,
`HL`, `IX` and `IY`. `BLOAD` is NOT in that position; it is separated by family in
`IX` and individually in `BC`. What the crossing lacks is a verb code, not all
discrimination.

🔑 **AND THE THREE REGISTERS AGREE ON ONE STRUCTURE, AT THREE RESOLUTIONS.** `HL`
splits program-file from channel (which buffer); `IX` splits program-file from
channel from binary image (which family); `BC` splits the same way and then
separates the binary pair, carrying `BSAVE`'s start address as typed (§6.6ab).
Three registers, one nested partition, measured independently.

⚠️ **`IY` STAYS UNNAMED.** It groups `{BLOAD, every OPEN}` against
`{LOAD, MERGE, SAVE, SAVE,A}` with `BSAVE` alone — a third partition that matches
neither of the others and that nothing in these ten points explains.

🔴 **CLEAN ROOM.** The partition is printed as verb groupings and page numbers.
No page-0 or page-1 address was printed, no target was followed, nothing was read
from ROM. That is what made a page-1 register reportable at all.

✅ **§8.9 IS NOW EMPTY** and the measurement arc is complete.

### 6.6ae 🔑 A SECOND VENDOR: §8 IS THE MSX STANDARD, NOT A NATIONAL QUIRK (D-2VENDOR, 2026-09-20)

Everything in `expansion-protocol.md` §8 was measured on ONE disk ROM — the
National CF-3300 — and §6.7's ruling commits us to copying it. Joost supplied the
**Philips NMS 1200** ROM (*"2DD Micro Floppydisk Drive"*, 720K like our media),
which runs on a stock **VG-8020**: a real machine combination, and a genuinely
independent implementation. The same probes, the same cases and the same readers
were pointed at it.

🔴 **A PREDICTION WAS STATED BEFORE THE RUNS AND SCORED 2 OF 4.**

| prediction | measured | |
|---|---|---|
| the crossing cell matches | `$FE5D`, claimed, 1 in / 1 out on both | ✅ |
| the open-mode codes match | byte-identical, every verb | ✅ |
| the claimed-cell COUNT differs | **identical: 35 of 118, the SAME cells** | ❌ |
| the RAM-cluster ADDRESSES differ | **identical addresses and spans** | ❌ |

🎯 **Both misses run the same way: I underestimated how standardised this is.**

🟢 **WHAT IS IDENTICAL, VENDOR TO VENDOR.** The claimed set — 35 cells, National
only: none, Philips only: none. The crossing at `$FE5D`, pairing entry with exit
in all thirteen cases. `DE`'s open-mode codes (`$0001`/`$0002`/`$0004`/`$0008`
and `$0080` for tokenised `SAVE` alone). `BC`'s four-class partition including
`$F871` one past the name block and `BSAVE`'s start address. `IX`'s three-class
family partition, `IY`'s. And the five RAM-code clusters, at the same addresses
with the same spans.

🔴 **WHAT DIFFERS — EXACTLY ONE THING, AND IT MATTERS FOR IMPLEMENTATION.** `HL`,
the file buffer, reads `$DC65`/`$DD6E` on the National and **`$DC67`/`$DD70` on
the Philips** — a constant **+2**, with the same two-class partition either side.
⚠️ **So those addresses are per-machine, not constants, and §8.2 stated them as if
they were.** A faithful implementation must take the buffer pointer from `HL`
rather than hardcode a value; that is now corrected in §8.2.

⚠️ **TWO READINGS OF THE SAMENESS, AND THIS MEASUREMENT CHOOSES NEITHER.** Two
independent vendors putting RAM code at identical addresses is consistent with
the MSX standard fixing that layout, and equally with both deriving from one
Microsoft/ASCII reference implementation. For our purposes the consequence is the
same — it is the standard behaviour rather than one maker's choice — and the cause
is not measured.

➡️ **WHAT IT CHANGES FOR THE RULING.** *"We do as the reference does"* is on much
firmer ground: **the reference** turns out to mean MSX, not National. And §6.7's
row 8 gets heavier rather than lighter — RAM-resident code at those addresses is
not a CF-3300 implementation detail we could decline to copy; two independent
disk ROMs do the same thing in the same place.

🔴 **CONTROLS ON A VENDOR NEVER MEASURED BEFORE.** There is no honest a-priori
answer for an unmeasured machine, so the census carries a **structural two-sided
check** — a reader stuck on `F7` claims every slot, one stuck on `C9` claims none,
and both produce a plausible table. `$FFA7` (HPHYD) is the one cell §2 lets us
demand in advance. The execution detector kept its known-answer pair (`$FE5D`
must appear, the read-only name block must not), both green on the new machine,
and two runs give an identical executed set.
⚠️ One arm was found INERT and is labelled as such rather than counted: the
"no slots read" check is subsumed by "nothing is claimed" for verdict purposes,
and a mutation deleting it stays green. It is kept for its message only.

🔴 **CLEAN ROOM.** Claim states (§2: slot and idiom), registers, work-area RAM,
ranges and regions. No ROM byte read on either machine, no target followed,
nothing disassembled, and not one byte of the RAM-resident code read on either.

### 6.6af 🟢 THE 18th-HOOK OBSTACLE IS DISSOLVED — THE ROW IS A PHASE METRIC AND ITS GREEN WAS LUCK (D-REARMSENS, 2026-09-20)

§6.6t parked a correlation with no mechanism and said exactly what to do about
it: *"doubt `E_rearm_under_held_key_refires` before doubting the hardware …
establish what makes IT move before attributing anything to hook installation."*
That was done. **Every arm below runs the SHIPPED ROM — no hook is installed, no
byte of `hook_tab` changes, nothing is rebuilt.**
([`scratchpad/rearmsens_probe.py`](../../scratchpad/rearmsens_probe.py))

🎯 **THE ROW READS RED ON THE UNMODIFIED BUILD AT 15 OF 20 TIMING
CONFIGURATIONS.** Shift the instant the key goes down, or shift the emulator's
boot delay, by a few milliseconds — nothing else — and the count collapses:

| knob (ROM untouched) | values |
|---|---|
| key-down at 0.300 … 0.340 s, 5 ms steps | **3**, 1, 2, 2, 1, 1, 1, 2, 1 |
| key-down at 0.34 / 0.38 / 0.42 / 0.46 s | 1, 1, 2, 1 |
| boot delay 6.000 … 6.040 s, 5 ms steps (press schedule untouched) | **3**, 1, 1, 1, 1, 1, 1, 1, 1 |

**Only the gate's own configuration is green.** The boot-offset arm is the
sharpest: of nine offsets spanning 40 ms, `boot=6.0` — the value
`basic_probe_stop_trap.run` defaults to — is the only one that scores above the
threshold, and every other offset reads 1.

🔴 **AND IT IS NOT A FLAKE, WHICH MATTERS AS MUCH.** Six identical runs at the
gate's own schedule all read 3; three runs with the row's literal 200 s hold all
read 3; every phase point read the same value on repeat. The metric is perfectly
DETERMINISTIC and pinned to the schedule — so §6.6t's nine builds were measuring
something real, just not hooks. The correlation and the determinism were never in
conflict.

🟢 **THE CONTROLS, AND THE REFERENCE IS THE ONE THAT SETTLES IT.** The same fine
sweep on the VG-8020 reads **122, 122, 122, 122, 122, 122, 122, 122, 121** — a
±1 wobble on 122, 0.8 %. So the instrument reads a large, phase-STABLE number
where one exists, and the fragility is zerobas's, not the probe's. The negative
control (same program, trap disarmed) reads 0 twice while still gating
`ran`/`done`, so the counter can produce a zero.

➡️ **SO THE OBSTACLE TO STEP 9 IS REMOVED — BY DISQUALIFICATION, NOT BY
EXPLANATION.** What an 18th installed hook does to the machine's sub-frame phase
is still not established, and this section does not guess at it. ⚠️ **§6.6ag
narrows it the same day:** installed and swept, the two builds read IDENTICALLY
at 8 of 9 key-down phases and differ only at the gate's own — so the effect is
confined to a knife-edge point, not spread across the phase space. It does not have
to: a row whose green depends on one schedule value, and which the unmodified ROM
fails at three quarters of nearby ones, cannot carry the claim *"our disk ROM
cannot install an 18th hook."* **That claim is withdrawn.** §6.6t's evidence —
identical hook-entry counts, identical interrupt totals, identical work, reds and
greens independent of which cells — always fitted "the measurement moved" better
than "the Z80 did"; it now has the direct demonstration it lacked.

🔴 **AND DOUBTING THE ROW FOUND SOMETHING WORSE THAN A FRAGILE GATE: A REAL
DIVERGENCE IT HAS BEEN HIDING.** The row asserts a PROPERTY — *flag ≥ 2*, i.e.
"a handler that re-arms itself under a held key fires again **at all**". At every
timing configuration but a handful, zerobas answers **1**: it fires once and
never again, while the reference fires 122 at every phase. **zerobas does not
implement the property the row exists to pin**, and the row has been green since
it was written because its fixed schedule happens to land on a phase worth two
extra fires. The count does not scale with how long the program runs either
(`FOR I=1TO` 1500 / 3000 / 6000 / 12000 → 2, 2, 3, 3), which is what an
edge-latched model predicts and a per-scan model does not — consistent with
zerobas latching Ctrl-STOP into PENDING (the T2 STRIG model adopted when
STOPGRACE was removed) against the reference re-latching on every keyboard scan.
Filed as its own TODO item; it is a BASIC-fidelity defect, not a disk one, and it
must not be "fixed" by loosening the threshold.

⚠️ **WHAT THIS DOES NOT LICENSE.** The gate is still GREEN and is left untouched
here: rewriting it is a design step (what should it assert, given the property is
absent?) and belongs with the divergence, not with this measurement. Until then,
**no step-9 work may cite `E_rearm_under_held_key_refires` as evidence in either
direction** — neither as an obstacle nor as a clearance.

### 6.6ag 🔬 THE 18th HOOK WAS INSTALLED AND RUN AGAINST A FULL BATTERY — ONE ROW, ONE POINT (D-REARMSENS round 2, 2026-09-20)

§6.6af withdrew the obstacle by disqualifying the row. The obvious next question
is whether that licenses the install, so the install was done: `dw H_FOPEN,
hk_dpload` back in `hook_tab`, the 16 D-DPLMOVE lines deleted from
`tools/deadcode-allow.txt`, a clean build, and `make gates-full`. **It is
reverted again — but for a different reason, and the difference is the finding.**

🟢 **THE DEAD-CODE CANARY WORKED EXACTLY AS ITS OWN NOTE PROMISED.** Those 16
entries each said *"DELETE THESE LINES when the hook lands: the gate will then
report them as no-longer-dead, which is the canary working."* With the row in,
**15 of the 16 went live** and exactly **one** stayed dead — `fat_io_open`, and
for a reason that was already written one line above it: `hk_dpload` calls
`fat_mount` and `fat_io_find` SEPARATELY, because their two carries are what tell
`file not found` from a mount/I-O fault (D-BLNF), which is the whole reason
`fatio-body.inc` carries the zero-byte `fat_io_find` label. The combined entry
`fat_io_open` is main's. That one entry is now allowlisted with the HONEST
reason instead of the retracted §6.6p one.

🔬 **THE BATTERY: 129/132, AND ONLY ONE RED IS REAL.**

| red | what it is |
|---|---|
| `stop-trap-acceptance` | the predicted casualty — `E_rearm_under_held_key_refires` |
| `selftest-check` | `tier_table.py --selftest` |
| `tiers-md-check` | `tier_table.py` |

The last two are ONE cause and it is bookkeeping, not behaviour: a ROM change
invalidates the knife pin, and `tier_table.py` **refuses** until
`kwknife.py --all` and `--allfn` are re-run — it names the old and new ROM hashes
and says so. Everything else — all 89 emulator targets, `diskbasic`, `bdos`,
`fat-*`, `nodisk` — passed with an 18th hook installed.

🎯 **AND THE SYMMETRIC MEASUREMENT IS SHARPER THAN §6.6af's, SO IT NARROWS IT.**
The same 5 ms key-down sweep, run against BOTH builds:

| key-down | 17 hooks | 18 hooks |
|---|---|---|
| 0.300 s | **3** | **1** |
| 0.305 | 1 | 1 |
| 0.310 | 2 | 2 |
| 0.315 | 2 | 2 |
| 0.320 / 0.325 / 0.330 | 1 | 1 |
| 0.335 | 2 | 2 |
| 0.340 | 1 | 1 |

**The profiles are identical at 8 of the 9 points.** They differ at exactly one —
`0.300`, which is the schedule the gate uses. The boot-offset sweep says the same
thing from the other side: the 18-hook build reads 1 at all nine offsets
including `6.000`, where the 17-hook build reads 3 and 1 everywhere else.

➡️ **SO THE PICTURE IS NOT "THE PHASE SHIFTED" — IT IS "THE GATE SITS ON A
SPIKE".** `0.300` is a singular point where the 17-hook build produces two extra
fires its own neighbours do not; an 18th hook flattens that one point and changes
nothing else anywhere measured. §6.6af's conclusion stands and is strengthened —
the row cannot carry a claim about hooks — but its open question is now narrowed:
whatever the 18th hook perturbs, its effect is confined to a knife-edge, not
spread across the phase space. **Note also that the 18-hook build still PASSES
the row at three of nine phases (0.310, 0.315, 0.335).** There is no build here
that is robustly green and none that is robustly red.

🔴 **WHICH IS WHY THE ROW IS NOW THE BLOCKER, AND IT IS ORDINARY WORK.** It has
no robust green to return to, on either build, because the property it asserts is
not implemented: zerobas answers **1** — it does not re-fire under a held key at
all — where the reference answers 122 at every phase. Fix that divergence and the
row stops balancing on a spike; then the `hook_tab` row goes back in as the
one-line change it is. **The obstacle to step 9 is no longer a mystery about
hooks; it is a known defect in the STOP trap with a measured oracle.**

⚠️ **THE COST OF THE ROW, FOR WHOEVER LANDS IT:** 4 B of `hook_tab` and the
5-byte RAM stub `install_hook` writes. Measured with the row installed on
2026-09-20, `disk.rom` had **8113 B** free in 29 runs — re-run
`make basic-reloc`, never quote that figure.

## 6.7 🔍 GAP ANALYSIS — zerobas AGAINST THE MEASURED PROTOCOL (D-HOOKCENSUS, 2026-09-19)

> 🏗️ **RULED BY JOOST, 2026-09-20: *"I think the answer to Two is obvious: we do
> as the reference does."*** The gap table below was put in front of him to
> decide, and this is the decision. **The FAT12 engine and the loader's sector
> loop move OUT of main and INTO `disk.rom`**, so that mount, directory search,
> FAT walk and transfer all live where the reference keeps them, reached through
> one claimed cell. Rows 2, 5 and 6 of the table are no longer open questions;
> they are the work.
>
> ➡️ **This supersedes the "clean middle path"** of
> `disk/docs/spec-diskbasic-relocation.md`, whose rejected alternative — *"move
> all disk-BASIC incl. `fat.asm`, ~5 KB, drop the interop"* — is now the chosen
> one. That spec's own escalation rule said reversing its decision must go to the
> user; it went, and this is the answer.
>
> ⚠️ **WHAT THE RULING DOES NOT BY ITSELF SETTLE.** "As the reference does" is
> about WHO OWNS WHAT, not about copying every implementation detail. The
> reference installs ~96 B of RAM-resident code at boot (§6.6ac); whether a
> faithful `disk.rom` needs its own equivalent is a separate question this ruling
> does not answer, and row 8 stays open until it is measured against a real
> design rather than assumed either way.
>
> 🔴 **AND THE FIRST STEP IS BLOCKED BY SOMETHING ELSE NOW — A KNOWN DEFECT,
> NOT A MYSTERY (§6.6ag).** The row was installed and run against a full battery
> the same day: 129/132, with the only behavioural red being
> `stop-trap-acceptance` and the other two a stale knife pin. That row has no
> robust green on EITHER build, because the property it asserts is not
> implemented. **Fixing that divergence is the unblock, and it is ordinary
> BASIC-fidelity work with a measured oracle.**
>
> 🟢 **AND THE THING THAT USED TO BLOCK IT NO LONGER DOES (§6.6af,
> 2026-09-20).** The move needs `$FE5D` claimed, and §6.6t recorded that claiming
> ANY new hook cell reddens `stop-trap-acceptance`'s
> `E_rearm_under_held_key_refires`. Its own advice was to doubt the ROW first;
> doing so showed the row reads RED on the UNMODIFIED ROM at 15 of 20 timing
> configurations and green only at the schedule the gate happens to use. **The
> obstacle is withdrawn, and no step-9 work may cite that row in either
> direction.** What it did expose is a real BASIC divergence — zerobas does not
> re-fire under a held Ctrl-STOP at all — filed separately.
>
> 🟢 **AND IT CUTS THE RIGHT WAY FOR THE DISKLESS COMBO** (Joost, same day: a
> VG-8020 plus a Philips NMS disk cartridge is a valid machine, and diskless
> zerobas plus that cartridge should work the same). With no disk implementation
> left in main+sub, a foreign cartridge's own Disk BASIC claims the hooks and
> runs — which is §0.0's point (3), reached for free rather than defended.

`disk/docs/expansion-protocol.md` §8 describes how `LOAD` works on the reference.
This is the other half: **what zerobas does, and whether the difference matters.**
Reference-side values are cited to §8; our side is either measured on our own
machine or cited to our source. ⚠️ **The table proposed no redesign** — it was
written to put the shape in front of Joost, and the ruling above is what came
back.

🔴 **AND THE HEADLINE IS THAT THE TWO ARCHITECTURES ARE INVERTED — BY AN EARLIER
DECISION, NOT BY OVERSIGHT.** The reference puts mount, directory, FAT and the
sector loop in its disk ROM and calls it once. zerobas puts the FAT12 engine and
the loop in MAIN (`basic/fat.asm`, `basic/cload.asm`) and uses the disk ROM as a
**pure sector transport** reached by `CALSLT $4010` (DSKIO). That is exactly the
committed **Depth-A** plan of `expansion-protocol.md` §4b/§5, chosen so our loader
can drive a FOREIGN disk ROM. Step 9 is the proposal to invert it back.

### The hook census, measured on BOTH machines the same way

`scratchpad/hookcensus_probe.py` reads the first byte of all 118 published slots
after boot and classifies `F7` (claimed) against `C9` (bare). Run on the
reference and on `C-BIOS_MSX1_EU_BASIC_DISK`, which wires our own `build/disk.rom`
(verified by hash, not assumed).

🔑 **The reference claims 35; we claim 18; and OUR 18 ARE A STRICT SUBSET.**
There is not one cell we claim that the reference leaves bare. The 17 it claims
and we do not are `$FD9F`, `$FE4E`, `$FE58`, **`$FE5D`**, `$FE62`, `$FE71`,
`$FE76`, `$FE80`, `$FE85`, `$FE8A`, `$FE99`, `$FE9E`, `$FEA3`, `$FEAD`, `$FEB2`,
`$FEB7`, `$FFAC`.

🔎 **AND THE CENSUS FOUND SOMETHING READING THE TABLE COULD NOT.** `hook_tab`
has 17 rows but 18 cells are installed: `$FFA7` (HPHYD) is written directly by
`disk/init.asm`, outside the table, for the PROVIDER direction so a foreign host
reaches our DSKIO. Benign and documented — but it is why the census was taken
instead of counting table rows. A table is an intention; a census is the machine.

*Controls: a two-sided known-answer pair on EACH machine — on the reference
`$FD9F` must be claimed (§2 observed its stub) and `$FE67` must not (§6.6v); on
ours `$FE7B` must be claimed and `$FE5D` must not (`disk/kernel.asm` records that
row as built and BACKED OUT). One arm alone would miss a reader wrong in the
other direction.*

### The gap table

| # | element | REFERENCE (§8) | ZEROBAS | MATTERS? | why |
|---|---|---|---|---|---|
| 1 | hook cells claimed | 35 of 118 | **18**, a strict subset of the reference's | 🟢 **NOT A GAP** | nothing we claim is claimed by nobody else; the sets are nested, not divergent |
| 2 | the file-verb crossing | `$FE5D`, claimed, once per operation (§8.2) | **not claimed at all** — `H_FOPEN` was built and backed out | 🔴 **BLOCKING** | the reference's shape has no other entry point; §6.6t's parked correlation currently reddens a row on any new claim |
| 3 | what crosses | an open MODE in `DE`, buffer in `HL`, name block via `BC` (§8.2) | per-sector DSKIO calls: drive/sector/count/buffer per MSX2 TH §5 | 🟡 **COSTS TIME** | one crossing per operation versus one per sector; §6.2c priced the arithmetic |
| 4 | verb selector | none — `LOAD`/`MERGE`/`BLOAD` indistinguishable (§8.2) | one claimed cell PER VERB | 🟢 **NOT A GAP, and cheaper than planned** | §6.6m's "selector" turns out to be unnecessary: a mode byte suffices |
| 5 | who owns the loop | the disk ROM, mount through sector transfer (§8.3) | **main** — `basic/cload.asm` `disk_prog_load`, `basic/fat.asm` | 🔴 **BLOCKING** | this IS step 9; D-DPLMOVE built the move and backed it out |
| 6 | who owns FAT/directory | the disk ROM | **main** (`basic/fat.asm`, loader-side engine over DSKIO) | 🟡 **COSTS BYTES** | the Depth-A choice — 🔴 but see the correction below: its stated justification is already assessed as theoretical |
| 7 | shared work-area contract | ~38 cells read, 22 written; two 13-byte name blocks (§8.4) | private: `DISKOP_OP`, `DISKOP_ERR`, `FAT_DBUF` and friends | 🟢 **NOT A GAP today** | we own both sides, so the contract is ours to pick; it matters only for the PROVIDER direction |
| 8 | RAM-resident code | **four** clusters the disk ROM installs, **~96 B of span** (§6.6ac); a fifth is the BIOS's inter-slot stub | **3 bytes** — `$F37D` gets `JP bdos_entry` at INIT (`disk/init.asm`) | 🟡 **COSTS BYTES IF WE INVERT** | we are not at zero, but ours is a dispatch vector for a foreign host, not logic that runs during our own load |
| 9 | hand-back during a transfer | none; page 1 goes `0-0` → `3-1` → `0-0` (§8.3) | n/a — main never leaves, so there is nothing to hand back | 🟢 **NOT A GAP** | a consequence of row 5, not an independent difference |

### What this changes about step 9

🟢 **Two things got CHEAPER.** Row 4: no verb selector is needed, so §6.6m's
shape costs a mode byte rather than a dispatch. Row 1: our claimed set is already
a subset of the reference's, so adopting `$FE5D` widens it in the direction the
reference already went rather than inventing a cell.

🔴 **Two things are confirmed BLOCKING, and they are the same slice.** Rows 2
and 5 are one change: claim `$FE5D`, move the loop below it. Row 2 is blocked by
§6.6t's parked correlation on `stop-trap-acceptance`; row 5 is the slice
D-DPLMOVE built and backed out.

⚠️ **And one thing is a genuine NEW cost nobody had priced (row 8).** RAM-resident
code is a different budget from ROM, and `wall-assertion-check` covers ROM only —
so its absence could never have been caught by a gate. We are not at zero (the
`$F37D` vector exists), but nothing in our design runs from RAM during a load.

### 🔴 CORRECTION (Joost, 2026-09-19): THE INTEROP COUNTERWEIGHT IS ALREADY DEAD

This section first justified row 6 as *"what keeps a foreign disk ROM drivable"*
and closed by calling the inversion a trade between two live directions. **Joost:
*"I thought we already let go of driving a disk ROM without basic…"*, and the
record is on his side.** `disk/docs/spec-diskbasic-hook-rearchitecture.md` §Phase 4
already settled it, quoting him on 2026-09-15:

> *"in practice I'd think any external cartridge providing a disk also provides
> disk basic"* — and earlier, *"this seems a theoretical situation"*.

and concluding that with a foreign cartridge present **its** Disk BASIC claims the
hooks and runs, whichever ROM our FAT sits in — ordinary MSX behaviour, not a loss.
**So "interop with a DSKIO-only disk ROM" describes hardware that does not exist
and is NOT a reason to keep the FAT in BASIC.** That spec further records that
`basic/fat.asm:11`'s *"disk-ROM-INDEPENDENT"* and the relocation spec's *"the
NECESSARY PRICE of the universal sector interface"* **rest on it and are
overstated**, with the correction **filed and awaiting Joost**.

🎯 **I cited those two documents' stated rationale without checking whether it
had been superseded** — and it had been, four days earlier, by the person I then
described as owing a decision on it. That is the same failure this arc keeps
paying for: treating a document's justification as current because it is written
down.

➡️ **WHAT IT CHANGES.** The inversion has **no interop counterweight**. What
still bears on where the FAT lives is the CHARTER, and only for our own primary
deployment, where our disk ROM is the one present: *we reimplement MSX1 BASIC, so
we implement its disk verbs* — the FAT is in BASIC because we wrote the verbs, not
because of interop. So rows 2 and 5 are not a trade against a second direction;
they are an ordinary cost/benefit against §6.6t's blocking correlation and the
size of the move.

⚠️ **WHAT THIS SECTION STILL DOES NOT DO.** It does not propose the inversion or
price it in bytes. And the filed correction to `basic/fat.asm:11` and the
relocation spec is still open — this section does not close it, it only stops
re-importing the claim they overstate.

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
