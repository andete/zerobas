# D-MKSD — `MKS$` / `MKD$` / `CVS` / `CVD`

**Status:** shipped 2026-09-03. **Probe:** `scratchpad/mksd_probe.py`.
**Knives:** `scratchpad/mksd_knives.py`. **Denominator:** `make kwsweep`.

## 0. What was actually wrong

These four were **absent from `basic/kwtable.inc` entirely** — 148 entries, and
only `MKI$` and `CVI` from the family. So `MKS$(1.5)` was never tokenised as a
keyword at all: it parsed as the string **array** `MKS$(1)` and answered the empty
string. That is the mechanism behind the filed symptom "`MKS$` returns an empty
string", and it is a **silent wrong answer**, which this project ranks below a
refusal.

`kwsweep` calls this class `SILENT-GAP`, its own "worst kind" — and could not see
it either until D-KWORACLE fixed the second oracle's boot the same day.

## 1. The oracle, and why it is the CF-3300

These are Disk-BASIC verbs: the cassette VG-8020 answers `Illegal function call`
to all of them, and that column is **printed in every table rather than dropped**,
so the disk-vs-cassette split is visible instead of asserted. Same split
D-LSETREF settled for `LSET`/`CVI`.

**Token bytes are black-box oracle readings** — `kwsweep`'s crunch layer captured
what the CF-3300 stores for `a$=mks$(1)` and friends:

| verb | token | verb | token |
|---|---|---|---|
| `MKS$` | `FF AF` | `CVS` | `FF A9` |
| `MKD$` | `FF B0` | `CVD` | `FF AA` |

Typed input in, stored bytes out. No disassembly.

## 2. The measured contract

32 rows, `cf3300` vs `zb`. **`MKS$`/`MKD$` emit exactly the bytes the variable
store holds** — `MKS$(1.5)` is `65 21 0 0`, byte-identical to `PEEK(VARPTR(A!))`
for `A!=1.5` (row `c.stored`, and the same on all three machines per
`docs/spec-basic-faczero.md` §0). So the coercion is the *same* widen + round/pack
pair `var_store_fac` uses, not a private encoder that could drift from it.

| row | stimulus | answer |
|---|---|---|
| `b.mks` / `b.mkd` | `MKS$(1.5)` / `MKD$(1.5)` | `65 21 0 0` / `65 21 0 0 0 0 0 0` |
| `b.mksneg` | `MKS$(-1.5)` | `193 21 0 0` |
| `b.mkszero` | `MKS$(0)` | `0 0 0 0` |
| `b.mksint` | `MKS$(1)` | `65 16 0 0` — an int argument is widened |
| `a.mksdbl` | `CVS(MKS$(1.23456789#))` | `1.23457` — a double is **rounded to single** |
| `x.cvimks` | `CVI(MKS$(1.5))` | `5441` — 2 bytes off a 4-byte string, no error |
| `x.cvslong` | `CVS("ABCDEFGH")` | `4.24344` — extra bytes ignored |
| `x.cvsshort` / `x.cvsempty` / `x.cvdmks` | too few bytes | **ERR 5** |
| `e.cvsnum` | `CVS(5)` | ERR 13 |
| `e.mksnoarg` | `LEN(MKS$)` | ERR 2 |
| `v.big` / `v.small` | `CVS(MKS$(1E30))` / `(1E-30)` | `1E+30` / `1E-30` |

⚠️ **`MKS$(0)` is `0 0 0 0` on the reference, and would have shipped as
`0 255 255 255` here** — zero kept a stale mantissa until D-FACZERO canonicalised
it the day before. That defect was found by the scout that was only *sizing* this
slice, which is the whole argument for measuring the representation before
writing the verb that exposes it.

## 3. The implementation

Two shared bodies, each parameterised by `C` = the width.

**`str_mkf`** (`basic/strvar.asm`) — `MKI$`/`MKS$`/`MKD$`. Parse `( expr )`, then
either the existing 2-byte integer store or `widen_rhs_operand` +
`round_single_and_pack` / `round_and_finalize`, then `ldir` the packed bytes into
`STRSCR` and wrap the usual descriptor.

**`ev_ff_cv`** (`basic/expr.asm`) — `CVI`/`CVS`/`CVD`. One body, so all three
inherit CVI's hard-won error ordering rather than re-deriving it twice: the
deferred missing-`(`/`)` syntax errors, the non-string vs nested-fault split
(D-CVITM + D-CVISTRTM), and the too-short-string check. The length test became
`cp c`, and the measurements say that is right at all three widths — `CVS("AB")`
and `CVS("")` are ERR 5 exactly as `CVI("A")` is.

🎯 **THE WIDTH *IS* THE FACTYP CODE.** MSX numbers the types 2/4/8 and the widths
are 2/4/8, so one register sizes the check *and* types the result. That is the
reference's own numbering, not a coincidence this code invented — and K-MK4
exists to prove the code actually depends on it.

⚠️ **A shared tail is a label, not a decision.** The width is threaded through
`C` and the only divergence is the last few instructions, because the three verbs
genuinely obey one rule at three widths — not because one body is shorter.

**Cost.** Main page 1 269 → **164 B** free; sub-ROM page 0 1992 → **1962 B** (the
four keyword-table entries — the table has a single copy, and it lives there).
Low region unchanged at 63 B.

⚠️ **Five `jr`s became `jp`s in `strvar.asm`.** Inserting the body pushed
`str_eval_no` out of relative range for the `INPUT$` block below it. Same family
as the D-NGRAM lesson: adding a helper moves labels, and the assembler is the only
thing that notices.

## 4. Result

**0 DIFF / 32 rows**, `cf3300` vs `zb`, every error case included. The four
controls (`c.mkilen`, `c.mkibytes`, `c.cvi`, `c.stored`) were green before and
after, so the fixture and the family's calling shape were never the variable.

`make kwsweep` — the denominator, not this slice's own probe — went from
`SILENT-GAP=2  MISSING=2  DIVERGENT=1  SUPPORTED=31` to
**`DIVERGENT=1  SUPPORTED=35`**, with all five MK/CV words `present SUPPORTED
match` on both layers. The lone `DIVERGENT` is `csrlin`, the documented probe
artifact, unrelated.

## 5. Knives — aimed at the parameterisation, not the presence

`scratchpad/mksd_knives.py`. Deleting a keyword-table entry only proves the verb
is wired up, which 32 green rows already say. Three of these four attack the
claims the shared bodies actually rest on.

```
base ROM da8f0da17c28   base DIFF: []
K-MK1  length check `cp c` -> `cp 2`     moved x.cvdmks, x.cvsshort          PASS
K-MK2  MKS$ packs as DOUBLE not single   moved a.mksdbl                      PASS
K-MK3  drop the CVD keyword-table entry  moved a.mkdint r.cvd r.third x.cvdmks  PASS
K-MK4  ev_cv_float types everything 4    moved r.third                       PASS
restored ROM da8f0da17c28 (base da8f0da17c28) OK
```

**K-MK1** is the one that matters most: with the width check weakened,
`CVD(MKS$(1.5))` reads eight bytes out of a four-byte string and answers
`1.50000????????`, and `CVS("AB")` answers `4.22229`. Plausible numbers read out
of whatever followed the string — exactly the failure D-CVITM fixed for `CVI`,
now prevented at all three widths by one `cp c`.

**K-MK2 and K-MK4 are deliberately narrow, and the narrowness is the claim.**
`MKS$(1.5)` packs to `65 21 0 0` under *either* rounding, and `CVD(MKD$(1.5))`
prints `1.5` even mis-typed as a single — 1.5 and 7 need no more than a single's
three mantissa bytes. Only `1.23456789#` and `1/3` need more, so only those two
rows can separate the rules. Both arms moved exactly those rows and nothing else.

### 5.1 Three faults in the knife harness, and one contaminated prediction

None of this was in the fix; all of it was in the instrument.

1. **The row parser ate the count.** `DIFF (cf3300 vs zb): 0/32` split to a list
   whose fifth element is `0/32`, not a row label, so every arm's `moved` set
   carried a phantom member and **all four arms reported FAIL** on a fix that was
   already correct.
2. **The ROM guard watched the wrong artefact.** `basic/kwtable.inc` is included
   by `sub/sub.asm` *only* — the table has a single copy and it lives in the
   sub-ROM — so hashing just the main ROM made K-MK3 look INERT. The guard
   refused to believe that arm, which is right, but for the wrong reason. It now
   hashes both ROMs.
3. 🔴 **The guard's own fast path contaminated the next arm.** Because `INERT`
   skips the probe run, that whole arm finished inside `make`'s **1-second mtime
   resolution**: the restored `kwtable.inc` was not strictly *newer* than the
   `sub.rom` built from the knifed copy, so the following arm built against a
   **stale sub-ROM and measured the previous plant**. K-MK4 duly reported
   K-MK3's four rows. The restore now stamps the file forward in time.

⚠️ **And I adopted those four rows as K-MK4's prediction for the next round.** A
prediction inherited from a contaminated measurement is not a prediction, and it
turned a passing arm into a recorded FAIL until the reasoning was done properly:
forcing `FACTYP=4` still copies `C` bytes, so only a value needing more than
three mantissa bytes can move — `r.third`, and nothing else.

The four `moved` sets are identical across two independent runs after the fix.
