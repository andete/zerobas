# D-DEVBARE — the `FOR` clause is optional on a device channel

*2026-08-30. `basic/files.asm` (the `LPT:`/`CRT:` open arm). Probe
`scratchpad/devbare_probe.py`, knife `scratchpad/devbare_knives.py`.
**Zero bytes.***

## 1. What was wrong

The device arm read:

```
                cp      FOR_TOKEN
                jr      nz,oo_fail_syn      ; device channels require FOR OUTPUT
```

The comment asserts a rule the reference does not have. On a CF-3300 a bare
device open is accepted **and the channel then works**:

| row | CF-3300 | zerobas (before) |
|---|---|---|
| `w.crtbare` · `w.lptbare` — `OPEN"CRT:"AS #1` | OK | **Syntax error** |
| `w.crtwrite` — …then `PRINT#1,"x"` | OK | **Syntax error** |
| `w.crtclose` — …then `CLOSE#1` | OK | **Syntax error** |

A bare device `OPEN` means **OUTPUT**, which is the only direction `LPT:`/`CRT:`
have.

## 2. 🔴 Found by a control that failed

This was not the subject of anything. `OPEN"LPT:"AS #1` was the **baseline** of a
D-OPEN2 discriminator run (device channels vs disk channels) — and it was red,
which **voided the whole run** before I noticed the baseline was the thing
failing. The re-run with `FOR OUTPUT` produced D-OPEN2's real table; the
divergence that broke the first attempt is this one.
[[classify-a-control-failure-by-which-side-failed-it]]

⚠️ **That is the fifth fixture fault in this arc**, and like three of the others
it produced a *plausible* wrong answer rather than a visible break.

## 3. The fix, and what it deliberately does not change

A **jump-target change**: `jr nz,oodv_as` instead of `jr nz,oo_fail_syn`, with
`oodv_as:` on the shared `oo_parse_as_chan` call. **Zero bytes** — run
`make basic-reloc`; the walls did not move.

🟢 **`LEN=` stays refused, and for free.** The terminator check after the channel
parse accepts only end-of-statement or `:`, so `OPEN"CRT:"AS #1 LEN=128` is still
`Syntax error` — which is what **both** machines answer (`w.crtlen`). The row is
there to prove the refusal survived rather than to assume it.

⚠️ **`FOR INPUT` on a device is deliberately NOT copied.** The reference answers
`<NO OUTPUT>` for `OPEN"CRT:"FOR INPUT AS #1` — the program dies or hangs — and a
hang is not a behaviour to reproduce. zerobas keeps refusing it, and the probe
carries the rows so the divergence is recorded rather than hidden.

## 4. The arm

**K-DB1** puts the `FOR OUTPUT` requirement back. Prediction **4 / 4 exact**, and
it discriminates: `w.forout` keeps its `FOR` clause and cannot move, `w.crtlen`
is refused by the terminator check rather than by this branch, and the two
`FOR INPUT` rows are already refused. 🟢 With the cut the ROM hashes **back to
the previous commit**, so the change is precisely this and nothing else.
