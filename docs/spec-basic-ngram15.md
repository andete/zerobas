# D-NGRAM15 — one `str_eval_ix` for the seven "string at the IX cursor" sites

*2026-08-31. `basic/strvar.asm` (body), `basic/expr.asm` (×4),
`basic/str-engine.asm` (×3). Probe `scratchpad/ngram15_probe.py`, arms
`scratchpad/ngram15_knives.py`.*

**Cost: −15 B** — page-0 low 112 → **121**, main page 1 361 → **367**.
**Rows: 14, 1 scored DIFF (pre-existing), 1 NO-ORACLE.**

## 1. The carve

Seven sites said `push ix / pop hl / call str_eval` verbatim — *evaluate the
string expression at the IX cursor*. Named from their **enclosing labels**, not
from nearby prose (D-NGRAM4 lost a site by reading the prose):

| site | file | verb |
|---|---|---|
| `ev_rel` | `expr.asm` | a relational operator's LHS |
| `evr_rhs` | `expr.asm` | ...and its RHS |
| `ev_ff_cvi` | `expr.asm` | `CVI` |
| `ev_ff_fre` | `expr.asm` | `FRE` |
| `ev_str_arg` | `str-engine.asm` | the shared string-function argument parse |
| `ev_f_instr` | `str-engine.asm` | `INSTR` |
| `ers_rhs` | `str-engine.asm` | the string relational's RHS |

6 B each, 42 B. A 6 B body plus seven 3 B calls is 27.

🔴 **A line-based grep found six of the seven.** `ev_ff_fre`'s site carries a
comment on its `push ix` line. The sites were enumerated at **instruction
level** by the sweep's own parser, and the shortfall is exactly the D-NGRAM2
hazard: *comments live inside the sequence.*

## 2. The body is sited where the callers are NOT

Four callers are in page 1 (361 B free) and three in the page-0 low region
(112 B free) — but `str_eval` itself lives in `strvar.asm`, **page 1**, and the
low-region callers already reach it. So the body goes beside `str_eval`:

| | before | after | |
|---|---|---|---|
| low region | 3 × 6 = 18 B | 3 × 3 = 9 B | **+9 B free** |
| page 1 | 4 × 6 = 24 B | 6 + 4 × 3 = 18 B | **+6 B free** |

**The scarce region takes the larger share, which is the opposite of where the
sites are.** Siting by "where the code lives" would have given low +3 instead
of +9.

## 3. The tail jump is frame-neutral by construction — and the arm says what that is worth

`call str_eval_ix` pushes the return to the **site**; the `jp` pushes nothing;
`str_eval`'s own `ret` returns to the site. The depth at `str_eval` is
**identical** to the open-coded form. That matters because `str_eval` declines
(CF clear) as well as succeeding and all seven callers keep their own `jr c` /
`jr nc` at the site — the structure D-NGRAM8 broke by putting `str_eval` behind
a `call` whose `ret` landed one frame too shallow.

⚠️ **K-N15B asserts the zero.** Turn the tail into `call` + `ret` and **no rows
move**: `str_eval` returns normally, so the extra frame is popped before any
caller sees it. The tail's value here is one byte plus a structural guarantee for
the next caller anyone adds — *not* a measured hazard at these seven sites. An
arm that asserts its own zero beats a comment asserting a danger never shown.

## 4. 🔴 Declining for the wrong reason looks exactly like declining for the right one

K-N15A points the cursor at garbage (`pop hl` → `pop de`, keeping the stack
balanced — cutting the `pop` outright leaves `push ix` unmatched and
`str_eval`'s `ret` jumps to the cursor *value*, which crashes the machine rather
than moving rows).

Predicted 12 rows; **8 moved**. The four that held — `b.cvi`, `b.len`,
`g.frenum`, `g.relnum` — are every row whose expected answer is *"str_eval
declined"*. **A garbage cursor declines too.** Those rows are real coverage
(they agree with both references) but this knife cannot witness them.

## 5. 🔴 The third arm moved the controls, so it was deleted

K-N15C forced CF **set** on the way out, so no site would take its `jr nc` arm —
built specifically to reach the half §4 cannot. It moved **all fourteen rows,
both controls included**: with CF forced, every site proceeds on a `STRPTR`
pointing at nothing and the interpreter does not survive to answer the next row.

**A knife that moves the controls has broken the machine, not the subject.** It
is deleted rather than kept with an "everything moves" expectation, which would
assert nothing. So the decline half rests on the rows agreeing with both
references, plus K-N15B's asserted zero on the frame question D-NGRAM8 actually
got wrong — said plainly rather than papered over.

## 6. 📌 One row has no oracle, and one is a real divergence

* `g.cvi` (`CVI("AB")`) — **NO-ORACLE**: `CVI` is a Disk BASIC verb, so the
  cassette-only VG-8020 answers `Illegal function call` to every `CVI`. The two
  references disagree with *each other*; zerobas targets the disk machine and
  matches it (`16961`).
* `b.cvi` (`CVI(5)`) — **a real, pre-existing divergence**: `Type mismatch` on
  the CF-3300, **`Syntax error`** here. Measured identically before and after
  the carve. This is the D-LEFTTM class — the argument parse rejects before the
  type check — and it is filed, not fixed here. No prior adjudication exists for
  it (checked, after D-EXPNEG).

## 7. Falsification

| claim | what would refute it | result |
|---|---|---|
| the seven runs were identical | the assembler, or a moved row | 14 rows, both DIFFs identical before and after |
| the collapse saves 15 B | `make basic-reloc` | low +9, page 1 +6 |
| every site is rewired | S1 counts them in the source | 0 open-coded runs, 7 calls, matcher alive |
| the tail jump prevents a real hazard | K-N15B | **refuted, and asserted**: 0 rows move |
| the decline rows witness the decline path | K-N15A | **refuted**: they hold, because a garbage cursor also declines |
