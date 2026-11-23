- [ ] **D-DOCLINKS — ~3,400 RELATIVE LINKS IN TOP-LEVEL docs/*.md AND ~900 IN scratchpad/*.md DO NOT RESOLVE FROM THEIR OWN FILE; NO GATE CHECKS LINKS**
      🎚️ TIER 6 — doc debt, no behaviour. Measured 2026-11-23 with `python3 scratchpad/linkscan.py` (strips `:line`
      suffixes, skips code spans): of 5,906 broken links in tracked markdown, almost all in top-level docs/*.md (3,432)
      and scratchpad/*.md (893) are written FROM THE REPO ROOT (`scratchpad/x.out` in docs/spec-*.md), which a renderer
      resolves from the file's own directory -- 3,413 of the docs/ ones resolve from the root. The spec pages under
      docs/<area>/ (bios, keywords, concepts, msx2) already link relative to the file and resolve.
      Found while fixing two breakages of my own the same day (both fixed in the same commit as this item): the TODO
      split moved ~1,400 root-relative links two directories down (`tools/todo_items.py --fix-links`; `--check`, so the
      pre-commit hook, now refuses a root-relative link in an item file), and ~160 links in docs/msx2/ one `../` short.
      🔴 No gate caught either: `check_citation_paths.py` matches the TEXT `scratchpad/<name>` wherever it sits, so a
      link can be broken and still "resolve" there.
      To do: (1) decide with the next touch whether top-level docs/*.md links go file-relative (`../scratchpad/...`) --
      mechanical, like --fix-links; (2) a `doc-link-check` gate over docs/** (and todo/**) using linkscan's rule, with
      the pre-existing set pinned until (1) lands.
