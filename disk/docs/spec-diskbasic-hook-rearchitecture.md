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
* **0b — one real inter-slot call, disk → main page 1 → back, PRICED.** Bytes per
  call site and frames per call.
  ⚠️ `disk/pageenv.asm`'s `calslt_h` is a **simulated** CALSLT for the boot
  bridge — its own comment says it "calls IX directly" because those targets are
  already mapped. It cannot reach main page 1. The runtime route is the BIOS's
  own `$001C`, and **zerobas has never made a disk→BASIC inter-slot call**.
* **0c — interrupt safety across the disk-ROM window.** `htimi_guard`
  (`docs/spec-traps-t1-htimi-page1-safety.md`) already exists because a VBLANK can
  land while page 1 is a SUB-ROM tenant; main→disk already wraps `di`/`ei`
  (`basic/interp.asm:186`). Confirm the guard covers the disk-ROM window and the
  call-back's re-entry.

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

### Phase 1 — the interface

Define the call-back ABI: what the handler passes, what comes back, what stages in
RAM (§2's constraint). Then build exactly ONE callee — *evaluate a filename
expression* — the thing every disk verb needs.

### Phase 2 — the first verb, end to end

`ex_copy` (24 B) or `ex_kill` (44 B): body into `disk.rom`, its hook pointed at
the real body instead of `hk_present`, argument via the call-back. Green on
`diskbasic-acceptance` 34/34, `bdos-acceptance`, `kwsweep`, and **critically
`nodisk-acceptance`** — with the hook unclaimed the verb must still answer ERR 5.

⚠️ **SEQUENCING TRAP.** Main page 1 had **3 B** free on 2026-09-15. A call-back
entry point costs bytes THERE, and the bytes only arrive when a verb LEAVES. So
phase 1's callee and phase 2's first move must land in **ONE SLICE** with a
net-negative footprint, or the first step does not fit.

### Phase 3 — roll out

One verb per slice, cheapest coupling first: the FAT-light four (`COPY`,
`FILES`/`LFILES`, `KILL`, `NAME` — 258 B), then the channel verbs (975 B), then
`field.asm` (600 B). Each slice its own battery. Each frees page-1 bytes, so it
gets easier as it goes.

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
