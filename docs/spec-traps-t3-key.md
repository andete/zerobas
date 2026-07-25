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
descending, or lay the band out reversed).

✅ **DECIDED at sign-off (§9): match the reference, unconditionally.** The
"accept ascending if it costs more than ~10 B" escape hatch was struck — any overrun
comes out of the carve surplus, not out of faithfulness. Gate case V2 enforces it.

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
before (`casmatch_tenant`, `cal_refill`), so the pattern is established.

✅ **DECIDED at sign-off (§9): lift BOTH the `cload.asm` cluster AND `do_disk_bload`,
UP FRONT** — ~906 + ~253 = **~1159 B** reclaimed, before any T3 code is written. This is
deliberately ~9× the T3 need; the surplus is headroom for T4/T5. The recommendation had
been the narrower "build first, carve to fit"; sign-off widened the *scope* and reversed
the *sequencing*. The playbook's **"measure + classify BEFORE implementing"** rule still
governs *how* each lift is done ([`subrom-tenant-playbook`](subrom-tenant-playbook.md))
— what was overridden is only the order relative to T3, not the discipline.

### 7.1 🔴 THE TABLE ABOVE IS WRONG — the carve does not exist as scoped (2026-07-25)

Acting on the sign-off, the very first step was the playbook's measure-and-classify
pass. It **falsified the classification the decision was based on.** The scout has been
rebuilt and committed as [`tools/carve_scout.py`](../tools/carve_scout.py) so this is
reproducible and does not have to be re-derived again.

**The methodological error.** The original scout measured each cluster's **direct**
low-region callees and *stopped at the main-page-1 boundary* — main page 1 stays mapped
during a page-0 tenant, so a call into it looks legal. But **the slot configuration
persists across that call.** When main-page-1 code called by a tenant itself calls
`$2812–$3FFF`, it hits the *sub-ROM* mapped there, not the low region. **The walk must
continue through main page 1.** Rebuilt that way:

| cluster | page-1 bytes | direct escapes | **reached THROUGH resident page-1** | verdict |
|---|---|---|---|---|
| `cload.asm` (`do_cload`/`do_tape_prog`/`ctp_line`/`dpl_line`) | **890 B** (not 906) | 3, all plumbing | **385** | 🔴 **NOT evictable** |
| `bload.asm` (`do_disk_bload`) | **470 B** (not ~253) | 0 | **1** — `subrom_call` | 🟠 one blocker |
| `bsv_cas_id` (cassette save) | — | 0 | **1** — `subrom_call` | 🟠 one blocker |

The reproduction of the old numbers is exact: `carve_scout` reports **`subrom_call`,
`subrom_absent_error`, `vars_reset` and nothing else** as `cload`'s *direct* escapes.
That column was never wrong — it was the wrong column.

**Why `cload` is structurally, not marginally, blocked.** ASCII `LOAD` tokenises each
line through the ordinary typed-line path:

```
do_tape_prog → cas_ascii_load → … → mrg_storeline → dispatch_line → tokenise → subrom_call
```

`dispatch_line` ([`basic/program.asm:30`](../basic/program.asm)) reaches the whole
interpreter and, through it, **385 low-region routines** including the float pack. This
is not a dependency that can be re-expressed sub-side: `dispatch_line` and `tokenise`
stay resident, so their calls cannot be rewritten from the sub ROM. Note the irony —
`tokenise` is *itself* a sub-ROM tenant, so the path is also a **nested sub-ROM call**,
independently unsupported.

**`bload`/`bsv_cas_id` are near-misses, one dependency each**, both the same shape
(`do_disk_bload → fat_io_open → fat_open → subrom_call`;
`bsv_cas_id → load_error → print_string → … → subrom_call`). `bsv_cas_id`'s runs through
an error path that is statically reachable but not taken at run time (`PRDEST` is zeroed
first) — a conservative walk cannot tell the difference.

**And there is no third option waiting.** A sweep of every `ex_*`/`do_*`/`cas_*`/`fat_*`
page-1 entry point for *exclusive* closure size found **nothing above 49 B** — page 1 has
no large self-contained cluster left. The remaining bulk (`expr.asm` 2077 B,
`files.asm` 1877 B, `program.asm` 1797 B) is thoroughly shared.

**One piece of good news.** The same audit was run against the **12 page-0 tenants
already shipping**, walking through their main-page-1 callees into the main graph:
**none reaches the low region.** There is no latent bug in shipped code. But
[`tools/check_tenant_closure.py`](../tools/check_tenant_closure.py) `--page0` has the
same blind spot by construction — it walks only sub sources, so it *would not catch*
this class. It passes today because no tenant triggers it, which is luck plus taste,
not a gate. **Closing that hole is a separate task; raised, not actioned here.**

⛔ **D-T3-5 is reopened. T3 is blocked on funding.** See §9.

### 7.2 T3's REAL cost, measured (2026-07-25) — 236 B, and it is split across TWO walls

With the carve reopened, the estimate was the next thing worth replacing with a number.
The whole slice was therefore **written** — C-BIOS patch, hook handler, both parser
generalisations, the reversed KEY band — and the build's own wall tripwires were read.
It assembles cleanly with the guards lifted (no undefined symbols, no syntax errors);
it has **never been run**, and under the arc's standing lesson that means nothing about
its correctness. What it does give is an exact size.

| wall | before | after | **deficit** |
|---|---|---|---|
| page-0 low region (`$2812–$3FFF`) | 6 B free | ends `$403C` | **60 B over** |
| page 1 (`$4000–$7FFF`) | 9 B free | ends `$80B0` | **176 B over** |
| | | **total** | **236 B** |

**The estimate was low by 106 B — 1.8×.** §7 predicted ~130 B *"deliberately pessimistic,
because T2's estimate was low by 70 B."* It was not pessimistic enough. Treat every
byte estimate in this arc as a lower bound.

**The structural surprise is the split.** §7 costed T3 as one page-1 number, but the
event source cannot live in page 1 at all. It fires from inside C-BIOS's keyboard scan —
the `$0038` ISR — which can land while a sub-ROM page-1 tenant owns page 1. `htimi_guard`
answers that for PLAY by skipping the frame, which is fine for an inaudible ≤1-frame
drain deferral; for KEY a skipped frame **leaks an undiverted keystroke into `KEYBUF`**,
a correctness divergence rather than a deferral. Page 0 is untouched during a page-1
tenant, so the handler goes in the low region and needs no guard at all — the same
reasoning that put `htimi_guard` itself there.

So **~66 B of the need is low-region-only**, and *every* carve candidate in §7.1
(`cload`, `bload`, `bsv_cas_id`) is a **page-1** cluster. A page-1 carve cannot fund the
low region directly. It can fund it *indirectly* — free page 1, then promote ~60 B of
existing low-region content into the freed page-1 space — but that is a second lift with
its own eligibility question, not a step anyone had costed.

**Where the 236 B actually goes** — measured by re-reading the walls with the KEY-specific
code gated out, which isolates the refactor from the feature:

| part | cost | vs. §7's estimate |
|---|---|---|
| KEY event source — hook handler + install (**low region**) | **66 B** | est. 55 B |
| **parser generalisation alone** (§5), before any KEY code | **76 B** | est. **0 — assumed free** |
| KEY-specific parse (`ON KEY GOSUB`, `KEY(n) ON/OFF/STOP`, the peeks) | **100 B** | est. 65 B |
| intra-family order (D-T3-4) | **0 B** | est. 10 B |

**The generalisation's plumbing costs 76 B** — five constants became five RAM parameters
plus `trap_slot_index` plus generalised range arithmetic, and *in isolation* that is more
than the immediate operands it replaced. That reading suggested §5's premise (*"sharing
rather than duplicating is what makes T3 affordable"*) was backwards, and that
duplicate-and-specialise would be smaller. **It was measured. It is not** — see §7.5.

**What did land as designed:** the C-BIOS hook, and **D-T3-4 for zero bytes** — laying
the KEY band out reversed gets the reference's high-to-low service order without touching
`ct_find` at all, and so without disturbing the scan direction T2's STRIG band depends on.

### 7.6 Sizing the rest of `bload.asm` — T3 CLOSES, and §7.4's unit was wrong again

§7.4 sized the carve at `do_disk_bload`'s closure (149 B → ~110 B net) and called the
remaining 321 B "the tape-BLOAD path plus shared parse helpers", warning it would spread
stub surface into `files.asm`. Sizing it properly shows **both halves of that were wrong**.

**`bload.asm` is not one unit — it is a verb plus three pieces of shared infrastructure
that merely live in the same file.** Counting external callers per label:

| | bytes | external callers |
|---|---|---|
| `load_error` | 15 B | **62** — the whole file/tape/disk error surface |
| `parse_disk_fcb` | 28 B | 9 (`do_files`, `do_kill`, `do_name`, `do_open`, `do_run`, `ex_merge`, …) |
| `parse_close_run` | 46 B | 6 (`do_run`, `dl_is_cas`, `dr_cas_close`, …) |
| **shared subtotal — must stay resident** | **89 B** | |
| **everything else — BLOAD-private** | **381 B** | none (only `ex_bload` → `do_bload`) |

**The stub-spread worry was unfounded.** Those three stay exactly where they are,
untouched, serving their 62/9/6 callers. The tenant gets its **own sub-local copies** —
and a duplicate in the sub-ROM costs **zero main page-1 bytes**, with 4667 B free there.
Nothing outside `bload.asm` changes except `ex_bload`, which becomes a stub.

**External dependencies of the 381 B private unit, all already answered:**

| dependency | resolution |
|---|---|
| `parse_close_run`, `parse_disk_fcb` | duplicate sub-side (74 B of free sub space) |
| `load_error`, `print_string` (from `dev_cas`) | the leaf-returns-an-error-**code** shape (§7.4) |
| `fat_io_open`, `fat_io_getbyte` | sub-local `t_fat_*` calls (§7.4) |
| `upcase`, `skip_spaces` | duplicate sub-side (16 B) |
| `TAPIN`, `TAPION`, `TAPIOF`, `WRTVRM` | BIOS — main page 0 stays mapped for a page-1 tenant ✓ |
| `subrom_call`, `subrom_absent_error` | low region — **also mapped** for a page-1 tenant; made sub-local anyway |

**Net: 381 B private − ~25 B resident `ex_bload` stub ≈ 356 B reclaimed from main page 1**
— more than double T3's 176 B.

**T3 closes.** Working the two walls through:

| step | low region | page 1 |
|---|---|---|
| today | 6 B free | 9 B free |
| after the BLOAD carve | 6 B | **365 B** |
| promote ~60 B low → page 1 | **66 B** | 305 B |
| T3 (60 B low + 176 B page 1) | **6 B left** | **129 B left** |

Low region lands tight; promoting a little more than 60 B buys margin, and §7.4 measured
4551 B as eligible.

> **Third correction to this same number, so state the pattern plainly:** §7.1 said 470 B
> (the file — right unit for "move the file", wrong for what is movable); §7.4 said 149 B
> (`do_disk_bload`'s closure — but BLOAD is *one verb*, and the disk path is half of it);
> the answer is **381 B** (the verb, minus shared infrastructure that stays). **Sizing a
> carve means choosing the unit first — file, entry-point closure, or verb-minus-shared —
> and they differ by 3×.** The scout reports the first two; the third needs the
> external-caller census that finally separated them.
>
> **Confidence.** Static; the byte counts for the sub-side rewrite and the `ex_bload` stub
> are estimates, and §7.2 is what estimates are worth here (1.8× low). What *is* solid is
> the 381/89 split — that comes from an exact external-caller census, not a judgement.

### 7.7 AS BUILT — the carve landed, page 1 9 B → 271 B

Executed (`35c7bb7`, `b9a3003`). `sub/bload.asm` is `SUBROM_IDX_BLOAD`, a page-1
tenant beside `fatprim`, and the projected mechanism held: it calls `fat_mount` /
`fat_find` / `fat_open` / `fat_read_file_sector` **sub-locally**, so the
`subrom_call` that made the cluster look un-evictable is simply gone.

| | before | after |
|---|---|---|
| main page-1 free | 9 B | **271 B** (+262) |
| low region free | 6 B | 6 B (untouched) |
| lean `basic.rom` | — | **byte-identical** (`9e723a02…`) |
| closure gates | 20 page-1 tenants | **21**, no main-page-1 escape |

**+262 B, not the projected ~356 B** — the estimate ran 26% optimistic again
(§7.2's standing lesson). The difference is the resident residue the projection
under-counted: `parse_disk_fcb`, `parse_close_run`, `load_error`+`err_io`,
`dev_cas` and a ~30 B stub all stay.

**It funds T3's page-1 half with room to spare.** Flipping `TRAPS_T3` to 1 now
measures **page 1: 75 B FREE** (was 176 B over). The low-region half is untouched
at 60 B over — that is the promotion step (§7.4: 4551 B eligible), not this carve.

Three shared `.inc` files carry the split, the `fcbname-body.inc` precedent one
level larger: `bload-body.inc` (the verb), `pdfcb-body.inc` (`parse_disk_fcb`,
split out because nine external callers keep it resident) and `fatio-body.inc`
(`fat_io_open`/`fat_io_getbyte` — identical source that is a cross-slot round trip
resident and four plain in-page calls in the tenant).

`load_handoff` is `SUB_BUILD`-conditional: its `,R` tail ends in `jp (hl)` into the
loaded program and never returns, so inside the tenant's `CALSLT` it would leave
main page 1 switched out forever. The tenant returns; the resident stub jumps.

**Two things the build caught that the static analysis had not:** `fatio-body.inc`
first swept in `fia_walk`/`fia_walked`/`fia_empty`, which already exist sub-side;
and `check_tenant_closure --page1` rejected `bl_upcase equ fcb_upcase`, because it
tells sub-local from switched-out-main **by name** and an alias reads as an escape
— answered with a real 6-byte label rather than by weakening a standing gate.

#### 7.7.1 Verification — what is proven, and what is NOT

✅ **Disk BLOAD: verified.** `make diskbasic-acceptance-repack` → **34/34 verbs
converged**, with the tenant live, including the `BLOAD` and `BSAVE/BLOAD(VRAM)`
cells. The shared routines are covered by the same run from their *other* callers:
`LOAD`, `RUN"file"`, `LOAD(ASCII)`, `FILES(wild)`, `KILL(wild)`, `OPEN(LEN=)` all
exercise `parse_disk_fcb` / `parse_close_run` / `fat_io_*`.

🔴 **Cassette BLOAD: NOT verified — a PRE-EXISTING coverage gap, not a regression.**
`basic_probe_bload.py` (the `BLOAD"CAS:",R` landmark probe) **times out** on
`C-BIOS_MSX1_EU_REPACK_DISK`. Before reading anything into that, the arc's control
rule was applied: the identical probe was run against the **pre-carve** build
(`35c7bb7`) on the same machine, and it **times out identically**. So the gap
predates this work — the repack machine carries no cassette completions, and
`bload.asm`'s own comment records that bare C-BIOS's `TAPION`/`TAPIN` are stubs
that always set CF. No installed machine carries both the carved build and a
working tape device.

> **This is exactly the arc's standing trap and it is NOT closed here.** The
> cassette path through the tenant — including the new `ei`/`di` window in
> `bload_tenant` and the `SUB_BUILD` handoff — **has never executed**. It builds,
> its closure is gated, and that is all. **Open task: a repack machine variant
> carrying the cassette completions, then re-run `basic_probe_bload.py`.** Until
> then, treat tape BLOAD on the repack build as unverified.

---

### 7.5 Duplicate-and-specialise, measured — the 76 B reading was MISLEADING

§7.2's "the generalisation costs 76 B" invited an obvious conclusion: duplicate T2's two
parsers, specialise each copy, skip the plumbing. That was written up as the likely win.
**Both variants have now been built and measured on the same wall. The prediction was
wrong.**

| variant | new page-1 code | T2 parsers |
|---|---|---|
| **generalise + share** (commit `a4e4bd4`) | **185 B** | rewritten (parameterised) |
| **duplicate + specialise** | **196 B** | untouched |

**Generalisation wins by 11 B (~6%)** — far less than §5 assumed, but it wins.

**Why the 76 B figure misled.** It is a real number measured correctly (build the refactor
with the KEY code gated out) — but it is only the *investment* half. The plumbing costs
76 B and then makes the KEY side cost **109 B instead of 196 B**, an 87 B return. Reading
the cost without the return inverted the conclusion. *A shared-code cost measured with its
beneficiaries gated out is not the cost of sharing; it is the down-payment.* To compare
two designs, build **both** and read the same wall — which is cheap here, and was not done
before writing the recommendation.

**Neither variant closes the gap**: T3's page-1 need is 176–187 B either way, against
~110 B from the `bload` carve (§7.4).

**What is in the tree is the DUPLICATED variant**, despite being 11 B larger, because it
is **strictly better for tree health**: every byte of it is inside `IF TRAPS_T3`, so with
the gate off it costs *nothing* and T2's shipped, gate-covered parsers are untouched. The
generalised variant rewrites those parsers unconditionally — it overran page 1 by 67 B
even with T3 gated out, which is why it had to be reverted at all. Reclaim the 11 B when
the slice is funded: `git show a4e4bd4 -- basic/program.asm basic/screen.asm | git apply`.

### 7.4 Is `bload`'s `subrom_call` dependency avoidable? YES — but it does not close

§7.1 left `bload` as a near-miss with one blocker,
`do_disk_bload → fat_io_open → fat_find → subrom_call`. Investigated.

**The dependency is avoidable — by moving the tenant to the OTHER page, not by
removing a call.** Every `fat_*` routine `do_disk_bload` reaches is a *stub* whose entire
body is "set `DISKOP_OP`, load `IX`, `call subrom_call`" — dispatching into
**`fatprim_tenant`, which is already a sub-ROM PAGE-1 tenant**
([`sub/fatprim.asm:69`](../sub/fatprim.asm)) with a selector for each one
(`t_fat_mount`, `t_fat_find`, `t_fat_open`, `t_fat_read_file_sector`, …). A BLOAD tenant
placed in **sub page 1, co-resident with `fatprim`**, calls those **directly and
sub-locally**: no `subrom_call`, no `CALSLT`, no low-region touch. The blocker only
exists because the caller is on the wrong side of the slot boundary.

`do_disk_bload`'s external dependencies reduce to exactly two families, and both dissolve:

| dependency | how it goes away |
|---|---|
| the `fat_*` stub layer (`fat_mount`/`find`/`open`/`io_open`/`io_getbyte`/`read_file_sector`) | sub-local calls to the `t_fat_*` selectors it already dispatches to |
| `load_error → print_string` — which is what drags in `pchar` and its whole device fan-out (`pch_file`, `pch_disk`, `cas_wbyte`, `CHPUT`) | the playbook's standard shape: **the leaf tenant returns an error CODE; the resident glue raises the disposition** |

Residual after both: `WRTVRM` (a BIOS call — main page 0 stays mapped for a page-1
tenant ✓) and RAM state (`FREAD_*`, `FSECTOR_BUF` — always mapped ✓). `CALSLT` disappears
with `subrom_call`. **That is a clean page-1 tenant.** Room exists: **sub-ROM page 1 has
4667 B free.**

🔴 **But the payoff is far smaller than §7.1's headline, and §7.1's number was the wrong
unit.** 470 B is `bload.asm`'s *whole file*; `do_disk_bload`'s movable closure is only:

| | bytes |
|---|---|
| `do_disk_bload` + `disk_load_loop` + `dll_adv` + `load_handoff` + … | **149 B** |
| less `load_error`, which stays resident as the error-code dispatcher | −15 B |
| less a resident `ex_bload` → tenant stub | ≈ −25 B |
| **net page-1 gain** | **≈ 110 B** |

against T3's **176 B** page-1 need. **It does not close on its own.** The other 321 B of
`bload.asm` is the tape-BLOAD path plus `parse_disk_fcb`/`parse_close_run`, which
`do_run` and `do_files` also call — movable by the same two transformations, but it
spreads the stub surface into `files.asm`.

**The low-region half, by contrast, is comfortably fundable.** Promotion (low region →
freed page 1) needs only that a routine is not called by a **page-1** sub-ROM tenant
(those see main `< $4000` only) and is not on the ISR path. Measured against the resident
ABI closure and the `event_poll`/`htimi_guard` closure: of 6142 B of low region,
**1591 B is pinned and 4551 B is not** — 75× T3's 60 B need. Promotion is also
*monotonically safe* for page-0 tenants: it removes low-region reaches rather than
creating them.

> **Confidence.** This is static analysis, and static analysis in this same session
> produced the §7.1 error. Two things differ: it applies the *corrected* walk rule, and
> the `fat_*` claim is not an inference — those stubs' bodies were read, and the
> selectors they name exist in `sub/fatprim.asm`. What is NOT verified: the sub-side
> rewrite's real byte cost, and the resident stub's. Both are measurements to take
> before committing, not estimates to trust — §7.2 is what estimates are worth here.

### 7.3 Tree state — main stays green, T3 is gated off

The slice does not fit, so it must not break the build for everyone else:

- **`TRAPS_T3`** ([`basic/sysvars.inc`](../basic/sysvars.inc)) is a build gate, default
  **0**. It covers [`basic/keytrap.asm`](../basic/keytrap.asm) in full and the
  `zkey_install` boot call. Flip it to 1 once the space exists.
- The **T3 parse surface in the tree is the DUPLICATED variant** (§7.5), entirely inside
  `IF TRAPS_T3`, so it costs nothing with the gate off and leaves T2's shipped parsers
  untouched. The **generalised variant is 11 B smaller when enabled** but rewrites those
  parsers *unconditionally* — it overran page 1 by 67 B even with T3 gated out, which is
  why it could not stay. Reclaim those 11 B at funding time:
  `git show a4e4bd4 -- basic/program.asm basic/screen.asm | git apply`.
- `make basic-reloc` is green: low region 6 B free, page 1 9 B free, lean `basic.rom`
  byte-identical, all four closure gates passing.

**Landed and verified regardless of funding:** the C-BIOS side is complete and
reproducible — [`cbios-repack/key-trap-hook.patch`](../cbios-repack/key-trap-hook.patch)
applies to the pinned tag, assembles clean, and
[`tools/build_repacked_cbios.py`](../tools/build_repacked_cbios.py) now applies both
patches in order and verifies the new pin `557aed9352cf8367eabb9a3cc081c83252579ab9`.

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
- no string building in probe programs; observation windows bounded by **iteration
  count, never by `TIME`** — `TIME` does not exist on zerobas (resolved below), so a
  `TIME`-bounded loop there never terminates;
- handler-timing cases size their handler from the measured loop rate, and the window
  is sized for **zerobas**, which runs an empty `FOR` loop ~7× slower than the VG-8020.

> **✅ RESOLVED 2026-07-25 — and the hypothesis was wrong in a way that matters.**
> The §4.2 observation was an `IF TIME-T<400 GOTO` loop that terminated normally on the
> VG-8020 (`done=1`) but was **still running on the repack target ~16 s later**, in an
> otherwise-healthy run. The recorded hypothesis was "`TIME` does not advance on
> zerobas." It is **not** that. Measured, both machines' `done` sentinel = 1 so both
> readings are valid:
>
> | | reached post-delay | `TIME` unchanged across the delay | `JIFFY` ($FC9E) |
> |---|---|---|---|
> | VG-8020 | 1 | **0** — `TIME` advances | 3101 |
> | repack target | 1 | **1** — `TIME` frozen | **3149 — the clock IS live** |
>
> `JIFFY` advances on zerobas exactly as on the reference; the ISR clock is fine.
> **`TIME` is simply not implemented** — it is absent from
> [`basic/kwtable.inc`](../basic/kwtable.inc), so it never crunches to a token and is
> parsed as the *variable* `TI` (2 significant chars), which reads 0 forever. Hence
> `TIME-T` ≡ `0-0` ≡ 0 `< 400` **always**, and the loop is infinite. This is a **silent**
> divergence: no error, no `Syntax error`, just a wrong answer.
>
> **Consequence for the gate:** the fix is not "bound the windows some other way in
> general" — it is that **no probe program may use `TIME` on the zerobas side at all**
> until `TIME` lands. Gate windows are sized by **iteration count** from the measured
> loop rate (§1.0: `FOR J=1 TO 3000` ≈ 4.8 s on the VG-8020, ~625 iter/s; zerobas ~7×
> slower). §1's `TIME`-bounded windows are unaffected — they all ran on the reference.
>
> **Out-of-slice gap raised, NOT actioned here.** `TIME` (both the function and the
> `TIME=n` assignment statement) is standard MSX1 BASIC and is in charter
> ([[charter-faithful-full-msx1-basic]]), but it is tracked in no doc. It is not T3's
> job; recorded here so it is not lost.

Coverage: the §1.1 delivery/repeat table, the §1.2 diversion table including T5 and the
T6 control, §1.3 (W1 servicing, U2 blocking-`INPUT`, K7/R11 SHIFT discrimination, V2
priority), and the §1.4 parse/error surface. Plus host unit tests in `tests/test_traps.py`
for the matrix→key-number fold and the repeat counter.

---

## 9. Sign-off items

> ## ✅ SPEC SIGNED OFF — 2026-07-25. Implementation authorised.
> All six decisions are closed. The three that were still open resolved as follows,
> and **two of them went further than the recommendation**:
>
> | | decision | vs. rec. |
> |---|---|---|
> | **D-T3-5** | Carve **both** the `cload.asm` cluster **and** `do_disk_bload` **up front**, before T3 code is written. ~906 + ~253 = **~1159 B** of page-1 reclaim. | **wider** — rec. was build-then-carve-to-fit |
> | **D-T3-4** | Match the reference's high-to-low intra-family order **unconditionally** — no byte-count escape hatch, no documented divergence. | **stricter** — rec. had a ≤10 B condition |
> | **D-T3-7** (2nd half) | **Adopt** the *A in/out* hook contract. | as rec. |
>
> **Consequence of the wider D-T3-5:** the carve is now a *prerequisite* task, not a
> fit-up afterthought, and it is sized well beyond T3 — the surplus is deliberate
> headroom for T4/T5. The playbook's "measure + classify before implementing" rule
> still governs *how* the lift is done ([`subrom-tenant-playbook`](subrom-tenant-playbook.md));
> what the sign-off overrode is only the *sequencing*.
>
> **Consequence of the stricter D-T3-4:** high-to-low is now a hard requirement of the
> gate, not a nice-to-have. If it costs more than the ~10 B budgeted, the extra comes
> out of the carve surplus — it does not become a deviation.

- **D-T3-1** — ✅ **DECIDED 2026-07-25: patch C-BIOS**, as a *thin 5-byte hook* at
  `put_key_fnk` with all policy in zerobas (§4). Confirm the hook contract (A = index,
  `CF=1` ⇒ swallow) and the new RAM vector's address.
- **D-T3-2** — auto-repeat: ✅ **moot under D-T3-1** — repeat is now inherited from the
  host BIOS's own decode, which is more faithful than replicating VG-8020 constants.
  Record the residual in `PROVENANCE.md`: cadence follows the running BIOS, not the
  VG-8020's ≈0.7–0.8 s / ≈17 Hz.
- **D-T3-7** — ✅ **CLOSED 2026-07-25** (§4.2): SHIFT+F1 *does* reach `put_key_fnk`, as
  index 0, so **fold SHIFT in our handler** (~8 B); no patch extension. Second half
  **DECIDED: adopt the *A in/out* contract** — our handler already folds SHIFT to compute
  the trap index, so writing the corrected index back to `A` costs one `ld` and also
  fixes *untrapped* SHIFT+F1..F5 expanding the wrong `FNKSTR` slot. That divergence is
  C-BIOS's, pre-dating T3; T3 closes it in passing. **Full contract:**
  `A` in = BIOS's fn-key index 0..4; `A` out = SHIFT-folded index 0..9;
  `CF=1` out ⇒ swallow the delivery, `CF=0` ⇒ expand `FNKSTR[A]`.
- **D-T3-3** — ✅ **ANSWERED 2026-07-25**: both published hooks run *before* the keyboard
  scan on C-BIOS *and* on the VG-8020, so diversion cannot be a same-frame removal.
  Nothing left to decide here; it now constrains D-T3-1.
- **D-T3-4** — ✅ **DECIDED 2026-07-25: match the reference's high-to-low order,
  unconditionally.** The ≤10 B condition in the recommendation was struck; ascending is
  not an acceptable fallback. Implement by scanning the KEY band descending in `ct_find`
  ([`basic/traps.asm:229`](../basic/traps.asm)) or by laying the band out reversed —
  whichever measures smaller. Gate-enforced (§8, case V2).
- **D-T3-5** — ⛔ **REOPENED 2026-07-25, same day** — the decision below was taken on a
  classification that the first measure-and-classify pass **falsified**. `cload.asm` is
  **not page-0-evictable at all** (385 low-region routines reached through resident main
  page-1 code, via `dispatch_line`), and no other large clean cluster exists in page 1.
  `bload.asm` (470 B) and `bsv_cas_id` are one blocker each. Full analysis and the
  rebuilt scout: **§7.1**. **T3 is blocked on funding until this is re-decided.**
  <br>~~Superseded decision:~~ ✅ **DECIDED 2026-07-25: carve BOTH clusters, UP FRONT.** The `cload.asm`
  program-load cluster (`do_cload`/`do_tape_prog`/`ctp_line`/`dpl_line`, ~906 B) **and**
  `do_disk_bload` (~253 B) both lift to page-0 tenants *before* T3 code is written —
  ~1159 B reclaimed against a ~130 B need. Both were classified evictable by the same
  closure scout (§7): their only page-0-low escapes are the tenant plumbing itself
  (`subrom_call`, `subrom_absent_error`, `vars_reset`). The surplus is intentional
  headroom for T4/T5.
- **D-T3-6** — ✅ **CONFIRMED 2026-07-25: `STOP` ≡ `OFF` for KEY.** Measured in §1.2
  (T3/T4): both deliver the key normally and neither latches. Same narrowing of the arc
  spec §3 wording that T2 took for STRIG (D-T2-3), now on a second family — the arc
  spec's "STOP latches, OFF discards" wording is the outlier and should be reworded to
  match the two measurements, not the other way round.
