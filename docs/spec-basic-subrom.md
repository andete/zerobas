<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — zerobas sub-ROM (Phase-3 space-strategy arc)

> **Adding the next tenant?** This spec is the *architecture*; the reusable
> *how-to* (decision tree + ABI recipe + gates) is
> [subrom-tenant-playbook.md](subrom-tenant-playbook.md). Start there.

Status: **SIGNED OFF 2026-07-11** — the §9 open questions are answered
(name = `zerobas-sub`; size = **32 KB, both pages up front**; absence error
reuses *"Illegal function call"*; D-1…D-11 otherwise as proposed).

> **AMENDMENT 2026-07-11 (S2 open, user-ratified) — D-2 slot map revised.**
> On re-examining compatibility for non-sub-slot-aware MSX1 software, the
> map is changed to **3-0 = RAM (UNCHANGED), 3-1 = disk (unchanged), 3-2 =
> zerobas-sub (NEW), 3-3 = empty** — i.e. the sub-ROM takes an *empty* subslot
> and **RAM does not move**. Rationale: the compatibility cliff for a program
> that pokes only `$A8` (never selects a subslot) is *expanded-vs-unexpanded*
> slot 3, which the disk machine already crossed; the RAM subslot *index*
> (0 vs 3) does not discriminate — both break the same naive programs
> identically. So the 3-0-vs-3-3 choice was only ever a faithfulness-vs-risk
> call, and keeping RAM in 3-0 (a) **eliminates R1 / §3e entirely** (no
> `$83→$8F` RAM-slot-id change, no disk/BDOS anchor re-baseline) and (b) is
> marginally *safer* for naive code (RAM stays in the reset-default subslot 0).
> The only cost is the 3-0-sub-ROM convention + HB-F700D homage (§8a). The
> sub-ROM slot id is now **`$8B`** (3-2 expanded); RAM keeps **`$83`**. All of
> §3a / §3e / §8-R1 / D-2 / §9-Q5 below are read under this amendment. The ABI
> (§3b/§3c) is unaffected — it depends only on the sub-ROM being a page-0 `CD`
> ROM *somewhere* in expanded slot 3, which `init_ext_roms` discovers by
> scanning all four subslots.
>
> **Reading the body under this amendment:** everywhere §3b–§3g below says
> "slot 3-0" or "3-0 pg0 / pg1" as *the sub-ROM's subslot*, read **3-2**; the
> opposite-island / placement architecture is subslot-index-independent, so the
> prose stands as written with only the number changed. "slot-0 page 1" (main
> BASIC) and RAM references are unchanged.

> **WAVE-1 REVISED 2026-07-11 (S2b, user call) — the tenant is the CRUNCH, not
> the formatter.** After the formatter eviction was built and green, the user set
> a sharper principle: **never evict a runtime-hot path.** The `flt_out` formatter
> runs on *every* float `PRINT` (a per-`PRINT` CALSLT + DI), so it stays
> **resident**. A page-0 sub-ROM tenant runs with the BIOS + low region switched
> out, so it must be **pure computation** — which disqualifies the cold
> *peripheral* verbs (LIST/SAVE/CLOAD are all I/O-bound and can't run sub-side).
> The one cold, pure-computation body is the `tk_float` **literal crunch**
> (tokenise-time only), so it becomes WAVE 1. Delta vs the formatter plan:
> - Evict `tk_float` (~825 B) → sub-ROM page-0 index 1; `flt_out` returns to the
>   main ROM. Frees **~727 B** in page 0 (more than the formatter's ~400 B).
> - The crunch's `jp`-threaded exits (`jp tk_loop`/`jp tk_end`) are refactored to
>   **return a disposition** in `A` (0 = continue → the main-ROM stub does
>   `jp tk_loop`; 1 = end/overflow → `jp tk_end`); `HL`/`DE` (source + dest
>   cursors) pass through CALSLT both ways (`subrom_call` preserves `DE`).
> - Pure-leaf via sub-local clones of `upcase`/`cmp16_bits`/`neg_de`, and the
>   crunch keeps its own `tkf_ref*` copy while `float.asm` gets a **resident**
>   copy for `float-arith` — so **no cross-ROM equate link** (the crunch does not
>   call `tk_loop`/`tk_end` any more; they became the stub's job).
> - Host harness: the crunch is on the tokenise path used by 11 unit tests. The
>   flat, single-slot host harness can't page a CALSLT, so `msxtest` runs the
>   tenant in a **separate machine** and shuttles only RAM (a low-mem/stack-shared
>   bridge corrupts host execution — verified). All gates green; the ROM itself
>   is proven correct by the openMSX gates (float LITERALS byte-identical, FORMAT
>   reference-identical, string-acceptance PASS).
>
> The prose below is the original formatter-based amendment, kept for the
> reasoning; read "wave 1 = the formatter" as **superseded by the crunch** per
> this block. The dispatch-mechanism and two-wave framing are unchanged.
>
> **WAVE-1 AMENDMENT 2026-07-11 (S2b open, user-ratified) — the §3f leaf-audit
> re-scoped the eviction.** S2b's named pre-gate (the §3f leaf-audit) ran and
> **falsified the §2 wholesale-eviction premise** (F2 had coupled float.asm ↔
> float-arith and made parts of float.asm hot — see the corrected §2 bullet).
> Post-audit reality of float.asm (`$32FB–$3808`, 1294 B):
> - **Cold + cleanly evictable:** `tk_float` crunch (`$32FB–$3634`) and `flt_out`
>   formatter (`$3635–$37E7`). Audit-clean: their only external code edges land
>   in page 1 (visible from sub-ROM pg0).
> - **Hot glue — must stay resident** in the low region: `flt_to_int16`
>   (per-factor), `flt_int_result` (8 callers), `flt_neg`, `neg_de`. A
>   CALSLT-per-factor would wreck the interpreter.
> - **`tkf_ref32767/65535/32768` data** sits in the crunch block but is read by
>   the *resident* float-arith core.
>
> So the eviction is **re-sliced into two waves along the pure-leaf/needs-linkage
> seam** (user chose "pure-leaf formatter", 2026-07-11):
> - **WAVE 1 (this S2b session) = the `flt_out` formatter, evicted as a ZERO-
>   LINKAGE PURE LEAF.** Two trivial moves make it self-contained: (a) its two
>   tail `jp print_string` become `ret` — the formatter writes `FOUTBUF` (RAM)
>   and returns, and the main-ROM *stub* does the `print_string` (which reaches
>   CHPUT/BIOS — switched OUT during a sub-ROM pg0 call, so it *cannot* run
>   sub-side anyway); (b) its only other page-1 callee, the 11-byte `cmp16_bits`,
>   is duplicated sub-side. Result: the evicted formatter references **only RAM**
>   → `sub.rom` stays self-contained, **no main→sub symbol-import build step**.
>   One stub site (`print.asm`), no float.asm split around `tkf_ref`, ~400 B
>   freed in page 0 — enough to fund the dispatch machinery and break the
>   circularity. Proves the *complete* mechanism: CD discovery
>   (SUBSLOT/SUBSLOT_OK/EXBRSA), CALSLT dispatch (already round-tripped by the
>   S2a ping gate), RAM marshalling (`FOUTBUF`), absence path.
> - **WAVE 2 (a later session) = the `tk_float` crunch.** This is where the
>   float.asm split, the `tkf_ref`→page-1 relocation, the cross-ROM equate link
>   (crunch calls `tk_loop`/`tk_end`/`upcase`/`cmp16_bits` in page 1), and its 2
>   stub sites (interp) genuinely belong — done once, with the mechanism proven
>   and page-0 space comfortable.
>
> The spec's original "fold all of float.asm into one eviction session" (§5-S3,
> §2, R2) was the source of the risk; splitting along the pure-leaf seam is the
> clean decomposition. Everything below that says "wave 1 = float.asm" now means
> **wave 1 = the `flt_out` formatter only**; the crunch is wave 2.
>
> **Dispatch mechanism (both waves, this session lands it):** `init_ext_roms`
> gains the page-0 `CD` scan (records SUBSLOT/SUBSLOT_OK/EXBRSA); a shared
> `subrom_call` helper does DI → `IY=SUBSLOT` / `IX=entry` → `call CALSLT` → EI,
> with `SUBSLOT_OK` clear → *Illegal function call* (§3d). All of it
> `IF ROM_BASE < $4000` (repack-only); the lean `basic.rom` has no float at all
> so it is byte-identical by construction. SUBSLOT/SUBSLOT_OK live in the
> repack-only free RAM window (`$F106+`, after S2a's `SUB_PING $F105`, below
> `DRVA_DPB $F195`).

This is S1
(spec + sign-off) of the sub-ROM arc — step 1 of the concrete sequence in the
signed-off
[`decision-phase3-space-strategy.md`](decision-phase3-space-strategy.md) §6,
under the Q1 user direction recorded in that doc's §8 (a **built-in
MSX2-style sub-ROM in slot 3-0** of the virtual zerobas machine, not a
cartridge). Per the spec-before-implementation rule ([[spec-before-implementation]])
S2 (skeleton + tooling) is now the green-lit next session. No implementation is
done in S1.

Cadence: this is an **arc** (like the float pack), S1 (this) → then a slice per
`decision §6` step, each with its own S2 (implement + gate) / S3 (close-out)
and its own commit-at-gate:

- **S2 — skeleton + tooling:** the empty sub-ROM builds and ships; machine
  configs gain it (sub-ROM added in **3-2**; RAM stays 3-0, disk stays 3-1);
  boot scan records its slot; a stub dispatch + absence-error path exists; new
  present/absent boot gate.
- **S3 — eviction wave 1:** `float.asm` (F1 tokeniser + output formatter,
  ~1 294 B) moves into the sub-ROM; full `float-acceptance` + crunch re-run;
  the in-window window regains ~1.3 KB.
- Downstream (own specs, not this arc): F3 lands in the freed window; the math
  pack becomes the sub-ROM's first *native* tenant; later eviction waves as the
  ~14–21 KB roadmap (`decision §3`) draws down.

## 1. Goal & scope

Stand up **`zerobas-sub`**, the virtual zerobas machine's built-in sub-ROM, as
the durable carrier for the Phase-3 roadmap remainder that the `$2812–$7FFF`
BASIC window (now FULL: 2 B page-0 slack, 29 B page-1 tail) cannot hold. This
is staging B of the decision doc: build the mechanism now rather than after one
more in-window stopgap, because the roadmap's in-window-bound demand
(~6.5–9 KB, `decision §3b`) provably exceeds every in-window supply and can
only be met by evicting cold code into a second ROM.

**In scope for the arc (S1 design + S2/S3 build):**

- The sub-ROM as a built-in **32 KB** ROM spanning **both pages** of expanded
  slot **3-2** (amended; was 3-0) — page 0 `$0000–$3FFF` (`CD` signature, the
  callable-from-main region) and page 1 `$4000–$7FFF` (the BIOS-visible island,
  F700-style) — of the merged/main zerobas machine, with the machine's slot-3
  map becoming **3-0 = RAM (unchanged), 3-1 = disk ROM (unchanged), 3-2 =
  sub-ROM (new), 3-3 = empty** (top-of-file AMENDMENT; RAM does not move).
- The **boot-scan** addition that records the sub-ROM's slot (MSX2 `CD`
  page-0 signature + EXBRSA `$FAF8` convention), reusing `init_ext_roms`.
- The **dispatch ABI**: main-ROM token handlers become thin stubs that parse
  args in page 1, marshal through page-3 RAM, CALSLT a fixed sub-ROM
  entry-table slot, and read results back from RAM.
- The **absence semantics**: reduced builds without the sub-ROM (lean 16 KB
  cart, tape IPS) abort a sub-ROM-backed statement with a proper own-design
  error instead of jumping into unmapped ROM.
- The **placement discipline** (`decision §8d`) as an inherited design rule that
  every downstream slice's spec must apply per-routine.
- ~~S2's **RAM 3-0 → 3-3 verification** budget~~ — retired by the amendment
  (RAM stays 3-0); S2 instead just re-runs the disk gates as an additive check.
- S3's first eviction (`float.asm`) as the proof-of-mechanism tenant.

The **32 KB choice (§9-Q2)** brings the page-1 island into scope *as tooling +
ABI* in this arc (the build produces a two-page ROM and the dispatch model
covers both pages, §3c), even though wave 1's actual tenant (`float.asm`) lands
in page 0. Page 1 is thus *reserved and buildable* from S2 on, ready for the
first BIOS-heavy body without a later tooling round.

**Out of scope for this arc** (each its own later spec, unblocked by this work):
the math pack (`^` + SQR/SIN/…), F3 and the numeric follow-ups, heap/arrays,
graphics, sound, and every later eviction wave — i.e. what actually *fills*
either page. S1 stands up the container (both pages) and the mechanism; slices
fill it.

## 2. Existing infrastructure this builds on (verified 2026-07-11)

- **Boot scan** ([initext.asm](../basic/initext.asm) `init_ext_roms`): already
  runs the rest of C-BIOS's cartridge boot scan that our non-returning INIT
  pre-empts. For every primary slot *after* ours, and every expanded subslot,
  it RDSLT-checks the `AB` header at `$4000` and CALSLTs the INIT word at
  `$4002`; it records the disk-ROM slot in `DISKSLOT`/`DISKSLOT_OK`
  (`sysvars.inc:2285`). **It already visits expanded slot 3's subslots** (the
  `ier_sloop` secondaries 0..3 loop), so 3-0 is on its path today — the arc adds
  a page-0 `CD` check alongside the page-1 `AB` check and a second slot record.
- **CALSLT precedent** ([files.asm](../basic/files.asm), [field.asm](../basic/field.asm)):
  every disk sector op already makes the exact page-1→page-1 inter-slot CALSLT
  this ABI needs (`$4010` DSKIO), with the text cursor (HL) guarded across it
  because CALSLT clobbers everything. 163 disk call sites establish the pattern
  the sub-ROM stubs mirror — but see §3c: the sub-ROM's page-0 mapping makes it
  *cheaper* than the disk case, not the same.
- **Host-adaptive RAM slot** ([init.asm](../disk/init.asm) `set_ramad`,
  `page0_ram_in`/`page0_ram_out`): derives the RAM slot id from page 3's
  *actual* runtime slot, not a hard-coded `$83`. Under the amendment RAM does
  not move at all, so this host-adaptivity is not even exercised by the arc —
  RAM keeps `$83`; the property is noted only because it means the disk side is
  robust regardless.
- **Machine tooling** ([install-openmsx-machine.py](../tools/install-openmsx-machine.py)
  `expand_slot3`, [install-repack-machine.py](../tools/install-repack-machine.py)):
  today lay slot 3 as `3-0 = 64 KB RAM, 3-1 = zerobas-disk, 3-2/3-3 empty`.
  S2 adds the sub-ROM in the empty **3-2** (`3-0 = RAM, 3-1 = disk, 3-2 =
  zerobas-sub, 3-3 = empty`); the RAM and disk blocks are unchanged.
- **float.asm ↔ float-arith decoupling** — ⚠️ **STALE, corrected 2026-07-11 by
  the S2b leaf-audit** (see the WAVE-1 AMENDMENT below). This bullet's original
  claim ("no call edge in either direction") was true at S1 sign-off but **F2
  introduced deep mutual coupling** after the spec was written: `flt_to_int16`
  (float.asm) `jp domain_convert_core` (float-arith, low region `$3C6F`), and
  float-arith calls back into `neg_de`/`flt_to_int16`/`flt_int_result` + reads
  the `tkf_ref*` data constants — all living inside float.asm. float.asm also
  now hosts *hot* glue (`flt_int_result` has 8 callers, `flt_to_int16` runs on
  every float factor). So "evict float.asm wholesale" is no longer viable; the
  leaf-audit re-scoped the arc into two waves (WAVE-1 AMENDMENT). The audit
  (§3f) worked exactly as intended — it caught the R2 hazard before any code
  moved.
- **Gates that must stay green after every slice**: crunch probe
  (byte-identical), string-acceptance (6), input-acceptance (8),
  float-acceptance (3 halves), diskbasic-acceptance-repack (34), the BDOS
  battery, `bdos-cbios-selfcheck` (10), unit-test (44),
  lean-`basic.rom`-byte-identical. Under the amendment the RAM move is gone, so
  the disk/BDOS gates and the selfcheck are **not** at risk (§3e) — S2 re-runs
  them only to confirm that adding a device in the empty 3-2 subslot perturbs
  nothing.

## 3. Design

### 3a. The map (ratified — recorded, not re-litigated)

Expanded slot 3 of the merged/main zerobas machine:

Expanded slot 3, **as amended 2026-07-11** (see the top-of-file AMENDMENT):

| Subslot | Tenant | Was | Signature / page | Slot id |
|---|---|---|---|---|
| 3-0 | **RAM** | unchanged | 64 KB mapper | `$83` |
| 3-1 | zerobas-disk | unchanged | `AB` at `$4000`, page 1 | `$87` |
| 3-2 | **zerobas-sub** (NEW) | empty | `CD` at `$0000`, **both pages** `$0000–$7FFF` | `$8B` |
| 3-3 | empty | empty | — | — |

RAM and disk are both **unchanged** from the shipping disk machine; the sub-ROM
takes the previously-empty 3-2. This diverges from the `decision §8a` convention
(sub-ROM in 3-0 in 53/72 machines) *deliberately*, to avoid moving RAM — the
amendment's faithfulness-vs-risk trade. Disk stays at 3-1 (not F700-style 3-0
stacking): no functional gain, and `DRVTBL`/Tier-2 machinery assume 3-1.

### 3b. Two pages, opposite visibility (the architecture, from `decision §8b`/§8d)

The sub-ROM is 32 KB across both pages of slot 3-0, and CALSLT switches only the
*called* page — so the two pages are **opposite islands** (`decision §8d`
symmetry):

- **Page 0 (`$0000–$3FFF`)** — mapping it (CALSLT with `IX` in page 0) switches
  slot 3-0 into page 0 and leaves **slot-0 page 1 (main BASIC) visible**; the
  BIOS + low region + ISR at slot-0 page 0 are switched *out*. This is the
  callable-from-main region and where wave-1 tenants live. Interrupts OFF.
- **Page 1 (`$4000–$7FFF`)** — mapping it switches slot 3-0 into page 1 and
  therefore switches **main BASIC out**, leaving the **BIOS visible** (slot-0
  page 0). This is the F700-style island for BIOS-heavy bodies that don't need
  main BASIC (future graphics/VDP primitives). Interrupts *may* stay enabled.
- **The two sub-ROM pages are separate islands to each other**: an in-slot
  pg0↔pg1 call needs explicit paging (you cannot straddle a CALSLT boundary).
  Treat page-0 and page-1 tenants as two disjoint tenant sets with two entry
  tables (§3c). Wave 1 uses only page 0.

While a **page-0** tenant is executing at `$0000–$3FFF`:

- **page 1 still maps slot 0 — the main BASIC ROM stays directly callable.**
  Sub-ROM code can call `pchar`, `eval`, the var store, `float-arith` *directly*
  (they live in page 1 or must be moved there), with no cross-slot
  interpreter-services ABI and no CALSLT-back per callback. This dissolves the
  original §4d cartridge model's biggest cost and makes eviction wave 2's
  "buffered-sink refactor" unnecessary.
- pages 2/3 (program RAM, sysvars, FAC/ARG/NUMTYP) stay visible — arg marshalling
  through RAM works from either side of the call.

Two consequences the arc inherits as hard rules:

1. **The low region `$2812–$3FFF` (slot-0 page 0) is INVISIBLE during a sub-ROM
   call.** Anything a sub-ROM tenant calls must sit in **page 1** (or be a
   sub-ROM-local copy). This is the §3f leaf-audit obligation.
2. **Interrupts are OFF while the sub-ROM is mapped** (the `$0038` ISR vector is
   switched out with the BIOS). Long tenants budget the DI span; BREAKX-style
   direct PPI polling still works under DI (§3d).

### 3c. Dispatch ABI

**Signature & discovery.** The sub-ROM carries the MSX2 sub-ROM ID byte pair
**`CD` at `$0000`** (own-machine layout following the published MSX2 convention;
cartridges use `AB`, sub-ROMs use `CD` — MSX2 Technical Handbook, allowed source
grade B). The boot scan (§3g) records the sub-ROM's slot id in **EXBRSA `$FAF8`**
(the published MSX2 work-area for the sub-ROM slot) and in a private
`SUBSLOT`/`SUBSLOT_OK` pair mirroring `DISKSLOT`/`DISKSLOT_OK` — EXBRSA for
convention-compatibility with a future real `$015C SUBROM`/`$015F EXTROM`
implementation, the private flag for our own dispatch (so the two concerns stay
decoupled and the private path never depends on a work-area a stray program
could clobber).

**Entry tables (the `$4010`-style fixed contract), one per page.** Each page
holds an append-only **jump table** of `jp` entries at a fixed base, and a tenant
is addressed by `IX = base + 3*index`:

- **`SUBROM_ENTRY_BASE_P0 = $0010`** — page-0 tenants (clear of the `CD` header
  and the sub-ROM-local RSTs at `$0008…$0038`). Wave-1 (`float.asm`) dispatches
  here.
- **`SUBROM_ENTRY_BASE_P1 = $4010`** — page-1 tenants; this deliberately mirrors
  the `$4010` disk-DSKIO offset, so a page-1 CALSLT looks exactly like the disk
  case the codebase already runs 163 times.

Adding a tenant *appends* to its page's table and never moves an existing entry,
so the ABI is stable across slices (the main-ROM stub for slice N hard-codes only
its page + index). Dispatch is a direct **CALSLT with IX = the entry address**,
matching the MSX2 EXTROM register contract (IX = target) so that a later real
`$015F EXTROM` implementation is a drop-in — and note `$015C`/`$015F` are exactly
the tape component's charter shape ("stubbed page-0 BIOS vectors C-BIOS leaves
fake", `decision §8b`).

**The call sequence** (main-ROM stub, per tenant):

1. Parse args in the main ROM (page 1) — **parsing always stays main-side**;
   the tokeniser/evaluator are not evicted.
2. Marshal args into page-3 RAM (FAC/ARG/NUMTYP and a small
   `SUB_ARG` scratch block are visible from both slots).
3. Guard the text cursor (HL) and any live page-1 pointers on the stack
   (CALSLT clobbers all registers — the disk stubs' exact discipline).
4. `SUBSLOT_OK` clear ⇒ jump to the absence-error path (§3d). Else load
   `IY` from `SUBSLOT`, `IX` from the entry address, `call CALSLT`.
5. Read results from RAM; restore the cursor; continue.

### 3d. Absence semantics & the DI budget

- **Absence.** The sub-ROM is part of the zerobas *virtual machine*'s built-in
  complement — the merged/main deliverable **always** ships it, so absence is
  not a normal runtime state there. It matters only for the reduced builds (lean
  16 KB `basic.rom` cartridge, standalone tape IPS) that don't compile the
  sub-ROM-backed statements in the first place. The stub still checks
  `SUBSLOT_OK` defensively: absent ⇒ abort the statement via the normal error
  path with **"Illegal function call"** (§9-Q4 answered — reuse the existing MSX
  error rather than mint a divergent string; a reduced build never reaches it in
  practice). No jump into unmapped ROM is ever possible.
- **DI budget.** Every sub-ROM tenant runs under DI. S1 sets the rule; each
  downstream slice's spec must **state its worst-case DI span** and confirm it
  is JIFFY-tolerant (the known MSX2 long-sub-ROM-call tick loss). Function-shaped
  tenants (a BCD SIN ≈ 10⁵ T-states) are fine; loop/stream tenants (a future
  LIST or PLAY moved sub-side) must either stay short or re-map the BIOS
  mid-body via an explicit trampoline (`decision §8d` 3-0 pg0 rule).

### 3e. ~~The RAM 3-0 → 3-3 move~~ — ELIMINATED by the 2026-07-11 amendment

**The RAM move is gone.** Under the amended map RAM stays in 3-0, so its slot id
stays `$83` and nothing the disk side derives (`set_ramad` /
`page0_ram_in` / `page0_ram_out`) sees any change. The arc's one-time
verification cost — the §3e RAM-move re-baseline and its `bdos-cbios-selfcheck`
risk (R1) — no longer exists.

S2's machine-config work is now purely *additive*: `expand_slot3` and the repack
machine gain a 3-2 sub-ROM block while their 3-0 RAM / 3-1 disk blocks are
byte-for-byte as today. The disk gates (bdos-acceptance, diskbasic-acceptance,
diskbasic-acceptance-repack, bdos-cbios-selfcheck) must still be **run** as a
regression check — merely adding a device to a new subslot must not perturb
them — but any change there would be a *regression to fix*, not an expected
re-baseline. (Historical note: the original signed-off spec put the sub-ROM in
3-0 and moved RAM to 3-3, which is what this section costed; that trade was
reversed on 2026-07-11.)

### 3f. Placement discipline (inherited design rule, `decision §8d`)

A CALSLT switches only the called page, so each executing context has its own
visibility set:

| Executing from | slot-0 pg0 (`$2812–$3FFF` low region + BIOS + tape + ISR) | slot-0 pg1 (main BASIC) | RAM pg2/3 | Ints |
|---|---|---|---|---|
| slot 0 (normal) | ✓ | ✓ | ✓ | ✓ |
| 3-0 pg0 (sub-ROM, wave-1 tenants) | ✗ (switched out, incl. `$0038` ISR) | ✓ | ✓ | **DI** |
| 3-0 pg1 (sub-ROM island, future BIOS bodies) | ✓ (BIOS + ISR reachable) | ✗ (main BASIC switched out) | ✓ | may EI |
| 3-1 pg1 (disk ROM) | ✓ | ✗ (the 163-site wall) | ✓ | existing |

Note the symmetry: **3-0 pg0 sees main BASIC but not the BIOS; 3-0 pg1 sees the
BIOS but not main BASIC** — the two sub-ROM pages are complementary islands.

Rules every downstream slice inherits and states per-routine:

- **Slot-0 page 1 is the premium region** — the only ROM visible to sub-ROM pg0
  code. Shared services (float-arith core, `pchar`, FAC/eval helpers) must live
  there. Evictions preferentially move **leaf** code *out* of page 1 (to the low
  region or the sub-ROM) to keep page-1 bytes for services — not the naive "cold
  code moves out".
- **The low region `$2812–$3FFF` is leaf-only**: nothing a sub-ROM tenant will
  ever call may sit there, in the gap fills, or in the tape block.
- Every future slice's spec **states, per new routine, its region and the
  contexts that may call it.** Placement is part of the design, not an assembler
  accident.

**S3 leaf-audit obligation** (the §3b caveat-1 discharge for wave 1): before
`float.asm` moves to the sub-ROM, audit its full call graph. Preliminary finding
(§2): `float.asm ↮ float-arith.asm` (no edge either way), so the BCD core is not
dragged along. S3 must still enumerate *every* call target of `float.asm` and
confirm each resolves in **page 1 or RAM** (not the low region); any low-region
callee must be moved to page 1 or copied sub-side before the eviction lands.

### 3g. Boot-scan addition

`init_ext_roms` gains a page-0 `CD` check parallel to its page-1 `AB` check.
Within the existing `try_init_slot` (or a sibling `try_sub_slot`): RDSLT
`$0000`/`$0001` for `'C'`/`'D'`; on a hit, record the slot id in `EXBRSA`
(`$FAF8`) and `SUBSLOT`/`SUBSLOT_OK`. Unlike the disk case, **no INIT CALSLT is
required at boot** — the sub-ROM installs no hooks and no SYSTEM vector; it is a
passive callee, so recording the slot is the whole job. (Whether the sub-ROM
carries an INIT word at all is an S2 detail; if present it may publish an
entry-table version byte for forward-compat, but S1 does not require one.)

- **Ordering (amended):** the sub-ROM now sits in slot **3-2**, which
  `ier_sloop` (secondaries 0..3) reaches *after* the disk ROM in 3-1. So the
  disk INIT is CALSLTed **before** the sub-ROM's `CD` is recorded — the reverse
  of the original 3-0 plan. This is safe: the disk INIT does not read `EXBRSA`
  or the sub-ROM slot (it is our own disk ROM, and the two subslots are
  independent), so recording the `CD` after the disk INIT loses nothing. Neither
  ROM depends on the other's slot record at boot.
- **Firewall:** the added RDSLTs read *our own* sub-ROM bytes; no C-BIOS code is
  read or relocated. Sourcing: RDSLT `$000C`, CALSLT `$001C`, EXPTBL `$FCC1`,
  EXBRSA `$FAF8`, port `$A8`, slot-id byte format, `CD` sub-ROM signature — all
  MSX2 Technical Handbook / MSX Assembly Page (allowed, already cited in
  `initext.asm`'s SOURCES block; EXBRSA + `CD` are the only new citations).

## 4. Decisions to ratify (S1 sign-off)

| # | Decision | Proposed | Basis |
|---|---|---|---|
| D-1 | Component name | **`zerobas-sub`** ✅ | naming convention `zerobas-<component>` ([[naming-convention]]); matches `zerobas-disk`/`zerobas-tape`. §9-Q1 answered |
| D-2 | Slot map | ~~3-0 sub / 3-1 disk / 3-3 RAM~~ → **AMENDED 2026-07-11: 3-0 RAM / 3-1 disk / 3-2 sub / 3-3 empty** | top-of-file AMENDMENT — RAM stays put (compat + risk); sub-ROM id `$8B` |
| D-3 | Signature | `CD` at `$0000` (page 0) | `decision §8b`; MSX2 TH sub-ROM convention |
| D-4 | Size | **32 KB (page 0 + page 1)** ✅ | §9-Q2 answered — reserve the F700-style island up front; both pages built + ABI'd from S2 |
| D-5 | Dispatch | CALSLT, IX = fixed `jp`-table entry; **two bases** `$0010` (pg0) / `$4010` (pg1), append-only | §3c; `$4010`-style + MSX2 EXTROM IX contract |
| D-6 | Slot record | EXBRSA `$FAF8` **and** private `SUBSLOT`/`SUBSLOT_OK` | §3c/§3g; convention-compat + robust private path |
| D-7 | Boot | record slot only, **no INIT CALSLT** | §3g; passive callee, no hooks |
| D-8 | Absence | `SUBSLOT_OK`-gated stub → **"Illegal function call"** ✅ | §3d; §9-Q4 answered — reuse existing MSX error |
| D-9 | DI | every tenant under DI; per-slice DI-span budget | §3b/§3d |
| D-10 | Placement | §3f table + leaf-only low region are inherited rules | `decision §8d` |
| D-11 | Wave-1 tenant | `float.asm` (tokeniser + formatter), gated by the §3f leaf-audit | `decision §6` step 3; §2 decoupling finding |

## 5. Arc slices & gates

> **S2 RE-SLICED 2026-07-11 (measured constraint + user call).** The window has
> exactly **2 B free in page 0, 29 B in page 1** (measured via `__MEAS_*`
> labels on the reloc build). The signed-off S2 skeleton's *main-ROM* parts —
> boot-scan+presence-flag (~50 B) and dispatch stub+absence error (~55 B),
> ~100 B — do **not** fit, and S3's `float.asm` eviction (which frees the room)
> can't precede the dispatch stub the evicted code calls back through
> (circular). So S2 is split:
> - **S2a (this session) — foundation, ZERO main-ROM bytes.** The `sub.rom`
>   binary (32 KB, `CD` header, ping `jp`-entries at `$0010`/`$4010`), the
>   machine tooling (3-2 sub-ROM block), and a **boot-gate-by-injection**: the
>   probe reads the sub-ROM's `CD` and drives a `CALSLT` to each ping entry from
>   the openMSX debugger, proving discovery + the two-page ABI + the round-trip
>   against the sub-ROM's own bytes — with no main-ROM change, so nothing can
>   overflow and the frozen lean/repack images stay byte-identical.
> - **S2b (folded into the eviction session) — main-ROM integration.** The
>   `init_ext_roms` `CD` scan (records `SUBSLOT`/`SUBSLOT_OK`/`EXBRSA`) and the
>   `subrom_call` dispatch stub + absence-error path land *together with* the
>   `float.asm` eviction, whose freed ~1.3 KB pays for them; `float.asm` becomes
>   the first real tenant through the entry table (subsumes the old S3). The
>   §3f leaf-audit stays that session's named pre-gate.
>
> Everything below under "S2" is the union S2a+S2b; the *tooling + injection
> gate* is S2a, the *main-ROM boot-scan/dispatch + absence gate* is S2b.

- **S1 (this)** — spec + sign-off. Gate: user answers §9, status → SIGNED OFF.
- **S2 — skeleton + tooling.** Empty **32 KB** `zerobas-sub` builds + ships as a
  plain `.rom` (disk.rom-style) spanning both pages, with a `CD` header + empty
  `jp`-table stubs at both entry bases (`$0010`, `$4010`); machine configs gain
  the 32 KB sub-ROM in the empty **slot 3-2** (RAM stays 3-0, disk stays 3-1);
  boot scan records the slot; a main-ROM stub + absence path exist; **new boot
  gate** (present: slot recorded, a probe stub round-trips through a CALSLT in
  *each* page; absent: stub errors cleanly with "Illegal function call"). Also:
  re-run the disk gate suite as an additive-regression check (the §3e RAM move
  is retired — nothing should perturb). Existing standing gates all green.
  ~1 session.
- **S3 — eviction wave 1.** `float.asm` → sub-ROM after the §3f leaf-audit; F1
  becomes the first real tenant through the entry table. Gate: full
  `float-acceptance` (3 halves) + crunch probe byte-identical + the window
  regains ~1.3 KB (measured). Lean `basic.rom` stays byte-identical (float.asm
  is not in the lean cart? — S3 confirms; if it is, the eviction is merged-build
  only and the lean image is unchanged by construction).
- **Downstream** (own specs): F3 in-window; math pack sub-native; later waves.

## 6. Firewall & provenance

- **`zerobas-sub` is pure zerobas bytes**, ships as a plain `.rom` like disk.rom
  — no C-BIOS interaction, no IPS splice, no relocation of stock code. The
  output firewall (`0 C-BIOS-leak bytes`, [`cbios-repack-provenance.md`](cbios-repack-provenance.md))
  is *trivially* preserved for the sub-ROM itself.
- The **boot-scan additions** in `initext.asm` (page-0 `CD` RDSLTs, EXBRSA
  write) read only our own bytes and cite only already-allowed sources (§3g).
- **Own-design divergences to document** (provenance registry entry, S2):
  (a) an MSX2-style sub-ROM on an MSX1-class machine; (b) core math functions
  living in the sub-ROM rather than the main ROM — faithful in *mechanism*
  (Disk/FM/Kanji BASIC all extend from ROMs), a documented divergence in
  *placement* (real MSX kept SIN/COS in the main ROM). `decision §7` Q3
  considers this acceptable under the sub-ROM framing.

## 7. What this arc unblocks

F3 two slices from sign-off (freed window + margin); the math pack with **no
further space decision**; and a standing placement rule that answers every
future slice's "where does it go" — hot/woven/service → slot-0 page 1;
leaf → low region; function-shaped cold body → sub-ROM. The ~14–21 KB roadmap
remainder (`decision §3`, all-of-MSX1 ambition) now has a home with a 16 KB
ceiling per page and a proven-mechanism path to a second page if ever needed.

## 8. Risks

- **R1 — ~~the RAM move breaks a disk/BDOS anchor byte-identity~~ RETIRED**
  (§3e). The 2026-07-11 amendment keeps RAM in 3-0, so no slot id changes and
  there is no re-baseline to reason about. The disk gates are still run in S2 as
  a plain additive-regression check.
- **R2 — a float.asm callee resolves in the low region** (§3f), forcing an
  unbudgeted page-1 move before S3. Mitigated: preliminary audit already clears
  the float-arith edge; the full audit is a named S3 pre-gate, and a page-1
  move is cheap (include-order shuffle, byte-neutral).
- **R3 — DI span of a future stream tenant** (LIST/PLAY) exceeds JIFFY
  tolerance. Out of this arc (wave 1 is function-shaped float.asm); flagged so
  downstream specs budget it (§3d).
- **R4 — EXBRSA clobbered by a user program** breaks dispatch. Mitigated by D-6:
  the private `SUBSLOT` path does not read EXBRSA at dispatch time.

## 9. Open questions — ANSWERED 2026-07-11

1. **Component name** → **`zerobas-sub`**. (D-1.)
2. **Size** → **32 KB, page 0 + page 1 up front** (not the 16-KB-page-0-only
   recommendation). The F700-style page-1 island is reserved and buildable from
   S2 on, so the first BIOS-heavy body needs no later tooling round; §1/§3b/§3c
   carry the two-page consequence. (D-4.)
3. **Entry-table base & shape** → accepted; extended to **two** append-only
   bases, `$0010` (page 0) / `$4010` (page 1), `IX = base + 3*index`. (D-5.)
4. **Absence-path error** → reuse **"Illegal function call"**. (D-8.)
5. **D-1…D-11 changes** → at sign-off, only D-4 (size). **AMENDED 2026-07-11:**
   D-2 also revised — sub-ROM → empty 3-2, RAM stays 3-0 (see top-of-file
   AMENDMENT). The rest stand as proposed.
