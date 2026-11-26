- [ ] **CTRL-C / CTRL-S DURING CONSOLE OUTPUT, AND THE LINE-EDITING KEYS THROUGH BASIC's $F37D -- NOT MEASURED (D-CTLOUTPUT,
      filed 2026-11-26 when D-BUFINCTL closed).**
      🎚️ TIER 3 — common errors: Ctrl-C is how a user stops a long `TYPE` or `DIR`; Ctrl-S pauses it.
      🤖 **AUTONOMOUS** — measure first, with the D-BUFINCTL harnesses.
      D-BUFINCTL fixed the keys at the LINE INPUT (BDOS $0A) under MSX-DOS. Not measured: (1) Ctrl-C and Ctrl-S typed
      WHILE output runs (`TYPE` of a long file, `DIR`): does the CF-3300 stop / pause, and through which call (CONST,
      the output path)? Ctrl-S at the PROMPT is stored, not a pause (AE_bufinctl_keys.out) -- so the pause, if any, is
      an output-side check. (2) The same keys through $F37D's BUFIN from a BASIC program: zerobas keeps storing them
      there (cinl_ctl tests DISKVE's high byte, 0 under BASIC); the CF-3300 under BASIC points BREAKV ($F325) into its
      own ROM, so it may treat Ctrl-C differently. Harnesses: probes/disk/disk_probe_bufinctl.py (BUFINX.COM's
      buffer) and disk_probe_dosctl.py (the session's screens and printer).
