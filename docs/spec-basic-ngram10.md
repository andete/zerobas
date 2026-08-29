# D-NGRAM10 — one `req_lineno` for RESUME / GOTO / GOSUB / ON ERROR GOTO

*2026-08-29. `basic/interp.asm` (helper + 2 sites), `basic/program.asm` (2 sites).
Probe `scratchpad/ngram10_probe.py`, arms `scratchpad/ngram10_knives.py`.*

**Cost: −17 B of main page 1** (331 → 348 B free; low unchanged at 118).
**Rows: 13, 1 DIFF — pre-existing and filed, not caused here.**

## 1. The carve

The fourth-ranked exact repeat in the main regions, and the same idea as
`req_letter` and `req_operand` beside it. Seven instructions, open-coded at four
sites:

```
                cp      LINENO_TOKEN
                jp      nz,stmt_error
                inc     hl
                ld      c,(hl)              ; target line number, LE
                inc     hl
                ld      b,(hl)
                inc     hl
```

| site | verb |
|---|---|
| `ex_resume` (interp.asm) | `RESUME <line>` / `RESUME 0` |
| `ex_goto_at` (interp.asm) | `GOTO`, and `IF … THEN <line>` |
| `ex_gosub` (program.asm) | `GOSUB` |
| `ex_on_error` (program.asm) | `ON ERROR GOTO` |

10 B each, **40 B**; an 11 B body plus four 3 B calls is **23 B**.

🟢 **The bail never returns**, so unlike D-NGRAM8's decline this run is safe
behind a `call`: `stmt_error` falls into `raise_error`, which resets SP from
SAVSTK. Checked at the source. No interior label appears inside any of the four
runs — `goto_resolve` sits *after* the run at the GOTO site, not within it.

## 2. Falsification

| arm | requires | measured |
|---|---|---|
| **S1** | 1 open-coded run left (the body), exactly 4 calls, **every pattern element alive** | ✅ |
| K-N10A | retarget the bail → every row the bail produces moves | **exactly the 4 `b.*`** |
| K-N10B | drop the last `inc hl` → the success half breaks | **all 13** |

🔴 **I predicted both wrong, and the arms caught it.**

- **K-N10A**: I predicted `b.resume` would *not* move — *"it reads
  `<Syntax error>` untrapped, so the message is the same either way."* Nonsense:
  an untrapped message **is** the error's text, and the text follows the code. It
  moved `<Syntax error>` → `<Type mismatch>` with the other three.
- **K-N10B**: I predicted six success rows. **All thirteen** moved, controls
  included, every one to `ERR 2 AT 10` — because **line 10 of every fixture is
  `ON ERROR GOTO 900`**, which goes through this very helper. Break the cursor
  and the fixture cannot parse its own first line.

🎯 That second one is a fact about the coverage rather than a defect in the arm:
`req_lineno` is on the path of *every row in this suite*. It makes K-N10B blunt
but decisive, and the **per-site** success witnesses are the four `g.*` rows,
each carrying a value only its own site can produce (`jumped` / `7` / `resumed` /
`ERR 11 AT 30`).

## 3. 🔴 Two apparatus faults this probe found in itself

**The blindness check read only zerobas.** `b.onerr` came back DIFF with the
*references* returning `";"unreached";"` — their own source text, because a run
that never reaches its `PRINT` reads the typed line back. Checking only the
zerobas column calls that a divergence. It now checks **every side**.

**And the fence has to detect the ECHO, not the payload.** The first repair
blinded on the word `unreached` — which is also what a row *prints when the bail
fails to fire*, so a real failure would have been filed as blindness. The
signature is `;"`, a fragment of the fixture's own `PRINT` statement that cannot
occur in any value. [[readout-blind-to-its-own-subject]] [[trapsvc-echo-fence]]

The two affected rows now carry their own `CLS`: their error fires at a **setup**
line, ahead of the fixture's `CLS` on line 60, so an untrapped message otherwise
prints onto a screen still holding the LIST echo.

## 4. 🔴 A pre-existing divergence, found by the new rows

| row | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|
| `ON ERROR GOTO A` | `<Syntax error>` **untrapped** | ″ | **`ERR 2 AT 30` — trapped** |

Both references let `ON ERROR GOTO <non-line>` raise **untrapped**; zerobas traps
it with the handler armed by the previous statement. **Pre-existing** — HEAD
gives the identical `ERR 2 AT 30` — so this carve exposed it rather than causing
it, and it is filed rather than fixed here: it is about `ON ERROR`'s disarm
ordering, not about `req_lineno`.

⚠️ The revert check ran **zb only**, which makes every verdict column vacuously
`SAME`. The evidence is the identical *reading*, not the verdict.
