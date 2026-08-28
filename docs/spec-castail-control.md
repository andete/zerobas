# D-CASTAILCTL — a battery that treats any control failure as a broken instrument cannot measure a knife

**2026-08-28.** Closes the item D-FNRUN filed on 2026-08-21. **0 ROM bytes**; a
probe change. The founding knife was re-created to prove it, and the probe now
**scores** the break it used to be voided by.

## 1. The defect

`basic_probe_castail.py` checked its positive controls across **every side** and
returned exit 2 — *"NOT MEASURED (a positive control failed)"* — if any of them
missed. D-FNRUN's K-FR3 cut `dr_cas_close`'s `ld hl,(FN_RESUME)` → `ld hl,(STRPTR)`,
`cas-run-hit` went `ZQ9` → `<load-failed>`, and because that row is a positive
control the whole run was discarded: **33 printed, 0 scored**.

A knife is *supposed* to break things. A battery that reads any control failure as
a broken instrument cannot score one.

🎯 **`basic_probe_namspc.py:1036` already had the right rule and is the precedent:**

> ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN. A control that fails on `zb`
> is a finding and is scored below like any other row.

The controls exist because *"a machine that runs no program at all produces
`<nothing>` and an error message for free"* — and that argument is about the
**reference** side, which is what defines the answer here.

## 2. The fix

`control_faults(results, sides, controls)` skips `zb`. A reference miss is still
exit 2 (fixture, ROMs or cassette wrong — nothing below can be believed); a
zerobas miss falls through to the ordinary scoring path, where controls are
already in `scored` and already print a `[CONTROL]` note.

## 3. Falsification, twice

**The rule, without booting** (`--selftest`, planted readings):

| planted | faults | meaning |
|---|---|---|
| zb misses, reference fine | **0** | a finding, scored below |
| reference misses | **1** | the instrument, exit 2 |
| both miss | **1** | still the instrument, only the reference listed |
| both fine | 0 | — |

**The founding knife, for real.** K-FR3 is not tracked anywhere, so
[`scratchpad/castail_knife.py`](../scratchpad/castail_knife.py) re-creates it.
With the cut in place:

```
castail: 2 reading(s) diverge
DIFF cas-run-hit       vg8020='ZQ9'  cf3300='ZQ9'  zb='<load-failed>'   [CONTROL]
DIFF cas-run-hit-res   vg8020='ZQ9'  cf3300='ZQ9'  zb='<load-failed>'
ROWS: 32 printed, 31 scored — 29 agree, 2 diverge, 1 pinned
```

Before: `33 printed, 0 scored — NOT MEASURED`. The probe now exits **1** and names
both rows. Clean tree: 31/31 agree, unchanged.

## 4. Two things the knife itself taught

🔴 **THE INSTRUCTION ALONE WAS NOT THE SITE.** `ld hl,(FN_RESUME) ; D-FNRUN:
resume past the EXPRESSION` occurs **twice** in `basic/cload.asm` — the disk path
at `:231`, whose comment continues `--`, and the cassette path — so the bare line
matched both *as a prefix* and the knife's uniqueness guard refused to cut. It is
anchored on the **label** instead, which is what makes it `dr_cas_close`'s. The
guard doing its job is the only reason a wrong site was not cut silently.

⚠️ **`make`'s exit code is not the probe's.** The first reading of this run said
`rc=2` and nearly recorded "still voided" — but GNU make exits 2 on *any* failed
target. The probe's own exit was 1, and only the log distinguishes them. The
script now says so rather than printing a number whose owner is ambiguous.

## 5. What this does not change

The scored set is identical on a clean tree, so no row *"starts being scored"*
today — the item's warning about that applies only when a zb control is actually
failing, which is exactly when you want the row scored.

⚠️ `castail-acceptance` is a `Makefile` target and **not in `make gates`**, so
nothing collects this probe's exit code routinely. That is the same shape as the
already-filed item about which probes earn a battery slot, and is left there.
