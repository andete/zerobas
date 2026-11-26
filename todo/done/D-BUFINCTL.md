- [x] 🐛 **CTRL-C AND CTRL-P DO NOTHING IN THE BDOS LINE INPUT: THEY ARE STORED AS CHARACTERS (D-BUFINCTL, found
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
      ✅ **FIXED 2026-11-26.** The buffer each key leaves, both machines (BUFINX.COM, one key between `AB` and `CD`;
      [AE_bufinctl_buf.out](../../scratchpad/AE_bufinctl_buf.out), [AE_bufinctl_buf2.out](../../scratchpad/AE_bufinctl_buf2.out)): Ctrl-X drops itself AND the next key (^X^X CD ->
      `ABCD`); Ctrl-E / Ctrl-S stored; Ctrl-R / Ctrl-N dropped; Ctrl-U / ESC erase the line; Ctrl-P is dropped and
      turns the printer echo on -- the CF-3300's flag is $F23B 0 -> 1, Ctrl-N back to 0 ([AE_prnflag.out](../../scratchpad/AE_prnflag.out)), the cell
      COMMAND.COM's DIR already reads (M27) -- and the rest of the line reaches the printer; Ctrl-C abandons the program.
      The fix (disk/kernel.asm cinl_ctl / cinl_echo, disk/runtime.asm conin_line_body / conout_not_dispatch), under
      MSX-DOS only (DISKVE's high byte, as bdos_dskio): the keys as measured; a stored control key echoes as `^E`;
      console output goes to the printer while $F23B = 1 (exactly 1: BASIC keeps the RAM fill $FF there). Ctrl-C:
      `^C` (no CR LF -- with one, a blank row more than the CF-3300), then the warm boot (`jp $0000`, as bdos_dskio's
      Abort). Entering the handler BREAKV ($F325 -> $D611 -> $D76D on both, [AE_breakv.out](../../scratchpad/AE_breakv.out)) from inside the call
      HUNG after the ^C ([AE_bufctl_dosctl1.out](../../scratchpad/AE_bufctl_dosctl1.out)). 142 B of the re-read's room, then 2 B back.
      Gates: new `make bufinctl-acceptance` (11 rows SAME, [AE_bufctl_probe1.out](../../scratchpad/AE_bufctl_probe1.out)); `make dosctl-acceptance` every
      row SAME, its four pins dropped ([AE_bufctl_dosctl4.out](../../scratchpad/AE_bufctl_dosctl4.out)) -- the printer log 1689 B on both, byte-identical.
      Left, filed as [D-CTLOUTPUT](../open/D-CTLOUTPUT.md): Ctrl-C / Ctrl-S during OUTPUT, and these keys through BASIC's $F37D.
