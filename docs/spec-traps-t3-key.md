# spec — interrupt-traps T3: the KEY trap (`ON KEY GOSUB` + `KEY(n) ON/OFF/STOP`)

Status: **DRAFT — awaiting sign-off.** Slice packet for T3 of the interrupt-traps arc
([`docs/spec-basic-interrupt-traps.md`](spec-basic-interrupt-traps.md), signed off
2026-07-24, slicing T1→T2→T3→T4). T1 (STOP) landed 2026-07-25 (`4fef347`,
[`spec-traps-t1-stop-reslice.md`](spec-traps-t1-stop-reslice.md)) with the reusable
skeleton; T2 (STRIG) landed 2026-07-25 (`00a593a`,
[`spec-traps-t2-strig.md`](spec-traps-t2-strig.md)) with the first device event source.
**T3 closes the other half of the input-devices `D-I-5` handoff** — `KEY(n) ON/OFF/STOP`
currently aborts with a divergence `ERR 2`.

Clean-room: every semantic below is **measured black-box on the Philips VG-8020** (§1);
the RAM layout, the detection mechanism and the divert mechanism are own-design. No
reference ROM bytes were read or decoded. The keyboard matrix rows, `NEWKEY`, and
`KEYBUF`/`GETPNT`/`PUTPNT` are **published contracts** (MSX Technical Handbook; the
buffer trio is already relied on and black-box-verified against C-BIOS — see
[`basic/PROVENANCE.md:2815`](../basic/PROVENANCE.md)).

> **T3 is NOT "T2 with ten entries."** T2's STRIG source samples a *level* and
> edge-detects it. The oracle says the KEY trap is a **delivery** trap: it fires on the
> BIOS key-delivery event — initial make **and every auto-repeat** — and it **removes
> that delivery from the input stream**. That difference is the whole slice.

---

## 1. Oracle characterization (VG-8020, 2026-07-25)

Six rounds of boot-per-case openMSX runs on `Philips_VG_8020`, driving the function
keys through the keyboard matrix (row 6: bit 0 SHIFT, bits 5/6/7 F1/F2/F3; row 7:
bits 0/1 F4/F5; F6–F10 = SHIFT + F1–F5) and reading RAM sentinels via `POKE`/`PEEK`.
Scripts `key_trap_char{,2,3,4,5,6}.py` (to be promoted into `probes/basic/` as the
gate, §8).

### 1.0 Apparatus — two rounds were VOID, and why that matters

Rounds 1–2 measured "did the key still reach the program?" with
`FOR I=1 TO 4000: A$=A$+INKEY$: NEXT`. **4000 string concatenations never reach the
sentinel `POKE` inside the capture window**, so that column read 0 unconditionally —
including for the *untrapped baseline*, which cannot be 0. Every `aux` reading in
rounds 1–2 is therefore void, and round 1's apparent finding "the trapped key's string
is suppressed" was **not evidence**; it is re-established properly in round 3 (T1/T2).

Round 5 then repeated the mistake in a second shape: its calibration `POKE`d
`(TIME-T)` straight into a byte, which is `ERR 5` for any loop over 255 jiffies, and
its "slow handler" (`FOR J=1 TO 30000`) had **not returned** by the end of the capture
window — so its `cnt==1` said nothing about latching.

**Method adopted from round 3 on, and required of the gate:** no string building; a
`TIME`-bounded observation window (`T=TIME` … `IF TIME-T<400 GOTO`), and a **`done`
sentinel that every reading is gated on** — a program that errored out or is still
running is discarded, never read as a measurement. Handler-timing cases size the
handler from a *measured* loop rate, and the handler itself records entry (`1`) and
exit (`2`) so "was it still running?" is observed rather than assumed.

> This is the **T2 lesson recurring for the third time in this arc**
> ([[traps-t2-strig-slice]]): the measurement apparatus is part of the measurement,
> and a baseline that cannot produce a non-zero answer proves nothing. **Calibrated
> constant:** `FOR J=1 TO 3000` takes **~4.8 s** on the VG-8020 (~625 iterations/s).

### 1.1 The event: delivery, not level

| # | case | result | conclusion |
|---|------|--------|------------|
| K1 | `ON KEY GOSUB 100` + `KEY(1) ON`, tap F1 | fires once | a single-line list arms F1 |
| K3 | two taps | fires twice | `RETURN` re-arms |
| K5 | arm, no `KEY(1) ON`, tap | never fires | arm ≠ enable (as T1/T2) |
| K2 | F1 **held 3 s** | fires **39×** | **not edge-per-press — it repeats** |
| T1 | *untrapped* baseline, `KEY 1,"X"`, held 3 s | **38 deliveries** | … |
| T2 | *trapped*, same hold, same loop | **39 fires**, 0 leaked | **the trap event IS the BIOS key-delivery event** |

`KEY 1,"X"` makes the F1 expansion one character, so an `INKEY$` drain counts
deliveries exactly. Trapped fires (39) ≍ untrapped deliveries (38) for the identical
hold: the trap fires once per delivery — the initial make plus each auto-repeat.

**Repeat timing** (hold length → fires): 0.6 s → 1, 0.7 s → 1, 0.8 s → 2, 0.9 s → 4,
1.2 s → 9, 3.0 s → 39, 4.0 s → 56. So an **initial delay of ≈0.7–0.8 s** (≈35–40
frames at 50 Hz) then a steady **≈17 Hz** (one per ~3 frames).

**`KEY 1,""` still fires** — once on a tap (R8) and 39× on a 3 s hold (R9). An empty
expansion puts *nothing* in the buffer, so **the event is upstream of string expansion**.
This falsifies any implementation that watches `KEYBUF` for insertions; the key must be
detected from the matrix itself (§4).

### 1.2 Diversion: a trapped key is removed from the input stream

Baseline (T1) is 38 delivered characters. All rows below hold F1 for the same 3 s with
`KEY 1,"X"`, and every row has `done==1`.

| # | state of entry KEY 1 | fires | chars reaching `INKEY$` | conclusion |
|---|---|---|---|---|
| T1 | (no trap at all) | 0 | **38** | baseline |
| T2 | **ON**, handler armed | 39 | **0** | trapped ⇒ **diverted** |
| T5 | **ON**, handler slot **empty** | 0 | **0** | **diversion follows the STATE alone** — an enabled-but-unarmed key is silently swallowed |
| T3 | **OFF** | 0 | **38** | delivered normally |
| T4 | **STOP** | 0 | **38** | delivered normally — **`STOP` does not eat the key and does not latch** |
| T6 | control: F2 held, only F1 trapped | 0 | **190** | untrapped keys unaffected (190 = 38 × F2's 5-char default) |

T5 is the easy-to-miss one: diversion is a property of the entry **state**, not of
having a handler. T3/T4 give the same `STOP` ≡ `OFF` narrowing T2 found for STRIG.

### 1.3 Servicing, blocking input, priority

| # | case | result | conclusion |
|---|------|--------|------------|
| W1 | press again inside a **measured** handler that provably returns (`done==2`) | fires **twice** | a press during **SERVICING is diverted and latched**, firing once after `RETURN` — the T2 rule |
| U2 | F1 tapped while blocked in `INPUT` (`INPUT` provably reached) | **does not fire** | **no dispatch from inside blocking input** — a statement-boundary dispatcher is faithful |
| K7 | SHIFT+F1 with both `KEY(1)` and `KEY(6)` ON | fires **KEY 6** | F6–F10 = SHIFT+F1–F5, and SHIFT is **discriminated** |
| R11 | SHIFT+F1 with only `KEY(1)` ON | never fires | ditto, from the other side |
| U3 | F1+F2 pressed in one frame | both fire; last serviced = **KEY 1** | … |
| V2 | F1+F2+F3 in one frame | all three fire; last serviced = **KEY 1** | within the family the reference services **high-numbered first** (`ct_find` scans ascending — §6) |

### 1.4 Parse surface

| # | case | result |
|---|------|--------|
| K16 | `ON KEY GOSUB` with **10** slots | accepted |
| K15 | an **11th** slot | **ERR 2** |
| K11/K12 | `KEY(11) ON` / `KEY(0) ON` | **ERR 5** |
| K8 | `ON KEY GOSUB 100,200` + `KEY(2) ON`, tap F2 | fires the *second* line — the list is positional |
| K10 | `KEY OFF` (display form) then the trap form | accepted, still fires |

**No deviation is needed for the over-long list**: unlike T2's 6th STRIG slot (which
takes the reference machine down, and where zerobas ships a deliberate trappable
`ERR 2`), the reference raises a clean `ERR 2` here by itself. `ERR 5` for an
out-of-range `n` matches T2's `STRIG(5)` precedent exactly.

---

## 2. The model (own-design, observationally equivalent)

> A function key **n** whose `ZTRAP` entry state is **ON or SERVICING** is **diverted**:
> every key-delivery event for it — the initial make and each auto-repeat — is removed
> from the input stream, and sets that entry's PENDING bit. While the state is **OFF or
> STOP** the key is not diverted, not sampled, and never latched: it is delivered to the
> input stream exactly as an untrapped key. Diversion depends only on the state, so an
> enabled entry with no handler swallows its key and fires nothing.

Sampling while ON *or* SERVICING is the identical rule T2 arrived at, and both states
already have state bit 0 set (`ON=01`, `SERVICING=11`) while neither unsampled state
does (`OFF=00`, `STOP=10`) — so the per-entry test stays one `bit 0,(hl)`, and
`trap_return_check`'s existing re-raise of `TRAPPEND` on `RETURN` delivers §1.3/W1 for
free. **No shadow-seeding rule is needed** (T2's subtlest mechanism): because the event
is a delivery rather than a level, a key already held when the trap is enabled simply
produces its next repeat delivery — there is no spurious edge to suppress.

---

## 3. RAM

No new allocation: `ZTRAP` entries 8..17 (`ZTI_KEY1` = 8, `KEY n` → `7+n`) are already
reserved and already zeroed by `trap_init` ([`basic/sysvars.inc:791`](../basic/sysvars.inc),
[`basic/traps.asm:147`](../basic/traps.asm)). T3 adds only the detector's own scratch:
a 2-byte previous-matrix snapshot (rows 6 and 7), a 1-byte "which key is repeating"
and a 1-byte repeat countdown — 4 B, inside the ~53 B of headroom the arc spec §3 left
in the VARTAB window.

---

## 4. The event source — and the one real design fork

`event_poll` ([`basic/traps.asm:53`](../basic/traps.asm)) runs from `H.TIMI`, DI,
register-transparent, and is **pinned to resident page-1 code** (the VBLANK `CALSLT`
ban). The KEY source must live there too.

**Detection** is settled by §1.1: read the raw matrix rows from **`NEWKEY`** (published
work area, rows 6 and 7 carry SHIFT and F1–F5), fold SHIFT into the key number
(1–5 / 6–10), and compare against the previous frame's snapshot. This is two RAM loads
per frame plus a bit walk — no port I/O, no BIOS call, cheaper than T2's five `GTTRIG`
calls. A `KEYBUF`-watching design is ruled out by R8/R9 (an empty expansion still fires).

**Auto-repeat and diversion are the fork.** Both are genuinely observable (§1.1, §1.2)
and both cost bytes; neither can be inherited from the host BIOS, because we detect the
key from the raw matrix rather than from the BIOS's decode layer.

**D-T3-1 — diversion fidelity. ✅ DECIDED 2026-07-25: patch C-BIOS, with a THIN HOOK.**

D-T3-3 (below) showed no published hook can see the current frame's insertion, and a
sweep of **all ~112 hook slots** confirmed no post-scan seam exists while a program runs
(§4.1). The alternatives were "no diversion" (a visible deviation), a measurably racy
flush (~1 press in 4 leaks), or a deferred-publish scheme that inverts the race at the
cost of rewiring zerobas's readers. **The decision is to patch C-BIOS** — which is what
a real MSX does, since there BASIC *is* the BIOS and its KEY trap sits inside the scan.

**This is an established, audited mechanism, not a new one.** zerobas already ships
[`cbios-repack/eu-drop-statements.patch`](../cbios-repack/eu-drop-statements.patch): a
tracked 0BSD patch describing edits to BSD-licensed C-BIOS **source**, applied to a
**pinned tag** in a throwaway worktree at build time and **sha1-verified**
([`tools/build_repacked_cbios.py`](../tools/build_repacked_cbios.py)); **no C-BIOS bytes
live in the zerobas repo** (decision D1). C-BIOS source is a *build input*, not a stock
reference ROM, so reading it does not touch the no-disassembly rule
([[no-reference-rom-disasm]]).

**Thin hook, not fat logic.** The patch must NOT teach C-BIOS about `ZTRAP` — that would
put BASIC policy inside the BIOS and force a re-pin on every semantic change. Instead it
adds **one 5-byte RAM hook**, exactly like `H.TIMI`, and all policy stays in zerobas:

- **Insertion point:** `put_key_fnk` (`cbios/src/main.asm:2830`), reached with
  **A = the function-key index 0–4**, immediately *before* the `FNKSTR` expansion loop.
- **Contract:** call the hook with A = index; **CF=1 ⇒ swallow this delivery entirely**
  (skip the expansion), CF=0 ⇒ expand as now. Default vector = `ret` with CF clear, so
  an unpatched/non-BASIC boot is unaffected.
- **zerobas side:** install the handler at boot beside `play_install`. The handler folds
  SHIFT, indexes `ZTRAP`, and if the entry is ON/SERVICING sets PENDING + `TRAPPEND` and
  returns CF=1.

**Why this is the *better* engineering answer, not merely the acceptable one:** hooking
where the BIOS has *already decoded the key* deletes three of T3's hardest parts at once
— the `NEWKEY` matrix scan and SHIFT fold, the hand-rolled auto-repeat (D-T3-2 becomes
moot: repeat is inherited from the host BIOS, which is *more* faithful than replicating
the VG-8020's constants), and the diversion race. It also lands the empty-expansion case
(§1.1 R8/R9) for free: the hook fires at `put_key_fnk` *entry*, before the loop that
would have inserted nothing. See §7 for what this does to the budget.

### 4.2 F6–F10 on the target (D-T3-7) — MEASURED 2026-07-25

C-BIOS's branch above `put_key_fnk` maps rows `$05`/`$04` to indices 0–4 and indexes
`FNKSTR` by `A*16`, with **no SHIFT fold**. Whether SHIFT+F1 nevertheless *reaches* that
path decided between "fold SHIFT in our handler" and "extend the patch", so it was
measured rather than reasoned about.

`shift_fkey_probe.py`: C-BIOS never initialises `FNKSTR`, so seed slots 0/1/5 by `POKE`
with the distinct one-char expansions `"1"`/`"2"`/`"6"`, then idle in a loop that
consumes nothing and let the BIOS's own insertions pile up in `KEYBUF`; the debugger
reads the pending bytes from `GETPNT` to `PUTPNT`. **The inserted character is the index
the BIOS chose.** Press F1, F2, SHIFT+F1:

| machine | pending | reading |
|---|---|---|
| Philips VG-8020 (reference control) | **`126`** | folds SHIFT itself → slot 5 (F6) — confirms §1.3 K7 at the buffer level |
| C-BIOS repack (target) | **`121`** | **reaches `put_key_fnk` with index 0**; SHIFT ignored |

**✅ D-T3-7 resolved: fold SHIFT in our handler.** SHIFT+F1 *does* arrive at the hook, so
reading `NEWKEY` row 6 bit 0 there (current, because the hook runs inside the scan) and
mapping index 0–4 → key 1–10 costs ~8 B and keeps the patch semantics-free. No patch
extension is needed.

> **Apparatus note — the §1.0 discipline bit again.** The first control run returned an
> *empty* buffer: that version of the program **ended**, and the returning REPL's `CHGET`
> ate the buffered characters before the capture. The target had only kept them because
> its loop happened never to terminate. **A control that returns "nothing" must be fixed,
> not interpreted.** The idle loop is now infinite by construction, and `$D004=7`
> positively asserts "program started and is idling".

**Adjacent free win — needs a call.** Because C-BIOS passes index 0 for SHIFT+F1, an
*untrapped* SHIFT+F1 on the target expands F1's string where the reference expands F6's
— a **pre-existing C-BIOS divergence, not one T3 introduces**. Since the handler computes
the folded index anyway, widening the hook contract to **A in/out** (the BIOS expands
whichever index the hook returns) fixes it for ~0 extra bytes on our side plus one `ld`
in the patch, and stays semantics-free. *Rec: adopt — it makes trapped and untrapped
function keys agree with the reference in one stroke.*

**D-T3-2 — auto-repeat.** (a) Replicate it with our own delay/rate constants sized from
§1.1 (≈38 frames then every ~3), ~25–30 B; or (b) fire once per physical press, ~0 B, a
documented deviation (a 3 s hold fires 1× instead of 39×). *Recommendation: (a)* — the
count difference is large and easy for a program to depend on. Note that under (a) our
repeat cadence is **ours**, not the host BIOS's, so a trapped key and an untrapped key
on the same machine may repeat at slightly different rates; that residual is
unavoidable given detection must be matrix-based, and belongs in `PROVENANCE.md`.

**✅ D-T3-3 — ISR ordering: MEASURED 2026-07-25, and the answer is the awkward one.**

`htimi_order_probe.py` breakpoints the timer ISR entry (`$0038`) and both published
interrupt hooks (`H.KEYI $FD9A`, `H.TIMI $FD9F`), watchpoints writes to `KEYBUF`
(`$FBF0..$FC17`) and `PUTPNT` (`$F3F8`), presses SPACE at the prompt, and reads the
interleaving within the ISR invocation that actually inserted. (Execution *order* of
published addresses only — no ROM bytes read or decoded.) Both machines, identically:

```
ISR -> HKEYI -> HTIMI -> KEYBUF -> PUTPNT
       C-BIOS repack (the target):  both hooks BEFORE the scan
       Philips VG-8020 (reference): both hooks BEFORE the scan
```

**Neither published hook can see the current frame's insertion.** The reference MSX
does not need one — there BASIC and the BIOS are the same ROM, so its KEY trap lives
*inside* the scan routine. zerobas has no such seam.

**Consequence.** At `H.TIMI` on frame *N*, both `NEWKEY` and the `KEYBUF` insertion
reflect frame *N−1*'s scan. Detection being one frame late is harmless (the trap still
fires once per delivery). Diversion is what suffers: the character is readable by
mainline BASIC for the ~19 ms between the frame-*N−1* insert and our frame-*N* poll.

**Exposure, measured rather than assumed:** a BASIC `INKEY$` polling loop runs
**~80 polls/s on the VG-8020 — ~1.6 per 50 Hz frame**. zerobas is ~7× slower
([[traps-t2-strig-slice]]), so ~0.25 polls/frame — i.e. a flush at the next `H.TIMI`
would still lose the race on **roughly one trapped press in four**. Nondeterministic
diversion is worse than an honest deviation, which is what drove D-T3-1 to the patch.

### 4.1 Falsifying the cheap way out — the full hook sweep

Before accepting a C-BIOS patch, the cheap possibility was tested rather than assumed
([[dont-prematurely-wall]]): the MSX hook area is ~112 five-byte slots
(`$FD9A`–`$FFC9`), and *any* of them firing between the insertion and the end of the ISR
would be an exact, **BIOS-agnostic** seam — strictly better than a patch.
`hook_sweep_probe.py` breakpoints every slot plus a `KEYBUF` watchpoint.

At the **BASIC prompt** four slots fire and two (`$FDA4`, `$FDC2`) do land after the
insert — but that is an artefact: the REPL is sitting in `CHGET`, so those are *mainline*
calls, not ISR ones. Re-run with a **BASIC program executing** (the only state in which
traps dispatch at all) and they vanish:

```
prompt:          ISR -> HFD9A -> HFD9F -> KEYBUF -> HFDA4 -> HFDC2
program running: ISR -> HFD9A -> HFD9F -> KEYBUF          <- nothing after
```

**No post-scan hook exists in the case that matters.** The negative result is what
justifies the patch; without the program-running control the sweep would have produced a
false positive and a seam that evaporates the moment a trap could actually fire.

---

## 5. Parsing — T3 is mostly a generalisation of T2, not new code

T2 deliberately pre-paid for this: `trap_line_link`
([`basic/program.asm:1331`](../basic/program.asm)) already factors the optional
`$0E,lo,hi` handler-line resolver "for T3's `ON KEY` list."

- **`ON KEY GOSUB <l1>,…,<l10>`** — `ex_on_strig`
  ([`program.asm:1379`](../basic/program.asm)) is already exactly this loop with a base
  index and a slot limit hard-coded (`ZTI_STRIG0`, 5). Generalise those two into
  registers and `ON KEY` is a handful of bytes plus a `cp KEY_TOKEN` peek in `ex_on`
  ([`program.asm:1063`](../basic/program.asm)). `KEY` is the single-byte token `$CC`
  ([`sysvars.inc:1453`](../basic/sysvars.inc)), so the peek is cheaper than T2's
  two-byte `$FF $A3`.
- **`KEY(n) ON|OFF|STOP`** — `ex_strig_stmt`
  ([`program.asm:1423`](../basic/program.asm)) is likewise the same parser with
  `ZTI_STRIG0`/limit 5/`ERR 5` baked in. Generalise to (base, lo, hi) and the KEY form
  is the `(`-peek in `ex_key` plus a parameter load. The T2 shadow-seeding tail (§2:
  not needed for KEY) is skipped via the same parameter.
- **`KEY ON` / `KEY OFF` disambiguation** — `ex_key`
  ([`basic/screen.asm:196`](../basic/screen.asm)) currently accepts only `ON`/`OFF` and
  falls through to `stmt_error`. Add a `(` test ahead of them (K10 confirms the display
  form must keep working unchanged).

Sharing rather than duplicating is what makes T3 affordable; see §7.

---

## 6. Dispatch and priority

`check_traps`/`ct_find` ([`basic/traps.asm:229`](../basic/traps.asm)) need no structural
change — the KEY entries are already in the table and already scanned.

**D-T3-4 — intra-family order.** `ct_find` scans **ascending**, so with F1+F2+F3 pending
in one frame it would service KEY 1 → 2 → 3; the reference services **3 → 2 → 1** (V2).
The observable difference is only the *order* of handler execution when two function
keys are struck within the same frame — rare, but cheap to match (scan the KEY band
descending, or lay the band out reversed). *Recommendation: match the reference*; it
costs a few bytes and removes a gratuitous divergence. If it proves more than ~10 B,
accept ascending and document it.

---

## 7. Byte budget and funding

**Measured now: page-1 free = 9 B, page-0 low region = 6 B** (`make basic-reloc`).
T3 does not fit; a carve is required, exactly as T1 and T2 needed one.

Estimate — deliberately pessimistic, because **T2's estimate was low by 70 B**:

**The C-BIOS hook (D-T3-1) roughly halves this slice.** Hooking where the BIOS has
already decoded the key deletes the matrix scan, the auto-repeat replication and the
diversion machinery outright:

| part | pre-hook est. | **with the hook** |
|---|---|---|
| `event_poll` KEY detector (matrix decode + SHIFT fold + edge) | ~70 B | **0** — the BIOS decoded it |
| auto-repeat (D-T3-2) | ~30 B | **0** — inherited from the host BIOS |
| diversion (D-T3-1) | ~45 B | **0** — `CF=1` on return |
| hook handler (SHIFT fold + `ZTRAP` index + PENDING/`TRAPPEND` + CF) | — | ~45 B |
| hook install at boot (beside `play_install`) | — | ~10 B |
| `ON KEY GOSUB` list (generalising `ex_on_strig` + the `ex_on` peek) | ~30 B | ~30 B |
| `KEY(n) ON/OFF/STOP` (generalising `ex_strig_stmt` + the `ex_key` peek) | ~35 B | ~35 B |
| intra-family order (D-T3-4) | ~10 B | ~10 B |
| **total** | **~220 B** | **~130 B** |

Plus, outside the BASIC ROM: ~10 lines of C-BIOS source patch, a re-pinned
`REPACKED_SHA1`, and an IPS/BPS rebuild ([[ips-rebuild-after-basic-change]]).

**Funding — the carve is available, and this is the good news of the slice.** A closure
scout over page-1 (`carve_scout.py`, static call-graph walk against
[[page0-tenant-eval-eviction-constraint]]: a page-0 tenant may call main page-1, RAM and
BIOS, but nothing in `$2812–$3FFF`) found the cassette program-load cluster is a clean
candidate:

| cluster | page-1 size | page-0-low escapes |
|---|---|---|
| `do_cload` / `do_tape_prog` / `ctp_line` / `dpl_line` (`cload.asm`) | **906 B** | only `subrom_call`, `subrom_absent_error`, `vars_reset` — the tenant plumbing itself |
| `bsv_cas_id` (`save.asm` cassette-save band) | ~847 B | only `subrom_call` |
| `do_disk_bload` | ~253 B | only `subrom_call` |
| `do_name`, `lrset_common`, `ex_paint`, `do_open`, `oo_num` | — | **eval-bound — not evictable** (624-node closures into the float pack) |

The cassette verbs are cold by construction and the cassette band has been tenant-ised
before (`casmatch_tenant`, `cal_refill`), so the pattern is established. **~130 B is
under a seventh of the available cluster** — a partial lift suffices, and it leaves
headroom for T4. *Recommendation: lift a `cload.asm` slice into a page-0 tenant per the
[`subrom-tenant-playbook`](subrom-tenant-playbook.md), measuring the real T3 cost first
(the playbook's "measure + classify BEFORE implementing" rule).*

---

## 8. Gate

`make key-trap-acceptance`, a new `probes/basic/basic_probe_key_trap.py` built on the
matrix-hold harness (`probes/lib/omsx_repl.py` `holds`), differential against the
VG-8020 like `basic_probe_strig_trap.py`. It promotes the round-3+ cases and inherits
the §1.0 discipline as a **hard requirement**:

- every case carries a `done` sentinel, and a case whose program did not finish is a
  **failure, not a zero**;
- the untrapped delivery baseline (T1) is itself an assertion — if it reads 0, the
  apparatus is broken and the run is void;
- no string building in probe programs; `TIME`-bounded windows — **but see the risk
  below before relying on `TIME` on the zerobas side**;
- handler-timing cases size their handler from the measured loop rate, and the window
  is sized for **zerobas**, which runs an empty `FOR` loop ~7× slower than the VG-8020.

> **⚠️ Open risk, observed in passing during §4.2 — verify before building the gate.**
> An `IF TIME-T<400 GOTO` loop terminated normally on the VG-8020 (`done=1`) but was
> **still running on the repack target ~16 s later**, in a run that was otherwise healthy
> (the program had started, and keys were accumulating exactly as intended). The obvious
> explanation is that `TIME` does not advance on zerobas, but that is a *hypothesis, not
> a measurement* — it was never the object of that experiment. It does not affect any
> §1 finding (all `TIME`-bounded windows there ran on the **reference**), but the gate
> runs on **zerobas**, so a one-line `TIME` check comes first; if it does not advance,
> the gate's windows must be bounded some other way (iteration counts sized from the
> measured ~7× slowdown, or debugger-side timing).

Coverage: the §1.1 delivery/repeat table, the §1.2 diversion table including T5 and the
T6 control, §1.3 (W1 servicing, U2 blocking-`INPUT`, K7/R11 SHIFT discrimination, V2
priority), and the §1.4 parse/error surface. Plus host unit tests in `tests/test_traps.py`
for the matrix→key-number fold and the repeat counter.

---

## 9. Sign-off items

- **D-T3-1** — ✅ **DECIDED 2026-07-25: patch C-BIOS**, as a *thin 5-byte hook* at
  `put_key_fnk` with all policy in zerobas (§4). Confirm the hook contract (A = index,
  `CF=1` ⇒ swallow) and the new RAM vector's address.
- **D-T3-2** — auto-repeat: ✅ **moot under D-T3-1** — repeat is now inherited from the
  host BIOS's own decode, which is more faithful than replicating VG-8020 constants.
  Record the residual in `PROVENANCE.md`: cadence follows the running BIOS, not the
  VG-8020's ≈0.7–0.8 s / ≈17 Hz.
- **D-T3-7** — ✅ **ANSWERED 2026-07-25** (§4.2): SHIFT+F1 *does* reach `put_key_fnk`, as
  index 0, so **fold SHIFT in our handler** (~8 B); no patch extension. **Still to
  confirm:** whether to widen the hook contract to *A in/out* so an *untrapped* SHIFT+F1
  also expands the right `FNKSTR` slot — a pre-existing C-BIOS divergence T3 can close
  for ~free. *Rec: adopt.*
- **D-T3-3** — ✅ **ANSWERED 2026-07-25**: both published hooks run *before* the keyboard
  scan on C-BIOS *and* on the VG-8020, so diversion cannot be a same-frame removal.
  Nothing left to decide here; it now constrains D-T3-1.
- **D-T3-4** — intra-family priority: match the reference's high-to-low, or accept
  ascending as a documented divergence. *Rec: match if ≤ ~10 B.*
- **D-T3-5** — the carve: confirm the `cload.asm` page-0-tenant lift as T3's funding.
- **D-T3-6** — confirm `STOP` ≡ `OFF` for KEY (§1.2 T3/T4), the same narrowing of the
  arc spec §3 wording that T2 took for STRIG (D-T2-3).
