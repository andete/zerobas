# D-CLAMPPITCH — an edge accidental wraps the semitone inside the octave, and two rules coincided on every edge row

*2026-08-31. `sub/playparse.asm` (`pt_note_letter`). Probe
`scratchpad/clamppitch_probe.py` (PSG-trace method, 8 rows × 2 machines);
fast-layer vectors in `tests/test_play_parse.py`. Closes the residual
[spec-basic-playcorner.md](spec-basic-playcorner.md) §1 left open.*

## 1. The question D-PLAYCORNER could not answer

Its screen rows showed `O1 C-` and `O8 B#` are *accepted* on both references —
but not **which pitch** they play. This tree clamped the note number (`C-`@O1 →
note 0 = C1, `B#`@O8 → note 95 = B8). The trace says the reference does
something else entirely:

| fixture | reference plays | this tree played |
|---|---|---|
| `O1 D C- D` | **B1** (period 1812) | C1 (3421) 🔴 |
| `O8 A B# A` | **C8** (27) | B8 (14) 🔴 |

## 2. Two rules coincided on every edge row

`C-`@O1 → B1 fits **both** "the semitone wraps mod 12 inside the octave" *and*
"borrow the octave, then clamp the octave to 1" — B0 does not exist, so the
edge rows cannot separate them. The mid-octave rows do
([[two-rules-that-coincide-on-every-row-you-have]]):

| fixture | mod-12 predicts | borrow predicts | reference plays |
|---|---|---|---|
| `O4 D C- D` | B4 (227) | B3 (453) | **227** |
| `O4 A B# A` | C4 (428) | C5 (214) | **428** |

**The accidental wraps the semitone mod 12 and the octave never moves** — at
the edges and mid-range alike. `C-` is B of the *same* octave (a seventh up);
`B#` is C of the *same* octave (a seventh down). So the divergence was never an
edge case: it fired at **every** octave boundary crossing, and D-PLAYCORNER's
accept/reject rows were blind to it by construction.

## 3. The fix

`pt_note_letter` now applies the accidental to the **semitone** (0..11) with a
mod-12 wrap *before* adding the octave base. The result is `(octave−1)·12 +
0..11` = 0..95 by construction, so the old edge clamp is unreachable and is
**deleted rather than kept as dead reassurance**.

## 4. After

- `clamppitch_probe`: **8/8 identical sequences** on both machines.
- Fast layer: new vectors pin the mid-octave cases too (the coinciding-rules
  lesson written into the test), `test_play_parse.py` ALL PASS.
- `musicf_probe` 5/5, `playcorner_probe` 10/10, `play-acceptance`,
  `play-trace-acceptance`, full battery.

## 5. Method note

Third PLAY slice in one evening, all from one review: the statement-review
tier (TODO.md "STANDING TIER") found D-MUSICF and D-PLAYCORNER by reading; this
one existed only because D-PLAYCORNER *named its own blindness* — "whether the
reference plays the same pitch needs a trace row, not a screen read" — and the
named hole was the finding.
