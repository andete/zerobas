# D-REPOINTMARK — the citation opt-out marker, honoured by the REWRITER too

**2026-09-01.** Closes the residual filed at `../TODO.md:5671 (T-B42BAC)`, whose own candidate was *"an explicit escape the tools honour ... plus a gate arm that a
marked example survives `--fix`"*. Half of that had already shipped and the item
did not know it; the other half was a live hole with five exposed lines.

## What was already true, and what was not

`check_todo_citations.py` grew `NOCITE = "NOT-A-CITATION"` in D-FILEDROT: `scan()`
skips any line carrying it, and `--fix` runs off `scan()`, so a marked example
already survived the fixer. Arm `S-NOCITE` checks both directions on the same
line of the same file. **Re-run before building on it**, not read:

```
$ python3 tools/check_todo_citations.py --selftest
selftest: GREEN control passes and a planted drift goes RED on
TODO.md:<the line, elided: quoting it here would make this doc a citation
the fixer repoints, which is the very defect below> (T-6FE392);
NOT-A-CITATION suppresses 2 citation(s) there and nothing else ✅
```

So the filed sentence *"neither the fixer nor `todo-citation-check` has a way to
mark one inert"* was **stale on both of its names**. What it missed is that the
repo has a **second** citation rewriter — `tools/split_todo_archive.py`'s
`repoint()` — and the marker meant nothing there.

## The hole, measured before it was fixed

`repoint()` did `CITE.sub(sub, txt)` over the **whole file text**. A whole-text
substitution cannot see which line a match landed on, so the marker was not
merely unimplemented there — it was **unimplementable in that shape**. Sweeping
the tracked tree for lines that carry the marker *and* match the repointer's own
`CITE`:

| exposed line | what it is |
|---|---|
| `tools/split_todo_archive.py:199` | the comment explaining the backtracking bug |
| `tools/split_todo_archive.py:328` | arm **S1**'s message |
| `tools/split_todo_archive.py:331` | arm **S2**'s *input* vector |
| `tools/split_todo_archive.py:332` | arm **S2**'s *expected* vector |
| `tools/split_todo_archive.py:335` | arm **S3**'s vector |

**Five, all in the rewriter's own file.** The next `--apply` would have repointed
its own test fixtures.

🔴 **AND ONE OF THE FIVE CORRUPTS SILENTLY.** S2 and S3 would have gone *red* —
rewriting `TODO.md:2811` to a form carrying ` (T-…)` makes `CITE` stop matching <!-- NOT-A-CITATION -->
it, so the assertions break loudly. But **S1's fixture asserts `== []`**, and a
rewritten citation is still `[]`. Its meaning would be destroyed while the arm
stayed green — which is precisely the failure mode the marker was invented to
stop, reappearing one file over.
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]

## The fix

Substitution moves **per line**, with the marked line returned byte-identical,
in a helper `_repoint_text(txt, sub_for_line)` that `repoint()` calls.

🎯 **THE HELPER WAS FACTORED FOR THE ARM, NOT FOR TIDINESS.** Inline in
`repoint()` — which shells out to `git ls-files` and writes real tracked files —
the only way to check the exemption is to read it, and reading is what missed the
defect the first time. `_append_or_write` exists in the same file for the same
reason.

Two consequences worth naming:

* `in_href` is now computed against the **line** rather than the whole text.
  These differ only for a `](` at the end of the *previous* line. Measured across
  the tree: **12 citations match the repointer's `CITE`, and the two readings
  disagree on 0 of them.**
* `n_cites` now counts **rewrites, not matches** — a marked line is a match this
  pass deliberately leaves alone, and reporting it as repointed would restate the
  old behaviour in the log.

## Arms (`--selftest`, collected by `make selftest-check`)

`S8` an unmarked citation is still rewritten · `S9` a marked line comes back
byte-identical · `S10` the marker is **line-scoped**, not file-scoped.

Falsified by planting, both directions on the same apparatus:

| plant | S8 | S9 | S10 |
|---|---|---|---|
| exemption removed (whole-text behaviour) | PASS | 🔴 | 🔴 |
| exemption unconditional (skip everything) | 🔴 | PASS | 🔴 |
| shipped | PASS | PASS | PASS |

**S8 is the load-bearing one.** An exemption scored only against a line nothing
would have rewritten passes for free; without the control, plant B ships. S10 is
what neither single-direction plant survives.

Fixtures are assembled by concatenation, so no literal citation exists in the
file for the *other* rewriter to repoint — the same discipline S1 already used.

## The marker in a Markdown file

This doc is the first `.md` to need it, and it needs it **twice** — once for the
quoted selftest banner, once for S2's vector in the table above. Two spellings,
picked by where the text sits:

* **In prose**, an HTML comment on the same line: `<!-- NOT-A-CITATION -->`.
  Renders as nothing, and both tools are line-scoped so it reaches the citation
  beside it.
* **Inside a fenced block**, neither tool's marker nor an HTML comment can go in
  without falsifying the quote — so the line number is **elided in place, and the
  elision says why**. A quoted tool banner is a transcript; annotating it is
  worse than trimming it.

🔴 **THE HAZARD IS RECURSIVE, AND THAT IS NOT A JOKE.** A document explaining
that citations-quoted-as-examples get rewritten is itself made mostly of
citations quoted as examples. The first draft of this file shipped three of them,
one of which the checker had already silently adopted as live.
