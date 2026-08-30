# D-DEADBODY — the only `.inc` nothing assembles, and the gate that found it

*2026-08-30. `tools/check_shared_bodies.py` + `tools/shared-body-allow.txt`,
wired as `make shared-body-check` (static tier). No ROM change.*

## 1. How it was found: a fix that had a twin

D-TRUNCLOAD bounded `relink`'s walk in `sub/lineedit.asm` — `HL == PRGEND`
became `>=`, because an equality test never fires again once `skip_to_eol`
overshoots on a truncated store, and relink then walks RAM forever.

A four-line sweep for the *same shape* — a 16-bit equality test against a RAM
limit, byte-wise, guarding a walk — found **four** sites. One of them was a
**second copy of the routine just fixed**:

| site | walks | verdict |
|---|---|---|
| `basic/lineedit-body.inc:211` `rl_lp` | the program, to `PRGEND` | 🔴 **a copy of the fixed loop, in a file nothing assembles** |
| `sub/lineedit.asm:996` `lrnm_lp` | the program, to `PRGEND` (RENUM's find) | judged: walks a **well-formed** store — every line it steps over was written by `store_line`, which terminates |
| `sub/arrays.asm:613` `scvf_notfound` | the variable region, to `ARYTAB` | judged: entry lengths are structural, not read from a file |
| `sub/strheap.asm:841` `sgw_sc_lp` | the scalar region, to `ARYTAB` | judged: same, and it runs *after* `vars_reset` has made the regions consistent |

**Only the first is reachable from a malformed input**, which is what separates
it from the other three: `relink` is the one walk a *file* can hand a store to.
The three are recorded rather than changed — a byte spent on a walk no input can
overshoot buys nothing, and the sweep is the standing measure.

## 2. 🔴 A dead shared body is worse than dead code

`basic/lineedit-body.inc` is **the only `.inc` under `basic/` or `sub/` that no
source includes**. Its own header says why: the body was extracted verbatim from
`basic/program.asm` so the *same source* could feed two homes, and the main-ROM
home is marked `(retired)`. The live copy is `sub/lineedit.asm`'s page-1 tenant.
It is still a Makefile dependency of the sub ROM, which can never affect the
build.

Ordinary dead code does nothing. **A dead COPY of a live routine reads as the
live one** — and this one had been byte-identical to its twin right up until
D-TRUNCLOAD, so the divergence is one day old and invisible.

⚠️ **`deadcode-check` cannot see this class.** It reasons about labels in an
assembled image; an unassembled file contributes none. That is not a bug in it —
it is a different question, and it needed a different instrument.

## 3. What the gate does, and the two ways it could have lied

Every `.inc` under `basic/`/`sub/` must be named by an `include` in some source,
or be allowlisted **with a reason**.

🔴 **The match is by BASENAME, and that is forced.** Sources include each other
across the directory boundary with relative paths — `include
"../basic/title-body.inc"` from `sub/title.asm`, `include "equates.inc"` from
`sub/sub.asm`. **The first cut compared include text against repo-relative paths
and reported FIVE dead files, four of them false**: every cross-directory
include missed. A checker whose failure mode is *"everything looks dead"* would
have been believed exactly once. `S1` is the control for it, on a file included
only that way.

🔴 **And it refuses on a degenerate scan.** If the include regex matches nothing
— a syntax change, a moved tree, a bad glob — every `.inc` reads as dead and the
report is catastrophic and entirely false. Fewer than 20 includes found is an
**instrument failure, exit 2, never a finding**. `S4` drives that path with a
regex that deliberately matches nothing rather than asserting it.
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]

## 4. 🙋 What was NOT decided

The dead file is **annotated and allowlisted, not deleted and not synced.**

* Deleting a deliberate historical record is not a judgement this gate — or the
  agent that wrote it — should make.
* **Syncing the dead copy would be worse**: it restores the illusion that either
  one is authoritative. `rl_lp` below the annotation still reads `==`, on
  purpose, and the header says so in the first ten lines.

Keep-or-delete is Joost's call. Either way the gate now watches the class.
