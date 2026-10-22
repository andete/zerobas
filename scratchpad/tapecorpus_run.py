#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TAPELOAD's tape run, rebuilt and TRACKED (2026-10-22): load each tape of a pick
on the VG-8020 (the tape reference) and on zerobas's diskless machine, and compare
what is on screen. The old one-off harness and its pick (pick_martos, 51) lived in a
session scratchpad and were lost; D-TAPELOAD's standing rule -- re-run ALL the tapes
after any page-0 / page-1 layout change -- needs one that survives.

Black box only. Each title's zip is unpacked into a fresh /tmp directory (the first
.cas in it, by name); openMSX's own `autoruncassettes` types the load command; the
throttle is off; at each capture time the probe reads VRAM (16 KB), the VDP
registers, the PC and the published CURLIN ($F41C). The software is RUN, never
decoded. 🔒 The collection's location is never written into this repo: pass it as
TAPECORPUS_DIR (or --dir). The pick is scratchpad/tapecorpus_pick.list.

  per title (the last capture):
    SAME      VRAM byte-identical            NEAR  < 128 VRAM bytes apart
    RUNS?     both running (a program line, or a graphics screen), far apart
    RESET     zerobas back at its boot banner while the reference is not
    ZB-PROMPT zerobas in direct mode at a text screen, the reference running
    REF-PROMPT the reference in direct mode, zerobas running
    BOTH-PROMPT both in direct mode     ERROR a machine did not run / no .cas

    TAPECORPUS_DIR=... python3 -u scratchpad/tapecorpus_run.py [--only SUBSTR]
        [--times 60,180,300,420] [--out /tmp/tapecorpus.json] [--resume]
"""
import argparse, hashlib, json, os, shutil, signal, subprocess, sys, tempfile, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import diskcorpus_run as D  # noqa: E402  (screen_text, mode_of)
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX", shutil.which("openmsx") or "/opt/homebrew/bin/openmsx")
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
PICK = os.path.join(HERE, "tapecorpus_pick.list")


def unpack(zpath, td):
    """The first .cas in the zip (by name), copied to td; None if there is none."""
    with zipfile.ZipFile(zpath) as z:
        cas = sorted(n for n in z.namelist() if n.lower().endswith(".cas"))
        if not cas:
            return None
        out = os.path.join(td, "t.cas")
        with z.open(cas[0]) as src, open(out, "wb") as dst:
            shutil.copyfileobj(src, dst)
        return out


def run_one(machine, cas, times):
    td = tempfile.mkdtemp(prefix="tcorp_")
    try:
        out = os.path.join(td, "cap.txt")
        # the setting BEFORE the insert: given on the command line, openMSX inserted the
        # tape first and typed nothing (the smoke run: both machines at the prompt)
        # 🔴 and omsx_preflight.guarded() un-arms autorun on every launch, so -- as
        # probes/basic/basic_probe_autorun.py does -- drop its trace and insert from
        # an `after`, still long before the first prompt
        lines = ["after time 0.3 {",
                 "  trace remove execution cassetteplayer leave ::__zb_unarm",
                 "  set autoruncassettes on",
                 f"  cassetteplayer insert {{{cas}}}",
                 "}",
                 "set throttle off",
                 "proc __cap {tag} {",
                 f"  set f [open {{{out}}} a]",
                 "  binary scan [debug read_block VRAM 0 16384] H* v",
                 "  set r {}",
                 "  for {set i 0} {$i < 8} {incr i} { lappend r [vdpreg $i] }",
                 "  binary scan [debug read_block memory 0xF41C 2] H* cl",
                 "  puts $f \"$tag [reg pc] $r $cl $v\"",
                 "  close $f",
                 "}"]
        for t in times:
            lines.append(f"after time {t} {{ __cap T{int(t)} }}")
        lines.append(f"after time {times[-1] + 0.5} {{ exit }}")
        tcl = os.path.join(td, "s.tcl")
        open(tcl, "w").write("\n".join(lines) + "\n")
        cmd = [OMSX, "-machine", machine,
               "-command", "set renderer none; set sound_driver null", "-script", tcl]
        proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + 60 + times[-1] * 2
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.2)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            time.sleep(1)
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        caps = {}
        if os.path.exists(out):
            for ln in open(out):
                p = ln.split()
                caps[p[0]] = {"pc": int(p[1]), "regs": [int(x) for x in p[2:10]],
                              "curlin": int(p[10][2:4] + p[10][0:2], 16),
                              "vram": bytes.fromhex(p[11])}
        return caps or None
    finally:
        shutil.rmtree(td, ignore_errors=True)


def state(cap, banner):
    text = " ".join(D.screen_text(cap))
    if banner in text and cap["curlin"] == 0xFFFF:
        return "BANNER"
    if cap["curlin"] != 0xFFFF or D.mode_of(cap["regs"]) not in ("S0", "S1") \
            or cap["pc"] >= 0x8000:
        return "RUNNING"
    return "PROMPT"


def classify(ref, zb, last):
    if not ref or not zb or last not in ref or last not in zb:
        return "ERROR", None
    apart = sum(1 for x, y in zip(ref[last]["vram"], zb[last]["vram"]) if x != y)
    if apart == 0:
        return "SAME", 0
    if apart < 128:
        return "NEAR", apart
    sr = state(ref[last], "MSX BASIC version")
    sz = state(zb[last], "zerobas version")
    if sz == "BANNER" and sr != "BANNER":
        return "RESET", apart
    if sr == "RUNNING" and sz == "RUNNING":
        return "RUNS?", apart
    if sr == "RUNNING":
        return "ZB-PROMPT", apart
    if sz == "RUNNING":
        return "REF-PROMPT", apart
    return "BOTH-PROMPT", apart


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.environ.get("TAPECORPUS_DIR"))
    ap.add_argument("--only", default="")
    ap.add_argument("--times", default="60,180,300,420")
    ap.add_argument("--out", default="/tmp/tapecorpus.json")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if not a.dir or not os.path.isdir(a.dir):
        sys.exit("give the collection with TAPECORPUS_DIR or --dir")
    times = [float(x) for x in a.times.split(",")]
    last = f"T{int(times[-1])}"
    titles = [ln.strip() for ln in open(PICK) if ln.strip() and not ln.startswith("#")]
    titles = [t for t in titles if a.only.lower() in t.lower()]
    results, tally = [], {}
    if a.resume and os.path.exists(a.out):
        results = json.load(open(a.out))["results"]
        for r in results:
            tally[r["class"]] = tally.get(r["class"], 0) + 1
    done = {r["title"] for r in results}
    for i, t in enumerate(titles, 1):
        if t in done:
            continue
        zpath = os.path.join(a.dir, t + ".zip")
        td = tempfile.mkdtemp(prefix="tcorpz_")
        try:
            cas = unpack(zpath, td) if os.path.exists(zpath) else None
            ref = run_one(REF, cas, times) if cas else None
            zb = run_one(ZB, cas, times) if cas else None
        finally:
            shutil.rmtree(td, ignore_errors=True)
        cls, apart = classify(ref, zb, last)
        tally[cls] = tally.get(cls, 0) + 1
        row = {"title": t, "class": cls, "apart": apart,
               "ref": {k: {"pc": c["pc"], "curlin": c["curlin"], "mode": D.mode_of(c["regs"]),
                           "sha": hashlib.sha1(c["vram"]).hexdigest()[:10],
                           "text": D.screen_text(c)[-3:]} for k, c in (ref or {}).items()},
               "zb": {k: {"pc": c["pc"], "curlin": c["curlin"], "mode": D.mode_of(c["regs"]),
                          "sha": hashlib.sha1(c["vram"]).hexdigest()[:10],
                          "text": D.screen_text(c)[-3:]} for k, c in (zb or {}).items()}}
        results.append(row)
        rl, zl = row["ref"].get(last, {}), row["zb"].get(last, {})
        print(f"[{i:2d}/{len(titles)}] {cls:11s} {str(apart):>6s}  ref {rl.get('mode')} "
              f"L{rl.get('curlin')}  zb {zl.get('mode')} L{zl.get('curlin')}  {t}", flush=True)
        json.dump({"times": times, "results": results, "tally": tally}, open(a.out, "w"),
                  indent=1)
    print("TALLY", json.dumps(tally, sort_keys=True))


if __name__ == "__main__":
    main()
