#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""todo_split -- ONE-OFF: split the single-file TODO.md into todo/open/<id>.md / todo/done/<id>.md and a skeleton
TODO.md with one stub line per item (tools/todo_items.py's layout; Joost 2026-11-23).

An item: a column-0 `- [ ]` / `- [x]` line and every following line that is indented, or blank with an indented line
after it; it ends at the next column-0 non-blank line. Its id: the first D-NAME in its first three lines, else a slug
of its title (X-...), made unique. PROOF: tools/todo_items.full_text() must equal the original byte for byte, and
todo_items.check() must be clean -- otherwise everything written is removed again and the script exits 1.

    python3 scratchpad/todo_split.py            # split (refuses if todo/ exists)
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import todo_items  # noqa: E402

ID = re.compile(r"\bD-([A-Z0-9]+(?:-[A-Z0-9]+)*)")


def slug(text):
    m = re.search(r"\*\*(.+?)\*\*", text.replace("\n", " "))
    words = re.findall(r"[A-Za-z0-9]+", (m.group(1) if m else text))[:6]
    return "X-" + "-".join(w.upper() for w in words) if words else "X-ITEM"


def main():
    if os.path.exists(todo_items.DIR):
        sys.exit("todo/ exists already -- refusing")
    orig = open(todo_items.TODO, encoding="utf-8").read()
    lines = orig.split("\n")
    out, seen, made = [], set(), []
    i = 0
    while i < len(lines):
        m = todo_items.ITEM_START.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        j = i + 1
        while j < len(lines):
            if lines[j][:1] in (" ", "\t"):
                j += 1
                continue
            if lines[j] == "":
                k = j
                while k < len(lines) and lines[k] == "":
                    k += 1
                if k < len(lines) and lines[k][:1] in (" ", "\t"):
                    j = k
                    continue
            break
        block = "\n".join(lines[i:j])
        # the id only from the bold TITLE: "Filed by D-X" / "split from D-X" in the first lines name a PARENT (the
        # first run gave nine items their parent's name, D-ENTRYTIERS-2 .. -6)
        mt = re.search(r"\*\*(.+?)\*\*", block.replace("\n", " "))
        mi = ID.search(mt.group(1)) if mt else None
        base = ("D-" + mi.group(1)) if mi else slug(block)
        ident, n = base, 2
        while ident in seen:
            ident, n = f"{base}-{n}", n + 1
        seen.add(ident)
        state = "open" if m.group(1) == " " else "done"
        it = todo_items.Item(state, ident, block)
        os.makedirs(os.path.dirname(it.path), exist_ok=True)
        with open(it.path, "w", encoding="utf-8") as fh:
            fh.write(block + "\n")
        made.append(it)
        out.append(todo_items.stub_line(it))
        i = j
    with open(todo_items.TODO, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    rebuilt = todo_items.full_text()
    bad = todo_items.check()
    if rebuilt != orig or bad:
        with open(todo_items.TODO, "w", encoding="utf-8") as fh:
            fh.write(orig)
        shutil.rmtree(todo_items.DIR)
        for b in bad[:10]:
            print("🔴", b)
        if rebuilt != orig:
            a, b = orig.split("\n"), rebuilt.split("\n")
            k = next((x for x in range(min(len(a), len(b))) if a[x] != b[x]), min(len(a), len(b)))
            print(f"🔴 the rebuilt text differs from line {k + 1}: {a[k:k + 1]!r} vs {b[k:k + 1]!r}")
        sys.exit("todo_split: REVERTED -- nothing changed")
    n_open = sum(1 for x in made if x.is_open)
    print(f"todo_split: {len(made)} items ({n_open} open, {len(made) - n_open} done) -> todo/; TODO.md "
          f"{len(orig)} -> {len(open(todo_items.TODO).read())} bytes; full_text() == the original: OK")


if __name__ == "__main__":
    main()
