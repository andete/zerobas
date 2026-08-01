<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — the MSX work-area (system variable) DENOMINATOR

**Status: PROPOSED, awaiting sign-off. No `basic/` or `sub/` edit is part of this
slice.**

Filed 2026-08-01 by D-CNAME as *"DOES ZEROBAS HONOUR THE OFFICIAL MSX RAM
VARIABLES? THERE IS NO DENOMINATOR"* ([`../TODO.md:3336`](../TODO.md:3336)).

---

## 1. Subject

One member of the class is already measured, and zerobas diverges. `$F414` is
MSX's `ERRFLG`; zerobas neither reads nor writes it, keeping the last error code
at `$E1C5` ([`../basic/sysvars.inc:847`](../basic/sysvars.inc:847)) inside the
freed `VARTAB` window, whose own comment says *"own choice — just-freed RAM"*.

```
                                vg8020  cf3300   zb
POKE&HF414,0  then PRINT ERR       0       0      8    (no effect on zb)
PEEK(&HF414)  after an error       8       8      0
POKE&HE1C5,0  then PRINT ERR       8       8      0
PEEK(&HE1C5)  after an error       0     255      8
```

`$F414` appears **nowhere** in the repo. The standard address was never
considered, and never rejected. That is not the finding — the finding is that
**there is no list against which the question could have been asked.** The
keyword surface had exactly this hole until 162 reserved words became
`make kwsweep`; the work-area table is the analogous list, and this slice builds
it.

⚠️ **This slice's framing is itself a hypothesis.** For four consecutive slices
the filed title has been the wrong subject (D-NAMBLANK, D-NAMDOT, D-LNLIST,
D-CNAME). "zerobas ignores the standard map" is the *obvious* reading of the row
above, and the obvious reading has lost four times running. zerobas already
honours `TXTTAB $F676`, `CSRX`/`CSRY $F3DD`/`$F3DC`, `RG0SAV $F3DF`, `LINLEN
$F3B0` and ~47 more, so a blanket rejection is refuted before the run starts.
The measurement has to say **which** addresses, not whether.

---

## 2. SCOPE — "uses" has three meanings, and only one is observable

| # | Question | Observable from BASIC? | In scope |
|---|----------|:---:|:---:|
| 1 | Does zerobas **write** what the reference writes? | only via its effect on 2 | ✗ |
| 2 | Does a read of that address **return the same value**? | **yes** | ✅ |
| 3 | Does zerobas **depend on** it internally? | no | ✗ |

**Recommendation, and this spec's scope: (2) only.** It is the one a program can
observe, so it is the one fidelity turns on — a program that `PEEK`s `ERRFLG`
gets the wrong answer on zerobas today, and that is the whole defect. (1) is
unobservable except through (2) and adds nothing a measurement can settle. (3) is
an implementation question about zerobas' own memory map, answerable by reading
this repo's source, and it is **not** a fidelity question at all.

⚠️ **Scoping to (2) has a cost, and it is stated rather than hidden:** a variable
zerobas maintains *correctly at a different address* is indistinguishable from one
it does not maintain at all. `ERRFLG` is exactly that case. The sweep reports it
as a divergence at `$F414`, which is true and is what a program sees; it does not
and cannot report "but the value exists at `$E1C5`". §9 is where that goes.

---

## 3. The denominator, and where it comes from

**Source: `~/projects/cbios/src/systemvars.asm`** (outside this repo — by decision
D1 no C-BIOS bytes live here), the pinned
C-BIOS checkout the repack build already depends on
([`../cbios-repack/README.md`](../cbios-repack/README.md), tag `v0.29-3-gb5ad9cb`).

Admissibility is not a judgement call here — it is already written down.
[`allowed-sources.md:121`](allowed-sources.md:121) rates **C-BIOS source B /
Conditional**, usable *"for facts (published sysvar addresses / memory map)
only"*. An address table is that fact and nothing else. Corroborating source of
the same facts: the **MSX Technical Data Book** ch. 2 work-area table
([`allowed-sources.md:108`](allowed-sources.md:108), B / Scoped). No reference-ROM
disassembly is involved on either side.

**279 entries, spanning `$F380`–`$FFFA`.** Measured against the current checkout,
not quoted from memory.

🔴 **The list is a GENERATOR ONLY. Every verdict comes from measurement.** This is
the same firewall `kwsweep` runs under, and for the same reason: C-BIOS is a peer
clean-room reimplementation, not an authority. If C-BIOS names an address the
references do not honour, the *references* win and the sweep says so.

⚠️ **The list is also not the span.** The sweep reads **every byte of
`$F380`–`$FFFE` (3199 B)**, not the 279 named ones. Names are the interpretation
layer applied afterwards. A byte that diverges and has *no* name is a finding the
named-only sweep would have thrown away.

---

## 4. Ownership — BIOS-owned vs BASIC-owned

Only the second is this project's to answer for. The split is made **mechanically
and checkably**, not by judgement:

* **BIOS-owned** — the symbol is referenced somewhere in C-BIOS source outside
  `systemvars.asm`. C-BIOS supplies it; zerobas does not, and must not.
  Divergence here is a C-BIOS-vs-reference-BIOS difference *below* the BASIC
  layer. The graphics arc already owns a worked instance: VDP R7 is excluded from
  every G8 assertion because C-BIOS programs it differently from the reference
  BIOS ([`../probes/basic/basic_probe_graphics.py:959`](../probes/basic/basic_probe_graphics.py:959)).
* **BASIC-owned** — C-BIOS never touches it. On a real MSX the *BASIC ROM* writes
  it, so on zerobas **zerobas** must, or nobody does. This is the bucket `ERRFLG`
  is in, and it is the bucket this slice is about.
* **Cross-referenced against zerobas**: does `basic/` or `sub/` mention the
  address literally? A first pass says **51 of 279**.

⚠️ **The static cross-reference is a GENERATOR TOO, never a verdict** — it has the
exact `INTERVAL` failure mode. "Absent from the source text" ≠ "absent from the
behaviour": an address can be written through a computed expression or an offset
from another symbol and never appear as a literal, and conversely a literal
mention does not mean the value stored there matches the reference's. Layer 1
generates candidates; layer 2 decides.

---

## 5. Instrument — a whole-span memory dump, not 3199 `PEEK`s

`omsx_repl`'s `("mem_abs", [(addr, len)])` capture already exists and is in
service ([`../probes/lib/omsx_repl.py:163`](../probes/lib/omsx_repl.py:163)); it
lowers to one openMSX `debug read_block memory`. So the entire work area comes
back in **one capture per case**, with **no BASIC payload delivered for the read
at all**.

That is not merely faster. It removes the whole payload-delivery failure class
from the read side: no tokeniser, no 38-char `KEYBUF` budget, no display-width
ceiling, no undeliverable characters. The `}` fake — a stable, *both-references-
agreeing* `<CA> X{5}` from a payload containing neither brace
([[both-oracles-agreed-payload-never-arrived]]) — cannot happen to a `read_block`.

🔴 **But the instrument is now a different one from the scope, and that gap is a
control, not a footnote.** §2 scopes this to what a `PEEK` returns; `debug
read_block` is not a `PEEK`. For `$F380`–`$FFFE` the two are the same CPU-visible
RAM in the default slot configuration — *assumed*, and therefore **pinned**:

> **C-INSTR.** A handful of addresses (a live one, a static one, a divergent one)
> are read **both** ways — through `PEEK` from BASIC and through `read_block` —
> on all three sides, and must agree. If they do not, no reading in the whole run
> is trustworthy and the run is void.

[[cursor-cluster-slice]]: pin the instrument first.

---

## 6. Verdict lattice, and the controls that make each verdict mean something

Per byte, per stimulus state:

| Verdict | Condition | Meaning |
|---|---|---|
| **VOLATILE** | differs between the two repeats of the *same* side | ticks/scans on its own — **no reading is possible**, on any side |
| **NO-ORACLE** | stable on both refs, but vg8020 ≠ cf3300 | the references do not agree, so there is nothing for zerobas to be right about |
| **AGREE** | refs stable and equal, zb equal | honoured, *at this stimulus* |
| **DIVERGE** | refs stable and equal, zb differs | the `ERRFLG` class |
| **INERT** | AGREE, but the byte holds the same value in the baseline state too | ⚠️ **agreement for the wrong reason** |

Three of these five rows exist because a naive sweep would count them as
successes:

1. 🔴 **VOLATILE is why `--repeat 2` is not optional.** `JIFFY`, the keyboard
   scan state, the `RND` seed and the cursor-blink counters move with no stimulus
   at all. A byte that changes on its own has no reading, and a single run cannot
   tell that byte apart from a divergence. **Each side is its own control here** —
   the repeat pair is run per side, not across sides.
2. 🔴 **NO-ORACLE is not "don't care".** The two references are structurally
   different machines (the CF-3300 has a disk ROM that claims work-area RAM and
   hooks; the VG-8020 does not), so this bucket will be large and *legitimately*
   so. It means **not measurable by this method**, which is a different statement
   from "not required". `$E1C5` reading 0 on one reference and 255 on the other is
   this bucket, and it is exactly why that address was free to take.
3. 🔴 **INERT is the `TAB(` trap in this surface.** Most of `$F380`–`$FFFE` will
   read the same on all three sides after a cold boot — much of it zero — and
   *that agreement proves nothing*, because a machine that never touches the byte
   agrees with one that does. `PRINT TAB(99999)` raised ERR 6 on both sides while
   the feature was **absent**; a byte reading `00` everywhere is the same shape.
   **An AGREE that is also INERT is reported as a non-result, and is excluded
   from the honoured tally.** [[kwsweep-msx1-denominator]].

The reciprocal control the brief demands — *a value like `0` means nothing
without a row pinning what "unset" looks like* — is the **baseline state itself**
(§7 `s0-boot`). Every stimulus verdict is a **delta against `s0-boot` on the same
side**, never an absolute value.

---

## 7. Stimulus battery

Each state is one boot; each is captured on 3 sides × 2 repeats. 3199 bytes per
capture.

**The load-bearing trio** — this is the filed finding turned into a class sweep:

| State | Payload | Role |
|---|---|---|
| `s0-boot` | *(nothing typed)* | 🟢 **CONTROL — the "unset" pin.** Every other verdict is a delta from here. |
| `s1-err` | `GOTO 99999` | the filed stimulus (Undefined line number, ERR=8). **Which bytes does the reference move when an error is raised, and which of those does zerobas move?** |
| `s2-noerr` | `A=1` | 🟢 **CONTROL — separates "moved because of the ERROR" from "moved because anything at all was typed."** Without it every byte the line editor touches reads as error state. |

`s1-err` is where `ERRFLG` lives, and it asks a strictly larger question than the
filed row did: the row asked about one address that was already suspected; the
sweep asks **what else moves**.

**Exploratory breadth**, clearly marked as such and not load-bearing:
`s3-def` (`DEFINT A`), `s4-var` (`A=1:B$="X"`), `s5-width` (`WIDTH 32`).
These exist to widen the *dynamic* coverage of the denominator; whatever they
find is a candidate, not a conclusion.

**Ordering is non-negotiable**: every state is oracle-locked
on **both references at `--repeat 2` before zerobas is run on it**. A mangle in
the oracle-lock direction is a false PASS forever.

---

## 8. Echo guard — mandatory, and here it is load-bearing in a new way

🔴 **A memory dump cannot tell "the byte did not move" apart from "the stimulus
never arrived."** A stimulus line that fails to deliver produces a capture
identical to the baseline on every side — a perfect, silent, three-way agreement
from a case that never ran. That is *this* surface's version of
[[both-oracles-agreed-payload-never-arrived]], and it fails **toward "pass"**.

So every stimulus state is run **twice**: once captured as memory, once captured
as **screen**, on **every side including zerobas** — not just the references
([[decblank-echo-guard-blind]], [[lof-probe-echo-guard]]). The screen pass must
show the stimulus' own evidence (for `s1-err`, an *Undefined line number* error;
for `s2-noerr`, a clean `Ok`). **A state whose delivery cannot be verified on a
given side yields no reading on that side** — it is not scored as agreement.

---

## 9. Deliverables

1. `probes/basic/basic_probe_sysvarsweep.py` — the sweep.
2. `make sysvarsweep` — modelled on `make kwsweep`: a **coverage report, not a
   pass/fail gate**. Its expected state is "N addresses diverge", so it exits 0
   with findings; a non-zero exit means the **apparatus** failed (C-INSTR, the
   echo guard, or the control group), not that coverage regressed.
3. `docs/sysvar-msx1-coverage.md` — the denominator itself: every entry, its
   address, owner, and verdict.
4. `TODO.md` — the item closed with its measurement, and whatever new items the
   sweep files.

**Explicitly NOT in scope, and left open on purpose:**

* ⚠️ **Whether `ERRFLG` should MOVE to `$F414` is a separate design question.**
  zerobas' memory map is its own, relocating live error state is not a free edit,
  and this slice ends with a *list*, not a relocation. Filed, not done.
* Meanings (1) and (3) from §2.
* Anything below `$F380` (zerobas' own tenant RAM at `$E1C0`+ is not part of the
  published map — on a real MSX it is ordinary user RAM, which is the whole reason
  it was available).
* The `dir-name` item, the `--say` batching item, and the ROM-region promotion
  work: **one item per session.**

---

## 10. Falsifiability — how this apparatus can be shown to have teeth

A sweep that reports nothing is indistinguishable from a sweep that measures
nothing, so the probe carries its own positive control:

> **C-REPRO.** The sweep must **independently reproduce the filed `$F414` row**
> under `s1-err`: `ERRFLG` DIVERGE, refs both `08`, zb `00`. It is derived from
> the same C-BIOS table as every other entry and gets no special handling.
> **If the sweep does not flag `$F414`, the apparatus is broken** — not the
> finding.

That control is what makes every *other* row in the report worth reading, and it
is the one row whose answer is already known from an independent measurement.

---

## Sign-off

Requested before any probe is written. The scope decision in **§2** and the
denominator source in **§3** are the two that are expensive to change later.
</content>
</invoke>
