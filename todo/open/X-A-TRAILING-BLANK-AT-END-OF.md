- [ ] **A TRAILING BLANK at end of line is not measurable through the keyboard.**
      Found 2026-07-31 in D-DECBLANK (`dec-eol` / `dec-eolctl`, both
      informational **by construction**). At `--repeat 2` the references drop a
      trailing blank and zerobas keeps it — in a `REM` tail as well as after a
      literal, and a `REM` tail is **verbatim**, so the difference is at **line
      ENTRY** (the editor), not in any scanner.
      ⚠️ But an earlier `--repeat 1` pass read the same `REM` row on zerobas
      *without* the blank, for a payload no crunch change can touch — so the cell
      is not stable enough to ground a rule, only to be filed.
      ⚠️ **The echo guard cannot referee it**: `echo_missing()` `rstrip`s every
      screen row, so a trailing blank is invisible to the guard no matter what the
      machine did with it, and a payload whose delivery cannot be verified may not
      gate. Resolving the cell needs a delivery path that bypasses the line editor
      — an ASCII `LOAD"CAS:`, the way `basic_probe_floatlit.py` reaches literals.
      Detail: [`docs/decblank-msx1-characterization.md`](docs/decblank-msx1-characterization.md) §5.
      ✅ **THE GROUND TRUTH IS MEASURED, 2026-09-05 (D-TRAILBLANK,
      `scratchpad/trailblank_probe.py`) — the entry's own suggested path, built.**
      An `$EA` ASCII program on tape, `LOAD"CAS:"`, and the readout is the
      TOKENISED PROGRAM at TXTBASE via `debug read_block` — **bytes, not a
      screen, so nothing rstrips anything.** Same payload path on all three
      machines; only the COMMAND differs (typed on the VG-8020 and zerobas,
      shipped as an `AUTOEXEC.BAS` on a disk for the CF-3300, whose date prompt
      hijacks the keyboard — the disk carries the command, never the payload).
      | line | delivered | vg8020 | cf3300 | zb |
      |---|---|---|---|---|
      | `10 REM HELLO ` | verbatim | `<8F> HELLO ` | same | same |
      | `20 A=1 ` | verbatim | `A<EF><12> ` | same | same |
      🎯 **ALL THREE KEEP THE TRAILING BLANK, in the `REM` tail AND after a
      literal.** So **the tokeniser is innocent on every machine** — "not in any
      scanner" is no longer a suspicion, it is a reading, and the crunch cannot
      be where the typed-path difference comes from.
      ⚠️ **What that does NOT do is establish the editor**, and this entry is the
      reason to be careful: its own second paragraph records the typed-path cell
      as unstable (`--repeat 1` read the `REM` row WITHOUT the blank on zerobas,
      for a payload no crunch change can touch). So the pair is
      "scanner: measured identical" + "editor: an unstable reading" — the
      difference itself needs re-establishing before anyone chases the editor,
      and this run deliberately does not lean on the unstable half.
      🎁 **AND THE GATING OBJECTION IS ANSWERED TOO.** *"A payload whose delivery
      cannot be verified may not gate"* was true of the KEYBOARD path; this one is
      verified by construction — the bytes are read out of memory, and the two
      informational rows could become scored rows through it. Not built here.
      🎚️ APPARATUS — keyboard measurability
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
