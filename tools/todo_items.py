#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""todo_items -- the roadmap as ONE FILE PER ITEM (Joost 2026-11-23: "do the one-file-per-item switch").

Layout:
  TODO.md                 the SKELETON: the headings and prose of the roadmap, and one stub line per item --
                          `- [ ] **<title>** -> [<id>](todo/open/<id>.md) <!-- item:open/<id> -->` -- in the
                          items' order. It is generated from the item files (`python3 tools/todo_items.py --index`,
                          also run by the pre-commit hook); hand edits go into the item files and the prose.
  todo/open/<id>.md       one open item: its text VERBATIM, from its `- [ ]` line on (body lines indented as
                          before). <id> is its D- name, or a slug of its title.
  todo/done/<id>.md       a closed item (`- [x]`) still listed in TODO.md.

full_text() rebuilds the old single-file TODO.md exactly -- each stub line replaced by its item file -- so a tool
that parsed the single file reads full_text() instead and sees the same text (that equality is the migration's
proof: scratchpad/todo_split.py). locate(n) maps a line number of that text to (file, line) for messages.

    python3 tools/todo_items.py --index     # rewrite TODO.md's stub lines from the item files (titles, open / done)
    python3 tools/todo_items.py --check     # exit 1 if a stub names a missing file or a file has no stub
    python3 tools/todo_items.py --full      # print the rebuilt single-file text
    python3 tools/todo_items.py --new D-X --after D-Y < item.md   # file a new open item, its stub after D-Y's
    python3 tools/todo_items.py --close D-X # [x], todo/open/D-X.md -> todo/done/, its stub updated
    python3 tools/todo_items.py --fix-links # links written from the repo root -> relative to the item file

LINKS in an item file are relative to THE FILE (`../../scratchpad/x.out`), like every docs page; --check refuses one
written from the repo root (the form it had in the single-file TODO.md), --new and --fix-links rewrite them.

EDITING: an item is edited in its file (todo/open/<id>.md); the prose and the order of the stubs in TODO.md by hand;
the stub lines themselves are generated (--index, and the pre-commit hook does it on any staged todo/**.md).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODO = os.path.join(ROOT, "TODO.md")
DIR = os.path.join(ROOT, "todo")
STUB = re.compile(r"<!-- item:(open|done)/([A-Za-z0-9][A-Za-z0-9._-]*) -->\s*$")
ITEM_START = re.compile(r"^- \[([ xX])\] ")


class Item:
    def __init__(self, state, ident, text):
        self.state, self.id, self.text = state, ident, text

    @property
    def path(self):
        return os.path.join(DIR, self.state, self.id + ".md")

    @property
    def rel(self):
        return f"todo/{self.state}/{self.id}.md"

    @property
    def is_open(self):
        return self.state == "open"

    def title(self):
        """the item's bold title, flattened to one line"""
        m = re.search(r"\*\*(.+?)\*\*", self.text.replace("\n", " "), re.S)
        t = m.group(1) if m else self.text.split("\n", 1)[0]
        return re.sub(r"\s+", " ", t).strip()


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def skeleton():
    return _read(TODO)


def items():
    """the items in the skeleton's order"""
    out = []
    for line in skeleton().split("\n"):
        m = STUB.search(line)
        if m:
            p = os.path.join(DIR, m.group(1), m.group(2) + ".md")
            out.append(Item(m.group(1), m.group(2), _read(p)))
    return out


def full_text():
    """the old single-file TODO.md, rebuilt: every stub line replaced by its item's text"""
    parts = []
    for line in skeleton().split("\n"):
        m = STUB.search(line)
        if m:
            txt = _read(os.path.join(DIR, m.group(1), m.group(2) + ".md"))
            parts.append(txt[:-1] if txt.endswith("\n") else txt)
        else:
            parts.append(line)
    return "\n".join(parts)


def locate(lineno):
    """a 1-based line of full_text() -> (repo-relative file, 1-based line in it)"""
    n = 0
    for sl, line in enumerate(skeleton().split("\n"), 1):
        m = STUB.search(line)
        if m:
            rel = f"todo/{m.group(1)}/{m.group(2)}.md"
            k = _read(os.path.join(ROOT, rel)).rstrip("\n").count("\n") + 1
            if n < lineno <= n + k:
                return rel, lineno - n
            n += k
        else:
            n += 1
            if n == lineno:
                return "TODO.md", sl
    return "TODO.md", lineno


LINK = re.compile(r"(\]\(<?)([^)>#\s]+)")


def _link_path(t):
    return re.sub(r":\d+(?:-\d+)?$", "", t)


def root_links(text):
    """links in an item that resolve from the REPO ROOT but not from todo/<state>/ -- the form an item had while it
    lived in the root TODO.md (the split moved ~1,400 of them two directories down, 2026-11-23)"""
    out = []
    for m in LINK.finditer(re.sub(r"`[^`\n]*`", "", re.sub(r"```.*?```", "", text, flags=re.S))):
        t = m.group(2)
        if re.match(r"[a-z]+:", t) or t.startswith(("/", "../")):
            continue
        if os.path.exists(os.path.join(ROOT, _link_path(t))) and not os.path.exists(os.path.join(DIR, "open", _link_path(t))):
            out.append(t)
    return out


def fix_links(text):
    """prefix `../../` to every root-relative link (root_links) outside code spans"""
    bad = set(root_links(text))
    if not bad:
        return text
    parts = re.split(r"(```.*?```|`[^`\n]*`)", text, flags=re.S)
    for i in range(0, len(parts), 2):
        parts[i] = LINK.sub(lambda m: m.group(1) + ("../../" + m.group(2) if m.group(2) in bad else m.group(2)), parts[i])
    return "".join(parts)


def write_item(item, text):
    with open(item.path, "w", encoding="utf-8") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")


def stub_line(item):
    box = "x" if item.state == "done" else " "
    t = item.title()
    if len(t) > 110:
        t = t[:107].rstrip() + "..."
    t = t.replace("*", "")
    return f"- [{box}] **{t}** -> [{item.id}]({item.rel}) <!-- item:{item.state}/{item.id} -->"


def write_index():
    """rewrite each stub line from its item file (the title may have changed)"""
    lines = skeleton().split("\n")
    for i, line in enumerate(lines):
        m = STUB.search(line)
        if m:
            it = Item(m.group(1), m.group(2), _read(os.path.join(DIR, m.group(1), m.group(2) + ".md")))
            lines[i] = stub_line(it)
    new = "\n".join(lines)
    if new != skeleton():
        with open(TODO, "w", encoding="utf-8") as fh:
            fh.write(new)
        return True
    return False


def check():
    bad = []
    named = set()
    for line in skeleton().split("\n"):
        m = STUB.search(line)
        if m:
            rel = f"todo/{m.group(1)}/{m.group(2)}.md"
            named.add(rel)
            if not os.path.isfile(os.path.join(ROOT, rel)):
                bad.append(f"stub names a missing file: {rel}")
    for st in ("open", "done"):
        d = os.path.join(DIR, st)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            rel = f"todo/{st}/{f}"
            if f.endswith(".md") and rel not in named:
                bad.append(f"item file with no stub in TODO.md: {rel}")
            if f.endswith(".md"):
                first = _read(os.path.join(d, f)).split("\n", 1)[0]
                m = ITEM_START.match(first)
                if not m:
                    bad.append(f"{rel}: does not start with an item line `- [ ] ` / `- [x] `")
                elif (m.group(1) == " ") != (st == "open"):
                    bad.append(f"{rel}: its box `[{m.group(1)}]` does not match its folder {st}/")
                rl = root_links(_read(os.path.join(d, f)))
                if rl:
                    bad.append(f"{rel}: {len(rl)} link(s) written from the repo root ({rl[0]} ...) -- an item file lives "
                               f"in todo/{st}/: `python3 tools/todo_items.py --fix-links`")
    return bad


def _stub_index(lines, ident):
    for i, line in enumerate(lines):
        m = STUB.search(line)
        if m and m.group(2) == ident:
            return i, m.group(1)
    return None, None


def new_item(ident, after, text):
    """file a new open item: todo/open/<ident>.md := text (must start `- [ ] `), its stub right after <after>'s"""
    if not ITEM_START.match(text) or not text.startswith("- [ ] "):
        sys.exit("todo_items --new: the text must start with `- [ ] `")
    if os.path.exists(os.path.join(DIR, "open", ident + ".md")) or os.path.exists(os.path.join(DIR, "done", ident + ".md")):
        sys.exit(f"todo_items --new: {ident} exists already")
    lines = skeleton().split("\n")
    i, _ = _stub_index(lines, after)
    if i is None:
        sys.exit(f"todo_items --new: no stub for {after} to file it after")
    text = fix_links(text)
    it = Item("open", ident, text)
    write_item(it, text)
    lines.insert(i + 1, stub_line(it))
    with open(TODO, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"filed {it.rel} after {after}")


def close_item(ident):
    """close an open item: its box -> [x], the file moved to todo/done/, its stub updated"""
    src = os.path.join(DIR, "open", ident + ".md")
    if not os.path.isfile(src):
        sys.exit(f"todo_items --close: no todo/open/{ident}.md")
    text = _read(src).replace("- [ ] ", "- [x] ", 1)
    it = Item("done", ident, text)
    os.makedirs(os.path.dirname(it.path), exist_ok=True)
    write_item(it, text)
    os.remove(src)
    lines = skeleton().split("\n")
    i, _ = _stub_index(lines, ident)
    if i is not None:
        lines[i] = stub_line(it)
        with open(TODO, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    print(f"closed: {it.rel} (stage the removal of todo/open/{ident}.md too: `git add -u todo`)")


def main(argv):
    if "--new" in argv:
        # todo_items.py --new ID --after OTHER-ID < text   (the item's text on stdin, from its `- [ ] ` line)
        ident = argv[argv.index("--new") + 1]
        after = argv[argv.index("--after") + 1] if "--after" in argv else sys.exit("--new needs --after OTHER-ID")
        new_item(ident, after, sys.stdin.read())
        return 0
    if "--close" in argv:
        close_item(argv[argv.index("--close") + 1])
        return 0
    if "--fix-links" in argv:
        n = 0
        for it in items():
            new = fix_links(it.text)
            if new != it.text:
                write_item(it, new)
                n += 1
        print(f"todo_items: links fixed in {n} item file(s)")
        return 0
    if "--index" in argv:
        print("TODO.md: stubs rewritten" if write_index() else "TODO.md: stubs current")
        return 0
    if "--check" in argv:
        bad = check()
        for b in bad:
            print("🔴", b)
        print(f"todo_items: {len(items())} items, {len(bad)} problem(s)")
        return 1 if bad else 0
    if "--full" in argv:
        sys.stdout.write(full_text())
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
