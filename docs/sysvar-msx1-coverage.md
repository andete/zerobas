<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# MSX work-area coverage — the system-variable DENOMINATOR

Measured 2026-08-01 on three sides (Philips VG-8020, National CF-3300, zerobas
repack) at `--repeat 2`, boot-per-case, jittered. Reproduce with:

```bash
make sysvarsweep
```

Probe [`../probes/basic/basic_probe_sysvarsweep.py`](../probes/basic/basic_probe_sysvarsweep.py),
spec [`spec-basic-sysvar-denominator.md`](spec-basic-sysvar-denominator.md).
This is a **coverage report, not a pass/fail gate** — the same standing as
[`kwsweep-msx1-coverage.md`](kwsweep-msx1-coverage.md). A non-zero exit means the
**apparatus** failed, never that coverage regressed.

**Scope (spec §2, signed off): meaning (2) — does a READ of that address return
the same value.** Not "does zerobas write what the reference writes" and not
"does zerobas depend on it internally". ⚠️ The cost is stated rather than hidden:
a variable zerobas maintains **correctly at a different address** is
indistinguishable here from one it does not maintain at all — §3 is that story.

---

## 0. Why there was no denominator

`$F414` is MSX's `ERRFLG`. zerobas keeps the last error code at `$E1C5`
([`../basic/sysvars.inc:847`](../basic/sysvars.inc:847)), inside the freed
`VARTAB` window, whose own comment says *"own choice — just-freed RAM"*, and
`$F414` appears **nowhere** in the repo. The standard address was never
considered, and never rejected.

That was found **by accident**, while asking an unrelated question about clearing
`ERR` between probe cases. The keyword surface had exactly this hole until 162
reserved words became `make kwsweep`. This is the same list for the other
surface.

---

## 1. The denominator

**279 named entries spanning `$F380`–`$FFFA`**, generated from
`~/projects/cbios/src/systemvars.asm` in the pinned repack checkout
([`../cbios-repack/README.md`](../cbios-repack/README.md), tag
`v0.29-3-gb5ad9cb`). [`allowed-sources.md:121`](allowed-sources.md:121) rates
C-BIOS source **B / Conditional**, usable *"for facts (published sysvar addresses
/ memory map) only"* — an address table is that fact and nothing else.
Corroborating source of the same facts: the **MSX Technical Data Book** ch. 2
work-area table ([`allowed-sources.md:108`](allowed-sources.md:108)). No
reference-ROM disassembly on either side.

🔴 **The list is a GENERATOR ONLY. Every verdict below comes from measurement.**
C-BIOS is a peer clean-room reimplementation, not an authority; where it names an
address the references do not honour, the references win.

**The sweep reads every byte of `$F380`–`$FFFE` (3199 B), not the 279 named
ones.** Names are an interpretation layer applied afterwards, so a divergent byte
with no name survives instead of being discarded. (`$FFFF` is excluded on
purpose: on a machine with an **expanded slot** it is the secondary-slot-select
register, not RAM. zerobas' repack machine expands slot 3 and the VG-8020 does
not, so including it would manufacture a guaranteed three-way divergence out of a
hardware difference that is not a behaviour.)

---

## 2. What is even MEASURABLE — the answer is not 3199

Three buckets are excluded before any finding is counted, and each exists because
a naive sweep would have counted it as a success.

| Bucket | Bytes | Why it has no reading |
|---|---:|---|
| **VOLATILE** | **6** | moves on its own between two runs of the *same* side |
| **NO-ORACLE** | **311** | stable on both references, but vg8020 ≠ cf3300 (312 under `s5-width`) |
| **INERT** | ~2626 | the references do not move it under the stimulus |

**The 6 VOLATILE bytes are exactly the clock-derived ones** — `SCNCNT $F3F6`,
`REPCNT $F3F7`, `JIFFY $FC9E`(2), `INTCNT $FCA2`(2) — and all six are BIOS-owned.

⚠️ **`NO-ORACLE` is not "don't care".** The two references are structurally
different machines: the CF-3300 has a disk ROM that claims work-area RAM and
hooks; the VG-8020 does not. The bucket is large and *legitimately* so. It means
**not measurable by this method**, which is a different statement from "not
required". `$E1C5` reading `0` on one reference and `255` on the other is this
bucket, and that is exactly why the address was free for zerobas to take.

⚠️ **`INERT` is the `TAB(` trap on this surface.** Most of the work area reads
identically on all three sides after a cold boot, much of it zero — and a machine
that never touches a byte agrees with one that does. `PRINT TAB(99999)` raised
ERR 6 on both sides while the feature was **absent**; a byte reading `00`
everywhere is the same shape. INERT bytes are **excluded from the honoured
tally**, never counted as fidelity.

---

## 3. Layer 0 (static) — published NAME, private address

Needs no emulator, no reference ROM and no stimulus. zerobas' `sysvars.inc`
shares **46 symbol names** with the published map: **38 at the published address,
8 re-homed.**

| Symbol | zerobas | published |
|---|---|---|
| `VALTYP` | `$E0C8` | `$F663` |
| `FRETOP` | `$E268` | `$F69B` |
| `SAVTXT` | `$E1CF` | `$F6AF` |
| `SAVSTK` | `$E1C3` | `$F6B1` |
| `ONELIN` | `$E1C8` | `$F6B9` |
| `ONEFLG` | `$E1CA` | `$F6BB` |
| `ARYTAB` | `$E1C0` | `$F6C4` |
| `DEFTBL` | `$F153` | `$F6CA` |

🔴 **This is the `ERRFLG` shape, eight more times, and it was sitting in the
source the whole time** — the same freed `$E1Cx` window, the same "own choice"
provenance, the same published name kept over a private address.

⚠️ **Two limits, and both matter:**

* It matches on the **NAME**, so the very pair that started this item —
  zerobas' `ERRCODE`/`ERRLINE` against the published `ERRFLG`/`ERRLIN` — is
  **spelled differently and therefore invisible here**. The list is a **lower
  bound** on the class, not a census of it.
* **A shared name is not shared semantics.** zerobas' `SAVSTK` is documented as
  an SP anchor for the trap unwind; whether that is what the published `SAVSTK`
  holds is a question this comparison does not ask. A row says *"the standard
  address was not used"*, not *"the behaviour is wrong"*.

---

## 4. Cold boot (`s0-boot`) — the "unset" pin

The baseline is a control, not a result: **every stimulus verdict below is a
delta against it on the same side**, never an absolute value.

**256 bytes where the two references agree on a power-on value and zerobas
differs — 114 of them BASIC-owned.** They are the variables a real MSX BASIC ROM
*initialises* and zerobas leaves at zero: `USRTAB` (the ten `$475A` "Syntax
error" vectors), the `CS120`/`CS240` tape-timing constants, `ENDPRG`,
`CURLIN = $FFFF`, `KBFMIN`, `BUFMIN`, `VALTYP`, `TEMPPT`/`TEMPST`, `DEFTBL`,
`RNDX`, `MAXFIL`.

⚠️ A cold-boot agreement is the **weakest** reading in this report and is
labelled `INERT` throughout: it cannot distinguish "correctly initialised" from
"coincidentally the same untouched RAM".

---

## 5. Under stimulus

Each state is one boot per side per repeat. The honest headline is the last
column: **of the bytes the references MOVE, how many does zerobas move
identically?**

| State | payload | refs move | zerobas matches | DIVERGE |
|---|---|---:|---:|---:|
| `s1-err` | `GOTO 99999` | 32 | **13** | 19 |
| `s2-noerr` 🟢 | `A=1` | 27 | **6** | 21 |
| `s3-def` | `DEFINT A` | 17 | **11** | 6 |
| `s4-var` | `A=1:B$="X"` | 41 | **13** | 28 |
| `s5-width` | `WIDTH 32` | 25 | **11** | 14 |

`s3`–`s5` are **exploratory breadth**, not load-bearing: what they find is a
candidate, not a conclusion.

---

## 6. 🔴 The headline — the filed row was the smallest part, and the CONTROL is what says so

Nineteen bytes diverge under `GOTO 99999`. The obvious write-up is *"19 bytes of
error state diverge"*. **That would have been wrong by roughly four times, and
`s2-noerr` is the row that proves it:**

```
s1-err  DIVERGE: CSRY KBUF+1..6 BUF CONTXT CONSAV CONTYP CONLO LINTTB  ERRFLG ERRLIN ERRTXT
s2-noerr DIVERGE: CSRY KBUF+1..2 BUF CONTXT CONSAV CONTYP CONLO LINTTB  + TEMP/TEMP2/TEMP3
                  \_______________ identical set, from a line that RAISES NO ERROR ______/
```

**Exactly three variables are error-SPECIFIC:**

| Variable | addr | refs (00 →) | zerobas | zerobas keeps it at |
|---|---|---|---|---|
| `ERRFLG` | `$F414` | `08` | `00` | `ERRCODE $E1C5` |
| `ERRLIN` | `$F6B3` | `FF FF` | `00 00` | `ERRLINE $E1C6` |
| `ERRTXT` | `$F6B7` | `1E F4` | `00 00` | — |

Everything else in the `s1-err` set — the line-input buffers `KBUF $F41F` /
`BUF $F55E`, and the `CONTXT`/`CONSAV`/`CONTYP`/`CONLO` resume anchor at
`$F666`–`$F66A` — the references rewrite on **every direct-mode line**, error or
not. They are not error state at all.

**The class is therefore bigger and different than filed**: it is not "zerobas
ignores `ERRFLG`", it is *"zerobas keeps its BASIC bookkeeping — error state,
`CONT` state, input buffers, array pointers — in its own RAM window, and the
published addresses stay at their power-on values."*

**66 named variables diverge in at least one state: 45 BASIC-owned (zerobas' to
answer for), 21 BIOS-owned** (C-BIOS's, below the BASIC layer — the same class as
the VDP R7 exclusion the graphics arc already carries).

---

## 7. What this report does NOT say

* **Not that zerobas ignores the standard map.** It honours `TXTTAB $F676`,
  `CSRX`/`CSRY`, `RG0SAV $F3DF`, `LINLEN $F3B0` and 38 more symbols at their
  published addresses. The measurement says **which**, not whether — and the
  blanket reading was refuted before the run started.
* **Not that any of this should be fixed.** Whether `ERRFLG` should move to
  `$F414` is a **separate design question**: zerobas' memory map is its own and
  relocating live error state is not a free edit. This slice ends with a list.
* **Not a verdict on the 311 `NO-ORACLE` bytes.** They are unmeasurable by
  *this* method, which is not the same as unimportant.
* **Nothing about meanings (1) and (3)** from spec §2.

---

## 8. Apparatus — and the two defects its own controls found in it

Three self-controls, all green in the quoted run:

* **echo guard** — every stimulus is also run as a SCREEN pass on **every side
  including zerobas**, because 🔴 *a memory dump cannot tell "the byte did not
  move" from "the stimulus never arrived"*: an undelivered line produces a
  perfect, silent, three-way agreement, failing **toward "pass"**.
* **C-INSTR** — the four addresses are read both through `PEEK` and through
  `read_block`, over the **identical payload**, on all three sides. One of them is
  `$F414` in the error state, so the instrument is pinned on the byte the whole
  finding turns on.
* **C-REPRO** — the sweep must independently re-find the filed `$F414` row with
  no special handling. It does. A sweep that reports nothing is indistinguishable
  from a sweep that measures nothing.

🔴 **Two of the probe's own defects were caught by its controls, not by luck:**

1. **The volatility control was connected to nothing.** The first cut jittered
   `cap_gap` — which is the gap *after* a case's capture, and this probe is
   boot-per-case, so the knob reached the emulator's exit and not the reading.
   It reported **`VOLATILE = 0` across the entire work area, JIFFY included**,
   while looking like it worked. Measured rather than argued: the same payload at
   `cap_gap` 2.5 and 4.2 returns `JIFFY = $01D3` **both times**; shifting `boot`
   by 1.7 s returns `$0229`, a delta of 85 ticks — exactly 1.7 s of the VG-8020's
   50 Hz. **openMSX is deterministic**, so every clock-derived byte samples at
   the identical emulated instant and reads back bit-identical
   ([[deterministic-mangle-is-still-a-mangle]] pointed at a new target). With the
   jitter on `boot`, `REPCNT` stopped being reported as zerobas *"EXTRA-moving a
   byte the references leave alone"* — **a false finding the broken control had
   published.**
2. **C-INSTR failed on all three sides at once, and was not an instrument
   fault.** The payload contains `"["` and `"]"` as literals, so its own **echo**
   puts a bracket pair on screen ahead of the output; a leftmost match spanned
   the echo and parsed as nothing. `result_span_after_echo` could not be used
   either — it anchors on a row that *equals* the command line, and this echo
   **wraps across two rows**. Anchoring on the **last** pair is correct and fails
   in the safe direction: a payload that printed nothing voids the run instead of
   passing it.

⚠️ A third, milder one: the C-BIOS table parser first anchored on a bare
end-of-line and silently dropped the 10 entries C-BIOS annotates inline — among
them **`JIFFY`** — after which the extent derivation absorbed the hole into its
neighbour and labelled the single most volatile byte in the work area
`PADX+1`. **A wrong name on a divergent byte is worse than no name.**

---

## 9. Filed by this sweep

* **`ARYTAB`/`STREND`/`ARYTA2` diverge under `A=1:B$="X"`** — the array/string
  pointers, the same re-homing shape as the error state (§3).
* **`CONTXT`/`CONSAV`/`CONTYP`/`CONLO` never move on zerobas**, on every
  stimulus measured. The `CONT` arc landed
  ([`../TODO.md`](../TODO.md), D-CONTR/D-CONTD) holding that state elsewhere.
* **`KBUF $F41F` and `BUF $F55E` stay zero on zerobas** while both references
  rewrite them on every direct-mode line.
* **`s3`–`s5` breadth is thin.** The dynamic denominator covers 5 stimuli; the
  *static* one covers all 279 entries. Widening the stimulus set is the obvious
  next increment, and `--only` makes it cheap.
</content>
