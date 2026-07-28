# D-WID — `WIDTH n`'s valid domain

Status: **implemented and gated, awaiting sign-off.**
Characterization: [`docs/width-vg8020-characterization.md`](width-vg8020-characterization.md).
Gate: `make width-acceptance` ([`probes/basic/basic_probe_width.py`](../probes/basic/basic_probe_width.py)),
76 rows, eight batteries. **76/76**; the baseline it replaces was **36/62**.

This is the last residue of the abort-depth slice.
[`docs/spec-basic-abort-depth.md`](spec-basic-abort-depth.md) §7 deferred it
explicitly: `4d35b6d` fixed how `WIDTH 300` *fails*, and left open which `n`
`WIDTH` should *accept*.

⚠️ §4's numbers are **measured, not estimated**. The implementation was built
and weighed against a clean tree before this document was written, the same way
[`docs/spec-basic-str-domain.md`](spec-basic-str-domain.md) §5 was — because in
this arc the estimates have been wrong in both directions, by as much as 100%.

---

## 1. The defect

`ex_width` ([`basic/screen.asm:169`](../basic/screen.asm:169)) evaluates its
argument, runs it through `get_byte_arg` — whose whole domain is 0..255 — and
then writes `LINLEN`, a per-mode default and calls `CHGMOD` **unconditionally**.
No bound, and the wrong mode split. Five divergences, measured
(characterization §3), and **every one of them silently destroys the display**:

| # | input | reference | zerobas (before) |
|---|---|---|---|
| D-WID-1 | `WIDTH 0` | `Illegal function call` | accepted → width 0 |
| D-WID-2 | `WIDTH 41`..`255` (`SCREEN 0`/`2`/`3`); `33`..`255` (`SCREEN 1`) | `Illegal function call` | accepted → that width |
| D-WID-3 | `SCREEN 2 : WIDTH 29` | records `LINL40` | records `LINL32` |
| D-WID-4 | `WIDTH "40"` / `WIDTH A$` | `Type mismatch` (ERR 13) | accepted → width 0 |
| D-WID-5 | `WIDTH` / `WIDTH :` / `X=1:WIDTH` | `Missing operand` (ERR 24) | accepted → width 0 |

This is the `WIDTH 300` symptom exactly — reached through the **accept** path
rather than the reject path, and so untouched by `4d35b6d`. Typed at the prompt,
each of these leaves the machine with no readable screen and no error.

**D-WID-4 and D-WID-5 were not on any list.** They came out of batteries written
to cover the argument surface rather than to confirm the known defect — the
fifth consecutive slice whose calibration turned up live defects in code nobody
was testing.

## 2. The rule (measured, characterization §2)

1. **The bound is mode-dependent, and the per-mode slot goes with it.**
   `SCREEN 1` → legal `1..32`, records `LINL32`. **Every other mode**, graphics
   included → legal `1..40`, records `LINL40`.
2. **A reject writes nothing** — `LINLEN`, `LINL40` and `LINL32` all unchanged.
3. **Four distinct errors**: out-of-bound-but-in-int16 → `Illegal function call`;
   beyond int16 → `Overflow`; a string argument → `Type mismatch`; an absent
   argument → `Missing operand`. (`WIDTH ,` stays `Syntax error`.)
4. **Coercion truncates toward zero before the bound check** — `40.9` accepted,
   `41.9` rejected, `-0.5` rejected.
5. **The domain check beats the deferred syntax error** — `WIDTH 41,` is ERR 5,
   not ERR 2. But an *accepted* argument is applied even when the line then
   fails: `WIDTH 32,` sets width 32 and *then* raises `Syntax error`.

`get_byte_arg`'s existing int16/byte two-stage rule is **already exactly the
reference's**, verified at both boundaries (`-32768`→ERR 5, `-32769`→ERR 6,
`32767`→ERR 5, `32768`→ERR 6). The mode bound sits on top of it; that half is
not touched.

## 3. The design, as built

All of it inside `IF ROM_BASE < $4000`, so the lean cart assembles nothing new
and stays **byte-identical** (confirmed by `check_reloc`).

```
ex_width:
        inc     hl
        call    skip_spaces         ; returns A = (HL)
        or      a
        jr      z,wid_missing       ; bare WIDTH / WIDTH : -> ERR 24
        cp      COLON
        jr      z,wid_missing
        call    eval
        ld      a,(TMISMATCH)       ; WIDTH "40" -> ERR 13
        or      a
        jp      nz,type_mismatch_error
        call    get_byte_arg        ; A = 0..255, or aborts ERR 5 / ERR 6
        ld      b,a
        ld      de,LINL40           ; ... LINL40 and LINL32 are ADJACENT ...
        ld      a,(SCRMOD)
        dec     a                   ; SCRMOD 1 = text-2
        ld      a,40                ; (no flags — the dec a Z survives)
        jr      nz,wid_bound
        inc     de                  ; ... so one inc picks the slot ...
        ld      a,32                ; ... and the bound rides the same test
wid_bound:
        cp      b
        jr      c,wid_illegal       ; wanted > the mode's maximum
        ld      a,b
        or      a
        jr      z,wid_illegal       ; WIDTH 0
        ld      (LINLEN),a
        ld      (de),a              ; the mode's per-mode default
        ...                         ; (unchanged: re-read SCRMOD, CHGMOD, exec_stmt)
wid_illegal:
        jp      gb_illegal          ; ERR 5
wid_missing:
        jp      loc_missing         ; ERR 24
```

Three things make it cheap:

- **`LINL40` ($F3AE) and `LINL32` ($F3AF) are adjacent**, so the slot is one
  `ld de` plus a conditional `inc de`, and the *bound* rides the same `dec a`
  test rather than needing its own.
- **All three raisers already exist and are all in page 1** with `ex_width`:
  `gb_illegal` ($4565), `type_mismatch_error` ($424B), `loc_missing` ($7ED1) —
  the last one being the ERR 24 raiser `LOCATE` built.
- **Neither reject needs return-address parking.** `exec_stmt` `jp`s to
  `ex_width`, so both run at the handler's own depth — the same reason
  `ex_swap` tests its operands there ([[missing-class-slice]]). Since `4d35b6d`
  the depth would not matter anyway, but it keeps the code a plain `jp`.

Ordering follows §2.5 directly: the argument is checked before anything else on
the line is scanned, so `WIDTH 41,` raises ERR 5; and `LINLEN` is written only
after both bound tests pass, so a reject writes nothing (§2.2).

## 4. Cost — measured from a clean tree

| wall | before | after | delta |
|---|---|---|---|
| page-0 low region | 30 B free | 30 B free | **0** |
| page 1 | 30 B free | **3 B free** | **−27 B** |

`rm -rf build` first, both times ([[measure-the-wall-from-clean]]). Lean
`basic.rom` byte-identical, so `LEAN_SHA256` does not move.

⚠️ **3 B is not headroom.** This slice fits, but it consumes essentially the
whole page-1 reserve — see the sign-off question in §7.

## 5. The gate

`make width-acceptance` — 76 rows, boot-per-case, VG-8020 differential.
Batteries: `ctl` (6), `s0` (15), `s1` (10), `s2` (11), `co` (14), `sx` (8),
`pe` (4), `unt` (7). Design rationale in the probe's docstring and
characterization §1; the two load-bearing properties are that **the readout is
numeric and width-independent** (the subject moves the instrument) and that
**the instrument is pinned on every row** (the two machines boot at different
widths).

### 5.1 Falsification

A green gate proves nothing until deleting the code under test reddens it
([[gate-can-be-green-while-measuring-nothing]]).

- **Baseline before/after.** 26 of the 62 baseline rows were red before the
  change and are green after. Those rows demonstrably have teeth.
- **Bound + zero rejects neutered to `nop`s** → `--only sx-` goes **6/8**, and
  the two that fall are exactly the ordering rows `WIDTH 41,` and `WIDTH 0,`
  (zerobas reports ERR 2 with the width *applied*, where the reference reports
  ERR 5 with nothing applied). **The six survivors are the point**: the
  missing-operand, `WIDTH ,` and in-domain trailing-comma rows do not depend on
  the bound and stay green, so the battery is not merely globally red. This is
  the falsification for the 14 gap rows, which never ran red against the
  baseline.
- **The `inc de` slot selection neutered to a `nop`** → `--only s1-` goes
  **0/11**. ⚠️ Not an *isolated* falsification: the probe's own pin line
  (`SCREEN 1:WIDTH 32`) runs through the same slot selection, so breaking it
  breaks the pin and reddens the reject rows too. It proves the byte is
  load-bearing; it does not separate slot from bound. The baseline before/after
  does that (`s2-1`/`s2-32`/`s2-33`/`s2-40` and `pe-s2-back` were red on a build
  whose bound logic did not exist at all).

### 5.2 Standing gates re-run

No existing probe depended on an out-of-domain width — every other `WIDTH` in
`probes/` is `WIDTH 40`, legal in `SCREEN 0`. All re-run on the clean build:

| gate | result |
|---|---|
| `unit-test` | 53/53 |
| `abort-acceptance` | 23/23 |
| `intarg-acceptance` | ALL PASS |
| `str-domain-acceptance` | 89/89 |
| `missing-acceptance` | OK |
| `cursor-acceptance` | OK |
| `width-acceptance` | **76/76** |

## 6. Out of scope

- **The unwind.** Already fixed and gated by `make abort-acceptance`; the `unt`
  battery here is a seam, not a re-litigation.
- **`get_byte_arg`'s int16/byte stage** — measured as already exact (§2).
- **`SCREEN`'s own argument surface.** `SCREEN 4` raises `Syntax error` where
  the reference would raise something else on an MSX1; not measured here and not
  this slice's subject.
- **`WIDTH` for the printer (`LPRINT` width).** Not an MSX1 `WIDTH` form.

## 7. Sign-off questions

- **S-WID-1 — the mode rule.** Implemented as "`SCRMOD == 1` → `LINL32`/32,
  everything else → `LINL40`/40". The four measured modes (0,1,2,3) are all
  consistent with it, and MSX1 has no others. An equally consistent reading is
  "graphics modes fall back to the text-1 defaults". They are indistinguishable
  on MSX1 hardware, so the cheaper one is implemented. Recommended: accept, and
  record the alternative reading here rather than in code.
- **S-WID-2 — the 3 B page-1 reserve.** This is the real question. The slice
  fits with 3 B to spare, which means the **next** page-1 slice starts with no
  reserve at all and must open with a carve. Options: (a) land as-is and let the
  next slice fund itself — it will have to anyway; (b) land a carve *now* to
  restore headroom, adding a session before anything else moves.
  `clone_scout.py` still lists `ev_*_lp` (~21 B) and small groups in
  `list.asm`/`files.asm`. Recommended: **(a)**. The carve is the same work
  whenever it happens, and doing it now would price a reserve nothing is
  currently waiting on — but this is a judgment call about sequencing, not a
  technical one, so it is yours.
- **S-WID-3 — `ERR 24` for a missing argument.** `Missing operand` is what the
  reference gives, and zerobas's message is the house-style lowercase
  `missing operand` that `LOCATE` added. That spelling difference is folded by
  the probe's `norm()`, consistent with the documented two-spelling split.
  Recommended: keep folding it; it is the D-2 house-style decision, not a
  finding.
- **S-WID-4 — should the gate be wired into a standing target?** It is
  `make width-acceptance`, heavy and oracle-dependent like its siblings, and not
  part of `unit-test`. Recommended: yes, same status as
  `str-domain-acceptance`.
