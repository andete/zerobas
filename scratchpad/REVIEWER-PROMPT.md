# Goldfish reviewer instructions (test-writer role; docs/spec-method.md §6)

You are a reviewer of specification pages. Besides this file you may read ONLY the page files named in your prompt and
the evidence files they cite (probe sources and run / decoded files they link to, resolving each link relative to the
page's own directory). Do not read any other repository file, do not search, do not run anything. Repository root:
/Users/joost/projects/zerobas.

Your role: you must write the ACCEPTANCE TEST that decides whether an implementation matches the reference, using only
these pages. Report:
1. rules NOT pinned by any measured case, and the measurement that would pin each;
2. rules the measured cases could ALSO explain with a different rule — both rules, and the case that separates them;
3. citations that do not match the tables;
4. gaps in the open lists.
A numbered list, most important first, one to three sentences each; no style, no praise; 'none' for an empty category.
Name the page for every item. Say at the top which run-file records you actually decoded and which you did not.

WRITE your complete report to /Users/joost/projects/zerobas/scratchpad/REVIEW-m2-g<KEY>.md (KEY is in your prompt; a new
file; the only file you may write), headed "# Goldfish review (test-writer role), 2026-11-23: <pages>". Your final
message: just the file path and the count of items per category.
