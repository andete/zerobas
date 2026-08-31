# D-MUSICF — a PLAY naming fewer voices silenced nothing and stopped everything

*2026-08-31. `sub/playparse.asm` (`pt_commit`). Probe
`scratchpad/musicf_probe.py`, 5 rows × 3 machines. **+2 B sub page 1.**
Found by a code-review pass over the PLAY implementation, then measured —
the row came second, but it came before the fix.*

## 1. The defect

`pt_commit` published the new statement's voice set with a **wholesale store**:

```
ld a,(AUDIO_VMASK)
ld (MUSICF),a
```

`MUSICF`'s bits are *per-voice* "queue active" flags that the H.TIMI servicer
drains. A `PLAY "E"` issued while voice B was still sounding from an earlier
`PLAY "…","…"` therefore **cleared B's bit mid-note**, with three linked
consequences:

1. B's drain stops — its queue is abandoned.
2. `psv_end` (the **only** writer of amplitude 0 for that channel) becomes
   unreachable — the channel keeps sounding at its last amplitude, forever.
3. `PLAY(2)` reports **idle under an audible tone** — the inverse of the filed
   start-up-window divergence.

## 2. Measured before the fix

| row | | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `ctl.idle` | no PLAY | 0 | 0 | 0 ✅ |
| `ctl.play2` | PLAY A+B, read `PLAY(2)` mid-music | −1 | −1 | −1 ✅ |
| `r.drop` | …then `PLAY "C"`, read `PLAY(2)` | **−1** | **−1** | **0** 🔴 |
| `r.keep1` | same, read `PLAY(1)` | −1 | −1 | −1 ✅ |

Both references keep the unmentioned voice playing. The 16 s `L1` fixture is
what makes "still playing" a stable reading against the harness's inter-line
pacing — and what separates this cleanly from the start-up-window item
(`tools/filed-row-known.txt`, `playfn_fixture_probe`), which lives on a
one-statement timescale with *no* string for the read voice.

## 3. The fix

OR the new set in; unmentioned voices keep draining:

```
ld a,(AUDIO_VMASK)
ld hl,MUSICF
or (hl)
ld (hl),a
```

Exact, not approximate: a voice being **replaced** is in both masks (its ring
was rebuilt by `pt_buf`), and the drain is suspended for the whole tenant call
(`htimi_guard`), so there is no torn read. "MUSICF set LAST" is preserved.

## 4. After: 5/5 SAME — and the completion row was wrong twice first

`r.drop` reads −1 on all three. A fifth row, `r.done`, proves the fixed drain
still *finishes* (reaches `psv_end`, silences the channel, drops the bit):
short music + a delay, then `PLAY(2)` = 0 everywhere.

That row shipped wrong twice, both the **echo-fence** class:

- 16 s fixture + 18 s `FOR`: **all three** sides read the string `";PLAY(2);"`
  — the probe's own typed line as a value. A three-way agreement on garbage is
  an agreement of silences.
- Retimed to ~3.5 s: the references cleared their pacing and **zerobas alone**
  still fenced — a one-sided echo-fence that *reads exactly like a regression*.

The row now runs on its own ~1 s timescale, inside every side's pacing.

## 5. Gates

`scratchpad/musicf_probe.py` 5/5 SAME · `make play-acceptance` and
`make play-trace-acceptance` (the heavy VG-8020 differentials over the same
subject) · full battery. The review that found this also filed three
unmeasured corners (16-bit `pt_number` wrap-around aliasing into range,
edge-of-range accidental clamps, `M0`) — those are TODO items, not this fix.
