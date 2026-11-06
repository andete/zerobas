#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Typed sessions (D-SESSIONS, 2026-11-06): the program ladder's other half.

The ladder (run_programs.py) loads a finished program from tape and RUNs it, so
everything a user does AT THE PROMPT -- typing lines in, AUTO, RENUM, DELETE,
LIST, editing a line by retyping it, STOP and CONT, NEW, MERGE -- is never
exercised end to end. A session is that: a file of lines TYPED at the prompt,
one at a time, on the reference and on zerobas, with the text screen captured
after every step.

    probes/sessions/S<n>_<name>.ses
      # a comment line (not typed)
      # @DISK          (first lines only) the CF-3300 + the DISK target, a
      #                private copy of an empty 720 KB disk in drive A
      10 PRINT "HI"    typed, then RETURN
      {STOP}           Ctrl-STOP held 0.2 s (keyboard matrix: CTRL row 6
                       bit 1, STOP row 7 bit 4)
      {CTRLC}          Ctrl-C ($03) into the keyboard buffer -- ends AUTO
      {WAIT 2}         let 2 emulated seconds pass before the next step
      {UP}{DOWN}{LEFT}{RIGHT}{INS}{DEL}{BS}{HOME}{CR}{ESC}  inline: that key
      ...{NOCR}        (at the end of a line) type it WITHOUT the RETURN

A step is typed only when the machine is IDLE: the keyboard buffer is empty
(GETPNT == PUTPNT) and CURLIN has held one value for 0.7 s since the last key.
A long line goes in 30-character pieces, each into an empty buffer (the
injector's limit is 39). So a session must not hold a program on ONE line
for long (`10 GOTO 10` looks idle): give it a {STOP} or keep loops short.

Compared, step by step: the text screen after each step settles (rows,
trailing blanks dropped; zerobas's `ZB` prompt reads as `Ok`), then the
printer log (LLIST / LPRINT), which never scrolls away. The first step whose
screen differs names the command that diverged.

Clean-room: keys in (the keyboard buffer and the key matrix); the text screen,
the printer port and work-area RAM (CURLIN, GETPNT/PUTPNT, SCRMOD, TXTNAM)
out. No reference ROM byte is read.

    python3 -u probes/programs/run_sessions.py            # every session
    python3 -u probes/programs/run_sessions.py S1_editor  # some (substring)
    ... --keep=DIR   # every snapshot and the printer log, per machine, in DIR
"""
import glob, os, re, shutil, signal, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)
import omsx_preflight                                # noqa: E402
import probe_tmp                                     # noqa: E402
from omsx_run import _tcl_dquote                     # noqa: E402
from omsx_repl import key_proc                       # noqa: E402
import run_programs as rp                            # noqa: E402

SESSIONS = os.path.join(REPO, "probes", "sessions")
LIMIT = 600.0      # emulated seconds
CHUNK = 30

TCL = r"""
set throttle off
set printerlogfilename {LOG}
plug printerport logger
DATEWATCH
KEYPROC
proc __rd16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
proc __scr {} {
  set nam [expr {[debug read memory 0xFCAF] == 1 ? [__rd16 0xF3BD] : [__rd16 0xF3B3]}]
  binary scan [debug read_block VRAM $nam 960] a* t
  return $t
}
set ::__f [open {OUT} w]
fconfigure $::__f -translation binary
proc __snap {tag} {
  set w [expr {[debug read memory 0xFCAF] == 1 ? 32 : 40}]
  puts $::__f "@@STEP $tag t=[format %.1f [machine_info time]] w=$w"
  puts $::__f [__scr]
  flush $::__f
}
# steps: {kind arg idle} -- kind K (inject the string), S (Ctrl-STOP), W (wait
# arg seconds); idle 1 = wait for an idle machine first and snapshot before it
set ::__steps [list STEPS]
set ::__ph 0
set ::__ff 0
set ::__cl -1
set ::__clt 0
set ::__lastk 0
set ::__n 0
set ::__waitto 0
# IDLE also needs the SCREEN to say so (S5: zerobas's FILES was still reading the
# directory 0.7 s after the key, CURLIN steady at $FFFF, and the snapshot caught a
# blank row): the last non-blank row is the prompt (`Ok` / `ZB`), or the screen
# has not changed for $::__still s (an AUTO number, an INPUT `?`, a program's wait).
# 🔴 AND THE PROMPT MUST HAVE BEEN STILL FOR 0.3 s: a read DURING a scroll (the
# copy moves the rows one at a time) shows a row twice -- S5's `MERGE "SUBS"`
# appeared doubled on zerobas while a CHPUT trace had it printed ONCE
# (scratchpad/mergeecho_trace.py): the `Ok` was already the last row, the scroll
# after its CR LF was half done.
set ::__ls ""
set ::__lst 0
proc __atprompt {t w} {
  set last ""
  # the function-key line is the bottom row while CNSDFG ($F3DE, published) is
  # set: skip it, or it is ALWAYS the last non-blank row and no prompt is ever
  # seen (every command then waited out the stillness fallback)
  set rows [expr {[debug read memory 0xF3DE] ? 23 : 24}]
  for {set r 0} {$r < $rows} {incr r} {
    set row [string trim [string map [list \xff " "] [string range $t [expr {$r * $w}] [expr {$r * $w + $w - 1}]]]]
    if {$row ne ""} { set last $row }
  }
  expr {$last eq "Ok" || $last eq "ZB"}
}
proc __idle {} {
  set w [expr {[debug read memory 0xFCAF] == 1 ? 32 : 40}]
  set t [__scr]
  if {$t ne $::__ls} { set ::__ls $t; set ::__lst [machine_info time] }
  expr {[__rd16 0xF3FA] == [__rd16 0xF3F8]
        && [machine_info time] - $::__clt >= 0.7
        && [machine_info time] - $::__lastk >= 0.7
        && [machine_info time] >= $::__waitto
        && (([__atprompt $t $w] && [machine_info time] - $::__lst >= 0.3)
            || [machine_info time] - $::__lst >= $::__still)}
}
# how long a still screen counts as idle, set per step: a numbered line is stored
# with no prompt (0.7 s), a direct command must reach the prompt and is given 5 s
# of stillness only as a fallback (the CF-3300's SAVE keeps the screen still for
# over 2 s before its Ok)
set ::__still 0.7
proc __poll {} {
  set cl [__rd16 0xF41C]
  if {$cl != $::__cl} { set ::__cl $cl; set ::__clt [machine_info time] }
  if {$::__ph == 0} {
    # booted: the prompt (CURLIN = $FFFF) held for 2 s
    if {$cl == 0xFFFF} { incr ::__ff } else { set ::__ff 0 }
    # a disk session waits past the date answers too: run_programs' DATE_TCL types
    # RETURN at 6 s and 10 s BLINDLY, and on a fast-booting target the second one
    # landed in the session as a stray empty line (S5's first DIFF)
    if {$::__ff >= 20 && [machine_info time] > MINSTART} { set ::__ph 1 }
  } elseif {[llength $::__steps] == 0} {
    if {[__idle]} { __snap END; close $::__f; exit }
  } else {
    set s [lindex $::__steps 0]
    lassign $s kind arg idle
    set go 0
    if {$idle} { set go [__idle] } else { set go [expr {[__rd16 0xF3FA] == [__rd16 0xF3F8]}] }
    if {$go} {
      if {$idle} { __snap [incr ::__n] }
      set ::__steps [lrange $::__steps 1 end]
      set ::__still [expr {[regexp {^[0-9]} $arg] ? 0.7 : 5.0}]
      switch $kind {
        K { __key $arg }
        S {
          keymatrixdown 6 0x02
          keymatrixdown 7 0x10
          after time 0.2 { keymatrixup 7 0x10; keymatrixup 6 0x02 }
        }
        W { set ::__waitto [expr {[machine_info time] + $arg}] }
      }
      set ::__lastk [machine_info time]
    }
  }
  if {[machine_info time] > LIMIT} { __snap TIMEOUT; close $::__f; exit }
  after time 0.1 __poll
}
after time 0.5 __poll
"""


# inline key names: the screen editor's control codes (MSX2 Technical Handbook,
# the CHGET codes of the cursor / edit keys)
KEYS = {"UP": "\x1e", "DOWN": "\x1f", "RIGHT": "\x1c", "LEFT": "\x1d", "INS": "\x12",
        "DEL": "\x7f", "BS": "\x08", "HOME": "\x0b", "CR": "\r", "ESC": "\x1b"}


def parse(text):
    """-> (disk, steps): steps are (kind, arg, idle) tuples."""
    # a CLS first, never compared: the boot banner differs by design (zerobas
    # names itself), and it would stay on the screen through the first steps
    disk, steps = False, [("K", "CLS\r", 1)]
    for line in text.splitlines():
        if line.startswith("#"):
            disk = disk or "@DISK" in line
            continue
        m = re.fullmatch(r"\{WAIT ([0-9.]+)\}", line.strip())
        if m:
            steps.append(("W", m.group(1), 1))
        elif line.strip() == "{STOP}":
            steps.append(("S", "", 1))
        elif line.strip() == "{CTRLC}":
            steps.append(("K", "\x03", 1))
        else:
            s = line
            nocr = s.endswith("{NOCR}")
            if nocr:
                s = s[:-len("{NOCR}")]
            for k, v in KEYS.items():
                s = s.replace("{%s}" % k, v)
            s += "" if nocr else "\r"
            for i in range(0, len(s), CHUNK):
                steps.append(("K", s[i:i + CHUNK], 1 if i == 0 else 0))
    if disk:
        # the CF-3300 boots in its 32-column text mode, the DISK target in the
        # VG-8020's SCREEN 0 / WIDTH 37 -- a STYLE split, ruled to the VG-8020
        # (Joost 2026-09-04) -- so a disk session starts from the same screen
        steps[0] = ("K", "SCREEN 0:WIDTH 37:CLS\r", 1)
    return disk, steps


def run(machine, name, text):
    disk, steps = parse(text)
    log = probe_tmp.tmp(f"ses_{machine}_{name}.lpt")
    out = probe_tmp.tmp(f"ses_{machine}_{name}.txt")
    tcl = probe_tmp.tmp(f"ses_{machine}_{name}.tcl")
    for p in (log, out):
        if os.path.exists(p):
            os.unlink(p)
    st = " ".join("{" + " ".join((k, _tcl_dquote(a) if k == "K" else (a or "-"), str(i))) + "}"
                  for k, a, i in steps)
    open(tcl, "w").write(TCL.replace("{LOG}", "{" + log + "}").replace("{OUT}", "{" + out + "}")
                         .replace("STEPS", st).replace("KEYPROC", key_proc())
                         .replace("DATEWATCH", rp.DATE_TCL if disk else "")
                         .replace("LIMIT", str(LIMIT))
                         .replace("MINSTART", "10.5" if disk else "0"))
    cmd = [rp.OMSX, "-machine", machine, "-command",
           "set renderer none; set sound_driver null", "-script", tcl]
    if disk:
        dsk = probe_tmp.tmp(f"ses_{machine}_{name}.dsk")
        subprocess.run([sys.executable, os.path.join(REPO, "tools", "make_test_dsk.py"),
                        "--empty", dsk], check=True, capture_output=True)
        cmd += ["-diska", dsk]
    proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 600
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    lpt = open(log, "rb").read().decode("latin-1") if os.path.exists(log) else ""
    snaps = []
    if os.path.exists(out):
        raw = open(out, "rb").read().decode("latin-1")
        for part in raw.split("@@STEP ")[1:]:
            head, _, scr = part.partition("\n")
            w = int(head.rsplit("w=", 1)[1])
            rows = [scr[i:i + w].replace("\xff", " ").rstrip(" \0") for i in range(0, min(len(scr), 24 * w), w)]
            # the prompt: zerobas prints `ZB` where the reference prints `Ok` (the
            # row carries the WIDTH 37 margin, so compare it trimmed)
            # (also when the screen editor has typed over the rest of that row:
            # `ZB        NEW` is the prompt row with text written into it)
            rows = [r.replace("ZB", "Ok", 1) if r.strip() == "ZB" or r.strip().startswith("ZB ")
                    else r for r in rows]
            while rows and not rows[-1]:
                rows.pop()
            snaps.append((head.split()[0], head, rows))
    return snaps, lpt, steps


def label(steps, n):
    """The text of the step whose RESULT snapshot n (1-based) shows: snapshot n
    is taken just before idle step n runs, i.e. after idle step n-1."""
    groups = []
    for k, a, f in steps:
        txt = {"K": a, "S": "{STOP}", "W": "{WAIT %s}" % a}[k]
        if f or not groups:
            groups.append(txt)
        else:
            groups[-1] += txt
    if n < 2:
        return "(boot)"
    if n - 2 >= len(groups):
        return "(end)"
    t = groups[n - 2].replace("\r", "").replace("\x03", "{CTRLC}")
    for k, v in KEYS.items():
        if v != "\r":
            t = t.replace(v, "{%s}" % k)
    return t


def main():
    pats = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = sorted(glob.glob(os.path.join(SESSIONS, "S*.ses")))
    if pats:
        # a path to a .ses anywhere (a scratch session, never part of the gate), or
        # a name substring of the committed ones
        files = ([p for p in pats if p.endswith(".ses") and os.path.exists(p)] or
                 [f for f in files if any(p in os.path.basename(f) for p in pats)])
    bad = 0
    for f in files:
        name = os.path.basename(f)[:-4]
        text = open(f).read()
        disk, _ = parse(text)
        ref = rp.DISK_REF if disk else rp.REF
        zbs = rp.DISK_ZB if disk else rp.ZB
        rs, rl, steps = run(ref, name, text)
        keep = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--keep=")), None)

        def dump(m, snaps, lpt):
            if not keep:
                return
            os.makedirs(keep, exist_ok=True)
            with open(os.path.join(keep, f"{name}.{m}.txt"), "w") as fh:
                for i, (tag, head, rows) in enumerate(snaps):
                    fh.write(f"=== snapshot {tag} after {label(steps, i + 1)!r}  [{head}]\n")
                    fh.write("\n".join(rows) + "\n")
                fh.write("=== printer\n" + lpt)
        dump(ref, rs, rl)
        print(f"== {name}: {len(steps)} steps; {ref}: {len(rs)} snapshots, last {rs[-1][1] if rs else 'NONE'}")
        for zb in zbs:
            zs, zl, _ = run(zb, name, text)
            dump(zb, zs, zl)
            first = None
            # snapshot 1 is the boot screen and snapshot 2 the runner's own CLS:
            # the comparison starts at the session's first typed step's result
            for i in range(2, max(len(rs), len(zs))):
                a = rs[i][2] if i < len(rs) else None
                b = zs[i][2] if i < len(zs) else None
                if a != b:
                    first = i
                    break
            same_lpt = rl == zl
            verdict = "SAME" if first is None and same_lpt else "DIFF"
            bad += verdict != "SAME"
            print(f"   {zb:30} {verdict}  ({len(zs)} snapshots, last {zs[-1][1] if zs else 'NONE'}; "
                  f"printer {'same' if same_lpt else 'DIFFERS'})")
            if first is not None:
                n = first
                tag = rs[n][0] if n < len(rs) else zs[n][0]
                print(f"   first screen difference at snapshot {tag}, after: {label(steps, n + 1)!r}")
                a = rs[n][2] if n < len(rs) else []
                b = zs[n][2] if n < len(zs) else []
                for j in range(max(len(a), len(b))):
                    x = a[j] if j < len(a) else ""
                    y = b[j] if j < len(b) else ""
                    print(f"     {'  ' if x == y else '!!'} ref |{x}")
                    if x != y:
                        print(f"        zb  |{y}")
            if not same_lpt:
                rl_l, zl_l = rl.splitlines(), zl.splitlines()
                for j in range(max(len(rl_l), len(zl_l))):
                    x = rl_l[j] if j < len(rl_l) else "<none>"
                    y = zl_l[j] if j < len(zl_l) else "<none>"
                    if x != y:
                        print(f"   printer line {j + 1}: ref {x!r} / zb {y!r}")
                        break
    print("ALL SAME" if not bad else f"{bad} DIFF")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
