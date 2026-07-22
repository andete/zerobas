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

## 8. Space — G6 hits the same wall as G4/G5

Measured now: `__MEAS_PAGE1_END = $7FEA` ⇒ **22 B** of page-1 tail, and 19 B of
page-0 low. Estimated resident cost of G6: statement plumbing + string eval +
the §7 pre-pass ≈ **200–260 B**. So, as with G4 and G5, the slice is **blocked on
an eviction** before its resident half can land.

Runway already scouted in [spec-eviction-g5-space.md](spec-eviction-g5-space.md)
(the runner-up to the landed cassette carve): the `do_tape_prog` `ctp_*` core,
≈ **+190 B**. That may not fully cover the estimate — the impl must **measure the
real `ex_draw` before choosing**, per the standing "measure byte budgets
empirically before declaring a wall" lesson, and a second candidate may be needed.
The tenant half has ample sub-ROM room and is not at issue.

## 9. Decisions — SIGN-OFF NEEDED

- **D-G6-1 substitution mechanism.** (a) resident pre-pass into a scratch buffer
  with a binary literal escape + inline `X` splice — **recommended** (§7);
  (b) tenant-side scan with a co-routine callback to the resident for each
  substitution (cheaper resident, more moving parts, re-entrant tenant);
  (c) tenant calls resident page-1 lookup directly (**not recommended** — the
  float-coercion path is unreachable from a page-0 tenant).
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
