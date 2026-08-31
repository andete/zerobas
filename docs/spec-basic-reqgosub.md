# D-NGRAM18 — one `req_gosub`, and two knives that were invisible to their own rows

*2026-08-31. `basic/interp.asm` (body), `basic/program.asm` (4 sites). Probe
`scratchpad/reqgosub_probe.py` (12 rows, three machines), arms
`scratchpad/reqgosub_knives.py`.*

**Cost: −14 B** — main page 1 357 → **371**. **Rows: 12, DIFF 0 before and
after.**

## 1. The carve

`call skip_spaces / cp GOSUB_TOKEN / jp nz,trap_syntax / inc hl` stood at four
sites, one per trap verb: `ON STOP` (`eos_common`), `ON INTERVAL=`
(`ex_on_interval`), `ON STRIG` (`ex_on_strig`), `ON KEY` (`ex_on_key`). 9 B each;
a 10 B body plus four 3 B calls is 22.

📏 **Five `cp GOSUB_TOKEN` sites exist.** The fifth is `ON x GOTO|GOSUB`'s
dispatch, which branches to **two** labels and shares no destination — the same
rule that kept the optional-comma sites out of `req_comma`.

⚠️ `trap_syntax` is `pl_syntax` = `ld a,2 / jp raise_error`: it never returns, so
the helper's extra frame is discarded with the rest.

🔴 **A line-based match found ZERO of the four.** Two hazards at once: the token
is `GOSUB_TOKEN`, not the lower-case name the sweep prints, and **a comment line
sits between the `jp` and the `inc hl`** at every site. Matched at instruction
level, tolerating interior comments.

## 2. 🔴 Two knives, both invisible, and neither because the code was wrong

| cut | moved | why |
|---|---|---|
| drop the `inc hl` | **0** | the slot loop then finds no line number at the GOSUB token and **silently clears the handlers**; the trailing `:PRINT "ZQ1"` still runs |
| `jp nz,trap_syntax` → `ret nz` | **0** | `ON KEY 100` still reports `Syntax error`, so that rejection comes from **later**, not from this check |

Neither is a failure of the carve; both are statements about the **row set**.
The first has a failure mode — a trap silently disarmed — that no row here can
read, because no row makes a trap *fire*. The second says the `b.*` rows are
blind to this helper even though the `g.*` rows are not.

## 3. The arm that does work, and why it is the right one

Making `req_gosub` **always raise** moves **exactly** the four `g.*` rows and
leaves all three controls alone. That is the observable form of *"every one of
the four sites was rewired"*, and it complements S1's static count: S1 says the
source has four calls, K-G1 says the machine takes them.

🎯 **It also settled a real doubt.** When both finer cuts moved nothing, the
live hypothesis was that the sites are unreachable — dead code, the D-DEADBODY
shape. The always-raise cut refuted that in one run.

➡️ **What would see the finer cuts**: a row that ARMS a trap and then makes it
FIRE (`ON STOP GOSUB` plus a Ctrl-STOP injection), which needs an input fixture
this probe does not build. Named rather than left as a silent gap.

## 4. Two apparatus faults on the way

* **The knife anchor was not unique.** `inc hl ; consume it` + `ret` is
  word-for-word `req_comma`'s tail from the previous slice, so the short form
  matched twice and the runner refused it as *pattern not unique* — correctly.
  Anchored on the line above.
* **Deriving the runner from the previous one by `sed` produced a half-rewritten
  file** that still spoke of commas. Rewritten from the source file
  programmatically instead, with the cuts written for this helper.

## 5. Falsification

| claim | what would refute it | result |
|---|---|---|
| the four runs were identical | the assembler, or a moved row | 12 rows, identical across the carve on three machines |
| the fifth site cannot share | it moving with the four | `ctl.ongosub` / `ctl.ongoto` hold under K-G1 |
| the sites are reachable | the always-raise moving nothing | it moves exactly the four `g.*` rows |
| the collapse saves 14 B | `make basic-reloc` | 357 → 371 |
