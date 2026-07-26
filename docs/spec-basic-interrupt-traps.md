# spec — interrupt traps (`ON INTERVAL/KEY/SPRITE/STOP/STRIG GOSUB` + the arming statements)

Status: **🔴 ARC REOPENED 2026-07-26 — T1 STOP, T2 STRIG, T3 KEY, T4 SPRITE landed
and gated** (`stop-`/`strig-`/`key-`/`sprite-trap-acceptance`), closing the
input-devices **D-I-5** divergence and the graphics **D-G7-4** handoff — **but
`INTERVAL` is a fifth MSX1 trap family and it was excluded on a FALSE PREMISE.**
See §0. Per-slice packets: [T1](spec-traps-t1-stop-reslice.md) ·
[T2](spec-traps-t2-strig.md) · [T3](spec-traps-t3-key.md) ·
[T4](spec-traps-t4-sprite.md) · **[T5 INTERVAL](spec-traps-t5-interval.md) —
characterized 2026-07-26, PACKET AWAITING SIGN-OFF.** T5's §1 also corrects §4's
INTERVAL bullet below: the counter must tick while the trap is STOPped and while
its handler runs, not only while it is ON.

## 0. RETRACTION — `INTERVAL` is MSX1 after all (2026-07-26)

On 2026-07-24 this arc recorded `INTERVAL` as "an MSX2 keyword, absent from MSX1"
and re-sliced around it. **That conclusion was wrong**, and the way it was wrong is
worth keeping: **the measurement was right and the inference was wrong.**

What was measured (and reproduces exactly today, on the VG-8020 *and* the
CF-3300): `INTERVAL ON` crunches to `FF 85 45 52 FF 94 20 95` — `INT` + the literal
bytes `"ER"` + `VAL` + `ON`. From "there is no `INTERVAL` entry in the MSX1 crunch
table" the arc concluded "`INTERVAL` is not an MSX1 feature". It does not follow,
and the functional test says so plainly:

| program | VG-8020 fires in ~160 jiffies |
|---|---|
| `ON INTERVAL=10 GOSUB … : INTERVAL ON` | **16** |
| `ON INTERVAL=5  GOSUB … : INTERVAL ON` | **33** |
| `ON INTERVAL=20 GOSUB … : INTERVAL ON` | **8** |
| … `: INTERVAL OFF` / `: INTERVAL STOP` / never enabled | **0** / **0** / **0** |

Exact 1/n scaling — it is a real jiffy-period trap, fully working, no error. And
`LIST` **round-trips to `INTERVAL ON`**, because detokenising `INT`+`"ER"`+`VAL`
concatenates back to the source spelling.

`INTERVAL` is simply **not a keyword** on MSX1 — it is a *reserved-word compound*,
the same shape `kwtable.inc` already documents for `MAXFILES` = `MAX`+`FILES` and
`OUTPUT` = `OUT`+`PUT`, with a literal `"ER"` in the middle. The first-match-wins
crunch finds `INT` before it can consider a longer word, and the statement layer
matches the resulting byte sequence.

**This inverts §8 and D-T-5 completely.** Adding an `INTERVAL` keyword would have
*broken* the byte-identical crunch discipline, not preserved it. And the happy
consequence: **zerobas already crunches `INTERVAL ON` and `ON INTERVAL=10 GOSUB 100`
byte-identically to the VG-8020 today**, because it already has `INT` and `VAL` —
verified 2026-07-26. T5 therefore needs **no token, no `kwtable` row, and no crunch
work at all** — only the parse + `event_poll` stanza, which §5/§6 already specify
(they were written for INTERVAL first and were never wrong, only orphaned).

*Reusable lesson:* "absent from the keyword table" ≠ "absent from the language".
A crunch probe answers a **tokenisation** question; only running the feature
answers a **support** question. See [[interval-is-msx1-after-all]].

Originally signed off **2026-07-24** — slicing **T1→T2→T3→T4** approved (D-T-6), and go
straight into T1 from this arc spec (no separate T1 packet). This is the arc-level
spec; T2–T4 still get their own signed-off packets before implementation, in the
graphics-arc style (g1…g8).

Repository: all paths under `/Users/joost/projects/zerobas`. The whole arc is
**repack-only** (`IF ROM_BASE < $4000`) — the trap table, the poll servicer, and the
input readers it leans on are all repack-gated; the lean `basic.rom` stays byte-frozen.

Provenance: the *behaviour* (trap types, `ON X GOSUB` syntax, the ON/OFF/STOP
tri-state, auto-suspend-while-servicing) is a **published contract** (MSX Technical
Handbook §2 the interrupt/trap model; A-tier — see [`allowed-sources.md`](allowed-sources.md)).
The **RAM layout is own-design**, like `CONTLINE`/`CONTVALID` before it: zerobas does
**not** reuse the reference `TRPTBL` address or its exact status-bit encoding — it
places its own table in the freed VARTAB window and matches only *observable*
behaviour. No ROM disassembly; the reference is a black-box + the published model.

---

## 1. Scope — the surface this arc closes

The last unchecked interpreter item ([`TODO.md`](../TODO.md) "Interrupt traps"), plus
the two explicit handoffs into it:

- input-devices **D-I-5** left `STRIG(n) ON/OFF/STOP` and `KEY(n) ON/OFF/STOP` raising
  a (documented-divergence) `ERR 2`; this arc makes them real.
- graphics **D-G7-4** left `SPRITE ON/OFF/STOP` as accepted **no-ops** and `ON SPRITE
  GOSUB` unimplemented; this arc wires them to a real collision trap.

**In scope — the five trap families, each: arm + tri-state + dispatch:**

| Family | Arm (define handler) | Enable/disable/suspend | Event source |
|---|---|---|---|
| **INTERVAL** | `ON INTERVAL=n GOSUB <line>` | `INTERVAL ON/OFF/STOP` | a per-frame down-counter (pure arithmetic) |
| **STOP** | `ON STOP GOSUB <line>` | `STOP ON/OFF/STOP` | Ctrl-STOP (intercept the break path) |
| **STRIG** | `ON STRIG GOSUB <l0>,…,<l4>` | `STRIG(n) ON/OFF/STOP`, n=0..4 | `GTTRIG(n)` edge, once per frame |
| **KEY** | `ON KEY GOSUB <l1>,…,<l10>` | `KEY(n) ON/OFF/STOP`, n=1..10 | function-key press edge |
| **SPRITE** | `ON SPRITE GOSUB <line>` | `SPRITE ON/OFF/STOP` | VDP sprite-collision status bit |

`ON KEY` and `ON STRIG` take a **comma-list** of handler lines, one per key/trigger
(a blank slot = keep/leave that key untrapped). The other three take a single line.

**Explicitly out (deferred / not in this arc):**

- `KEY <n>,"str"` (function-key string assignment) and `KEY LIST` — a display feature,
  not a trap; still `stmt_error` (unchanged, tracked under the editor TODO item).
- Any MSX2 trap surface (`ON INTERVAL` sub-second granularity beyond the 1/frame model
  is already MSX1-faithful; no MSX2-only traps exist to defer).

---

## 2. The reuse story — almost everything already exists

This arc is mostly **wiring**, not new mechanism. Three landed subsystems supply the
parts (map anchors from the infra survey):

### 2.1 The `ON ERROR` trap-branch = the GOSUB-into-handler model
[`basic/interp.asm:752-767`](../basic/interp.asm) is the exact branch to copy for
dispatch: `ld sp,(SAVSTK)` (unwind to run-loop-clean depth) → save resume context →
`ld (CURLINE),de` (setting `CURLINE` **is** the branch, reusing `rp_lp`) → set the
in-handler flag → `jp rp_lp`. The error trap does a **GOTO**-flavoured branch (no
return frame — `RESUME` is its return). An **event trap does a GOSUB**: it must push a
4-byte GOSUB frame first, so the handler's `RETURN` resumes the interrupted line —
frame shape from [`ex_gosub`](../basic/program.asm) `504-561` / `eon_gosub` `939-973`
(`[CURLINE:2][resume-ptr:2]` at `(GSP)`, bounds-checked vs `GOSUB_STK_END`).

### 2.2 The H.TIMI PLAY servicer = the per-frame poll seam
[`basic/playsvc.asm:48-93`](../basic/playsvc.asm). `play_install` writes a bare `JP
play_service` into `H_TIMI` ($FD9F). `play_service` is **main page-1 resident, reached
by a near JP** (never a sub-ROM tenant: every page-1 tenant runs under DI so a VBLANK
never fires mid-tenant), entered DI, register-transparent, touches only PSG + its
queues + `MUSICF` — **never `JIFFY`, never the keyboard**. Its `MUSICF`-zero fast-out
(`57-62`) is the exact insertion point: the event poll runs first, then falls into the
existing `MUSICF` check. **A `CALSLT` in the VBLANK path is ruled out** (input-devices
§, D-I-2 precedent): the poll must be resident code doing direct port / RAM work.

### 2.3 The matrix-hold acceptance harness = the gate mechanism
[`probes/lib/omsx_repl.py:232-244`](../probes/lib/omsx_repl.py) (`holds` →
`keymatrixdown/up` scheduling) and the `prologue` seam (`191-198`) were built by the
input-devices arc **explicitly for this arc** ("the interrupt-trap arc needs the same
capability for `ON KEY`", D-I-3). `basic_probe_input_devices.py`'s `MATRIX` table
(`140-151`) is the pattern each slice's gate extends to press keys/triggers *while a
trap-armed program runs* and count the fires.

### 2.4 The run-loop dispatch point
[`basic/program.asm:262-269`](../basic/program.asm) — the `BREAKX` poll between
statements. The event-trap dispatch check lives **right here**: after `BREAKX`, before
`call exec`, test "any trap enabled AND pending?" and if so branch into its handler.

### 2.5 The input readers
`ev_ff_strig` ([`basic/expr.asm:1022`](../basic/expr.asm)) / `GTTRIG $00D8`,
`GTSTCK $00D5`, function-key matrix rows — the STRIG/KEY event sources. `ex_sprite` /
`spr_noop` ([`basic/graphics.asm:1023-1038`](../basic/graphics.asm)) — the no-ops to
promote. `ex_key` ([`basic/screen.asm:196-217`](../basic/screen.asm)) — the `KEY
ON/OFF` display statement to disambiguate from the new `KEY(n)` trap form.

---

## 3. Own-design RAM: the trap table `ZTRAP`

Reference `TRPTBL` is not reused (address or bit layout). zerobas defines **`ZTRAP`**
in the freed VARTAB window: `$E1D1..$E240` (~111 B) is free repack RAM **adjacent to
the existing error-trap state** (`SAVSTK`…`SAVTXT` end at `$E1D1`) — the natural home.

**Layout (proposed, own-design — sign-off item D-T-1):** 18 entries × 3 B = 54 B, plus
the interval counter pair. Entry order chosen so the poll can index by a small enum:

```
ZTRAP        equ $E1D1     ; 18 * 3 = 54 B
  ; index 0        : INTERVAL   (1 entry)
  ; index 1        : STOP       (1 entry)
  ; index 2        : SPRITE     (1 entry)
  ; index 3..7     : STRIG 0..4 (5 entries)
  ; index 8..17    : KEY   1..10(10 entries)
  ; each entry = db state ; dw handler_line_link   (3 B)
ZINTVAL      equ $E207     ; 2 B: INTERVAL reload period (frames); 0 = disarmed
ZINTCNT      equ $E209     ; 2 B: INTERVAL live down-counter
  ; -> $E20B, still < $E240; ~53 B headroom left in the VARTAB window
```

**State byte encoding (own-design — sign-off item D-T-1):**
```
bit 1-0 : tri-state  00=OFF  01=ON  10=STOP(suspended)
bit 7   : PENDING    an event occurred and is latched, awaiting dispatch
```
- `ON X GOSUB` sets the entry's `handler_line_link` (and, per the reference, implies
  the trap starts **OFF** until an explicit `X ON`). A zero link = "no handler" → the
  arming statement is a no-op / the trap can never fire.
- The dispatcher fires an entry iff **state==ON AND PENDING AND handler!=0**. On fire it
  clears PENDING, **sets state=SERVICING** (a distinct 4th state, auto-suspend while the
  handler runs — see the re-enable mechanism below), pushes the GOSUB frame, and branches.
  `RETURN` from the handler restores state to **ON** (the classic auto-resume).

**Re-enable-on-RETURN — the GSP-match service stack (own-design, D-T-1a).** A repeating
`ON INTERVAL=n GOSUB … : RETURN` must re-fire every period, so `RETURN` from a trap
handler has to put the trap back to ON — and it must nest (a trap firing inside another
handler). The 4-byte GOSUB frame (`[CURLINE][resume-ptr]`) has no spare bit to tag, and
widening it would touch all of RETURN/GOSUB. Instead: on dispatch, after pushing the
normal GOSUB frame, record a service entry `{gsp: <GSP after the push>, idx: <trap>}` on
a small LIFO (`TRAPSTK`, a few entries — nesting depth of *simultaneously-servicing*
traps is tiny). `ex_return`, gated by a `TRAPSVC` count byte (zero for the common case →
no added cost), compares `GSP` (before its pop) against the top service entry's `gsp`;
on a match this RETURN is the trap's own return, so it pops the service entry and, iff
that trap is still in SERVICING (a handler `X OFF`/`X STOP`/`X ON` overrides), sets it
back to ON. Nested normal GOSUBs push `GSP` higher and their RETURNs pop back down first;
only when `GSP` returns to the recorded value is the trap frame on top — so the match is
exact and nests. **Four states, not three:** `00=OFF 01=ON 10=STOP(user) 11=SERVICING`;
only ON fires, so SERVICING is the auto-suspend. A recurrence during the handler re-sets
PENDING but cannot fire (state≠ON) — it fires once after RETURN, matching the reference.
- `X STOP` = state→STOP but PENDING still latches (a suspended trap *remembers* one
  event); a later `X ON` with PENDING already set fires at the next statement boundary.
- `X OFF` = state→OFF **and** clears PENDING (a disabled trap forgets).

This bit layout and the auto-STOP/auto-resume are the observable reference semantics;
the encoding itself is quarantined in [`basic/PROVENANCE.md`](../basic/PROVENANCE.md)
as own-design (same treatment as `CONTVALID`).

---

## 4. The per-frame poll (H.TIMI extension)

Insert an `event_poll` ahead of the `MUSICF` fast-out in the `H_TIMI` seam (D-T-2 is
*how* to insert — extend `play_install`'s target, or a 2-entry micro-dispatcher).
`event_poll` is resident, DI, register-transparent, and for each **armed** trap sets
PENDING on an event **edge**:

- **INTERVAL** — if `ZINTVAL!=0`: `dec ZINTCNT`; on reaching 0, reload from `ZINTVAL`,
  set INTERVAL PENDING. Pure arithmetic, zero I/O — this is why INTERVAL is slice T1.
- **STRIG(n)** — read the trigger (direct PSG/PPI, the `GTTRIG` logic inlined — a
  `CALSLT` is banned in VBLANK), edge-detect vs a 5-bit "last frame" shadow, set PENDING
  on a 0→1 press.
- **KEY(n)** — scan the function-key matrix rows directly, edge-detect vs a shadow, set
  PENDING per newly-pressed function key.
- **SPRITE** — sample the VDP sprite-collision status (D-T-4, the source fork), set
  PENDING on a 0→1 collision edge.
- **STOP** — Ctrl-STOP: **not** polled here (it is caught on the break path, §6), so the
  poll only touches INTERVAL/STRIG/KEY/SPRITE.

Register-transparency and the "no `JIFFY`/no BIOS-buffer read" contract are inherited
verbatim from `play_service`.

---

## 5. The dispatcher (run-loop)

At [`program.asm:262-269`](../basic/program.asm), after `BREAKX`, add a
**`check_traps`** step (only when at least one trap is armed — a single "any trap live"
byte gates the whole cost, so the common no-trap program pays ~one load+or). It scans
`ZTRAP` in priority order and, for the first entry with state==ON && PENDING &&
handler!=0, performs the §2.1 GOSUB-branch: clear PENDING, auto-STOP that entry, push
the GOSUB frame, `ld (CURLINE)` the handler link, `jp rp_lp`. `RETURN` unwinds normally
(`ex_return`) and restores the entry to ON.

**Priority (D-T-3):** the reference services in a fixed order. Proposed: the enum order
of §3 (INTERVAL, STOP, SPRITE, STRIG 0..4, KEY 1..10). One trap dispatched per statement
boundary (a second pending trap fires at the next boundary) — matches the reference's
"one trap per inter-statement gap."

---

## 6. STOP trap — intercepting the break path

Ctrl-STOP has an existing owner: the `BREAKX`→`do_break` path
([`program.asm:262-269, 307-336`](../basic/program.asm)) prints `break in <line>` and
ends the RUN. When the STOP trap is **ON**, a Ctrl-STOP must instead **fire the trap**
(GOSUB the handler) and *not* break. When OFF/STOP, the normal break happens. So
`do_break`'s entry gets a guard: if STOP-trap state==ON, set its PENDING and let
`check_traps` dispatch it (do **not** break). A held Ctrl-STOP inside the handler still
breaks (reference behaviour: a second Ctrl-STOP while servicing the STOP trap aborts) —
covered because the trap auto-STOPs itself on dispatch.

---

## 7. Parsing — statements + `ON X GOSUB`

**`ON X GOSUB` family** — `ex_on` ([`program.asm:907-913`](../basic/program.asm))
already peeks the token after `ON` (`jp z,ex_on_error` for `ERROR`). Add sibling peeks:
`INTERVAL`/`KEY`/`SPRITE`/`STOP`/`STRIG` → a shared `ex_on_trap` that (a) for
`INTERVAL`, consumes `=n` and stores `ZINTVAL`; (b) reads the handler line(s) —
single line for INTERVAL/STOP/SPRITE, a comma-list for KEY/STRIG — via the existing
`find_line_bc`; (c) writes the `handler_line_link` field(s) of the matching `ZTRAP`
entries; leaves state OFF (arm ≠ enable).

**Arming statements** — five `<kw> ON|OFF|STOP` forms:
- `INTERVAL ON/OFF/STOP` — new keyword+token (§8), new `ex_interval`.
- `STOP ON/OFF/STOP` — `ex_stop` ([`program.asm:383`](../basic/program.asm)) currently
  takes no argument; add the `ON/OFF/STOP` sub-parse (bare `STOP` stays the break).
- `SPRITE ON/OFF/STOP` — promote `spr_noop` ([`graphics.asm:1023-1038`](../basic/graphics.asm))
  to set the SPRITE entry's state (from D-G7-4 no-op → real).
- `STRIG(n) ON/OFF/STOP` — new `ex_strig_stmt`, replaces the D-I-5 `ERR 2`; parse
  `(n)` (0..4), set entry n's state.
- `KEY(n) ON/OFF/STOP` — extend `ex_key` ([`screen.asm:196`](../basic/screen.asm)) to
  branch on `(` (trap form, n=1..10) vs `ON/OFF` (the existing display form). Replaces
  the D-I-5 `ERR 2` for `KEY(n)`.

Malformed forms follow the **trappable** `ld a,2 / jp raise_error` convention
(`gfx_syntax`, [`graphics.asm:1044`](../basic/graphics.asm)), not `stmt_error`, so a
program can `ON ERROR`-trap its own bad trap statement — consistent with the
error-handling follow-up (statement syntax errors are trappable).

---

## 8. Tokens

No new tokens **at all** — including for `INTERVAL`. The `ON X GOSUB` statements are
built from existing tokens (`ON $95` + event keyword + `GOSUB $8D` + `$0E`
line-refs), and `KEY $CC`/`SPRITE $C7`/`STOP $90`/`STRIG $FF$A3`/`OFF $EB` already
exist.

⚠️ **This section previously said "`INTERVAL` is the one new keyword" and D-T-5 told
us to pick a token byte for it. Both are RETRACTED — see §0.** `INTERVAL` is not a
keyword on MSX1; it is a reserved-word compound `INT` + literal `"ER"` + `VAL`
(`FF 85 45 52 FF 94`), like `MAXFILES` = `MAX`+`FILES`. **Adding a token would have
broken byte-identical crunch, which is what this section exists to protect.**
zerobas already emits the reference bytes for `INTERVAL ON` and
`ON INTERVAL=n GOSUB` with no change whatsoever (verified 2026-07-26), so T5's token
work is **zero** and its `kwtable`/low-region row is **zero bytes**.

---

## 9. Slicing (the primary sign-off decision, D-T-6)

The arc is naturally cut by **event-source mechanism**, simplest first so the
machinery (table + poll seam + dispatcher + GOSUB-branch + RETURN-resume) is proven on
the zero-I/O case before any device scanning:

- **T1 — trap core + INTERVAL.** `ZTRAP` table, the H.TIMI `event_poll` seam, the
  run-loop `check_traps` dispatcher, the GOSUB-branch + auto-STOP + RETURN-resume, and
  INTERVAL as the first event (pure counter). `ON INTERVAL=n GOSUB` + `INTERVAL
  ON/OFF/STOP` + the new keyword/token. **Proves the whole skeleton with no device
  complexity.** Gate: a new `interval-trap-acceptance` probe — a program that counts
  fires over a known frame span; plus a host unit test of the counter + state machine.
- **T2 — STOP + STRIG traps.** `ON STOP GOSUB` / `STOP ON/OFF/STOP` (the break-path
  intercept, §6) and `ON STRIG GOSUB` / `STRIG(n) ON/OFF/STOP` (GTTRIG edge). Both are
  "sample an input, edge-detect." Gate extends the matrix-hold harness (press the
  trigger / Ctrl-STOP while a trap program runs). Closes the D-I-5 STRIG divergence.
- **T3 — KEY trap.** `ON KEY GOSUB` / `KEY(n) ON/OFF/STOP` (10 function keys, matrix
  decode, `KEY(`-vs-`KEY ON` disambiguation). The fiddliest scan → last of the input
  traps. Gate presses function keys via the matrix harness. Closes the D-I-5 KEY
  divergence.
- **T4 — SPRITE collision trap.** Promote `SPRITE ON/OFF/STOP` from no-op + `ON SPRITE
  GOSUB`; resolve the VDP collision-source fork (D-T-4). Gate: a graphics program that
  collides two sprites and counts trap fires. Closes the graphics D-G7-4 handoff.

Alternative cuts to weigh at sign-off: **(a)** fold T2+T3 into one "input traps" slice
(STOP+STRIG+KEY together) — fewer slices but a bigger byte step and a fatter gate;
**(b)** put SPRITE (T4) second, right after the core, since it's a single-entry trap
like INTERVAL and defers the multi-entry list parsing. Recommend the four-slice order
above (**T1→T2→T3→T4**): monotone in mechanism complexity, and it lands the two
divergence-closing input traps (D-I-5) before the graphics handoff.

---

## 10. Byte budget — the dominant risk

**Measured now: page-1 free = 2 B, page-0 low region = 19 B** (`make basic-reloc`).
The arc is byte-starved before it starts. Every slice will need a carve or eviction,
exactly as input-devices did. This is the #1 execution risk and it shapes the order:

- Do the standard **measure-first** step per slice (per the recurring arc lesson: never
  declare a wall before measuring the real number).
- Candidate funding levers, cheapest first (to be scouted per slice, not pre-committed):
  a dispatch-golf on `ex_on`'s sibling peeks; the `ev_f_ff` / trap-statement parsers
  sharing one range-check helper; and, only if a real carve is needed, an eviction to a
  page-0 sub-ROM tenant of something **not** in the interrupt path (the poll/dispatch
  code itself must stay resident — never evict interrupt-context code, D-I-4 precedent).
- The poll (`event_poll`) and dispatcher (`check_traps`) are small; the table is RAM
  (free). The bulk is the **parsers** (five arming statements + the `ON X GOSUB` list
  walker) — these are the eviction candidates if page 1 can't hold them.

**Because page-1 is at 2 B, the first real work of T1 is a measured carve, and the T1
packet must land that carve before the feature.** If measurement shows the core doesn't
fit even after the cheap golf levers, that is a genuine STOP-and-confirm fork (a larger
eviction changes scope) — surfaced at the T1 packet, not decided here.

### 10.1 T1 carve — sizing (measured 2026-07-24)

Free ROM in the merged main = **2 B page-1 + 19 B page-0 low region = 21 B** (the run
loop can `call` page-0 low-region code directly — same slot, both pages mapped — so both
pools are usable for the EI-context dispatcher; only `event_poll` is hard-pinned to
page 1 by the DI/H.TIMI contract).

**Refined architecture (D-T-2a, decided 2026-07-24 during T1 — supersedes the
"resident dispatcher" assumption of §5).** Detailing the actual Z80 showed a *resident*
general dispatcher + service stack + RETURN hook runs **~145–185 B**, not ~90 B — a
~110 B carve. But only `event_poll` is genuinely interrupt-path (DI, in H.TIMI); the
dispatcher (`check_traps`), the service-stack push, and the RETURN re-enable all run in
the **EI run loop**, touch only **RAM** (`ZTRAP`, `GSP`, `TRAPSTK`, `GOTOTGT`/`GOTOFLAG`/
`CURLINE` — all always-mapped), and can therefore live in a **page-1 sub-ROM tenant**
(sub.rom has its own budget, off the 37 B). They are invoked by `subrom_call` **only when
a resident `TRAPPEND` byte is set** — `event_poll` (resident) raises `TRAPPEND` when it
latches a PENDING, so the per-statement run-loop cost is just `ld a,(TRAPPEND) / or a /
jr z` (a RAM load), and the expensive `subrom_call` fires ~once per trap *event* (e.g.
once/second for `INTERVAL=60`), never per statement — no perf regression even for a
trap-armed tight loop. `gosub_push` (main page-1) is unreachable from the tenant (page 1
is switched out), so the tenant **inlines** its own frame-push — that's fine, it's the
one place that doesn't reuse the golfed helper.

**Split the T1 resident need (measured, refined):**
- **Resident page-1 (unavoidable):** `event_poll` INTERVAL tick + `TRAPPEND` raise
  (~47 B, DI); the run-loop `TRAPPEND` gate + `subrom_call` (~15 B); the `ex_return`
  `TRAPSVC` gate + `subrom_call` (~12 B); `trap_install` htimi seam (~6 B, extends
  `play_install`). ≈ **80 B**.
- **Sub-ROM page-1 tenant (off the 37 B budget):** `check_traps` dispatch + service-push
  + RETURN re-enable + `trap_init` (zero `ZTRAP` at boot).
- **Sub-ROM page-0 tenant (off-budget):** the statement parsers — `ON INTERVAL=n GOSUB`
  arm + `INTERVAL ON/OFF/STOP` + the `set_state` helper (adjusts `TRAPENA`). Plus the
  `INTERVAL` keyword row (low region).

So resident T1 ≈ **80 B** against **37 B** free (post-golf) → a **~43 B carve** (was ~70).

**Funding plan (cheapest first):**
1. **Golf — factor `gosub_push`.** ✅ **DONE 2026-07-24** (commit after 3284a6e): repack-
   only branch, lean byte-identical, `test_control_flow` + `unit-test` 51/51 green.
   **Freed page-1 2 B → 37 B (35 B, better than the ~20 B estimate).**
2. **Move dispatch + parsers to tenants** (D-T-2a above) — keeps ~100 B of the machinery
   *off* the 37 B page-1 budget entirely.
3. A cold-cluster eviction — see §10.2 for the **measured** requirement (~80 B; the
   D-T-2a ~43 B projection under-counted the per-site `subrom_call` stub boilerplate).

### 10.2 T1 resident — MEASURED (2026-07-24, `basic/traps.asm` written + wired, then backed out)

Wiring the resident poll (`event_poll` + `htimi_service` trampoline + `trap_init`) and
building `basic-reloc` overran the `$8000` page-1 ceiling by **34 B** (`__MEAS_PAGE1_END
= $8022`). Measured routine sizes:

| Piece | Bytes | Placement |
|---|---|---|
| `event_poll` (INTERVAL tick, DI) | **48** | resident page-1 (hard) |
| `htimi_service` trampoline | 6 | resident page-1 |
| `trap_init` (ZTRAP zero-fill) | 14 | movable → dispatch tenant |
| run-loop gate + dispatch `subrom_call` stub (est.) | ~34 | resident page-1 (in `rp_exec`) |
| `ex_return` gate + reenable `subrom_call` stub (est.) | ~30 | resident page-1 (in `ex_return`) |

So resident T1 ≈ **48 + 6 + 34 + 30 = ~118 B** (with `trap_init` in the tenant) against
**37 B** free → **a ~80 B eviction is required** — bigger than §10.1's ~43 B, because
each `subrom_call` site carries ~15–20 B of IX-setup/marshalling boilerplate that the
D-T-2a estimate omitted. Tenant-dispatch is still the right call (a *resident* dispatcher
would need ~132 B eviction, per §10.1's 145–185 B), but the eviction is real and
moderate, not negligible.

**Eviction target (D-T-8 — ⛔ PAINT+CIRCLE WHOLESALE EVICTION NON-VIABLE, scouted
2026-07-24; the sign-off was on a false premise).** The closure scout found the killer:
`ex_paint` (171 B private) and `ex_circle`/`circ_aspect` (661 B private) are **~90–100 %
`eval`/float-pack-bound**, and the float pack (`fp_*`, and `eval` itself bottoms out in
it) lives in the **page-0 low region `$2812–$3FFF` that the sub-ROM overlays** — a page-0
tenant *cannot* call it (confirmed: `basic/graphics.asm:928-930` says so verbatim for
DRAW; `tools/check_tenant_closure.py --page0` fails the build on exactly this escape).
This is precisely why the current split exists (resident stub does all eval/float **while
page 0 is mapped**, then marshals an *integer* param block to the tenant). So neither can
move wholesale; the `--page0` gate would reject the cut. The **only** mechanism that
reclaims eval-heavy parse bytes is the **DRAW-style co-routine** (`gfx_draw_op`,
`basic/graphics.asm:916-1001`): the tenant walks tokens and bounces each sub-expression
back to the resident via `GFX_DEXP`/`GFX_DREQ`/`GFX_DVAL`/`GFX_DRESUME`. Re-authoring
CIRCLE's ~218 B grammar walk as such a co-routine is a substantial, risky sub-arc — out
of proportion to T1.

**Revised floor (D-T-8a).** Even a *maximally* tenant-ised T1 (dispatch + reenable +
`trap_init` all behind one selector-dispatched sub-ROM entry, one shared `subrom_call`
stub) still needs **~80 B resident** and cannot go below **~45 B**: `event_poll` ~48 B is
DI-pinned to page 1, plus the run-loop `TRAPPEND` gate + `ex_return` `TRAPSVC` gate + the
shared stub (~30 B, must live in the resident routines they hook). Against **37 B** free,
the floor is a **~45 B page-1 carve of genuinely `eval`-free, cold, self-contained code**
(the only kind a tenant can take). **This is a real STOP-and-confirm fork** — the byte
budget the spec flagged as the dominant risk from day one. Options in §10.3.

Original candidate list (for record):
- **`ex_paint` (75 B)** → the existing `graphics_tenant` (page-0). Precedent: the G5
  slice already evicted `casmatch` *to fund PAINT*; moving PAINT itself onward is the
  mirror. Risk: PAINT's flood-fill closure may drag helpers.
- **`ex_circle` + `circ_aspect` (~160 B, take one)** → `graphics_tenant`. More than
  needed; a clean CIRCLE-cluster lift.
- **disk `lrset_common` (82 B) / `do_name` (98 B)** → `dirverb_tenant`. Cold, but disk
  closures can be tangled.
- **`event_poll` golf** first (shave the 48 B — e.g. `and 3`/`dec a` for the state test,
  fold the reload) — worth ~4–6 B, reduces but does not remove the eviction.

### 10.3 The space fork — options (D-T-8b, needs a call)

The ~45 B floor needs `eval`-free cold page-1 code, which PAINT/CIRCLE are not. Paths:

1. **Targeted scout for pure (non-`eval`) cold clusters.** Find ~45–80 B of page-1 code
   that bottoms out only in page-1/RAM/BIOS (no `eval`/`fp_*`/`parse_coord`/`str_*`) —
   the only kind a page-0 tenant can take. Candidates to check: VDP/screen helpers, the
   line-editor tail, cassette/tape byte plumbing, `list.asm` residue, disk sector glue
   not already in `fatprim_tenant`. *May or may not exist in sufficient size — a scout
   answers it. Lowest-risk if it lands.*
2. **CIRCLE grammar-walk → DRAW-style co-routine** (~150 B reclaimed). The proven
   mechanism, but a substantial, risky sub-arc (re-author CIRCLE's parser tenant-side
   with the eval-bounce protocol; keep the CIRCLE differential green). Overkill for T1's
   ~45 B but would fund the whole trap arc T1–T4. *High effort, high risk.*
3. **A page-1 tenant for the dispatch** (opposite visibility): reaches the float pack but
   **not** `eval`/`parse_coord`/`skip_spaces` (main page-1, switched out) — so it doesn't
   help the parse either, and the dispatch itself needs no float. Doesn't move the needle.
4. **Reclaim page-0 low-region space** to host `event_poll` there (it's reachable during
   H.TIMI while page 0 is mapped) — but the low region is also nearly full (19 B), so this
   just relocates the same eviction problem.
5. **Pause the interrupt-traps arc as blocked-on-space**; do a dedicated page-1 space
   program (option 2, or a broader eviction sweep) as its own arc first, or pick a
   different, space-cheap TODO item now.

*Recommendation: option 1 (targeted pure-code scout) — cheapest and lowest-risk if it
finds ~45–80 B; fall back to option 2 (or 5) only if the scout comes up dry.*

### 10.4 Space RESOLVED (2026-07-24) — evict `build_83_name` (D-T-8c)

**✅ LANDED 2026-07-24.** The carve is implemented and gated green: `build_83_name`
now lives in the page-1 tenant `fcbname_tenant` (`SUBROM_IDX_FCBNAME=18`,
`sub/fcbname.asm`), body shared byte-identically via `basic/fcbname-body.inc`, the
resident stub is `basic/bload.asm`'s repack branch. **Measured page-1 free rose
37 B → 155 B** (~118 B net freed, matching the projection) — enough to keep the trap
dispatch RESIDENT (no dispatch tenant). Gates: `make basic-reloc` (lean byte-identity
+ `--page1` closure with 19 tenants), `unit-test` 51/51, `diskbasic-acceptance-repack`
34/34 (NAME / FILES(wild) / KILL(wild) / LOAD / SAVE / BLOAD exercise the tenant +
the `bn_star_*` wildcard path on the live merged machine). One implementation note vs
the plan below: the body calls `fcb_upcase` (not `upcase`) — a zero-byte EQU onto the
resident `upcase` in the lean cart, a co-located page-1 clone in the tenant — because
the sub image already owns the name `upcase` in its (unmapped-here) page-0 island.
**Next span: wire `basic/traps.asm` in + `check_traps`/`ex_return` dispatch + parsers.**

The option-1 scout found the cheap path exists. **Chosen: evict `build_83_name`** (the
disk 8.3-FCB-name builder, `basic/bload.asm:301-411`, ~139 B) to a new **page-0 sub-ROM
tenant** — substituted for the non-viable PAINT+CIRCLE. Why it's the pick:
- **Closure is clean:** its only external callee is `upcase`, **already sub-resident**
  (`sub/tkfloat.asm:648`); everything else (`bn_*`) is private. No `eval`/`fp_*`, no
  page-0-low escape, no BIOS — passes `--page0`.
- **Cold:** one caller (`parse_disk_fcb:200`), on the disk LOAD/SAVE/FILES/NAME path;
  never per-statement/per-loop.
- **Over-delivers:** ~139 B freed (net ~122 B after the ~17 B resident marshal stub) —
  well past T1's ~45 B floor, enough headroom to keep the trap **dispatch RESIDENT**
  (`check_traps` + `ex_return` reenable call `gosub_push` directly) — **no dispatch
  tenant, no `subrom_call` stubs** — materially simpler than D-T-2a assumed. T2–T4 get
  headroom too.
- **Lower-risk than PAINT/CIRCLE:** a self-contained RAM name-builder, not a flood-fill.

**PAGE-1 tenant, not page-0 (D-T-8d — sub-obstacle resolved).** The page-0 dispatch
table is **FULL**: 12 entry rows (indices 0–11) fill `$0010..$0037` right up to the
`$0038` interrupt vector (`sub/sub.asm` `sub_p0_ping` comment — the ping already had to
move *below* the vector to fit index 11). No room for a 13th page-0 entry. So `build_83_
name` becomes a **page-1** tenant at **`SUBROM_IDX_FCBNAME = 18`** (P1 space; base `$4010`
+ 3·18 = `$4046`, table has room; page-1 tenants have no `$0038` cap). A page-1 tenant
can't reach the sub `upcase` (it's page-0), so **inline `upcase`** into the moved body
(~8 B, trivial) — then the tenant is a pure RAM leaf (reads the filename via `HL` from
`BN_PTR`, writes `DISK_FCB_NAME`, all RAM/always-mapped), passing `--page1`.

**Marshalling (SPLIT, cf. `fatprim_tenant`/`casmatch`):** resident stub at
`parse_disk_fcb:200` stores `HL`→`BN_PTR` (new sysvar), computes `IX = SUBROM_ENTRY_
BASE_P1 + 3*SUBROM_IDX_FCBNAME`, `subrom_call`; the tenant reads `BN_PTR`, runs the moved
body (inlined `upcase`, writes `DISK_FCB_NAME`), writes back `BN_PTR`=advanced ptr and
`BN_STAT`=CF; the stub reloads `HL`←`BN_PTR`, `rra` `BN_STAT`→CF, `jp c,load_error`.
Verify: `make diskbasic-acceptance` + disk LOAD/SAVE/FILES/NAME probes + reloc/lean
byte-identity + `check_tenant_closure.py --page1`. Files: new `sub/fcbname.asm` (+
`Makefile` `SUB_PARTS` — the stale-tenant landmine), `sub/equates.inc` idx 18 (P1),
`sub/sub.asm` `sub_p1_table` `jp fcbname_tenant`, `basic/bload.asm` (remove body 290-411
+ stub the call at 200), `basic/sysvars.inc` (`BN_PTR`/`BN_STAT` + tenant ABI note +
`SUBROM_IDX_FCBNAME` sync). **This is pure, well-scoped implementation — the next span.**

---

## 11. Open decisions for sign-off

- **D-T-1 — `ZTRAP` layout + state-bit encoding (§3).** Own-design table at `$E1D1`,
  18×3 B + the interval pair; tri-state in bits 1-0, PENDING in bit 7. *Recommend as
  written.* Alternative: separate parallel arrays (states / links) instead of
  interleaved entries — marginally simpler poll indexing, same byte cost.
- **D-T-2 — poll insertion (§4).** Extend the `H_TIMI` seam so `event_poll` runs ahead
  of `play_service`'s `MUSICF` fast-out. *Recommend:* a tiny resident dispatcher at the
  seam target (`event_poll` then fall into `play_service`), so both share one `H_TIMI`
  hook. Alternative: chain two `JP`s.
- **D-T-3 — dispatch priority + one-per-boundary (§5).** Fixed enum order, one trap per
  inter-statement gap. *Recommend as written* (matches the reference).
- **D-T-4 — SPRITE collision source (§4, T4). ✅ RESOLVED at the T4 packet
  ([`spec-traps-t4-sprite.md`](spec-traps-t4-sprite.md) §2): option (a), read
  `STATFL`.** Option (b) is impossible by construction, not merely worse — C-BIOS
  latches S#0 *before* calling `H_TIMI` and S#0 is read-to-clear, so nothing at that
  seam can ever see the bit; the same ordering makes (a) exact, with no one-frame
  lag. The "weak provenance" worry below does not survive: `$F3E7` is a published
  work-area address, already what `VDP(8)` returns. *Original text:*
  The VDP collision flag (status reg S#0
  bit 5) is **read-to-clear** and C-BIOS's own $0038 ISR already samples S#0 each frame
  (latching into its status sysvar) — so a second direct-port read in `event_poll`
  races the BIOS and one of the two loses the flag. Options: **(a)** read the C-BIOS
  status latch (depends on a BIOS internal — weak provenance, but the graphics arc's
  [`vdp-direct-port-read-fetch-window`] lesson shows direct reads are workable); **(b)**
  direct-port sample in `event_poll` and accept the race characteristics; **(c)** defer
  T4 and ship T1–T3, leaving `SPRITE ON/OFF/STOP` as the current no-op + `ON SPRITE
  GOSUB` a documented not-yet. *Recommend deciding this at the T4 packet after an
  empirical read of how C-BIOS handles S#0* — it is the one fork with a real oracle
  question, and it does not block T1–T3.
- **D-T-5 — `INTERVAL` token (§8). 🔴 RETRACTED 2026-07-26 — the decision as written
  would have SHIPPED A BUG.** There is no `INTERVAL` token to pick: it is a
  reserved-word compound (§0), and adding a keyword row would have made zerobas
  crunch it differently from every real MSX1 — the exact failure this decision was
  meant to prevent. **Nothing to do:** zerobas already emits the reference bytes.
  The 2026-07-24 "oracle-confirm via the crunch probe" step *did* run and *did*
  return the truth; what failed was reading "no keyword entry" as "no feature".
- **D-T-6 — slicing + order (§9). ✅ SIGNED OFF 2026-07-24: T1→T2→T3→T4** by mechanism
  complexity, and start T1 directly from this arc spec (no separate T1 packet).
- **D-T-7 — byte strategy (§10).** Measure-first each slice; cheap golf before any
  carve; never evict interrupt-path code. *Recommend as written*; the one that could
  bite is T1 not fitting in 2 B even after golf — a STOP-and-confirm at that packet.

---

## 12. Implementation order (T1, after sign-off)

1. **Measure** the T1 core's byte cost against the 2 B page-1 budget; scout the cheapest
   funding lever; land the carve **before** the feature (STOP-and-confirm if it doesn't
   fit after golf).
2. `ZTRAP` sysvars + the state-machine helpers (arm / set-state / fire) — host
   unit-tested first (`tests/test_traps.py`, emulator-free), since the tri-state +
   auto-STOP + PENDING-latch logic is where the subtle bugs live.
3. `event_poll` INTERVAL counter at the `H_TIMI` seam; `check_traps` dispatcher at the
   run-loop point; the GOSUB-branch + RETURN-resume.
4. Parse `ON INTERVAL=n GOSUB` + `INTERVAL ON/OFF/STOP` + the new keyword/token;
   crunch-corpus oracle-confirm the token.
5. The `interval-trap-acceptance` gate (fire-count over a frame span, VG-8020
   differential) — and **run it** (the standing "builds green but never run" trap).
6. Full standing-gate sweep + the reloc/lean byte-identity gate; commit.
