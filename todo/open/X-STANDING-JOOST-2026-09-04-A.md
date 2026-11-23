- [ ] 🔁 **STANDING (Joost, 2026-09-04): A PURELY STYLISTIC ORACLE SPLIT GOES TO
      THE VG-8020, ON BOTH TARGETS.** *"when there is stylish differences (color,
      screen) between the oracles, pick the VG8020"*. So a references-split row
      that is only presentational is neither a NO-ORACLE park nor a per-target
      answer: the VG-8020 value ships everywhere, including the disk build whose
      oracle is otherwise the CF-3300. **The point is that a cosmetic split must
      not fork the ROMs** — the first such row, `KEY`'s F6 default (`color
      15,4,4` vs `color 15,4,7`), would otherwise have made the two targets
      differ in shipped DATA rather than only in the disk ROM's presence.
      ⚠️ **SCOPE, as given: colour and screen.** It does NOT cover splits that
      exist because the CF-3300 has **Disk BASIC** — those are capability
      differences and each target still follows its own oracle. Measured examples
      of the distinction, all in
      [`probes/basic/basic_probe_pusing.py`](../../probes/basic/basic_probe_pusing.py):
      `PRINT USING"&";…` and `"\ \"` print on the VG-8020 and are ERR 5 on the
      CF-3300 — Disk BASIC, **not covered**. And `PRINT USING"$$#";5` reads
      `  $5` vs `$$ 5`, which is formatting rather than colour or screen —
      **outside the words as given, so not assumed covered; ask before
      extending.**
      ⚠️ **IT DECIDES THE VALUE, NEVER WHETHER TO MEASURE.** A split still has to
      be read off both machines first; this only says which reading ships.
      🔁 STANDING — a ruling of Joost's, kept open so it stays visible. NOT
      pickable work: the /loop reads it, it does not do it.
      🎚️ STANDING — ruling
