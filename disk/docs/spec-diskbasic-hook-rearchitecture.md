<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — Disk BASIC in the disk ROM, reached through the hooks

**Status: 🟢 DIRECTED BY JOOST, 2026-09-15** — verbatim: *"now update our disk
basic to use the same architecture"*, after *"I'd expect most if not all of disk
basic to be in the disk rom, and installed via the hooks"*.

⚠️ **THIS SUPERSEDES THE PARK.** Earlier the same day Joost ruled *"Park it —
carve somewhere else"* on rung 3 of
[`spec-diskbasic-relocation-seam.md`](spec-diskbasic-relocation-seam.md), against
a measured 36 B of movable code. That figure was measured under a constraint that
does not apply here — see §3 — so the park is lifted by a later direction rather
than contradicted. Rungs 3/3b/4 as *byte-carving* exercises stay closed; this
spec is about ARCHITECTURE, and the bytes are a consequence rather than the goal.

> 🧭 **2026-09-17 — THIS DOCUMENT IS THE MECHANISM; THE DENOMINATOR IS
> [spec-diskcode-eviction.md](spec-diskcode-eviction.md).** Joost ruled *"there
> should probably be hardly any disk code left in the main Rom"*, and that spec
> measures what "hardly any" is against: **2394 B** in six disk-only files, 250 B
> of it interface. It also carries a CORRECTION that matters here: §4's phase-0b
> framing of the disk→BASIC call as unpriced is **stale** — `calbak` stands at 19
> call sites and its ABI was measured in phase 1 (D-XSLOTABI). Phase 3's blocker
> below is unaffected: it is hook-cell IDENTIFICATION, not the call.

## 0. The one-line target

**Every Disk-BASIC verb body lives in `disk.rom`, is reached through its standard
MSX hook, and calls back into main BASIC across slots to evaluate its own
arguments** — which is what the reference does, measured, on every argument.

## 1. What the reference actually does (measured, not assumed)

D-CFARCH and D-CFEVAL, black-box on the National CF-3300. **No instruction of the
reference was read or recorded**; the line is the one
[`expansion-protocol.md`](expansion-protocol.md) §2 drew — a hook cell's
`F7 <slot> <lo> <hi> C9` may be read for its SLOT and its IDIOM, and the target
addresses are the reference's internal detail, noted and never called.

* **35 claimed hook cells**, every one slot `$87` (expanded 3-1, the disk ROM),
  every entry in PAGE 1, every tail `C9`. No page-0 handlers, no RAM stubs, no
  exceptions ([`scratchpad/cf3300_arch_probe.py`](../../scratchpad/cf3300_arch_probe.py)).
* **The hook is CALLED, not inspected.** A cell keeping its `F7` signature but
  redirected to a `RET` we control behaves exactly like an unclaimed cell, so the
  outcome tracks what the TARGET DOES rather than what the cell LOOKS LIKE
  ([`whoevals3.py`](../../scratchpad/whoevals3.py), read-back control in
  [`whoevals4.py`](../../scratchpad/whoevals4.py)).
* **The argument is evaluated AFTER the handler is entered, by main BASIC.** The
  RAM stub switches page 1 in at `SP=DB85` and back out at `SP=DB79` — twelve
  bytes DEEPER, so a CALL and not a return — and inside that call-back, slot-0
  code reads `KBUF` and the variable entry **at the same PCs the control
  `PRINT A$+".BAS"` uses**. `FILES 5` raises its Type mismatch inside the
  call-back; bare `FILES` skips the call-back entirely
  ([`cf_trace.py`](../../scratchpad/cf_trace.py),
  [`cf_whoreads.py`](../../scratchpad/cf_whoreads.py)).
* **Not carry.** Neither `SCF;RET` nor `XOR A;RET` signals "handled"; the
  reference's convention is something else and is **left unclaimed**.

### 1.1 Deliberately unresolved

Which BIOS entry the reference's call-back uses; which routine it enters in slot
0; who writes its staged name. Settling any of them needs disassembly. **None
changes the design**, and none is guessed here.

## 2. The slot model, and the one constraint that matters

From the machine definition, not recollection:

| | page 0 `$0000` | page 1 `$4000` | pages 2–3 |
|---|---|---|---|
| BASIC running | main | main | RAM (3-0) |
| disk handler running | **main** | disk ROM (3-1) | RAM |
| during the call-back | main | **main** | RAM |

**Page 0 is never swapped out.** Measured on the reference: the stub writes `FC`
(page1=3) to switch in and `F0` (page1=0) to switch back — only the page-1 bits
move. That is why `disk/basic-resident-abi.inc` works with plain absolute calls
and why its generator refuses any symbol at or above `$4000`.

🔴 **THE CONSTRAINT: DURING THE CALL-BACK THE DISK ROM IS GONE.** Its code and
data are not addressable. Everything the callee needs must be in REGISTERS or
staged in RAM beforehand — which is exactly what the reference was observed doing
with a parsed filename in the work area.

## 3. Why D-VERBCLASS's 155 B "STAY" is a price, not a wall

D-VERBCLASS classified the FAT-light span as STAY 155 / TENANT 67 / MOVE 36 B.
**STAY meant "cannot move under the SUB ROM's *no main-page-1 escape* rule."**
The DISK ROM is not bound by that rule — it is a proper expansion ROM and can
make an inter-slot call, which the reference does on every argument. So for this
architecture STAY means *cannot move WITHOUT an inter-slot call*: a price, and an
unmeasured one. §4's phase 0b measures it.

## 4. The plan

### Phase 0 — prerequisites. No code moves. Each step can kill the project cheaply.

* **0a — a dead-code model for cross-ROM callees. ✅ DONE 2026-09-15
  (D-XROMSEED).** A main-page-1 symbol whose
  only caller lives in `disk.rom` reads as DEAD to a main-image analysis. This
  already stopped a first attempt: `deadcode` refused `calbak_ping` as live only
  because a `tools/` file named it, an INTERSECTION a rename would drop silently.
  The gate names the remedy — *"give these names a per-tool lookup model that
  fails loudly, or seed them from something that does"*.
  ⚠️ The existing resident-ABI symbols are masked from this only because they
  also have main-side callers; a callee that exists purely for the disk ROM does
  not.

  **What shipped.** A third import class, `REQUIRED_DISK_CALLBACK` in
  `tools/gen_resident_abi.py` — main **page-1** targets reached by an inter-slot
  call — ceiling-checked in the OPPOSITE direction to the existing code class:
  a code import must be BELOW `__MEAS_LOW_END` (absolute call, page 0 stays
  mapped), a call-back import must be AT OR ABOVE `$4000`, because a page-0
  target is already reachable and an inter-slot call to it is pure overhead.
  `check_dead_code.py`'s new `disk_abi_seeds()` seeds the main build from that
  declaration and makes the generator, the generated file and the main label set
  agree or fail — the per-tool lookup model the gate asked for. The list is
  EMPTY today; phase 1 adds the first name to it.

  **Measured, not argued** — a page-1 stub with no main-side caller was planted,
  and all three directions checked before it was reverted:
  | experiment | result |
  |---|---|
  | stub planted, NOT declared | `deadcode` reports `[main] calbak_ping basic/files.asm 0x7265 PAGE1` dead — the sweep SEES it |
  | stub declared as a call-back | 0 dead; readout `disk import surface 4 seed(s) (1 of them page-1 call-backs)`; the `tools/` weight guard stays QUIET, so the model carries it, not the intersection |
  | a page-0 symbol declared as a call-back | generator refuses: `flt_fmt=$30B5 … belong in the CODE list` |

  **And it found a defect on the way.** `check_tenant_closure.collect_sources()`
  hardcoded the assembler's `-I sub`. Walking `disk/disk.asm` under that rule
  returned SUB's `equates.inc` and dropped six of the disk ROM's eight parts —
  a 3-file closure for an 8-file ROM, silently, because `sub/` happens to have
  an `equates.inc` too. The search path now comes from the caller (defaulting to
  the top file's own directory); `sub` stays at 71 files and `basic/main.asm` at
  50, so no other build's closure moved.
* **0b — one real inter-slot call, disk → main page 1 → back, PRICED.
  ✅ DONE 2026-09-15 (D-XSLOTPRICE). IT WORKS, AND IT IS CHEAP.**

  **The route.** `disk/pageenv.asm`'s `calslt_h` is a **simulated** CALSLT for
  the boot bridge — its own comment says it "calls IX directly" because those
  targets are already mapped — so it cannot reach main page 1 and was never the
  candidate. The runtime route is the BIOS's own `$001C` with `IX` = the main
  page-1 target and `IYh` = the main-ROM slot id from `EXPTBL`. Page 0 is never
  swapped (§2), so `CALSLT` itself stays mapped while it switches page 1 out
  from under the caller — the same geometry main→sub page-1 tenants already use
  on every `SQR`, `PLAY` parse and `LIST`.

  **It runs.** Measured on the merged machine with a scaffolded probe
  ([`xslot_plant.py`](../../scratchpad/xslot_plant.py), reverted after): a 2-byte
  main-page-1 callee `ld a,(hl) / ret` reached from a disk-ROM loop behind the
  `CVI` hook. **The witness is two-sided** — the callee returns the byte at
  `$4002`, which is `$10` in the main ROM and `$34` in the disk ROM, so the value
  says WHICH ROM was mapped rather than merely that something returned
  ([`xslot_stage.py`](../../scratchpad/xslot_stage.py)):

  | case | reads |
  |---|---|
  | control, no hook touched | `2` — the rig answers |
  | armed 0 calls | `255` — the cell is untouched; nothing ran |
  | armed 1 call | **`16`** = `$10`, main's byte — the switch happened |
  | armed 64 calls | `16` |

  **Bytes, assembled not counted** ([`xslot_bytes.asm`](../../scratchpad/xslot_bytes.asm)):
  **7 B per call site** with a 7 B shared helper, or 11 B fully inline.
  🎯 **7 B is exactly what `subrom_call` costs per site today** (`ld ix,<entry>`
  + `call`), so a call-back site is the same size as the sub-ROM calls this
  interpreter is already built out of. It also corroborates, rather than
  refutes, `disk/kernel.asm`'s filed *"~36 B of call overhead"* for the
  conversions: that verb names five main-page-1 callees, and 5 × 7 = 35 B.

  **Frames** ([`xslot_price.py`](../../scratchpad/xslot_price.py)). Six cases,
  **one build, one POKE apart** — `$E771` carries the number of inter-slot calls
  the handler makes per hook entry, so the slope cannot be a different machine:

  | calls | extra frames | per call |
  |---|---|---|
  | 100 | +1 | 0.0100 |
  | 800 | +8 | 0.0100 |
  | 1600 | +15 | 0.0094 |
  | 3200 | +30 | 0.0094 |
  | 6400 | +60 | 0.0094 |

  Fit through the origin: **0.0094 frames/call = 0.156 ms = ~107 inter-slot
  calls per frame.** At 3.58 MHz that is ~560 T-states for the round trip, which
  is the right order for a slot save/switch/call/restore plus our 17 B of
  wrapper — the physics agrees with the slope, independently of the baseline.

  ⚠️ **A CAP ON THE CASE LENGTH IS PART OF THIS MEASUREMENT.** Programs past
  ~140 frames come back with an empty capture. That boundary is the HARNESS, not
  the subject: a plain `FOR I=1 TO 2000:NEXT` that touches no hook at all goes
  equally quiet ([`xslot_window.py`](../../scratchpad/xslot_window.py)). Every
  case above is kept short enough to answer, and no silent case is reported as a
  reading.
* **0c — interrupt safety across the disk-ROM window. ✅ DONE 2026-09-15
  (D-XSLOTPRICE). THE GUARD COVERS IT — AND IS NOT THE MECHANISM THAT MATTERS.**

  🔴 **THE QUESTION CHANGED UNDER MEASUREMENT.** 0c was filed as *"confirm
  `htimi_guard` covers the disk-ROM window"*. It does. But measuring it found
  something UPSTREAM of the guard: a hook handler is entered through the
  inter-slot CALLF, which leaves **interrupts OFF**, so for the whole disk-ROM
  window nothing runs at all — not H.TIMI, not the guard, and **not the BIOS
  timer ISR that drives `TIME`**. A guard cannot cover a window it is never
  reached in.

  Four arms, one build, three POKEd cells
  ([`xslot_intwin.py`](../../scratchpad/xslot_intwin.py), planted by
  [`xslot_plant0c.py`](../../scratchpad/xslot_plant0c.py)). `ON INTERVAL=1`
  ticks once per frame in which `event_poll` runs, and `event_poll` is exactly
  what the guard gates (`basic/traps.asm`), so **fires ÷ frames is the fraction
  of frames main page 1 was mapped**. `TIME` is the BIOS ISR, which the guard
  does NOT gate, so the denominator stays honest — and reading both numbers is
  the point: `TIME` alone cannot separate *"the guard skipped"* from *"no
  interrupt happened"*.

  | arm | fires | frames | ticked | |
  |---|---|---|---|---|
  | `base` | 3 | 3 | 100% | the instrument's own rate |
  | `disk.ei0` | 3 | 3 | 100% | **but ~1 s of real work advanced `TIME` by 3 frames — the clock is STOPPED** |
  | `disk.ei1` | 2 | 61 | **3.3%** | interrupts forced on: `TIME` runs true, `INTERVAL` does not — **the guard covering the window** |
  | `cb.ei1` | 19 | 19 | **100%** | during the CALL-BACK page 1 is main, so the guard passes and everything is serviced |

  **`disk.ei1` is the confirmation 0c asked for**, and it is two-sided: the same
  spin with interrupts live shows the timer ISR running normally *while*
  `INTERVAL` stays frozen. That is the guard reading a nonzero page-1 primary
  field and skipping `event_poll` — not an absence of interrupts.

  🎯 **AND `cb.ei1` IS THE ANSWER FOR THE CALL-BACK'S RE-ENTRY: 100%.** During
  the call-back both pages hold main, so `$0038` and `htimi_guard` are equally
  valid and the frame is serviced in full.

  **What this hands phase 1.** The freeze is not something this re-architecture
  introduces — every hook handler today, `hk_mkfloat` included, already stops the
  clock for its duration; it is simply short. Moving verb bodies into `disk.rom`
  lengthens those windows, so **the call-back ABI should EI for the duration of
  the call-back**: page 0 and page 1 are both main there, the ISR is live, the
  guard passes, and the architecture ends up BETTER for interrupt latency than
  doing the same work disk-side would be.
  ⚠️ Whether the handler may also EI around its own disk-ROM work is a separate
  question with a real hazard behind it — the `htimi_guard` comment's FATPRIM
  precedent — and it is NOT settled here.

🔴 **KILL CRITERION FOR 0b — AND IT IS NOT "IS THE MACHINE FAST ENOUGH".**
Joost, 2026-09-15, on an earlier draft that made it one: *"yes, but that is a
separate concern"*. He is right, and the draft conflated two things. **This tree
being a flat ~3× slower than the reference is its own filed issue** (measured
84/28, 113/38, 142/47 frames) and it is not evidence about this architecture:
**the reference pays a call-back per argument too**, and pays it happily.
🎯 So the criterion is COMPARATIVE, not absolute: **does our inter-slot call cost
roughly what the architecture inherently costs — the same shape of work the
reference does — or does it cost dramatically more?** Only the second kills it,
and it would point at our implementation rather than at the design. A number that
merely looks big beside our own interpreter speed proves nothing either way.

✅ **ANSWERED, AND IT DOES NOT KILL IT.** Measured on the same machine, in the
same loop shape, 100 iterations each
([`xslot_compare.py`](../../scratchpad/xslot_compare.py)):

| | per iteration |
|---|---|
| `X=1` — the interpreter's per-statement floor | 7.17 ms |
| `X=CVI("AB")` — + the HOOK entry and the whole argument evaluation | 8.67 ms |
| **one call-back** | **0.156 ms** |

**A call-back costs ~10% of the hook entry the verb already pays to arrive**, and
the hook entry is itself an inter-slot call the reference pays too on every disk
verb. So the call-back is a small fraction of the work the architecture already
does around it, not a multiple of it.
⚠️ **The per-statement figures are this tree's own, and they are slow** — that is
the filed ~3× issue Joost separated out, and it is why the honest comparison is
call-back-against-hook-entry (both inter-slot, so the slowness cancels) rather
than call-back-against-statement, which would flatter us.

### Phase 1 — the interface. ✅ ABI MEASURED 2026-09-15 (D-XSLOTABI)

**Registers cross. Both ways. Intact.** The house rule so far has been *"everything
crosses in RAM"* (`hk_mkfloat`), reasoning from *"CALSLT is documented to affect
most of them"*. That is a document talking, not this machine, and every staged
byte is work a call-back would pay on every argument. So it was measured
([`xslot_abi.py`](../../scratchpad/xslot_abi.py), planted by
[`xslot_plant_abi.py`](../../scratchpad/xslot_plant_abi.py)) —
🎯 **with zero new main-ROM bytes**, which is the only reason it could be done at
all with 3 B free: both callees already exist in main page 1 (`$686A` is a bare
`ret`, `$40A3` is `inc hl / ret`).

| leg | measured |
|---|---|
| **inbound** — the hook, `RST 30h` / CALLF | `HL`=`$FE3F` (main set the hook cell), `DE`=`$508A` (main set `ev_cv_back`), `C`=2 (the width) — **all arrive intact** |
| **outbound** — the call-back, CALSLT to page 1 | `HL`/`DE`/`BC`/`A` all pass through unchanged; `IY` is consumed (slot id), `IX` is consumed (target) |
| **return** — a callee that MODIFIES a register | `HL` in `$1111` → out `$1112`: **the callee's own value comes back** |

The return leg is its own witness: `inc hl / ret` is at `$40A3` in MAIN, while the
disk ROM holds `ld a,(nn)` there, which does not return — so `$1112` can only mean
main page 1 was mapped and main's bytes ran.

🔴 **AND THIS FALSIFIES A FILED CLAIM THAT IS CURRENTLY BLOCKING A VERB.** Four
sites say *"DE — a register CALSLT does not preserve"* (`disk/kernel.asm:2138`
and `:2251`, `basic/strvar.asm:344` and `:395`), and `hook_tab` routes `H_MKI` at
`hk_present` instead of a real disk-side body **because of it**. DE was measured
preserved on both legs. Correcting those four sites, and revisiting whether
`MKI$` can now move, is its own slice.

#### The ABI

* **In**: `HL` = the statement cursor. Other arguments in `DE`/`BC` where a callee
  already takes them. No staging needed for these.
* **Out**: `HL` = the callee's result (typically the resumed cursor); `A` where the
  callee already returns one. Carry is the callee's own.
* **RAM stays the medium for anything the callee reaches for by itself** — §2's
  constraint is unchanged and is about the DISK ROM being gone, not about
  registers.
* **`IX`/`IY` are the ABI's own**: `IX` is the target, `IY` the slot id. A caller
  needing either across the call stages it.
* ⚠️ **A callee may RAISE. `fname_expr` answers ERR 13 for a non-string operand,
  and a BASIC error does NOT return** — it resets SP and unwinds to the statement
  driver, abandoning the disk ROM's CALSLT frame. That is correct behaviour, not a
  leak, but it means **a handler must do nothing after the call that an abort would
  skip** (no un-freeing, no half-written state to repair). Stated here so it is a
  designed property rather than a later surprise.
* **Interrupts**: the handler is entered with them OFF (0c). The call-back is where
  they should go back on — both pages hold main there, so `$0038` and
  `htimi_guard` are equally valid.

#### The callee — and it needs no main-ROM bytes at all

*Evaluate a filename expression* is `fname_fcb`, and it is **already shaped for
this**. It is a page-0 trampoline over two PAGE-1 halves:

```
fname_fcb:  call fname_expr      ; $6E91 — HL = cursor in; stashes FN_RESUME, STRSCR
            jp   pdfcb_resume    ; $6E8A — parse_disk_fcb, then HL = (FN_RESUME) out
```

Everything between the halves already crosses in **RAM** (`FN_RESUME`, `STRPTR`,
`STRSCR`), and `HL` is the only register in the contract — which the measurement
above says survives. So a disk-ROM handler reaches it as **two call-back sites,
14 B, all of them in `disk.rom`** (8820 B free), and **0 B in main page 1**.

🎯 **THIS DISSOLVES THE SEQUENCING TRAP BELOW.** That warning assumed a call-back
entry point costs bytes in main page 1. It does not: the entry points are the
existing page-1 labels. Phase 1 therefore needs no co-landing, and phase 2 becomes
purely net-negative — a verb leaves and nothing arrives.

### Phase 2 — the first verb, end to end

`ex_copy` (24 B) or `ex_kill` (44 B): body into `disk.rom`, its hook pointed at
the real body instead of `hk_present`, argument via the call-back. Green on
`diskbasic-acceptance` 34/34, `bdos-acceptance`, `kwsweep`, and **critically
`nodisk-acceptance`** — with the hook unclaimed the verb must still answer ERR 5.

⚠️ ~~**SEQUENCING TRAP.** Main page 1 had **3 B** free on 2026-09-15. A call-back
entry point costs bytes THERE, and the bytes only arrive when a verb LEAVES. So
phase 1's callee and phase 2's first move must land in **ONE SLICE** with a
net-negative footprint, or the first step does not fit.~~
✅ **WITHDRAWN 2026-09-15 by phase 1's measurement.** A call-back entry point costs
NOTHING in main page 1: the entry points are main's existing page-1 labels, reached
by address. The 3 B wall is real and still binds anything else, but it does not
bind this. Phase 2 may land on its own, and it only frees bytes.

### Phase 3 — roll out

One verb per slice, cheapest coupling first: the FAT-light four (`COPY`,
`FILES`/`LFILES`, `KILL`, `NAME` — 258 B), then the channel verbs (975 B), then
`field.asm` (600 B). Each slice its own battery. Each frees page-1 bytes, so it
gets easier as it goes.

#### ✅ THE FAT-LIGHT FOUR ARE DONE (2026-09-15)

`0f15a873` KILL · `b26857de` NAME · `3f6a6099` COPY · `e1bbf7e5` FILES/LFILES.

| | before | after |
|---|---|---|
| main page 1 | 3 B | **153 B** |
| page-0 low region | 0 B | **36 B** |
| `disk.rom` | 8820 B | 8502 B |

Both scarce budgets went from nothing to workable for ~320 B spent in the ROM
that has thousands spare. Each verb got cheaper than the last: COPY and
FILES/LFILES needed **no new call-back targets at all**, and COPY's saving landed
in the LOW REGION because `fname_fcb` died with its last caller.

#### 🔴 AND PHASE 3 STOPS HERE UNTIL A QUESTION IS ANSWERED

**There is no hook cell for any channel verb.** This ROM claims fourteen —
`H_DSKF`, `H_MKI`/`H_MKS`/`H_MKD`, `H_CVI`/`H_CVS`/`H_CVD`, `H_NAME`, `H_KILL`,
`H_FILE`, `H_DSKO`, `H_DSKI`, `H_COPY`, `H_ERRP` — and not one of them is `OPEN`,
`CLOSE`, `INPUT`, `LINE INPUT`, `MERGE` or `MAXFILES`.

🎯 **THE FOUR VERBS THAT MOVED ARE EXACTLY THE FOUR THAT HAD HOOKS** (`H_KILL`,
`H_NAME`, `H_COPY`, `H_FILE`). That is not a coincidence the plan noticed: its
"cheapest coupling first" ordering tracked hook availability without saying so.
The pattern is *point the verb's hook at a disk-ROM body* — with no cell to
point, it does not apply, and the remaining 975 B cannot start.

**This is a KNOWN open item arriving from the other side**: the CF-3300's census
is **35 claimed cells** (D-CFARCH) against our fourteen. Some of the other
twenty-one are very likely these verbs. Identifying them is an ORACLE
measurement — `scratchpad/hookid_probe.py`'s POKE method, with its two controls
(poke nothing must not move; poke a NAMED cell must flip its verb) — not a code
move, and it is the prerequisite for the rest of phase 3.

##### ✅ ONE CELL RECOVERED: `$FE5D` (D-CHANHOOKID, 2026-09-15)

[`hookid_chan.py`](../../scratchpad/hookid_chan.py) sweeps the twenty
unidentified cells from the LIVE 35-cell census — not the superseded 27-cell
scan the older probe used. Un-claiming a cell is `POKE <cell>,201`: a claimed
cell holds `F7 <slot> <lo> <hi> C9`, an unclaimed one is a bare `RET`.

| subject | baseline | flipped at | to |
|---|---|---|---|
| `OPEN"NOSUCH.DAT"FOR INPUT AS#1` | ERR 70 | **`$FE5D`** | ERR 51 |
| `MERGE"NOSUCH.BAS"` | ERR 70 | **`$FE5D`** | ERR 51 |

Exactly one cell of twenty moved, and the same one for both — so 🎯 **`$FE5D` is
not "OPEN's hook"; it is the cell both FILE-OPENING verbs route through**, which
is what MERGE opening a file to merge it would predict. Naming it for OPEN alone
would be a name narrower than its class.

All three controls passed on both sweeps: the baseline held with no poke;
un-claiming the already-named `H_FILE` flipped `FILES` to ERR 5, which is what
proves the METHOD works on this machine; and un-claiming `H_FILE` left the
subject unchanged, so a flip identifies a CELL rather than meaning some hook is
gone.

⚠️ **`CLOSE` AND `MAXFILES` ARE NOT MEASURED, AND THAT IS NOT "NO HOOK".** Four
attempts; each failed in the apparatus, never in the subject:
`CLOSE#1` on a never-opened channel is a NO-OP in both implementations and
`MAXFILES=2` simply succeeds, so both read baseline ERR 0 and nothing COULD
flip; a subject that opens a real channel first needs a disk and a line under
~38 columns; and even split and disk-backed it reads nothing inside the batch
while the identical program answers standalone at a wider capture gap. The probe
REFUSES (rc 2) rather than scoring a sweep with no baseline. They are the two
SMALLEST channel verbs (54 B and 41 B of 975), so this is filed rather than
chased.
⚠️ **`$FEB7` gave no reading in every sweep** and is listed as outstanding, not
as a negative.
⚠️ And a non-flip never proves absence: a cell can belong to a verb the sweep
does not run.

🔴 **FOUR APPARATUS FAULTS IN ONE MEASUREMENT, EACH PRODUCING A PLAUSIBLE
ANSWER** — the reason `ctrl.named` is built to fail:
| fault | what it looked like |
|---|---|
| the fence matched its own ECHOED source line (`PRINT"[0]"`) | twenty clean "no flip" rows |
| the subject could not reach a hook | "CLOSE has no hook" |
| a typed line past ~38 columns | no reading anywhere |
| the capture window too small for a disk WRITE | the same, but only in the batch |

#### AND THE COUPLING IS A DIFFERENT SHAPE TOO, MEASURED

[`xslot_chanprice.py`](../../scratchpad/xslot_chanprice.py) counts every call
site in each channel verb's span and resolves it against the symbol file. A
page-1 site costs 7 B and 0.156 ms **each time it runs**, so a site inside a loop
multiplies by the iteration count:

| verb | bytes | page-1 sites | of those, in a loop |
|---|---|---|---|
| `ex_open` | 560 | 40 | **18** |
| `ex_close` | 445 | 29 | **25** |
| `ex_input` | 131 | 16 | **10** |
| `ex_merge` | ? | 20 | 0 |
| `ex_maxfiles` | 41 | 7 | 0 |
| `ex_line` | 13 | 3 | 0 |

**The FAT-light four had about three sites each, all once per statement, and ZERO
in loops.** `ex_close` has twenty-five inside one — it walks a channel list
calling `eval` and four channel helpers per iteration. Routing each of those
through an inter-slot call is not the same design at all.
🎯 **THE ANSWER IS PROBABLY THAT THE HELPERS TRAVEL WITH THE VERBS** — `fch_check`,
`fch_select`, `fch_modes_ptr`, `fch_mode_class` are channel-only and small, so
moving the cluster turns twenty-five inter-slot calls per iteration into local
ones. That is a CLUSTER move, not a verb move, and it is a different slice shape
from anything phase 3 has done. ⚠️ The seam spec's 15 labels / 164 B called from
OUTSIDE `files.asm` are the ones that cannot travel.
⚠️ The table is a STATIC count and says so in the probe: a span belongs to the
verb that opens it only if nothing else jumps in, and a backward branch is a
necessary but not sufficient sign of a loop. It ranks candidates; it does not
authorise a move.

### Phase 4 — the FAT itself, and it is a SEPARATE DECISION

Whether `basic/fat.asm` follows the verbs is not a continuation of phase 3. It is
what would turn us from a DSKIO-driving host into a Disk-BASIC ROM.

⚠️ **AND THE "FOREIGN DISK ROM" ARGUMENT FOR KEEPING IT IS WEAKER THAN IT LOOKS.**
Joost, 2026-09-15: *"in practice I'd think any external cartridge providing a disk
also provides disk basic"* — and earlier, *"this seems a theoretical situation"*.
He is right, and it follows that with a foreign cartridge present **its** Disk
BASIC is what claims the hooks and what runs, whichever ROM our FAT sits in. That
is ordinary MSX behaviour, not a loss. So "interop with a DSKIO-only disk ROM"
describes hardware that does not exist and is NOT a reason to keep the FAT in
BASIC. `basic/fat.asm:11`'s *"disk-ROM-INDEPENDENT"* and the relocation spec's
*"the NECESSARY PRICE of the universal sector interface"* both rest on it and are
overstated; correcting them is a filed, separate item awaiting Joost.
🎯 **WHAT DOES STILL BEAR ON IT** is the charter, and only for OUR OWN primary
deployment, where our disk ROM IS the one present: **we reimplement MSX1 BASIC, so
we implement its disk verbs.** `hk_present` is `scf`/`ret` today, so there is no
alternative implementation to delegate to — the FAT is in BASIC because we are the
ones who wrote the verbs, not because of interop.
Out of scope until phase 3 is done and we can see what is left.

## 5. What this spec does not claim

* That the reference's handler uses any particular BIOS entry (§1.1).
* That our call-back must copy the reference's register or carry convention — ours
  is ours to define, and the reference's is not observable.
* Any byte figure for the finished architecture. §3 says why the existing one does
  not apply; phase 0b produces the first real one.
