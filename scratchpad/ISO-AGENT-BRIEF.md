# Brief for a parallel MSX2-spec agent (D-MSX2SPEC), 2026-11-23

You measure a few MSX2 / MSX2+ BIOS call pages, raising each from DRAFT 0 to DRAFT 1, in YOUR OWN isolated
zerobas instance. Other agents are doing the same at the same time in their own instances.

## Your instance

- Worktree: `/Users/joost/projects/zerobas-iso-<NAME>` (NAME is given in your prompt). It already exists at the
  current HEAD. Work and edit ONLY there. NEVER edit, stage or commit in `/Users/joost/projects/zerobas` (the main
  checkout) or in any other `zerobas-iso-*`.
- Run every emulator command through the wrapper, from anywhere:
  `python3 /Users/joost/projects/zerobas-iso-<NAME>/tools/agent_wt.py <NAME> --fresh -- python3 -u probes/bios/biosl_run.py probes/bios/spec/<probe>.asm --row msx2all > scratchpad/AE_<probe>_msx2.out 2>&1`
  (cwd of COMMAND = your worktree; `--fresh` = empty clock-chip/persistent state, so readings are reproducible.)
  Redirect to a file and READ the file; never `| tail` a probe.
- NEVER run `probes/basic/basic_probe_cas_verify.py` or `basic_probe_cas_match_cf3300.py` (they kill every openMSX
  on the host). Never `pkill`/`kill` openmsx or a python parent. Do not run `make gates*`, `tools/gate_wt.py`,
  `run_gates.py`, or anything in `../zerobas-gate` -- the lead gates your commits.
- `timeout` does not exist on this host.

## 🔴 CLEAN ROOM (absolute)

Registers, RAM addresses, work-area RAM contents, I/O ports, VDP/VRAM state and slot state are READABLE. NEVER read a
ROM byte of a reference machine, follow a hook target, single-step into ROM or disassemble; NEVER read the bytes of a
reference's RAM-resident code. Behaviour is learnt only from what a call does to registers / RAM / VRAM / ports.
A call that plays / copies / reads "from an address" (PCMPLY, the BLT calls, LDIRMV-likes ...) reads whatever is
mapped there DURING the call, which may be a ROM even if the caller sees RAM: give such calls sources in page 2 / 3 RAM
or VRAM only, NEVER page 0 / 1 (incident 2026-11-23, docs/clean-room-audit.md).

## Method -- read these first

1. `docs/spec-method.md` (the whole thing: page format, [M]/[P]/[A] tags, executable rules §3a, the loop §5,
   the stopping test §7, the test audit §8 -- no pointless tests).
2. A finished example unit: commit `6c9dfd3c7` (`git show 6c9dfd3c7`): `docs/msx2/sub/DSPFNK.md`,
   `probes/bios/spec/xsubfnk.asm`, `scratchpad/AE_xsubfnk_msx2.out`. Also look at 2-3 other
   `probes/bios/spec/xsub*.asm` for the probe idioms (EXTROM $015F with IX = entry for sub-ROM calls; H.KEYI guard;
   restoring VDP registers per case) and `probes/bios/biosl_run.py`'s docstring for the directives (@caplen,
   @vdpfull, @portlog, @type-ready, ...).
3. `docs/msx2/index.md` and the existing DRAFT 1 pages near yours, for tone and the "Differences" section.

References = Sony HB-F900 (msx2jp), Philips NMS 8250 (msx2eu), Panasonic FS-A1WSX (msx2p); subject = C-BIOS's own
MSX2 builds (CBIOS2_CUR_*). `--row msx2all` runs all three pairs. Joost's ruling: NOTHING is assumed unchanged from an
earlier generation -- measure it.

Per page: write a probe (`probes/bios/spec/<name>.asm`) -- `ls` the path AS ITS OWN COMMAND first; the name must be
free -- run it, decode, then update the page: DRAFT 0 -> DRAFT 1 with the date 2026-11-23, every claim tagged and
cited to the run file, the C-BIOS differences in "Differences". If the three references disagree with each other,
say so on the page per reference. If something cannot be measured with the current harness, say exactly what is
missing and leave that part [P]/unmeasured rather than guessing. Do NOT edit `probes/bios/biosl_run.py` unless your
prompt says you own it.

## Links and new pages (added after the first batch)

- Links are RELATIVE TO THE PAGE'S OWN FILE. From `docs/msx2/sub/X.md` a probe is `../../../probes/bios/spec/<probe>.asm`
  and a run file `../../../scratchpad/AE_<probe>_msx2.out` (THREE `../`; the first batch's pages used two and were broken).
  Check: `python3 scratchpad/linkscan.py "docs/msx2/**/*.md"` must list nothing for your pages.
- A page that DOES NOT EXIST yet: create it modelled on a finished sibling (e.g. docs/msx2/sub/DSPFNK.md, also an
  entry C-BIOS lacks): header with address / ROM / standard / where it is listed, the [M]/[P]/[A]-tagged sections,
  "Differences", "Open". The index row (docs/msx2/index.md) already links it; do not edit the index.

## Committing (in YOUR worktree)

- `git switch -c iso/<NAME>` once, then one commit per finished page (or per tight group), staging EXPLICIT paths
  (`git add -A` is banned): the probe, the run file `scratchpad/AE_<probe>_msx2.out`, the page, any decoder script you
  cite. Do not touch `TODO.md`, `todo/`, `docs/bios/index.md` or other generated pages -- the lead does the
  bookkeeping.
- Message in a FILE (`scratchpad/commitmsg-<NAME>.txt`), `git commit -F`, first line
  `D-MSX2SPEC: <CALL> measured -- <one-line finding>`, body = what was measured and found, then a blank line and
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Check `git show --stat HEAD` after.
- The pre-commit hook may regenerate a page; that is fine. Never push.

## Report back (your final message)

Per page: DRAFT level reached, the commit hash, the finding in one or two lines, every C-BIOS difference (wrong
result / missing behaviour), any reference-vs-reference disagreement, and anything you could NOT measure and why.
