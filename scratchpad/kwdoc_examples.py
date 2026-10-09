#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Run the example of every keyword page (docs/keywords/*.md) on zerobas AND on
the reference, and check that both print what the page says they print.

A page carries its own instructions in a metadata comment, e.g.

  <!-- example: reference=VG-8020 disk=no -->
  <!-- example: reference=CF-3300 disk=yes run=LIST answers="5|JOOST" wait=12 -->
  <!-- example: verify=no reason="needs a joystick" -->

and its `## Example` code block is: the lines a person types (each <= 39
characters), the run command (`RUN` unless `run=` says otherwise), then the
rows the screen shows, without the final prompt. `answers=` are typed after the
run command, one per `|`. Disk examples run on a private copy of
disk/test720.dsk.

Clean-room: typed BASIC in, the text screen out. No reference ROM byte is read.

  python3 -u scratchpad/kwdoc_examples.py              # every page (not README.md / about.md)
  python3 -u scratchpad/kwdoc_examples.py 'MID$' COPY  # some pages
  python3 -u scratchpad/kwdoc_examples.py --dir DIR    # pages in another folder
  python3 -u scratchpad/kwdoc_examples.py --write ...  # when both machines agree
                                                       # but the page does not,
                                                       # rewrite its output rows

Each page's screens go to scratchpad/kwdoc_<slug>.out (slug: lowercase, `$` ->
`_s`). Verdicts: PASS (both machines print the page's rows), PAGE (both agree,
the page is wrong), DIFFER (the machines disagree: a finding), NOCAP (no
screen), SKIP (verify=no), BAD (the page breaks a rule above).
Exit 0 when every page is PASS or SKIP.
"""
import glob, os, re, shlex, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

MACHINES = {  # reference name -> (reference machine, zerobas machine)
    "VG-8020": ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"),
    "CF-3300": ("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"),
}
PROMPTS = ("Ok", "ZB")      # zerobas's prompt reads `ZB` (Joost's ruling): ignored
MAXLINE = 39                # the longest line the direct-mode typist delivers


def slug(kw):
    return kw.lower().replace("$", "_s")


def parse(path):
    """-> dict(kw, meta, typed, expected, block span) or raise ValueError."""
    text = open(path).read()
    kw = os.path.basename(path)[:-3]
    m = re.search(r"<!-- example:(.*?)-->", text)
    if not m:
        raise ValueError("no `<!-- example: ... -->` metadata comment")
    meta = dict(kv.split("=", 1) for kv in shlex.split(m.group(1)) if "=" in kv)
    if meta.get("verify") == "no":
        return dict(kw=kw, meta=meta, skip=True)
    h = re.search(r"^## Example\s*$", text, re.M)
    if not h:
        raise ValueError("no `## Example` section")
    b = re.search(r"^```[^\n]*\n(.*?)^```", text[h.end():], re.M | re.S)
    if not b:
        raise ValueError("no code block under `## Example`")
    lines = b.group(1).rstrip("\n").split("\n")
    run = meta.get("run", "RUN")
    if run not in lines:
        raise ValueError(f"the run command `{run}` is not in the example block")
    k = lines.index(run)
    typed, expected = lines[:k + 1], [r.rstrip() for r in lines[k + 1:]]
    expected = [r for r in expected if r]
    long = [t for t in typed if len(t) > MAXLINE]
    if long:
        raise ValueError(f"typed line over {MAXLINE} characters: {long[0]!r}")
    if meta.get("reference") not in MACHINES:
        raise ValueError(f"reference= must be one of {sorted(MACHINES)}")
    start = h.end() + b.start(1) + sum(len(x) + 1 for x in typed)
    end = h.end() + b.end(1)
    return dict(kw=kw, meta=meta, skip=False, typed=typed, expected=expected,
                run=run, span=(start, end), text=text)


def screen_out(screen, run):
    """The rows the program printed: after the run command's row, prompts,
    blank rows and the function-key row (the last) left out."""
    if screen is None:
        return None
    rows = [screen[i:i + 40].rstrip() for i in range(0, len(screen), 40)][:-1]
    if run in rows:
        rows = rows[rows.index(run) + 1:]
    return [r for r in rows if r and r not in PROMPTS]


def run_page(p):
    ref, ours = MACHINES[p["meta"]["reference"]]
    disk = p["meta"].get("disk") == "yes"
    answers = [a for a in p["meta"].get("answers", "").split("|") if a]
    step = 4.5 if disk else 3.0
    wait = float(p["meta"].get("wait", 30.0 if disk else 8.0))
    got, raw = {}, {}
    for side, machine in (("reference", ref), ("zerobas", ours)):
        kw = dict(batch=False, reset=("", "SCREEN 0:WIDTH 40"), step=step,
                  run_gap=max(wait, step * (len(answers) + 1) + 3))
        if disk:
            dsk = probe_tmp.tmp(f"kwdoc_{slug(p['kw'])}_{machine}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            kw.update(diska=dsk, boot=14.0)
        scr = omsx_repl.run_cases(machine, [("direct", p["typed"] + answers)], **kw)[0]
        raw[side] = (machine, scr)
        got[side] = screen_out(scr, p["run"])
    return got, raw


def main(argv):
    write = "--write" in argv
    argv = [a for a in argv if a != "--write"]
    d = os.path.join(REPO, "docs", "keywords")
    if "--dir" in argv:
        i = argv.index("--dir")
        d = argv[i + 1]
        del argv[i:i + 2]
    pages = sorted(p for p in glob.glob(os.path.join(d, "*.md"))
                   if os.path.basename(p) not in ("README.md", "about.md"))
    if argv:
        pages = [p for p in pages if os.path.basename(p)[:-3] in argv]
    tally = {}
    for path in pages:
        kw = os.path.basename(path)[:-3]
        try:
            p = parse(path)
        except ValueError as e:
            print(f"=== {kw}: BAD {e}", flush=True)
            tally.setdefault("BAD", []).append(kw)
            continue
        if p["skip"]:
            print(f"=== {kw}: SKIP ({p['meta'].get('reason', 'no reason given')})", flush=True)
            tally.setdefault("SKIP", []).append(kw)
            continue
        got, raw = run_page(p)
        a, b = got["reference"], got["zerobas"]
        if a is None or b is None:
            verdict = "NOCAP"
        elif a != b:
            verdict = "DIFFER"
        elif a != p["expected"]:
            verdict = "PAGE"
        else:
            verdict = "PASS"
        out = os.path.join(REPO, "scratchpad", f"kwdoc_{slug(kw)}.out")
        with open(out, "w") as fh:
            for side in ("reference", "zerobas"):
                machine, scr = raw[side]
                fh.write(f"--- {kw}: {side} {machine}\n")
                if scr is None:
                    fh.write("<NO CAPTURE>\n")
                else:
                    rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)]
                    fh.write("\n".join(r for r in rows if r) + "\n")
            fh.write(f"=== {kw}: {verdict}\n")
        print(f"=== {kw}: {verdict}", flush=True)
        if verdict in ("PAGE", "DIFFER"):
            print("  page:      " + " | ".join(p["expected"]))
            print("  reference: " + " | ".join(a))
            print("  zerobas:   " + " | ".join(b))
        if verdict == "PAGE" and write:
            s, e = p["span"]
            new = p["text"][:s] + "".join(r + "\n" for r in a) + p["text"][e:]
            open(path, "w").write(new)
            print("  page rewritten from the measured screen")
        tally.setdefault(verdict, []).append(kw)
    print("\n" + "  ".join(f"{k} {len(v)}" for k, v in sorted(tally.items())))
    for k in ("PAGE", "DIFFER", "NOCAP", "BAD"):
        if k in tally:
            print(f"{k}: {' '.join(tally[k])}")
    return 0 if set(tally) <= {"PASS", "SKIP"} else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
