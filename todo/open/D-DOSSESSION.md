- [ ] **D-DOSSESSION — MSX-DOS COMMANDS AS TYPED SESSIONS ON THE CF-3300 AND ZEROBAS: THE SCREEN AFTER EACH COMMAND, THE DISK AFTER THE SESSION**
      🎚️ TIER 1 — Joost 2026-11-23, the order "3, 2, 1": this first, then D-MSX2SPEC, then D-KWSPEC.
      🤖 **AUTONOMOUS** — Not spec pages per command: COMMAND.COM / MSXDOS.SYS are Microsoft's, loaded from the user's
      disk (docs/concepts/msx-dos.md); zerobas supplies the disk ROM, the BDOS and the boot. An integration suite instead:
      the reference DOS disk (test.dsk, MSX-DOS 1.03 / COMMAND 1.08) + a known text file, typed commands at A> (DIR,
      DIR /W, TYPE, COPY, REN, DEL, VERIFY, DATE, MODE, ...), the text screen compared after each, the disk's directory
      and file bytes compared after the session -- the National CF-3300 against zerobas's disk machine. Template:
      probes/disk/disk_probe_dosmode.py. The commands that reach zerobas's OWN code (BASIC, FORMAT's H.FORM, the boot)
      get rules on the disk pages.
      ✅ STEP 1 (2026-11-23 / 11-25): probes/disk/disk_probe_dossession.py, gate `dossession-acceptance` (in the
      battery since 2026-11-25): DIR, DIR /W, TYPE, COPY, COPY a+b, REN, DEL (and of a missing file), TYPE of a missing
      file, VERIFY ON, DATE (and setting it), REM, an unknown command -- the screen after each and the disk's directory
      and file bytes after the session, the CF-3300 against zerobas's disk machine: 20 / 20 SAME
      (scratchpad/AE_dossession_run4.out). It found D-COPYDATE (fixed 2026-11-25). The session sets MODE 40 first:
      the start-up screen is the host's ($7D2F; JP SCREEN 1 on the CF-3300, EU TEXT1 here), scored against the
      VG-8020 + HBD-F1 by dosmode-acceptance, so `boot` / `date` are printed here and scored there.
      ➡️ LEFT: (a) the commands that reach zerobas's OWN code -- BASIC typed at A> (the hand-over to Disk BASIC) and
      FORMAT (H.FORM's dialogue) -- with rules on the disk pages; (b) the disk row leaves the directory's date / time
      out ("neither machine has a clock") -- both machines are deterministic (1984-01-01 or the date the session set),
      and D-COPYDATE showed the DIR screen was the only witness of a date, so the disk row should compare them too.
      ✅ (b) DONE 2026-11-25: the disk row compares each entry's date and time words too (both machines are
      deterministic), and prints the listing it compared on agreement, so the agreement can be read
      (scratchpad/AE_dossession_dates.out: HELLO.TXT $14A5 = 1990-05-05, CAT.TXT -- COPY a+b -- the current $0821 on
      both, MSXDOS.SYS its own); 20 / 20. LEFT: (a) BASIC and FORMAT typed at A>.
      ✅ (a) DONE 2026-11-25 (scratchpad/AE_dossession_basic.out, 21 / 21): BASIC typed at A> -- its screen differs by
      design (zerobas's banner, "ZB"), so the row after it is scored by its values, HIMEM / FRE(0) / FRE(""): DE77 23430
      200 on both. FORMAT at A> is fmtdos-acceptance's (D-DOSFORMAT). 🔴 AND A ROW SET THAT AGREED FOR THE WRONG REASON:
      `dateset` typed "11-23-87", which both machines answer "Invalid date" (their order is Y-M-D), so REM and the
      unknown command were typed INTO the still-open date prompt and agreed there since 2026-11-23. Now "87-11-23", and
      every agreeing row prints its last two screen lines as a witness (the date taken, "A>REM A REMARK", "Bad command
      or file name"). D-DOSSESSION's own scope is done; what is left is the disk pages' rules for BASIC / FORMAT
      (D-DISKCONTRACT).
