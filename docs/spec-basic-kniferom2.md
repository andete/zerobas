# D-KNIFEROM2 — do the knife runners act on their ROM hash, or only print it?

*2026-08-29. `tools/check_knife_rom_guard.py` (new gate),
`scratchpad/banner_knife.py` (the one real fix), `Makefile`, `tools/run_gates.py`.
No ROM change.*

## 1. The question, and why it needed an instrument

A knife can be **silently inert because the build did not happen**: write the cut
source, run `make`, and the previous ROM can still be in place — the probe then
measures the **uncut** machine and reports `moved 0 rows`, which is exactly what
an arm that legitimately found nothing looks like. The defence is to hash the
images around the plant and refuse the arm when they did not move.

*How many runners actually do that?* was filed as *"~10 look like they print"*.

🔴 **I answered it with a regex four times and was wrong four times, always
overstating the gap.** 33 print-only → 10 → 24 → 6. Each pass found an idiom the
last one missed. It is the **second** time this same claim has been filed too
pessimistically; the earlier attempt said *"none of 14"* where the answer was 5
of 41. Counting by pattern-match over free-form Python is the wrong instrument.

## 2. What the AST version got wrong, five more times

Reading the AST was better and **not sufficient** — the first version failed in
the *same direction as the regexes, for the same reason*: it encoded a
**spelling** instead of following the data.

| # | what it required | what broke it |
|---|---|---|
| 1 | a `build/*.rom` path *inside* the `def hashes()` body | `missop`, `screen3` — module-level `ROMS = [...]` |
| 2 | one level of taint | `missop` — hashes pass through a local `moved(base, now)` |
| 3 | the function be *named* `hashes` | `circdom`, `forret`, `y192` — `sub_sha()`, `romh()` |
| 4 | the hash source be called *directly* | `circdom` — `sub_sha()` returned out of `build()` |
| 5 | a literal image filename anywhere | `grpac` — builds its path as `f"{rom}.rom"` |

Each was caught by **pinning the real file that broke the previous version** as
its own arm (S8 is five real files, by name). An arm set that only ever sees
synthetic fixtures could not have found any of them.

**The rule that finally holds** asks about data flow, not names: a *function* is
a ROM-hash source when its body calls `hashlib` in a module that deals in ROM
images; taint propagates through assignments **and function returns**, to a
fixpoint; and a runner **acts** when any `if`/`assert` test reads a tainted name.

⚠️ **A source hash is not a ROM hash and looks identical to a grep.**
`banner_knife.py` hashed its own source text to verify its restore — a real
check, of a different claim. S5 is the synthetic negative control for that shape.

## 3. The answer

| | n |
|---|---|
| ✅ act on the ROM hash | **48** |
| ➖ no ROM to hash, reason stated | **4** |
| ⚠️ hash but never read it back | **0** |
| 🔴 unguarded | **0** |

**52** runners is the denominator — not the 41 previously filed.

The four exemptions are not a heuristic's leftovers. `prologue`, `seedhole2` and
`seedprose` knife a **source reader** and never invoke a build at all
(`seedprose_knives.py` says so in its own header: *"No ROM is built"*);
`xreg_knife.py` is named in an `EXEMPT` dict **with its reason** — K-XR1 requires
`make basic-reloc` to go **red**, so there is no post-cut ROM to hash.

🔴 **And "mentions a build path" is not "builds".** All three sweep knives read
`build/*.sym`, so a hint list containing `build/` counted them as ROM-building
and demanded a hash they have nothing to hash. The check now requires an actual
`make repack-machine` / `make basic-reloc` invocation.

## 4. The one real fix

`banner_knife.py` was the last runner with no ROM check. It verified its
**anchor** and its **restore** — both over the source — and never asked whether
the cut reached the ROM. It now hashes the three images around the plant and
returns an instrument fault when they do not move. Arm S9 pins it.

## 5. The gate

`make knife-rom-guard-check`, in the **static** tier (~0.2 s). The threshold is a
**ratchet at 0**: a new runner cannot ship without either a ROM-hash check or a
stated reason. Nine self-test arms, including a positive control that the
discovery glob finds the real tree — an arm set that examines only the files it
is handed cannot tell an empty tree from a broken glob.
