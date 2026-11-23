- [ ] **D-DOSSESSION — MSX-DOS COMMANDS AS TYPED SESSIONS ON THE CF-3300 AND ZEROBAS: THE SCREEN AFTER EACH COMMAND, THE DISK AFTER THE SESSION**
      🎚️ TIER 1 — Joost 2026-11-23, the order "3, 2, 1": this first, then D-MSX2SPEC, then D-KWSPEC.
      🤖 **AUTONOMOUS** — Not spec pages per command: COMMAND.COM / MSXDOS.SYS are Microsoft's, loaded from the user's
      disk (docs/concepts/msx-dos.md); zerobas supplies the disk ROM, the BDOS and the boot. An integration suite instead:
      the reference DOS disk (test.dsk, MSX-DOS 1.03 / COMMAND 1.08) + a known text file, typed commands at A> (DIR,
      DIR /W, TYPE, COPY, REN, DEL, VERIFY, DATE, MODE, ...), the text screen compared after each, the disk's directory
      and file bytes compared after the session -- the National CF-3300 against zerobas's disk machine. Template:
      probes/disk/disk_probe_dosmode.py. The commands that reach zerobas's OWN code (BASIC, FORMAT's H.FORM, the boot)
      get rules on the disk pages.
