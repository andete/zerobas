# Spec — graphics Slice G2: `PSET` / `PRESET` / `POINT` (the pixel op + color clash)

**Status: LANDED (2026-07-21).** Signed off, implemented, gated. `PSET`/`PRESET`/
`POINT` land byte-identical to the VG-8020.

> **Verified (2026-07-21).** `make graphics-acceptance` — the VG-8020 differential —
> is **PASS**: Phase A (9 pixel cases: single / clash / clear-bg / PRESET-erase /
> PRESET-c / STEP / mid-screen / default-FORCLR / off-screen-no-op) reads back the
> **pattern AND colour planes** and matches the reference byte-for-byte; Phase B (5
> behaviour cases: SCREEN-0 ERR 5, >int16 ERR 6, off-screen no-op, POINT values,
> POINT STEP) matches too. `make unit-test` (35 graphics leaf cases) PASS; the G1
> floor gate still PASS; lean `basic.rom` byte-identical.
>
> **Load-bearing bug found only by the differential (the arc lesson, [[error-handling-arc]]):**
> the tenant's direct-port VRAM read raced the VDP's **read-ahead fetch window**. A
> tight `out $99 / out $99 / in $98` reads the data port before the VDP has fetched
> `VRAM[addr]` into its read-ahead latch, so the byte is the STALE previous latch —
> the BIOS `RDVRM` gets the ~30-T gap for free from its `SETRD` ei/ret/call framing,
> our inline read had zero. Symptom: a plot's colour read intermittently returned the
> pattern byte, and *which* cases failed shifted with unrelated upstream timing (a
> STEP-token parse flipped it) — a textbook Heisenbug. Fixed with an 8-NOP settle
> window in `gfx_rd_raw` (matching RDVRM's gap); the gate regresses without it.
> Interrupts were NOT the cause (a whole-op `di` changed nothing). Every step was
> measured empirically ([[graphics-arc]] direct-port fragility). Implementation:
> [sub/graphics.asm](sub/graphics.asm), [basic/graphics.asm](basic/graphics.asm),
> [probes/basic/basic_probe_graphics.py](probes/basic/basic_probe_graphics.py),
> [tests/test_graphics.py](tests/test_graphics.py).

The §9 decisions are approved and the three open measurements (G2-d/f/g) are RESOLVED
on the Philips VG-8020 (folded into §4/§5/§6/§9 and arc §11.5/§11.8/§11.9).
Slice-design addendum to the arc
spec [`spec-basic-graphics.md`](spec-basic-graphics.md) (crux D1/D2/D3/D4 approved;
§11 characterization complete) and the landed floor [`spec-basic-graphics-g1.md`](
spec-basic-graphics-g1.md). G1 built and proved the VDP floor (direct-port I/O,
DI-guarded latch, `gfx_calc_addr`, interrupt-under-draw gate); **G2 is the first
user-visible statement** and delivers the atomic read-modify-write pixel op that all
of G3–G6 (`LINE`/`CIRCLE`/`PAINT`/`DRAW`) call. The whole risk of G2 is
**color-attribute faithfulness** — the 8-pixel color clash (arc D3, §11.3) — which
falls out here for the first time. No asm is written until the decisions in §9 are
approved.

> **Recurring arc lesson applies with force** ([memory: error-handling-arc],
> [memory: gate-during-implementation]): a green build hides a wrong pixel as easily
> as a dead trap branch. G2's Definition of Done (§8) is a **VG-8020 differential**
> that reads the pattern *and* color planes back byte-for-byte — the color plane is
> where the clash lives, and a PSET that plots the right bit but the wrong attribute
> byte passes every naïve "did the pixel light up" check while being wrong.

---

## 1. What lands in G2 vs. what defers

| Piece | G2 | Notes |
|---|---|---|
| `PSET (x,y)[,c]` statement | ✅ | the atomic RMW pixel plot (§3) |
| `PRESET (x,y)[,c]` statement | ✅ | = `PSET` whose default color is `BAKCLR` (§3.4) |
| `POINT(x,y)` function | ✅ | returns the pixel's color, off-screen → −1 (§5) |
| `STEP` relative coordinates `PSET STEP(dx,dy)` | ✅ | the shared coordinate parser (§4) resolves `STEP` against `GRPACX/GRPACY`; `STEP_TOKEN=$DC` already exists |
| The color-clash RMW in the tenant (`GFX_OP=1`) | ✅ | read pattern+color byte via ports, apply §3 rule, write both (§3) |
| Work-area cells written for the first time: `GXPOS/GYPOS` (target), `GRPACX/GRPACY` (last point), `CLOC/CMASK` (computed addr+mask) | ✅ | equates pinned in G1; G2 is the first writer (§6) |
| Tokens `PSET=$C2` / `PRESET=$C3` / `POINT=$ED` + kwtable entries + dispatch | ✅ | repack-only kwtable (§7); statement dispatch in `interp.asm`, function dispatch in `expr.asm` |
| Resident `basic/graphics.asm` (verb stubs: eval + marshal) | ✅ | repack-only; the arc's first resident graphics bytes (§2) |
| `LINE`/`CIRCLE`/`PAINT`/`DRAW`, box forms, aspect, fill | ❌ G3+ | G2 is the single-pixel primitive only |
| SCREEN-2 auto-init of the color table | ❌ | `SCREEN 2`/`CLS` already bring the mode up (as in G1); G2 plots onto the mode the user set |

**Explicitly deferred but flagged for a probe (not code):** the **unmeasured
color-clash edge** (§11.3) — a group whose fg nibble already equals its bg nibble,
with `c` equal to both — is unobservable black-box (which branch runs cannot be seen
in the resulting bytes). G2 handles it by the deterministic §3 rule and the G2 gate
records it as a known-unobservable case, not a pass/fail assertion.

---

## 2. Placement + invocation (inherits arc D1/D2/D5)

**The pixel RMW lives in the page-0 tenant** ([sub/graphics.asm](sub/graphics.asm)),
extended from G1's single self-test into a **selector-dispatched** entry (arc D5, the
`fatprim`/`dirverb` pattern — [sub/equates.inc:87](sub/equates.inc)). `SUBROM_IDX_
GRAPHICS = 8` is unchanged; `graphics_selftest` becomes `graphics_tenant`, which
reads `GFX_OP` and dispatches:

| `GFX_OP` | Op | Origin |
|---|---|---|
| 0 | floor self-test (unchanged) | G1 — stays, the floor gate still runs it |
| 1 | **plot pixel** (`PSET`/`PRESET`) — RMW one pixel from the param block | G2 |
| 2 | **read pixel** (`POINT`) — return one pixel's color | G2 |

**Why the RMW is in the tenant, not resident** (D2/D5, sign-off G2-b): the pixel op
is a VRAM **read-modify-write** — read the pattern byte, read the color byte, decide
the clash, write both — and a page-0 island is the only place we have direct VDP port
access with the BIOS paged out. Doing it resident would need a *second* VRAM-access
method (BIOS `RDVRM`/`WRTVRM`) that arc D2 explicitly rejected ("two VRAM-access
methods in one arc"). The tenant already owns `gfx_calc_addr` + `gfx_vram_rd/wr`
(G1); G2 adds the RMW logic beside them and reuses the DI-guarded latch verbatim.
PSET is short, so it never spins long enough for the EI question to bite — but it
costs nothing to live in the same island, and G3's `LINE` (which loops the same
primitive) needs exactly this home.

**What stays resident** (like `ex_sound`/`ex_play`): the token dispatch, the
coordinate/color **expression evaluation** (`eval`/`get_int16_checked` are resident,
[basic/interp.asm:1254](basic/interp.asm)), the `STEP`/`(`/`,`/`)` syntax walk, the
`SCREEN 2`-mode precheck, and the error raises (`raise_error` is resident). The
resident stub marshals a small param block and issues one `subrom_call`.

**BIOS-agnostic (inherited from G1 §2).** G2 still touches only the VRAM
address/data ports `$98`/`$99` — never a VDP mode register — so the BIOS register
shadows stay coherent; no BIOS coupling.

---

## 3. The pixel RMW + color-clash rule (arc D3 — PINNED §11.3) — the crux of G2

In GRAPHIC-2 the pattern plane is 1 bit/pixel (on = fg, off = bg) and the color
plane is one `hi=fg | lo=bg` **byte per 8×1-pixel group**. `gfx_calc_addr` (G1)
already gives the pattern byte address `P` and the MSB-first mask `M = $80 >> (x&7)`;
the color byte is `P + GFX_COLOR_OFST` (`$2000`).

**`PSET (x,y),c` — the exact pinned rule (§4/§11.3 of the arc spec):**

1. compute `P`, `M`, and the color byte address `Pc = P + $2000`.
2. read the current color byte `cur` (di-guarded, via `gfx_vram_rd`).
3. **if `c` equals `cur`'s low (bg) nibble** → the pixel should read as background:
   **clear** the pattern bit (`pat &= ~M`, write pattern byte). **The color byte is
   left untouched.**
4. **else** → **set** the pattern bit (`pat |= M`, write pattern byte) **and** write
   the color byte's **high nibble = `c`, preserving the low nibble**:
   `cur = (c << 4) | (cur & $0F)`. This is the **8-pixel color clash**, bug-for-bug
   faithful ([memory: bug-for-bug-compat-over-accuracy]): a second pixel plotted in
   the same 8-group with a different color rewrites the shared high nibble, so *every
   already-set pixel in that group changes color* — exactly the VG-8020 behavior
   (`PSET(0,0),15:PSET(1,0),6` → both become 6, §11.3).

`PSET` **never writes the bg (low) nibble** (§11.3 disambiguation run). The read of
`cur` and the two writes are each individually di-guarded byte accesses (G1's
`gfx_vram_rd`/`gfx_vram_wr`); the read-modify-write need not be one atomic unit for
correctness because no ISR writes this color byte — only the display reads it. (If
a later measurement shows otherwise we widen the guard; flagged, not assumed.)

**3.4 Default color / `PRESET`:**
- `PSET (x,y)` with `c` omitted → `c = FORCLR` ([basic/sysvars.inc:86](basic/sysvars.inc),
  `$F3E9`); §11.3 pinned (omitted → `$D4`, i.e. fg = 13 = FORCLR after `COLOR 13`).
- `PRESET (x,y),c` behaves **exactly** like `PSET (x,y),c` (§11.3: `PRESET(0,0),6`
  → `$80`/`$64` = `PSET,c`).
- `PRESET (x,y)` with `c` omitted → `c = BAKCLR` ([basic/sysvars.inc:87](basic/sysvars.inc),
  `$F3EA`). Since bg is usually the group's low nibble, the omitted-`c` `PRESET`
  normally hits branch 3 (clear the bit) — which is the "erase the pixel" intent.

So the ONE resident difference between the two verbs is the default-color source
(`FORCLR` vs `BAKCLR`); both marshal into the identical `GFX_OP=1` tenant op with
`c` already resolved.

---

## 4. Coordinate parsing (own-design, resident) — `(x,y)` + `STEP`

No coordinate parser exists yet (graphics is new); G2 introduces the shared one that
G3–G6 reuse. Resident, own-design, host-unit-testable shape:

```
parse_coord:            ; HL = cursor after the verb token; on return DE=x, ...=y in the
                        ; param block, HL past ')'. Own-design.
  skip_spaces
  peek STEP_TOKEN ($DC)?  -> set a "relative" flag, consume it
  expect '('              -> else Syntax error (ERR 2)
  eval ; get_int16_checked -> DE = x  (signed int16; |x|>32767 -> ERR 6 here)
  expect ','              -> else Syntax error
  eval ; get_int16_checked -> DE = y  (signed int16; ERR 6 as above)
  expect ')'              -> else Syntax error
  if relative: x += GRPACX ; y += GRPACY   (16-bit wrap, matches STEP semantics)
```

- **`STEP` is relative to the last-referenced point** `GRPACX/GRPACY` (§11.5:
  `PSET(10,20):PSET STEP(5,5)` → (15,25); negative STEP verified). `STEP_TOKEN=$DC`
  and its kwtable entry already exist ([basic/kwtable.inc:97](basic/kwtable.inc)) —
  G2 only adds *handling* in the coordinate walk, no new token.
- **`>int16 → ERR 6 (Overflow)`** is raised **inside** `get_int16_checked`
  ([basic/interp.asm:1256](basic/interp.asm), `fac_to_int_strict` → `check_fperr_
  only`), *before* any clip decision — matching §11.4 (`(32768,0)`/`(−32769,0)` →
  ERR 6). `get_byte_arg` is **not** usable here (it raises ERR 5 on negatives/>255,
  but a coordinate of −1 or 300 is a *legal, silently-ignored* value — §11.4).
- **Off-screen but within int16 → silent no-op (no plot), NOT clipped** (§11.4:
  `(256,0)`/`(0,192)`/`(−1,0)`/`(300,100)`/`(32767,0)` all light no pixel, and are
  **not** drawn at the edge). The range test `0 ≤ x ≤ 255 ∧ 0 ≤ y ≤ 191` decides
  plot-vs-no-op — **resident** (G2-c): skip the plot `subrom_call` on a no-op, which
  also guarantees the tenant only ever sees in-range pixels, so `gfx_calc_addr`'s
  "no carry into H" preconditions (y≤191, x≤255 — [sub/graphics.asm:176](sub/graphics.asm))
  hold by construction.
- **BUT the last-referenced point still moves on a no-op — MEASURED (G2-d,
  RESOLVED).** VG-8020 capture: `PSET(10,20):PSET(300,100)` leaves `GRPACX/GRPACY =
  (300,100)`, the **raw unclipped** coordinate. So the work-area update (§6) is
  **unconditional** — the resident stub writes `GXPOS/GYPOS/GRPACX/GRPACY = the
  resolved target ALWAYS`, drawn or not; only the *pixel plot* is gated by the range
  test. (A drawn plot writes both cell pairs to the target too: `PSET(10,20)` →
  `GRPAC=(10,20)`, `GXPOS=(10,20)`.)
- **`SCREEN 0/1 → ERR 5 (Illegal function call)`** (§11.4). Precheck `(SCRMOD)==2`
  resident (`SCRMOD`, [basic/screen.asm:125](basic/screen.asm)); else `raise_error`
  with ERR 5. (Arc is SCREEN-2-only, D4; SCREEN 3+ deferred.)

**Work-area writes (§6): unconditional — MEASURED (G2-d, RESOLVED above).** Both a
drawn and a no-op `PSET` write `GXPOS/GYPOS/GRPACX/GRPACY` to the resolved
(unclipped) target; only the plot is skipped on a no-op.

---

## 5. `POINT(x,y)` function (§11.8)

`POINT` is a **function** token (`$ED`, single-byte like `BASE`/`VARPTR`), so it
dispatches in the expression evaluator, not the statement loop: add
`cp POINT_TOKEN / jp z,ev_f_point` in the `IF ROM_BASE < $4000` function block of
[basic/expr.asm:546](basic/expr.asm) (beside `ERR`/`ERL`/`INSTR`). **Cursor
caution:** the expression evaluator walks with **IX** (`ev_f_var` uses `ix+0`,
[basic/expr.asm:577](basic/expr.asm)), not the statement `HL` — the POINT stub must
parse its `(x,y)` on the evaluator's cursor and return a numeric FAC. This is the
one structural difference from the PSET/PRESET stubs and a real bug-surface (guard
the cursor across the `subrom_call`, the `ex_play` `push/pop hl` lesson but for IX).

Pinned behavior (§11.8):
- returns the pixel's **color** (a `c=13` pixel → 13; its bg neighbor → the group's
  bg nibble, 4). Implemented via `GFX_OP=2`: compute `P`/`M`/`Pc`, read the pattern
  byte; if the bit is **set** return the color byte's **high** nibble, else the
  **low** nibble. Result marshalled back as a byte in the param block, widened to a
  float FAC by the resident stub.
- **off-screen `POINT` → −1** (§11.8). The resident stub range-tests first (same
  test as §4) and returns −1 without calling the tenant.
- `POINT` in `SCREEN 0` does **not** error (§11.8; only "no error" is pinned, the
  value is screen-content dependent). So POINT — unlike PSET — has **no SCREEN-mode
  precheck**. **G2-e:** the returned value in SCREEN 0/1 is content-dependent and not
  black-box-pinnable; the gate asserts "no error raised", not a value, for
  non-SCREEN-2 POINT.
- **`POINT STEP(dx,dy)` is accepted — MEASURED (G2-g, RESOLVED).** VG-8020 capture:
  `PSET(50,50),9 : C = POINT STEP(0,0)` runs (no error) and returns `9` — the color
  at the last point. So POINT reuses the shared §4 coordinate parser (STEP resolved
  against `GRPACX/GRPACY`) exactly like PSET. Whether POINT itself then *re-writes*
  `GRPAC` is unpinned and low-value; implement POINT **read-only** (does not move the
  last point) and note it.

---

## 6. Work-area contract (first writes; addresses pinned in G1 §11.5)

G2 is the first slice to **write** the reference-faithful cells (G1 only declared the
equates). Per **every** `PSET`/`PRESET` — drawn **or** no-op (G2-d measured):
- `GXPOS=$FCB3` / `GYPOS=$FCB5` ← the resolved target (x,y) (int16 LE), unclipped.
- `GRPACX=$FCB7` / `GRPACY=$FCB9` ← the last-referenced point = (x,y) (§11.5, and the
  G2-d no-op capture), so a following `LINE -(x2,y2)` (G3) draws from here. Written
  **unconditionally**, before the range test.
- `CLOC=$F92A` ← the computed pattern-byte VRAM address `P`; `CMASK=$F92C` ← `M` —
  these two only on a **drawn** pixel (the tenant computes them; a no-op never enters
  the tenant, and `CLOC/CMASK` of an off-screen pixel are meaningless).

These are the standard MSX work-area addresses ([basic/sysvars.inc:54](basic/sysvars.inc)),
the same faithfulness choice as the audio arc's VCB cells. Whether they are written
resident (the stub already has x/y in registers) or by the tenant (which computes
`P`/`M`) is an implementation detail; recommend **resident writes GXPOS/GYPOS/GRPAC**
(it holds the coords and the raw values) and the **tenant writes CLOC/CMASK** (it
computes them) — but the tenant is page-0 and these are page-2/3 RAM, always mapped,
so either works. Pin at implementation.

**Own-design scratch — the G2 param block** (marshalling): appended to the
`GFX_*` block ([basic/sysvars.inc:65](basic/sysvars.inc), the probe-only high-scratch
region `$C1xx`, or a dedicated repack-free cell — decide at implementation from the
live free-RAM map, the G1 discipline). Fields: `GFX_OP` (1, already exists),
`GFX_X` (2, target x), `GFX_Y` (2, target y), `GFX_C` (1, resolved color 0..15),
`GFX_RES` (1, POINT result). All dead outside a `GFX_OP` call.

---

## 7. Tokens + kwtable (arc §7, PINNED §11.1)

All single-byte, no `$FF` prefix; repack-only kwtable entries (lean build unaffected
— page-0 tenants exist only on the merged machine, so the lean cart never tokenizes
these). Add token equates to [basic/sysvars.inc](basic/sysvars.inc) and rows to
[basic/kwtable.inc](basic/kwtable.inc) (format `db <len>,"<KW>",1,<TOKEN>`):

| Keyword | Token | Kind | Dispatch site |
|---|---|---|---|
| `PSET` | `$C2` | statement | `interp.asm` `IF ROM_BASE<$4000` block ([basic/interp.asm:268](basic/interp.asm)) |
| `PRESET` | `$C3` | statement | same |
| `POINT` | `$ED` | function | `expr.asm` `IF ROM_BASE<$4000` fn block ([basic/expr.asm:546](basic/expr.asm)) |

Collision check (done): no existing equate uses `$C2`/`$C3`/`$ED`; neighbors are
`BEEP=$C0`, `PLAY=$C1`, `SOUND=$C4`, `VPOKE=$C6`, `BASE=$C9` ([basic/sysvars.inc](basic/sysvars.inc)),
and `STEP=$DC`/`VARPTR=$E7` on the function side. Capture the three tokens black-box
(stored-line crunch, the `scratchpad/spike_sound_token.py` shape) as the §8 build
step before asserting them — the `SOUND`-token-`$C2`-guess-was-wrong discipline
([basic/sysvars.inc:308](basic/sysvars.inc)); note `$C2` is precisely the value that
wrong guess used, so **re-verify** rather than trust the arc-spec table.

---

## 8. Gates (Definition of Done, G2)

- **New load-bearing gate `make graphics-acceptance`** → new
  `probes/basic/basic_probe_graphics.py`: a **VG-8020 differential**. For a battery
  of PSET/PRESET/POINT programs, draw on **both** zerobas (merged machine) and the
  Philips VG-8020 reference, read the **pattern plane and the color plane** back
  (`VPEEK` into RAM then capture, the §11 KEYBUF-injection method — [omsx_repl.py](probes/lib/omsx_repl.py)),
  and assert **byte-identical** pattern+color VRAM. Case battery (each a pinned
  §11.3/§11.4/§11.8 fact so the oracle is known before the run):
  - single `PSET(0,0),15` → pattern `$80`, color `$F4` (after `COLOR 15,4,7:SCREEN2`).
  - clash: `PSET(0,0),15:PSET(1,0),6` → `$C0`/`$64` (both become 6).
  - branch-3 clear: `PSET(0,0),15:PSET(1,0),4` (c == byte bg nibble) → `$80`/`$F4`
    (2nd bit NOT set, color untouched).
  - `PRESET` after `PSET` clears the bit, color untouched; `PRESET(0,0),6` == `PSET,c`.
  - omitted `c`: `PSET` → FORCLR, `PRESET` → BAKCLR.
  - clip/no-op: `PSET(256,0)`/`(0,192)`/`(−1,0)`/`(300,100)`/`(32767,0)` → VRAM
    unchanged (not edge-clipped); `PSET(32768,0)` → ERR 6; `PSET` in SCREEN 0 → ERR 5.
  - STEP: `PSET(10,20):PSET STEP(5,5)` lights (15,25); negative STEP.
  - `POINT`: color of a set pixel; bg neighbor; off-screen → −1; SCREEN 0 → no error.
  - the **unobservable edge** (§1) logged as known-unmeasured, not asserted.
- **Host unit tests** (`make unit-test`, [memory: host-unit-test-harness]) for the
  pure logic G2 adds: the color-clash nibble arithmetic (given `cur`,`c`,bit → new
  pattern+color bytes for both branches), and `parse_coord`'s STEP add + range test.
  Locks the math the differential proves, emulator-free.
- **Teeth / anti-green-build** ([memory: error-handling-arc]): the differential MUST
  read the **color** plane, not just the pattern plane — a PSET that sets the right
  bit but writes the wrong nibble passes a pattern-only check. Include at least one
  case (the clash case) where a pattern-only check would pass but a color-plane check
  fails, and confirm during bring-up that corrupting the nibble logic makes the gate
  fail (the G1 `GFX_UNGUARDED` teeth-check discipline, applied to the color rule).
- **Build wiring:** no new `SUB_PARTS` file (graphics.asm already listed), but the
  page-0 dispatch is now selector-based — force-rebuild the sub-ROM; the new resident
  `basic/graphics.asm` needs its `include` + repack-only guard; **rebuild+reinstall
  the IPS** before the machine probe ([memory: makefile-subparts-stale-tenant],
  [memory: ips-rebuild-after-basic-change]).
- **G1 floor gate still green** (`make graphics-floor-acceptance`): `GFX_OP=0` is
  unchanged; the selector dispatch must not regress it. **`make unit-test`** keeps
  the G1 `gfx_calc_addr` table.
- **Lean build byte-identical** — G2 is entirely repack-only; the lean 16 KB cart
  must assemble unchanged (no token, no stub, no kwtable row on the lean path).

---

## 9. Decisions — SIGN-OFF NEEDED

| # | Decision | Recommendation |
|---|---|---|
| **G2-a** | Extend the G1 tenant to a `GFX_OP` selector (0=self-test, 1=plot, 2=point); `graphics_selftest`→`graphics_tenant` dispatch | Yes — arc D5 (one selector-dispatched page-0 tenant for G2–G6); reuses G1's `gfx_calc_addr`/`gfx_vram_rd/wr` verbatim |
| **G2-b** | The color-clash **RMW runs in the tenant** (page-0, direct ports); the resident stub does eval + `SCREEN`/clip policy + marshalling only | Yes — arc D2 forbids a second VRAM-access method; keeps `LINE` (G3) reusing the same in-page primitive |
| **G2-c** | The **range/no-op** test (0..255 × 0..191) is **resident** — skip the `subrom_call` on an off-screen no-op | Yes — keeps ERR/clip policy in one resident place and guarantees `gfx_calc_addr`'s in-range preconditions |
| **G2-d** | Does an **off-screen (no-op) `PSET` still move `GRPACX/GRPACY`?** | **RESOLVED (measured):** YES — a no-op moves the last point to the raw unclipped coord; work-area write is unconditional, only the plot is gated (§4/§6) |
| **G2-e** | `POINT` in SCREEN 0/1: **no error**, value content-dependent (§11.8) → gate asserts "no error", not a value; no SCREEN-mode precheck for POINT | Yes — matches the only pinned fact |
| **G2-f** | Re-capture `PSET`/`PRESET`/`POINT` **tokens** black-box (`$C2` is the known-wrong `SOUND` guess value) | **RESOLVED (measured):** `PSET=$C2 PRESET=$C3 POINT=$ED` confirmed on VG-8020 |
| **G2-g** | `POINT STEP(dx,dy)` acceptance + anchor | **RESOLVED (measured):** accepted; STEP resolved against `GRPAC`; returns the pixel color; POINT implemented read-only (§5) |

Implementation order (capture pass ✅ done): token equates + kwtable + dispatch →
`parse_coord` + color-clash host unit tests (fast, emulator-free) → resident
`basic/graphics.asm` stubs (PSET/PRESET/POINT) → tenant `GFX_OP=1`/`=2` ops beside
the G1 floor → the `graphics-acceptance` differential (with the color-plane teeth
check) → verify G1 floor gate + unit-test still green → commit.

## Appendix — sources

Inherited from the arc spec §0/§Appendix and G1: TMS9918A datasheet (GRAPHIC-2
pattern/color-plane layout, VDP ports), MSX2 TH (work-area addresses `FORCLR`/
`BAKCLR`/`GRPAC*`/`CLOC`/`CMASK`, `SCRMOD`), public MSX-BASIC language reference
(`PSET`/`PRESET`/`POINT` semantics, `STEP`), the arc-spec §11 VG-8020 black-box pins
(color-clash rule §11.3, clip/error §11.4, last-point/STEP §11.5, POINT §11.8), plus
the G2 capture pass (tokens, GRPAC-on-no-op, POINT STEP). Own-design: the coordinate
parser, the color-clash RMW, the selector dispatch. No reference-ROM disassembly
([memory: no-reference-rom-disasm]).
