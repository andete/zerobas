- [ ] 🔴 **CLEAN ROOM: PROBES RECORD REFERENCE PC VALUES -- IN TRACKED OUTPUTS AND IN THE REFERENCE CACHE (D-REFPCAUDIT,
      found 2026-11-27).**
      🎚️ APPARATUS — the clean-room rule "never record a reference PC value" (Joost 2026-11-27: "keep the rule, redact
      them" -- asked "Is sampling PC that bad really?", answered: it is the inside of the reference, and the one trace
      on record misled D-BOOTREGS, see D-BOOTP0).
      🤖 **AUTONOMOUS** — mechanical, but scope (how far, history) is Joost's.
      DONE 2026-11-27: tracked outputs redacted -- scratchpad/wboot_run.out, bootcallf_run.out (34 lines; their *_run2
      twins are zerobas-only), calculus_regs.out, basent_autoexec.out, f368bas_nodos.out, basentrun_nowaste.out (42
      lines), and 40 disk-corpus outputs (3370 lines: the reference PC -> the classifier's bucket ram / rom);
      scratchpad/diskcorpus_run.py writes only the bucket for the reference (in its Tcl: no raw value is written, cached
      or printed); ~/.cache/zerobas/diskcorpus.json's 143 rows bucketed. Audits after: PC / pc with 4 hex digits
      beside a reference name, and under a reference section header -- 0 tracked hits.
      LEFT: (1) 92 tracked probes / tools read the PC in Tcl ([reg pc]); at least 13 of them run on references
      (probes/disk/omsx_session.py -- the shared session driver --, disk_probe_diff.py, disk_probe_boot.py, biosl_run.py,
      run_programs.py, tools/ram_atlas.py, ...). Classify each: PC used only as a CONDITION on our own machine (fine),
      or WRITTEN for a reference (fix as diskcorpus_run.py: a bucket, or nothing). (2) The reference cache
      (~/.cache/zerobas/refcache): 7460 of its 11842 entries with stored outputs hold a reference PC in the decoded
      output; delete them once (1) is done, or the next runs write them again. (3) Git history keeps the redacted text;
      rewriting it is Joost's call (it would change every later hash, incl. the commits C-BIOS pins).
      (4) A static gate: a check that refuses a probe writing [reg pc] on a reference machine.
