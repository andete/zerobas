# Spec — graphics Slice G6: `DRAW` (the MML-style macro language)

Slice G6 of the graphics arc ([spec-basic-graphics.md](spec-basic-graphics.md)),
the last drawing statement before sprites (G7). `DRAW` interprets a *string* of
one-letter movement/state commands — structurally the twin of the `PLAY` MML
parser ([sub/playparse.asm](../sub/playparse.asm)) — and renders each movement
through the **already-landed G3 line rasteriser**.

Everything in §3–§6 is **measured** on the reference machine profile; the raw
findings and the probes behind them are the characterization notebook
[scratchpad/g6_draw_notes.md](../scratchpad/g6_draw_notes.md). Nothing here is
derived from a disassembly.

---

## 1. What lands in G6 vs. what defers

**In:** the whole MSX1 `DRAW` surface — the eight direction letters `U D L R E F
G H`, absolute and relative `M`, the `B` (blank) and `N` (no-update) prefixes,
`C` colour, `S` scale, `A` angle, `X` substring execution, `=var;` substitution,
and the measured error surface.

**Out:** nothing MSX1-visible. (MSX2's `DRAW` additions — none that apply on
SCREEN 2 here — stay out of charter with the rest of the MSX2 surface.)

## 2. Placement + interrupt discipline (inherited)

Unchanged from G3–G5: the interpreter is a **page-0 sub-ROM tenant** under the
EI-trampoline (`SUBROM_IDX_GRAPHICS`, selector `GFX_OP = 6`), drawing through the
existing `GFX_OP = 3` segment primitive — **EI between pixels, DI per-pixel RMW**,
reads through `gfx_rd_raw` with its load-bearing fetch-window settle. Music keeps
playing through a long `DRAW`, as it does through `LINE`/`CIRCLE`/`PAINT`.

**Rasteriser identity is measured, not assumed:** `PSET(20,20):DRAW"M53,37"` and
`LINE(20,20)-(53,37),15` produce the same bitmap row for row (notes §9). G6 adds
**no** new rasteriser and needs **no** new host-fit oracle — a first for this arc.

## 3. Grammar + semantics (measured — notes §1, §3, §4)

The argument is an ordinary **string expression**; a numeric argument is `ERR 13`.

**Movement.** `U D L R` = up/down/left/right, `E F G H` = the four diagonals
moving `n` in *each* axis. A bare letter means `n = 1`. `M x,y` moves to an
**absolute** point when the first operand carries no sign; if the first operand is
`+`/`-` prefixed the move is **relative** and the second operand's prefix is then
optional (`M+20,10` is relative in both axes).

**Prefixes.** `B` = move without drawing; `N` = draw, then restore the position.
`BN`/`NB` combine (net no position change). Bare `B` or `B N` with no following
command is accepted and does nothing.

**Scale `S n`** is in **quarter units** — `S4` is 1:1 — and `S0` means 4. The
scaled distance follows one exactly-measured rule (notes §3, falsified on seven
fresh (n,S) pairs):

> **distance = signed16( (n × S) mod 65536 ) ÷ 4**, truncating **toward zero**.

That single rule produces every large-count wrap observed (`U32767` → *down* 1,
`U32768` → no move, `U33000` → up 232, `U40000` → up 7232, `U65535` → down 1) and
the negative rounding (`S3U-10` → 7, not 8). A negative count therefore moves in
the opposite direction, and `+` may prefix a count.

**Angle `A n`** (`0..3` = 0/90/180/270°) rotates **relative** motion only — the
eight letters and relative `M`, including under `B`/`N` — and never absolute `M`.

**Colour `C n`** — see §6, it is the *shared* graphics attribute.

**`X <strvar>;`** executes that string variable's contents and continues after the
`;`; state set inside it persists on return; nesting works; an empty string is a
no-op. **`=<var>;`** substitutes a variable's value as the command's argument;
the value is coerced like any int argument (`10.6` → 10, negatives and values
>255 fine).

**Separators.** Spaces and TAB are skipped anywhere. `;` **terminates** a command
— a trailing `;` is fine, but a leading `;`, a doubled `;;`, or a `,` between
commands is `ERR 5`. Command letters may be lowercase. An empty string draws
nothing.

## 4. ★ The state is PERSISTENT (measured — notes §2)

`S` and `A` survive **`RUN`, `NEW`, `CLEAR`, `CLS`, `COLOR`, and `SCREEN`** — a
`DRAW"S8A1"` in one program is still in force in the *next* program run. Only a
power-on resets them, to `S = 4`, `A = 0`.

⇒ their cells must live in the graphics block's own RAM (§6), be initialised
**once at cold boot**, and be touched by nothing else. Any "reset it at statement
entry / at `SCREEN 2`" convenience would be measurably wrong.

## 5. Errors (all measured — notes §8)

| condition | error |
|---|---|
| unknown letter; bare `S`/`A`/`C`/`M`/`X` (argument required) | `ERR 5` |
| `A > 3`, `C > 15` or `C < 0`, `S > 255`, count > 65535 | `ERR 5` |
| `M` missing its 2nd operand; `=var` or `X var` without `;` | `ERR 5` |
| leading `;`, doubled `;;`, `,` between commands, junk character | `ERR 5` |
| `SCREEN 0` / `SCREEN 1` | `ERR 5` |
| numeric argument (`DRAW 5`) | `ERR 13` |

Accepted (no error): off-screen motion of any size, counts ≤65535, absolute `M`
operands up to 65535, empty string, bare `B`/`N`, `S0`, `S255`, negative counts.
Off-screen motion **clips by masking** and leaves the *unclipped* coordinate in
the position cells — identical to G3, and free by reusing its primitive.

## 6. Colour: the shared graphics attribute `ATRBYT` (measured — notes §6)

Three rounds of probing settled this, and two of them were confounded before the
third removed the intervening statement (notebook §6 records the wrong reading
and its correction — it is exactly the "green but never actually discriminating"
trap this arc keeps meeting).

The rule that reproduces all seven observations: there is **one shared graphics
attribute cell** (`ATRBYT`, `$F3F2` — published MSX work area). Every graphics
statement given an explicit colour stamps it; every graphics statement *without*
one stamps FORCLR; **`DRAW` reads it and writes it only on `C n`.** Hence
`LINE …,4 : DRAW"BM…R8"` draws in 4, `DRAW"C6…" : SCREEN2 : DRAW"BM…R8"` still
draws in 6, but `DRAW"C6…"` followed by a colourless `LINE` draws in 15.

**Gap in our engine:** `basic/graphics.asm` resolves each statement's default
straight from `FORCLR`/`BAKCLR` and keeps no `ATRBYT`. Closing it is a small
cross-cutting change (one stamp at each statement's effective-colour site);
see D-G6-3.

## 7. Marshalling ABI + the substitution problem

The tenant draws through `GFX_OP = 3` and keeps its cursor in the pinned work
area exactly as G3 does, so the only new marshalling is the **command string**
plus the new persistent state cells:

| cell | meaning |
|---|---|
| `GFX_DRAW_PTR` / `GFX_DRAW_LEN` | the command buffer (body address + length) |
| `GFX_SCALE` | persistent scale, cold-boot init 4 |
| `GFX_ANGLE` | persistent angle, cold-boot init 0 |
| `GFX_RES` | existing result cell — tenant's `ERR` code, 0 = ok |

**The substitution problem.** `=var;` and `X var;` need *variable lookup*, which
is resident page-1 code, while the tenant runs with page 0 switched to the
sub-ROM. Page 1 stays mapped (CALSLT switches only page 0), so a direct call is
*mechanically* possible — but the int coercion of a float variable bottoms out in
the float pack, which lives in the page-0 low region and is **not** reachable from
a page-0 tenant. So a direct callback is a hazard, not a shortcut.

**Recommended (D-G6-1a): a resident pre-pass.** Before the `subrom_call`, the
resident walks the evaluated string into a scratch buffer, copying bytes verbatim
except:

- `=name;` → resolved through the existing variable lookup + int coercion and
  emitted as a **3-byte binary literal escape** (`$01`, int16 LE). No int→decimal
  formatting is needed, and the tenant reads it as just another argument form.
- `X name;` → the string variable's body is **spliced inline** and re-scanned, so
  nesting falls out for free.

The tenant then parses a self-contained buffer and never touches a variable. This
keeps the whole page-0/page-1/float hazard out of the tenant, at the cost of
resident bytes (§8) and a buffer. Buffer home: the LINEBUF scratch region already
used by G3/G5 (dead during any graphics statement, below the `PLAY` ISR), 256 B.
A splice that overruns the buffer is an own-design cap — D-G6-4.

## 8. Space — G6 hits the same wall as G4/G5 (now MEASURED)

Page-1 tail free: `__MEAS_PAGE1_END = $7FEA` ⇒ **22 B** (plus 19 B of page-0 low).

**Measured 2026-07-22, both halves written:** with `ex_draw` + the §7 pre-pass in,
the page-1 image ends at **`$80EF` — a 239 B overrun** (so `ex_draw` ≈ **261 B**,
at the top of this spec's own 200–260 estimate). The resident half therefore ships
gated behind `G6_RESIDENT equ 0` (sysvars.inc) until the space exists; the tenant
half (`GFX_OP = 6`) is unconditional, since the sub-ROM has room. Flipping that one
equate to 1 is the whole switch-on.

⚠️ **The scouted runway is NOT usable.** `do_tape_prog`/`ctp_*` measures 224 B, but
scouting it properly (rather than trusting the estimate) shows it is a **straddle**:
six of its callees — `load_error`, `cas_open_match`, `cas_put`, `verify_error`,
`cas_ascii_load`, `new_prog`, `relink` — are **page-1 resident**, which a page-1
sub tenant cannot call; and it calls BIOS `TAPION`/`TAPIN`/`TAPIOF`, which a
**page-0** tenant cannot reach (page 0 is the sub-ROM during the call). So it fits
neither tenancy. This is the same wall that stopped [the disk/file eviction at
Phase 2](spec-eviction-g5-space.md).

**Useful structural finding for future carves:** the two tenancies have
*complementary* reach. A **page-1** tenant sees BIOS + the page-0 low region (float
pack) but not page-1 residents; a **page-0** tenant sees page-1 residents (CALSLT
switches only page 0) but neither the BIOS nor the float pack. A carve is clean if
its whole callee closure lands on one side. Anything reached through `eval` is
effectively barred from page-0 tenancy, because `eval` bottoms out in the float
pack.

**RESOLVED (2026-07-22).** Option (a) was taken and the deficit is closed with
room to spare — page-1 now has **45 B free with `DRAW` resident**, more headroom
than the arc had *before* G6 started:

| step | bytes |
|---|---|
| D-G6-1b co-routine (replaces the resident pre-pass) | −124 |
| the two G5 DRY levers, re-applied and now re-verified | −46 |
| `DEFtype` → page-0 sub tenant ([spec-eviction-g6-space.md](spec-eviction-g6-space.md)) | −115 |
| **net vs the 239 B overrun** | **45 B free** |

The carve was found by `scratchpad/g6_carve_scout.py`, which applies the tenancy
rule above to every resident routine transitively — the eviction spec records
both the rule and why the previously-banked runway failed it.

## 9. Decisions

- **D-G6-1 substitution mechanism — SETTLED on (b), the co-routine.** (a) the
  resident pre-pass was implemented first, measured, and then replaced by (b)
  when the space verdict came in: the tenant scans in place and keeps an
  X-substring frame stack, and calls back to the resident once per substitution.
  −124 B resident, and it deletes the 256 B pre-pass buffer. (c) — calling
  resident page-1 lookup directly — stays rejected: the float coercion behind
  `=var;` is unreachable from a page-0 tenant.
- **D-G6-2 persistent state.** `S`/`A` in the graphics RAM block, **cold-boot init
  only** (§4). Confirm we are willing to carry statement state that no `RUN`,
  `CLEAR` or `NEW` clears — it is what the reference measurably does.
- **D-G6-3 colour fidelity.** Introduce `ATRBYT` and stamp it from
  `PSET`/`PRESET`/`LINE`/`CIRCLE`/`PAINT` so a colourless `DRAW` inherits the
  previous statement's colour (**recommended**, ~15–25 B across sites) — *or*
  take a documented deviation (`DRAW` defaults to `FORCLR`) to save those bytes
  in a slice that is already space-blocked.
- **D-G6-4 `X` recursion / splice cap.** Own-design: a splice that overruns the
  256 B buffer raises `ERR 5`. The reference's own limit is unmeasured (a
  self-referential `A$="XA$;"` was not probed); measure during impl if cheap,
  otherwise ship as a documented deviation like G4-rneg / G5-align.
- **D-G6-5 scale arithmetic.** Implement §3's model literally (16-bit product,
  arithmetic ÷4 truncating toward zero). Cheap on Z80 and exactly measured.
- **D-G6-6 how to close the measured 239 B — NEEDS SIGN-OFF (new, §8).**
  (a) **Shrink first, then a smaller carve — recommended.** Switch D-G6-1 to its
  already-listed alternative (b): the tenant scans and keeps an X-substring stack,
  and calls back to the resident once per substitution to resolve it. That deletes
  the resident splice/recursion machinery (≈115 B), and applying the two DRY levers
  G5 wrote but had to revert (`gfx_eval_int16` / `gfx_store_colour_checked` at the
  PSET/LINE/CIRCLE sites, ≈28 B) takes the deficit to ≈100 B — a much smaller
  eviction to find, with headroom left for G7. It also **removes** the D-G6-4
  splice cap and the 256 B buffer, so it is *more* faithful, not less.
  (b) **Keep the pre-pass, find a ~260 B clean carve.** Needs fresh scouting
  against the §8 tenancy rule; no candidate of that size is currently known to be
  non-straddle.

## 10. Gates (Definition of Done)

1. `make graphics-acceptance` gains **Phase K** — a VG-8020 differential over
   `DRAW` reading **pattern *and* colour** planes (movement letters, `M` both
   forms, `B`/`N`, scale incl. a wrap case, angle, `C` inheritance, `X`, `=var;`);
   **Phase L** — the §5 error table; **Phase M** — the §4 persistence-across-`RUN`
   behaviour, which is invisible to any single-program test.
2. Host unit tests (`make unit-test`) for the pure leaves: the §3 scale
   arithmetic (including the wrap and negative-rounding cases as fixtures) and
   the angle rotation.
3. `make diskbasic-acceptance` + `make bdos-acceptance` green after the eviction,
   and the **lean cart byte-identical** to its frozen baseline.
4. `make audit-citations` clean; a paper-trail pass over the landed asm.

The recurring lesson applies without exception here: the differential on real
hardware behaviour is what has caught every serious bug in G2–G5 (3 in G5 alone,
all invisible to host tests). A green build that was never run against the
reference is not evidence.

## 11. Impl order

**LANDED 2026-07-22.** All of §10 is green: `make graphics-acceptance` PASS
(Phases K/L/M — the pixel differential incl. the cross-statement colour rule, the
25-case error surface, and the across-`RUN` persistence), `make unit-test` 51/51
with the `gdrw_scale`/`gdrw_rotate` leaves, `make diskbasic-acceptance` 34/34,
`make bdos-acceptance` 12/12, lean cart byte-identical, `make audit-citations`
clean.

One bug survived to first run and was caught by running it: **nested `X` hung**
— the banked-substitution counter was reset only at end-of-command, so an inner
frame's first command consumed the *outer* command's value and re-executed the
outer string forever. The reset belongs at the start-of-command path, which a
resume deliberately enters below (that is what lets `M`'s two substitutions
accumulate across two round trips). Host tests could not have seen it; it is the
arc's recurring lesson again.

1. eviction (measure first, then carve) → re-gate → 2. tenant `GFX_OP = 6` parser
+ movement over the G3 primitive (host-unit-tested leaves) → 3. resident
`ex_draw` + pre-pass + `DRAW` kwtable row/interp arm (repack-only, the `CIRCLE`
pattern) → 4. `ATRBYT` stamping (D-G6-3) → 5. gates → 6. spec/PROVENANCE/TODO
writes.

## Appendix — sources

- `DRAW` *language* semantics: public MSX-BASIC language reference.
- `ATRBYT $F3F2`, `GRPACX/GRPACY`, `GXPOS/GYPOS`, the `$0038`/CALSLT/slot
  contracts: MSX2 Technical Handbook / MSX Assembly Page (called and cited, never
  disassembled).
- Every numeric behaviour in §3–§6: this project's own black-box oracle
  observations, [scratchpad/g6_draw_notes.md](../scratchpad/g6_draw_notes.md),
  probes `scratchpad/g6_draw_char{1,2,3,4,5,6,7}.py`.
- No MSX-BASIC / BIOS / reference-ROM disassembly was used
  ([PROVENANCE.md](../PROVENANCE.md)).
