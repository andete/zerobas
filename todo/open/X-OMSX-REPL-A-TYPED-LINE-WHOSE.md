- [ ] **omsx_repl: a typed line whose CHUNK ends on `\` breaks the Tcl**
      🎚️ APPARATUS —
      🤖 **AUTONOMOUS** — lifted from D-ENTRYTIERS; picked up by tier.
      `slot()` braces each chunk (`{text}`), and a chunk ending on a backslash escapes its own
      closing brace: the run dies at boot with "missing close-brace" and reads as MISSING.
      Whether a line hits it depends only on where MAX_DIRECT cuts; slotregs' SLOTCALC
      (`P\16`, `P\64`) is safe by its lengths today. Fix: split so no chunk ends on `\`
      (Tcl byte-identical for every line that does not).
      (Lifted out of D-ENTRYTIERS on 2026-11-23 when that umbrella closed.)
