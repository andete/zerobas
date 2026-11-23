- [ ] **D-FMTERR — FORMAT'S DIALOGUE OFF THE HAPPY PATH IS UNMEASURED (filed 2026-11-11 by
      D-DSKFMT's close)**
      🎚️ TIER 6 — every error: a key outside A / B or 1..4, a write-protected disk, Ctrl-STOP
      at each prompt, from MSX-DOS's `format` and from CALL FORMAT.
      🤖 **AUTONOMOUS** — probes/disk/fmtdos_acceptance.py's screen-polled steps drive both
      machines; compare what each prints and what the disk holds afterwards. Today a failed
      format is main's `load error` from CALL FORMAT (the old disposition).
