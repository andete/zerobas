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
| 9 | the tokenised `LOAD` loop (`dpl_*`) **+ the stream cursor `fat_io_getbyte`** — 🔴 not "already disk-only" (§6.5) and 🛑 not sufficient alone (§6.6) | ✅ **MEASURED §6.2c**, ✅ **SCOPED §6.5**, 🛑 **RE-SCOPED §6.6: the loop ALONE creates the per-byte crossing it exists to remove** |
| 10 | `OPEN`/`CLOSE` disk arms + the channel write-back manager | needs 8 |
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
| `disk.rom` free, 2026-09-19 | **8324 B in 29 runs**, from 8435 B — the layer cost **111 B** |
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
