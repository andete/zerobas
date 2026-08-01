# D-NAMDOT — `.` is an identifier character to the TOKENISER

*Spec. Measurement: [`docs/namedot-msx1-characterization.md`](namedot-msx1-characterization.md).
Parent slice: [`docs/spec-basic-nameblank.md`](spec-basic-nameblank.md) §3, which
filed this and deliberately did not fix it.*

**Status: LANDED 2026-08-01.** `lnblank-acceptance` **145/145** at `--repeat 2`
across `vg8020`/`cf3300`/`zb`, 0 `UNSTABLE`, 1 allowlisted (`dot-goto`, a
different defect — §6 of the characterization). **NET −10 B, all sub-ROM page 0**
(4014 → 4024 B free); both main ROMs **byte-identical** to the parent commit.
Five knives run and reverted (§7).

---

## 1. The rules

> **R-D1** — a `.` arriving with the in-a-name state **LIVE** continues the
> identifier: copied verbatim, and the state **survives** it exactly as a digit
> does. `B.5` is the identifier `B.5`; `B .5` is the same identifier across a
> blank (D-NAMBLANK R-N1).
>
> **R-D2** — a `.` arriving with the in-a-name state **DEAD** begins a numeric
> constant, **and the digit is OPTIONAL**. A bare `.` is the single-precision
> literal `0` (`$1D,00,00,00,00`).
>
> **R-D3** — the RUN-TIME variable-name scan is **UNCHANGED**. The crunch stores
> `B.5` as name bytes that the executor then **refuses** with `Syntax error`.

R-D3 is a claim about code this slice does **not** write, and it is measured, not
argued: [`namedot-msx1-characterization.md`](namedot-msx1-characterization.md) §4.

---

## 2. ⚠️ THE FILED PRESCRIPTION IS REFUTED — and that is the headline

`TODO.md` and the parent characterization both state that a crunch storing `B.5`
as name bytes **requires** [`basic/vars.asm`](../basic/vars.asm) `is_ident_cont`
to accept `.` too, *"or the executor looks up a different variable than the
tokeniser stored"*, and direct the reader to check `DEFINT`/`DEFSNG`/`DEFSTR`,
`VARPTR`, `FOR` variables, `DIM`/array names and `INPUT`/`READ` targets.

**The reference does the forbidden thing.** `B.5=7` and `A=B.5` both raise
`Syntax error` (ERR=2) on the VG-8020 and the CF-3300, against a `B5=7` control
that reads ERR=0. The tokeniser's identifier charset and the executor's are
**different charsets on MSX1**, and reproducing that is this project's charter
([[bug-for-bug-compat-over-accuracy]]).

Consequences, and they are the whole shape of the slice:

* **`basic/vars.asm` is not touched.** Neither is any of the six surfaces the
  brief listed — they all reach that one unchanged scanner.
* **The fix is confined to [`basic/tokenise.inc`](../basic/tokenise.inc)**, which
  [`sub/sub.asm:209`](../sub/sub.asm:209) includes and nothing else — so it is
  **sub-ROM only**, and the main ROM's 23 B low / 8 B page-1 walls are not in
  play at all. No carve is needed. §6 asserts the split by hash.

---

## 3. The change

[`basic/tokenise.inc:80`](../basic/tokenise.inc:80), the `tk_nondigit` arm. The
one-character lookahead **goes away entirely** — R-D2 says there is nothing to
look ahead *for*, and R-D1 says the question was about the name state all along.

```
tk_nondigit:
                cp      '.'
                jr      nz,tk_nondot
                ld      a,b                 ; R-D1: was the previous char part of
                or      a                   ; a name? B is the in-a-name state,
                jr      nz,tk_namedig       ; loaded at the top of tk_loop
                jp      tk_float            ; R-D2: no digit required
```

`tk_namedig` is **reused, not cloned**: it already stores `TKNAME=1`, copies
`(HL)` verbatim and returns to `tk_loop` — which is exactly what a `.` inside a
name must do. Net **−10 bytes**, all sub-ROM (17 bytes of lookahead deleted,
7 written). Like D-EXPBAD, the correct rule is *smaller* than the wrong one.

Three properties that have to hold, and each is a place this project has been
bitten before:

1. **`B` is live here.** The `.` test sits **before** `match_kw`
   ([`tokenise.inc:103`](../basic/tokenise.inc:103)), which clobbers `B`. This is
   the identical liveness argument D-NAMBLANK's K4 established for `tk_blank`,
   and it is why the fix can read the state at all.
2. **No new label is inserted before an existing one.** The edit rewrites the
   interior of `tk_nondigit` and jumps **backwards** to `tk_namedig`. Nothing
   falls through into either (`tokenise.inc:70` and `:79` are unconditional
   `jp`s). 🔴 This is the check D-NAMBLANK's K2 had to find the hard way, on a
   build that read 29/31 green *by luck* ([[knife-found-defect-in-own-fix]]).
3. **`tkf_fetch` keeps four callers** inside [`sub/tkfloat.asm`](../sub/tkfloat.asm),
   so deleting this one does not orphan it — `make basic-reloc`'s hard dead-code
   gate (0 dead, both builds) would fail the build otherwise.

R-D2 rests on `tk_float` already handling a digitless `.`: `tkf_scan_digits`
finds 0 digits, `tkf_fetch` finds the `.`, `tkf_dot` sets `has_dot` and scans 0
fractional digits, and `tkf_bydcount` emits a single. **That is a prediction, not
a reading** — `dot-start`, `dot-lead`, `dot-eol` and `dot-exp` are what confirm
it, and if the emitted bytes are not `$1D,00,00,00,00` this section is what was
wrong. `dot-exp` additionally requires `tkf_try_exponent` to consume `E5` off a
zero mantissa, which the reference does (characterization §3.1).

**Scope decision, signed off 2026-08-01:** R-D2 is folded into this slice, and
`dot-eol`/`dot-exp` were oracle-locked on both references **before** any code was
edited, so the rule ships no wider than its denominator (§4).

---

## 4. ⚠️ Scope — ONE decision to sign off

R-D2 was found by rows written to be **controls** for R-D1 (§3 of the
characterization). It is a genuinely different rule, and this repo's habit is to
**split** — D-EXPBAD left D-DECBLANK for exactly this reason.

**Recommendation: fold R-D2 in, and here is the argument against my own
recommendation.** The split precedent held because `dec-expbad`'s rule lived in a
different *scanner*; here both rules live in the **same five-line dispatch arm**,
and the R-D1 fix must rewrite the lookahead that R-D2 deletes. Splitting would
mean writing that arm twice and would leave the second slice with no code site of
its own. Against that: R-D2 makes `20 A=.` and `20 A=.E5` reachable for the first
time and **neither is measured** (characterization §7), so folding it in ships a
rule whose denominator is one row wider than what was asked.

`dot-goto` (§6 of the characterization) is **not** folded in either way — it is
`branch_lineno`, different code, and it gets its own TODO entry with exact bytes.

---

## 5. Rows

**Must move (12 red today):** `nam-dot`, `nam-dot0`, `dot-two`, `dot-dig`,
`dot-blk2`, `dot-lval`, `dot-print`, `dot-op` (R-D1) · `dot-start`, `dot-lead`,
`dot-eol`, `dot-exp` (R-D2) · plus the `dotd-lead` say row.

**Must NOT move (green on all three sides today):** `dot-sfx`, `dot-paren`,
`dot-kw`, `dot-many`, `dot-ctl`, `dot-let`, `dot-str`, `dot-rem`, `dot-data` ·
`dotd-var`, `dotd-ctl`, `dotd-rd`, `dotd-b5` · and D-DECBLANK's `dec-dotlead0`,
`dec-dotlead`, `dec-dotpre`, `dec-dotpost`, `dec-dotx`, `dec-dotx0`, `lit-float`.

`nam-dot`/`nam-dot0` are `KNOWN_DIVERGE` entries pinned to zerobas' exact current
bytes; the fix turns the gate **RED** and both entries are **retired**. That is
the mechanism working, not a failure.

---

## 6. Gates

* `make lnblank-acceptance` at `--repeat 2`, three sides — **125 → 145 gating
  rows, all agreeing**, 0 `UNSTABLE`, 1 allowlisted (`dot-goto`, §6 of the
  characterization). The 20 new `dot` rows join the gate; the 5 `dotd` rows are
  `--say` and stay outside it. `nam-dot`/`nam-dot0` are **retired** from
  `KNOWN_DIVERGE` — the gate went red until they were deleted, which is the
  mechanism working.
* **The split assert.** A sub-only change must leave the main ROM byte-identical:
  `build/basic-reloc.rom` = `1d270536…`, `build/zerobas-main-eu.rom` =
  `90403dbb…` (HEAD, verified 2026-08-01). Any drift means the edit escaped
  `tokenise.inc`.
* Full corpus after the change: `unit-test` 55/55 · `badfnum` 93 · `lof` 45 ·
  `chancost-characterize` 53 · `diskbasic` 34/34 · `bdos` 12/12 · `fat-error`
  8/8 · `error-trap` · `abort` 49/49 · `stop-trap` · `linemax` 60/60 ·
  `arrdim` 73/73 · `clearpool` 52/52 · `array` 149/151 (`ifc.instr.zero`,
  `ifc.instr.neg`).
  ⚠️ `linemax` measures crunch **expansion** byte-for-byte and this slice turns
  a 5-byte float token into 2 ASCII bytes for a dotted name. Its payloads are
  `A=0#0#…` and `REM`+filler, neither of which puts a `.` behind a name — so no
  row should move, and a row that does is a finding, not a rubber stamp.

---

## 7. Knives — five, RUN, each with a RED set **and** surviving GREEN controls

Each keeps the code **reachable** (a changed constant or one swapped
instruction), because an orphaned block fails the dead-code gate and measures
nothing. All five built clean (0 dead, both builds) and were **reverted**.
Scoped `SIDES=vg8020,zb ONLY=dot,nam,lit,dec-dotlead` — 61 gating rows.

| | cut | RED (measured) | GREEN control half |
|---|---|---|---|
| **K1** | `ld a,b` → `xor a` (R-D1 off, R-D2 intact) | 11: the 8 R-D1 rows **+ `dot-ctl`, `dot-let`, `dot-many`** | every R-D2 row (`dot-start`, `dot-lead`, `dot-eol`, `dot-exp`) and every bounding row **stayed green** — the two rules are separable |
| **K2** | `jp tk_float` → `jp tk_copy` (R-D2 off) | 9: `dot-start`, `dot-lead`, `dot-eol`, `dot-exp`, `dec-dotlead0`, `dec-dotlead`, `dot-sfx`, `dot-paren`, `dot-kw` | all 8 R-D1 rows green |
| **K3** | `ld a,b` → `ld a,1` (the WRONG rule: "`.` is *always* an identifier char") | 9: same row set as K2, **different bytes** — K2 copies the dot (`.<16>`), K3 makes it a name char (`.5`) | all 8 R-D1 rows green — 🔴 **the knife that says the spec picked R-D1 over "always ident". No filed row could tell those apart** |
| **K4** | add `.` to `is_ident_cont` in `basic/vars.asm` — **the brief's own prescription** | `dotd-var`, `dotd-rd`: ERR **2 → 0** | `dotd-ctl` held at 0 — 🔴 **a knife aimed at my own justification**, and it says the brief's fix would have shipped a live divergence ([[apparatus-is-part-of-the-measurement]]) |
| **K5** | `tk_namedig`'s `ld a,1` → `ld a,0` (the dot is copied but does not SET the state) | 17: the whole digit-continuation family (`nam-ctl`, `nam-digblk`, `nam-run`, `nam-more`, `nam-lval`, `nam-print`, `nam-amp0`, `nam-ampz`, `nam-ampl`) + `nam-dot`, `nam-dot0`, `dot-two`, `dot-dig`, `dot-blk2`, `dot-lval`, `dot-print`, `dot-op` | `dot-ctl`, `dot-let`, `dot-many` green — the dot must **set** the state, and `dot-two` (`B..5`) is the row that says so |

### 7.1 🔴 K1 and K5 both refuted a predicted-GREEN control — corrected in place

K1 was predicted to leave `dot-ctl`, `dot-let` and `dot-many` green; it reddened
all three. The prediction was wrong, and the reason is worth keeping:

> **A cell that is a two-sided control between the two CANDIDATE rules can still
> be moved by a knife, because a knife is a THIRD rule.** `20 A=B.` reads `B.`
> under rule F (a digitless dot is copied verbatim) *and* under R-D1 (it is a
> name character) — for opposite reasons. K1 is neither: it is R-D2 alone, which
> makes that dot a **literal**. So `dot-ctl`/`dot-let`/`dot-many` are genuine
> R-D1 evidence, not inert padding, and the `^` mark on them means
> "two-sided between F and N", not "invariant".

K5 was predicted to redden `dot-many`; it did not — `B.C.D`'s `C` re-establishes
the name state after each dot, so the row survives a state that does not persist.
Both corrections are made here rather than dropped
([[knife-that-refutes-its-own-control]]).

### 7.2 ⚠️ A `REFUSED` that was a dropped keystroke, not a behaviour

Under K1, `dot-eol` (`20 A=.`) came back `REFUSED (empty program)` in the batched
run — a row K1 does not touch at all. Re-run **alone at `--repeat 2`** on the
same installed K1 build it read `A<EF><1D><00><00><00><00>`, agreeing with the
reference. openMSX is deterministic, so a harness race reproduces exactly; alone
✅ + batch ❌ is a **delivery** failure ([[deterministic-mangle-is-still-a-mangle]]).
Had it been taken at face value it would have been written up as R-D2 rejecting
its own literal.

⚠️ A knife that reddens a row whose payload contains **no `.` at all** would be a
defect report about the fix, not a knife result — the D-NAMBLANK K2 shape.
`dot-str`, `dot-rem`, `dot-data` and `dotd-ctl` are the rows that would say so,
and none of them moved under any of the five.

⚠️ K4 is the only knife that touched the main ROM; it cost 4 B of page 1 (8 B →
4 B free), a wall the landed fix never goes near.
