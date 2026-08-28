# D-NGRAM3 — one `le_call` for five lineedit sub-ROM call sites

*2026-08-28. `basic/program.asm` (helper), `basic/list.asm`. Probe
`scratchpad/ngram3_probe.py`, arms `scratchpad/ngram3_knives.py`.*

**Cost: −49 B of main page 1 (226 → 275 B free).** Low region unchanged.
**Rows: 9, DIFF 0/9** against both references.

## 1. The shape

Five sites drove `SUBROM_IDX_LINEEDIT` with the identical 14 B run — LIST
(`list.asm`), and the line STORE, DELETE, RENUM and AUTO (`program.asm`):

    ld ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_LINEEDIT
    call subrom_call / jp c,subrom_absent_error / ld a,(LE_STATUS) / or a

70 B in all; a 15 B body plus five 3 B calls is 30 B. 🎯 **And four of the five
set `LE_OP` immediately before it**, so `le_call_op` is a 3 B second *entry*
rather than a second body, and those four drop their own `ld (LE_OP),a` for
nothing. Together **−49 B**.

Every caller branches on `A`/`Z` straight afterwards, and `ret` preserves both.

⚠️ **A SIXTH SITE WAS MEASURED AND DECLINED.** `relink` has the same prefix but
returns *without* reading `LE_STATUS`, so routing it through the helper would
change the `A` and flags its callers see — and `cload.asm` has two plain
`call relink` sites whose flag dependence is unverified. 7 B, declined until that
contract is measured rather than assumed. [[a-shared-tail-is-not-a-decision]]

## 2. 🔴 THE PER-SITE WITNESS HAS TO BE STATIC, AND FINDING THAT OUT WAS THE WORK

The hazard in this class is not a wrong helper — it is **a site that was never
rewired**, which behaves identically while the saving quietly comes up short. In
D-NGRAM2 a runtime knife answered that: retarget the helper, and any row that
fails to move names the missed site.

**Here that instrument does not exist.** The line STORE is one of the five
sites, and this harness *types its own program* through it — so a knife on
`le_call` takes the fixture down with it and **every** row moves, controls
included. There is no control on this apparatus that survives such a knife.

So the question is answered by an exact static enumeration instead (arm **S1**):
the open-coded 5-instruction run must occur **zero** times in the tree and
`call le_call`/`le_call_op` exactly **five**. Measured: 0 and 5.

That enumeration is at INSTRUCTION level, not by grepping lines — comment lines
sit *inside* the sequence at the DELETE site, so a line-adjacent regex is wrong
here exactly as it was in D-NGRAM2.

The runtime arms keep their own, smaller job: **K-N3A** (`ld a,(LE_STATUS)` →
`ld a,7`) and **K-N3B** (drop the `LE_OP` store) each move all 9 rows, which says
the helper is load-bearing and nothing about which sites call it. Predicting
*"all 9, controls included"* is the honest statement; a control set that pretended
to survive would have been decoration.

## 3. The probe's own blind rows, again

The first row set had green controls `DELETE 10`, `RENUM 100,10,10` and
`LIST 10-10` — the OK paths. All three read `";"ok";"` on **all three sides**:
those verbs operate on the harness's *own* typed program, so a successful one
destroys the very lines that would report the result, and what came back was the
ECHO of the typed source, scored `SAME`.

**Three echoes agreeing is not agreement**, and `<NO OUTPUT>` is not the only way
to measure nothing — the blind-detector inherited from D-NGRAM2 missed these
because an echo is not a blank. The rows are removed rather than left as
decoration, the fence now also refuses any answer containing the typed quote
character, and the OK paths of LIST/DELETE/RENUM are recorded here as **not
witnessable in this fixture**. [[an-unnamed-outcome-reads-as-no-outcome]]
