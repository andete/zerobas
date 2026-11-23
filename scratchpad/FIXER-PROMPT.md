# Fix-agent instructions: act on a goldfish review (D-MSX2SPEC), 2026-11-23

Your prompt gives your NAME and KEY. First read /Users/joost/projects/zerobas/scratchpad/ISO-AGENT-BRIEF.md and follow it
exactly (worktree /Users/joost/projects/zerobas-iso-<NAME>, branch `iso/<NAME>`, every emulator run through
`agent_wt.py <NAME> --fresh -- ...`, links relative to the page, commits in your worktree only, never push).

The findings: /Users/joost/projects/zerobas/scratchpad/REVIEW-m2-g<KEY>.md (read it from there; do not copy it into the
repo). The pages are the ones its heading names. Verify each finding against the run files before acting -- a reviewer
can be wrong; if so, say why in your report and change nothing for it. Note which records the reviewer did NOT decode
(its top line) and check those claims yourself where a finding depends on them.

For every finding that holds:
- a wrong citation, figure or wording -> correct the page;
- a rule not pinned, or two rules the cases cannot tell apart -> if the separating case is a cheap addition (new cases in
  an existing probe, or a small new probe) MEASURE it on --row msx2all and state the result with [M]; otherwise downgrade
  the claim ([P] / [A]) and add an open row naming both rules and the separating case;
- a gap in an open list -> add the row.
When you re-run an existing probe, confirm its old cases decode as before (say so in the report). Regenerate tracked
run / decoded files you re-run. No pointless tests: measure only what decides a rule a reimplementation needs. Do not
edit docs/msx2/index.md, TODO.md, todo/, or a page outside your review. Keep DRAFT 1; add to each page's status block a
dated line "Goldfish pass 1 (test writer) 2026-11-23: N findings, M measured, K moved to open". Commit per page or per
tight group. `python3 scratchpad/linkscan.py "docs/msx2/**/*.md"` must report nothing for your pages.

Report (your final message, short): the commits; per page one line of the most important change; any finding rejected
and why; anything you could not measure. Keep it under 300 words.
