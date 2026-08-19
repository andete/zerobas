# spec — interrupt-traps T2: the STRIG trap (`ON STRIG GOSUB` + `STRIG(n) ON/OFF/STOP`)

Status: **DRAFT — awaiting sign-off.** Slice packet for T2 of the interrupt-traps arc
([`docs/spec-basic-interrupt-traps.md`](spec-basic-interrupt-traps.md), signed off
2026-07-24, slicing T1→T2→T3→T4). T1 (STOP) landed 2026-07-25 (commit `4fef347`,
[`docs/spec-traps-t1-stop-reslice.md`](spec-traps-t1-stop-reslice.md)) and shipped the
whole reusable skeleton: the `ZTRAP` table, the `event_poll` H.TIMI seam, `check_traps`,
`set_state`, `trap_return_check`, and the RETURN re-enable. **T2 adds the first real
*device* event source** — five joystick triggers — and closes half of the input-devices
**D-I-5** handoff (`STRIG(n) ON/OFF/STOP` currently aborts ERR 2).

Clean-room: the semantics below are **measured black-box on the Philips VG-8020** (§1);
the RAM layout, the shadow/edge mechanism and the seeding rule are own-design. No
reference ROM bytes were read or decoded.

---

## 1. Oracle characterization (VG-8020, 2026-07-25) — the semantics, measured

Three rounds of boot-per-case openMSX runs on `Philips_VG_8020`, driving the SPACE key
via the keyboard matrix (row 8 bit 0 **is** joystick trigger 0) and reading RAM
sentinels (`POKE`/`PEEK`, echo-immune — the harness lesson from T1). Scripts:
`strig_trap_char{,2,3}.py` (to be promoted into `probes/basic/` as the gate, §7).

### 1.1 Firing semantics

| # | case | result | conclusion |
|---|------|--------|------------|
| Q1 | `ON STRIG GOSUB 100` + `STRIG(0) ON`, tap SPACE | fires once | a **single-line** list arms trigger 0; the trap works |
| Q2 | same, SPACE **held 3 s** | fires **once** | **edge-triggered, not level** — no repeat while held |
| Q3 | two taps | fires **twice** | `RETURN` re-arms (auto-resume confirmed) |
| Q5 | arm, **no** `STRIG(0) ON`, tap | never fires | arm ≠ enable (as T1) |
| R7 | tap, then tap again **while the handler is still running** | fires **once** | a press during SERVICING is **LOST**, not latched |
| R8 | program `END`ed before the press | never fires | no run loop ⇒ no dispatch |

### 1.2 The shadow question — a press that pre-dates the enable (the load-bearing one)

| # | case | result |
|---|------|--------|
| R1 | trigger held from mid-delay **through** `STRIG(0) ON`, released later | **never fires** |
| R2 | held across a `STRIG(0) STOP` window **and** the later `STRIG(0) ON` | **never fires** |
| R3 | same with `STRIG(0) OFF` | **never fires** |
| Q6 | tap (pressed *and released*) during a `STOP` window, then `ON` | **never fires** |
| Q7 | same with `OFF` | **never fires** |

**Conclusion — the model (own-design, observationally equivalent to the reference):**
> A trigger is sampled **only while its entry state is exactly ON**. A 0→1 transition
> against a per-trigger *shadow* bit sets PENDING. On any **transition into ON**, the
> shadow bit is **set to 1** ("assume pressed"), so a trigger that is already held when
> the trap is enabled cannot manufacture a spurious edge; the next frame samples the real
> level and the shadow self-corrects.

That single rule reproduces every row above, including the STOP/OFF cases (no sampling
while not ON ⇒ nothing to latch — for STRIG, `STOP` is observationally identical to
`OFF`, which is a *narrowing* of the arc spec §3 "STOP still latches" wording; §6 D-T2-3)
and R7 (during SERVICING the state is not ON, so the second press is never sampled; on
`RETURN` the shadow is still 1 from the fire, so a **still-held** trigger does not
re-fire — which is exactly what Q2's 3 s hold shows). It also costs **zero device reads
outside the ISR**: seeding is a bit-set, not a sample.

### 1.3 Parsing / arming

| # | case | reference |
|---|------|-----------|
| Q10 | `STRIG(0)` bare as a statement | **ERR 2** (Syntax error) — zerobas already matches |
| Q11 | `STRIG(5) ON` | **ERR 5** (Illegal function call) |
| S8 | `STRIG(.4) ON` | truncates to 0 and **works** (normal int coercion) |
| S4 | `STRIG(0)ON` (no space) | works |
| Q9/S1 | `ON STRIG GOSUB ,,300` / 5 slots | parse cleanly, **no error** |
| R4 | `,,300` then `STRIG(0) ON` + tap | never fires — slot 0 has no handler |
| R5 | `ON STRIG GOSUB 100,200`, trigger 0 | fires **slot 0** ⇒ list is positional, slot *n* = trigger *n* |
| R6 | `ON STRIG GOSUB 100,200`, `STRIG(1) ON`, tap SPACE | never fires (SPACE is trigger 0 only) |
| S3 | `ON STRIG GOSUB 100` then `ON STRIG GOSUB ,100`, trigger 0 | never fires ⇒ **a listed-empty slot CLEARS that handler** |
| S5 | `ON STRIG GOSUB 999` (undefined) | **ERR 8** Undefined line number |
| S6 | `ON STRIG` (no GOSUB) | **ERR 2** |
| S7 | `ON STRIG GOTO 100` | **ERR 2** |
| S2 | `ON STRIG GOSUB` with **6** slots | **the run dies** — sentinels revert to the power-on pattern, reproducible ×3. No clean error; consistent with a handler-table overrun. |

---

## 2. Scope of this slice

**In.**
1. `ON STRIG GOSUB [<l0>][,<l1>[,<l2>[,<l3>[,<l4>]]]]` — arm up to five handlers.
2. `STRIG(n) ON | OFF | STOP`, n = 0..4 — replaces the D-I-5 `ERR 2` with the real thing.
3. The `event_poll` STRIG stanza — the first device stanza in the ISR (§4).
4. The shadow byte `ZSTRIGSH` + the seed-on-enable rule (§3).
5. Host unit tests + the `strig-trap-acceptance` VG-8020 differential gate (§7).

**Out.** `KEY(n)` (T3), `SPRITE` collision (T4), `INTERVAL` (MSX2, out of charter —
[[interval-is-msx2-not-msx1]]). No new tokens: `STRIG` is `$FF $A3`, `ON`/`OFF`/`STOP`
already exist.

---

## 3. Data — one new RAM byte

The five entries `ZTRAP[3..7]` (`ZTI_STRIG0`) already exist. Add, next to `STOPGRACE`
in the freed VARTAB window (still well clear of `$E240`):

```
ZSTRIGSH   equ $E221   ; 1 B: per-trigger "was pressed last sample" shadow,
                       ; bit n = trigger n (n = 0..4). Bits 5-7 unused.
```

`trap_init` already fills `ZTRAP..STOPGRACE`; extend the fill length to cover
`ZSTRIGSH` so a cold boot / `RUN` starts with every shadow clear.

**Seeding.** On a state transition **into** ON for entry `ZTI_STRIG0+n` (and only on a
*change* — `ON` on an already-ON trap must be a no-op, else a program that re-issues
`STRIG(0) ON` every statement would hold the shadow at 1 forever and never see a press),
`set` bit n of `ZSTRIGSH`. This is done by the STRIG arming statement, **not** by the
shared `set_state` (which stays generic for STOP/KEY/SPRITE).

---

## 4. `event_poll` — the STRIG stanza (interrupt path)

Appended after the existing INTERVAL stanza in [`basic/traps.asm`](../basic/traps.asm),
inside the `TRAPENA != 0` guard (so a program with no ON trap still pays only the
existing load+test).

```
for n = 0..4:
    entry = ZTRAP[ZTI_STRIG0 + n]
    if (entry.state != ON) continue          ; not sampled -> §1.2
    a = GTTRIG(n)                            ; $00/$FF
    if (a == 0)  { ZSTRIGSH bit n = 0; continue }      ; released: shadow follows
    if (ZSTRIGSH bit n) continue                       ; still held: no edge
    ZSTRIGSH bit n = 1; entry.PENDING = 1; TRAPPEND = 1 ; 0->1 edge: latch
```

**D-T2-1 — read the trigger via the published BIOS `GTTRIG` ($00D8), not inlined port
I/O.** Rationale: it is the same published contract our `STRIG(n)` *function* already
uses ([`basic/expr.asm:1039`](../basic/expr.asm)), it keeps the code BIOS-agnostic (the
standing rule — [[cbios-target-cf3300-oracle]]), and it is a page-0 BIOS entry, so it is
a plain `call`, **not** a `CALSLT` (the VBLANK ban stands). Cost: register-transparency
now needs `IX`/`IY` pushed as well (`GTTRIG` is documented "Registers: All"), on the
armed path only.

**The PSG-latch race, and its fix.** `GTTRIG(1..4)` selects PSG register 15 and reads 14.
Our own PSG writes are already `DI`-guarded ([`basic/sound.asm:71`](../basic/sound.asm),
the audio-slice-3 fix), and `play_service` runs later in the *same* ISR, so neither can
interleave. The one remaining hole is the **mainline `STRIG(n)`/`STICK(n)` function
reader**, which calls `GTTRIG`/`GTSTCK` un-guarded: a VBLANK landing between its latch
and its read would now be answered by our own `GTTRIG`. Fix = wrap those two call sites
in `di`/`ei` (2 B), exactly as `ex_sound` does. **This is a real, pre-existing-shape bug
that T2 would otherwise create; it is in scope.**

**Cost discipline.** The loop only *calls* `GTTRIG` for entries that are ON — a program
with one armed trigger pays one BIOS call per frame, the same order as the PLAY drain
that already runs there.

---

## 5. Parsing

### 5.1 `ON STRIG GOSUB <list>` — a sibling peek in `ex_on`

`ex_on` already peeks `ERROR` and `STOP` after the `ON` token. `STRIG` is the two-byte
`$FF $A3`, so the peek is: on `PEEK_PREFIX` ($FF), look at the next byte for
`STRIG_TOKEN` ($A3) → `ex_on_strig`. (A `$FF` that is not `$A3` falls through to `eval`,
which is what makes `ON MID$(...)...` still evaluate — the existing behaviour.)

`ex_on_strig` then, per the oracle (§1.3):
- require `GOSUB` (else ERR 2 — S6/S7);
- walk up to 5 comma-separated slots. For each slot: an empty slot (`,` or end)
  **writes 0** into that entry's handler field (S3); a `$0E,lo,hi` line-ref resolves via
  `find_line_bc` and writes the LINK, ERR 8 if undefined (S5);
- **a 6th slot → trappable ERR 2** (`ld a,2 / jp raise_error`). This is a **documented
  deviation**: the reference does not raise a clean error, it appears to run off the end
  of its handler table and takes the machine down (S2, reproducible ×3). Replicating a
  table overrun is not clean-room-achievable *and* is actively harmful; per
  [[bug-for-bug-compat-over-accuracy]] this joins division as an explicit deviation.
- state is **not** touched (arm ≠ enable); flow continues on the same line (`jp exec_stmt`).

The `$0E` → LINK resolution is byte-for-byte what `ex_on_stop` does today; **factor it
into a shared `trap_handler_line` helper** (returns DE = LINK or jumps `ex_goto_undef`)
and re-point `ex_on_stop` at it — a net byte *saving* that also pre-pays T3's `ON KEY`
comma-list.

### 5.2 `STRIG(n) ON | OFF | STOP` — a new statement

Reached from the `$FF` statement dispatch that today lands in `ex_mid_stmt`
([`basic/interp.asm:273`](../basic/interp.asm), the D-I-5 `ERR 2` site): add a
`STRIG_TOKEN` branch → `ex_strig_stmt`.

```
ex_strig_stmt:  expect '(' ; eval ; get_byte_arg      ; float truncates (S8)
                n > 4 -> ERR 5 (Q11)
                expect ')'
                next token: ON -> ZTS_ON, OFF -> ZTS_OFF, STOP -> ZTS_STOP
                            anything else (incl. EOL/':') -> ERR 2 (Q10)
                HL -> ZTRAP + (ZTI_STRIG0+n)*3
                if (new == ON && old != ON) set bit n of ZSTRIGSH   ; §3 seeding
                call set_state
                jp exec_stmt                ; NOT `ret` — the T1 `es_set` lesson
```

The trailing `jp exec_stmt` is non-negotiable: a bare `ret` swallows the rest of the
line, which is exactly the green-hidden bug the T1 B2 differential caught.

---

## 6. Decisions for sign-off

- **D-T2-1 — `GTTRIG` from the ISR** (§4). *Recommend: yes*, plus the `di`/`ei` guard on
  the mainline `STRIG`/`STICK` readers. Alternative (inline PSG/PPI port reads) buys
  nothing and forfeits BIOS-agnosticism.
- **D-T2-2 — the shadow + seed-on-enter-ON model** (§1.2/§3). *Recommend: yes* — it
  reproduces all 11 measured firing cases with one RAM byte and no mainline device read.
- **D-T2-3 — `STRIG(n) STOP` is observationally `OFF`** (it does not latch, because a
  non-ON entry is never sampled). This *narrows* arc-spec §3's "a suspended trap
  remembers one event", which was written before any device source existed. Measured
  (Q6/R2). *Recommend: accept, and amend arc-spec §3 to say the latch-while-STOPped
  property belongs to sources that are sampled unconditionally, not to STRIG.*
- **D-T2-4 — the 6-slot deviation** (§5.1): trappable ERR 2 instead of the reference's
  crash. *Recommend: yes, documented in PROVENANCE/TODO as a deliberate deviation.*
- **D-T2-5 — trailing slots.** `ON STRIG GOSUB 100` after a 5-slot arm: are slots 1..4
  cleared or kept? Now *testable* thanks to §7.3, so **measure it on the oracle at
  implementation time** rather than deciding here. Provisional: parse-as-you-go (write
  listed slots, empty ⇒ 0, leave absent trailing slots untouched).
- **D-T2-6 — the acceptance machine now models PSG port directions like the oracle**
  (§7.3). `tools/install-repack-machine.py` emits
  `<ignorePortDirections>false</ignorePortDirections>`, matching `Philips_VG_8020.xml`;
  openMSX's default is `true`. *Landed as a harness fix* — it removes an asymmetry that
  had nothing to do with our ROM (which never writes R7's direction bits — the
  `play-trace-acceptance` gate asserts R7 stays `$B8`), and it is what makes triggers
  1..4 drivable. `input-devices-acceptance` 50/50 and `play-trace-acceptance` re-run
  green afterwards.

---

## 7. Gates

### 7.1 Host unit tests — `tests/test_traps.py` (`make unit-test`)
Extend with: the shadow edge machine (released→pressed fires once; held does not
re-fire; release then press fires again); seed-on-enter-ON suppressing a held trigger;
`ex_strig_stmt`'s range check; the 5-slot list writer including empty slots.

### 7.2 `strig-trap-acceptance` — the VG-8020 differential (**and run it**)
Promote the characterization scripts into `probes/basic/basic_probe_strig_trap.py`,
boot-per-case, POKE-sentinel, zerobas-vs-VG-8020, with the §1 table as the case list.
**Trigger 0 (SPACE, matrix row 8 bit 0) is fully drivable**, so Q1/Q2/Q3/Q5/Q6/Q7/R1/R2/
R3/R4/R5/R6/R7/R8 and every §1.3 parse case are all real differential cases.

### 7.3 Triggers 1..4 — the press mechanism (deficit CLOSED, measured 2026-07-25)

openMSX has no joystick-button command, and the obvious routes are all dead ends
(**measured**, so nobody re-derives them):

- `debug write joystickports …` — accepted but inert; reads return the live pin state.
- `msxjoystick1_config` maps **host** events, and there is no Tcl host-event injector.
- **No pluggable presents a pressed trigger**: `magic-key`, `tetris2-protection`,
  `circuit-designer-rd-dongle`, `joytap`, `ninjatap`, `arkanoidpad`, `trackball`,
  `mouse` all read released, on *both* machines. (A free differential result.)

**What works — the PSG-latch injection.** Put PSG port A into **output** mode
(`debug write "PSG regs" 7 0xF8`, i.e. R7 bit 6) so the AY returns register 14's
**latch** instead of the joystick pins, then write R14 (active low):

| R14 | pressed |
|-----|---------|
| `0xEF` (bit 4 low) | `STRIG(1)` **and** `STRIG(2)` |
| `0xDF` (bit 5 low) | `STRIG(3)` **and** `STRIG(4)` |
| `0xCF` | all four |
| `0xFF` | released |

**Verified identical on the VG-8020 and the repack build** in all four configurations,
and — the property the trap gate actually needs — a press/release/press sequence counts
**exactly 2 rising edges on both machines**. This depends on D-T2-6 (the machine now
carries `<ignorePortDirections>false</ignorePortDirections>`; without it openMSX
silently drops the R7 write and the injection is inert).

*Residual limitation, not a blocker:* the injection replaces the latch **behind** the
port-A/port-B multiplexer, so triggers 1 and 2 cannot be distinguished from each other,
nor 3 from 4. Every trigger can still be pressed, released and edge-detected, which is
what the trap gate asserts. Distinguishing the two physical ports stays untested —
record that single residual in
[`disk/docs/tier2-review-queue.md`](../disk/docs/tier2-review-queue.md).

### 7.4 Standing sweep
`make unit-test`, `diskbasic-acceptance`, `string-acceptance`, `play-trace-acceptance`
(the ISR seam changed — this one is load-bearing), `stop-trap-acceptance`,
`input-devices-acceptance` (the `di`/`ei` guard touches its call sites), `basic-reloc`
lean byte-identity.

---

## 8. Byte budget

Page-1 free **measured 2026-07-25: 230 B** (`make basic-reloc`,
`__MEAS_PAGE1_END = $7F1A`); page-0 low region 6 B.

Rough estimate, to be **measured before implementing** (the standing arc lesson):
`event_poll` STRIG stanza ~55 B · `ex_strig_stmt` ~55 B · `ex_on_strig` ~65 B ·
`ex_on` peek ~8 B · `$FF` dispatch branch ~6 B · `di`/`ei` guards 4 B — **~190 B**,
*minus* the `trap_handler_line` factoring (~25 B back from `ex_on_stop`). Call it
**~165 B against 230 B**: it should fit, but with ~65 B left it is the **last** slice
that fits without a new carve. T3 (KEY, 10 entries + matrix decode) will need one —
scout it at the T3 packet, not now.

---

## 9. Implementation order

1. Measure the real cost of the pieces above; confirm the fit.
2. `ZSTRIGSH` sysvar + `trap_init` fill extension; `trap_handler_line` factoring
   (re-point `ex_on_stop`, `make unit-test` must stay green).
3. `ex_strig_stmt` + `ex_on_strig` + the two dispatch peeks; host unit tests **first**.
4. The `event_poll` stanza + the `di`/`ei` guards on the mainline readers.
5. `basic_probe_strig_trap.py` and **run it** — then the standing sweep, then commit.

---

## 10. AS-BUILT (2026-07-25) — what the live gate changed

T2 is implemented and gated: `make strig-trap-acceptance`, **25 cases / 51 assertions,
all PASS** against the VG-8020. Four things differ from the §1–§4 design above; the
first is a genuine correction to the measured semantics, and it is the reason the
"never commit an ungated slice" rule exists.

### 10.1 CORRECTION — a press during SERVICING is LATCHED, not lost

**§1.1 case R7 / §1.2 were WRONG.** The characterization run that produced "a press
during the handler is lost" closed its capture window **before the slow handler
returned**; with a long enough window the reference reports **two** fires. The press is
latched as PENDING while the trap is SERVICING, cannot fire then (state ≠ ON), and
fires exactly once when `RETURN` restores ON — which is precisely what arc-spec §3
always said, and what `trap_return_check` already implemented.

**Consequences for the model:** a trigger is sampled while its entry is **ON *or*
SERVICING**, never while OFF or STOP. Conveniently both sampled states have bit 0 set
(`ON`=01, `SERVICING`=11) and neither unsampled one does (`OFF`=00, `STOP`=10), so the
whole test is a single `bit 0,(hl)` — cheaper than the original `and`/`cp` pair.

*Method note worth keeping:* a capture window is part of the measurement. Two
characterization rounds agreed on the wrong answer because they shared the same too-short
window; only the differential — where the reference and zerobas disagreed — exposed it.

### 10.2 The shadow lives in the entry byte, not a RAM byte

`ZSTRIGSH` was dropped. The shadow is **bit 6 of the entry state byte** (`ZTS_SHADOW`),
so every access is a 2-byte bit op on the pointer the poll already holds, no mask
arithmetic and no new sysvar — and `trap_init`'s existing fill clears it. Two write
paths had to learn to preserve it, both now covered by host tests:

- `check_traps`' `ON → SERVICING` write (was `ld (hl),ZTS_SERVICING`, which dropped it —
  a trigger still held when the handler returned would have re-fired);
- `set_state`'s `ss_write` (was `and ZTS_PENDING`). The load-bearing case is `ON → ON`:
  a redundant `STRIG(n) ON` deliberately does **not** re-seed, so clearing the shadow
  there would let a trigger held across it fake an edge on the next frame.

`OFF` still clears the whole byte — the single "forget everything" reset — which is safe
because the next enable re-seeds.

### 10.3 `event_poll`'s fast-out needed `TRAPSVC` too

`TRAPENA` counts only ON traps and `check_traps` **decrements it on fire**, so with a
single armed trap it is 0 for the entire time that trap's handler runs. Gating the poll
on it alone switched device sampling off exactly during SERVICING, dropping the §10.1
press. The gate is now `TRAPENA != 0 || TRAPSVC != 0` — still two RAM loads on the
common no-trap path. (Found by RAM-tracing the entry byte across the handler, not by
reading the code: the trace showed the press latching correctly and the service record
never being popped.)

### 10.4 Budget — funded by deleting dead code

Measured, not estimated: the §8 guess of ~165 B was **low**. The first assembly overran
the $8000 ceiling by 70 B; the §10.2 refactor recovered ~41 B and two dispatch golfs a
few more, leaving 29 B over. That was funded by **deleting the T1 INTERVAL counter
stanza from `event_poll`** — provably dead code (INTERVAL is MSX2, out of charter, so
nothing writes `ZINTVAL` and nothing can set entry 0 to ON; it predates the oracle
finding that re-sliced T1 to STOP). This is exactly the lever T1 spec §10.3 listed.
The `ZTRAP` entry itself stays allocated so the index enum and priority order are
undisturbed. **Page-1 free after T2: 9 B** — T3 (KEY) needs a real carve, as expected.

### 10.5 Also landed

- `ex_on_stop`'s malformed-syntax exits moved from `stmt_error` (prints and aborts) to
  the **trappable** ERR 2 the reference raises — arc-spec §7's stated convention, now
  oracle-confirmed for `ON STRIG` / `ON STRIG GOTO` (gate cases T/U).
- `trap_line_link` — the shared `$0E,lo,hi` → LINK resolver — replaces the open-coded
  copy in `ex_on_stop` and pre-pays T3's `ON KEY` comma-list.
- `di`/`ei` around the mainline `GTSTCK`/`GTTRIG` calls (§4), since the ISR now reads
  the same PSG latch.

### 10.6 Harness fact worth remembering

zerobas runs an empty `FOR` loop roughly **7× slower** than the VG-8020, so any gate
case that times a handler needs a window sized for zerobas, not for the reference. The
`I_press_in_handler` case takes its delay on the first invocation only for that reason.
