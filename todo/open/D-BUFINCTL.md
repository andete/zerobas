- [ ] 🐛 **CTRL-C AND CTRL-P DO NOTHING IN THE BDOS LINE INPUT: THEY ARE STORED AS CHARACTERS (D-BUFINCTL, found
      2026-11-26 by D-DISKCONTRACT gap 5).**
      🎚️ TIER 3 — common errors: Ctrl-C at A> is how a user abandons a line; under MSX-DOS 1 the line input (BDOS $0A,
      BUFIN) is the disk ROM's.
      🤖 **AUTONOMOUS** — the probe and its gate exist; the fix needs disk-ROM room first.
      MEASURED (`make dosctl-acceptance`, probes/disk/disk_probe_dosctl.py, scratchpad/AE_dosctl2.out): at A> after
      MODE 40, both machines with the printer logger plugged --
      * `DIR` (no Enter) then Ctrl-C: the CF-3300 echoes `^C`, and a fresh `A>` follows; zerobas shows nothing.
      * Ctrl-P, `DIR`: the CF-3300 also PRINTS the listing (1689 B to the printer); zerobas prints nothing.
      * Ctrl-P again, `TYPE HELLO.TXT`: the CF-3300 types the file; zerobas prints NOTHING -- the stray Ctrl-P is part
        of the command line COMMAND.COM then parses.
      CAUSE (by reading, disk/runtime.asm conin_line_body): only CR and BS are handled; every other code is stored and
      echoed, Ctrl-C ($03) and Ctrl-P ($10) included.
      FIX DIRECTION: in conin_line_body, Ctrl-C -> echo `^C` + CR LF and abandon (what MSX-DOS 1 does next -- a warm
      start of COMMAND.COM, as the fresh `A>` suggests -- to be MEASURED first: registers / the jump at $0000); Ctrl-P ->
      toggle a printer-echo flag that conout_body honours (LPTOUT beside CHPUT). Ctrl-S (pause), Ctrl-N, Ctrl-U / X
      (cancel the line) and Ctrl-C during OUTPUT (CONST) are NOT measured yet -- measure them with the same harness
      before the fix. The disk ROM has ~0 B usable (docs/disk/port-readiness.md row 5): carve first.
      The gate pins the four rows (ctrlc, ctrlp, type2, printer) as KNOWN differences; a fix turns it red until the
      pin is dropped.
      📏 EVERY LINE-EDITING KEY ON THE CF-3300, one key per boot: `AB`, the key, `CD`, the line read after each
      ([AE_bufinctl_keys.out](../../scratchpad/AE_bufinctl_keys.out), 2026-11-26) -- the spec the fix copies:
      Ctrl-C `AB^C`, newline, fresh `A>` (abandoned) · Ctrl-U and ESC erase the line (`A>`, then `A>CD`) · Ctrl-H
      backspace (zerobas matches) · Ctrl-E and Ctrl-S echo as caret + letter and stay (`AB^ECD`; Ctrl-S does NOT
      pause at the prompt) · Ctrl-R and Ctrl-N: nothing visible (`ABCD`) · Ctrl-X: nothing visible, but the NEXT key
      is swallowed (`ABD`) -- not understood; measure what the buffer holds before copying it.
      Joost 2026-11-26: "I think we need to fix D-BUFINCTL probably" -- next after the disk-ROM re-read finds room.
