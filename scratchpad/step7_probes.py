#!/usr/bin/env python3
"""D-STEP7DATE, the raw-Tcl half of the apparatus: every disk probe that boots
zerobas with a disk in the drive types one RETURN at 4 s.

Measured with the ROM half built (scratchpad/step7b_timing.out): zerobas shows
`Enter date (M-D-Y):` by 3 s; a RETURN at 6 s had BASIC's banner up by 6.5 s. 4 s
is after the prompt (a key pressed before it is lost: the boot runs masked) and
before the 5 s memory sentinels some probes plant (a BASIC cold start after the
answer would wipe them). On today's ROM it is a blank line at the BASIC prompt.

Three shapes:
  PRE    `pre = '<cf RETURN at 11>' if cf3300 else ""`  -> else the zb RETURN
  BODY   `if cf3300: body.append(<cf RETURN>)`          -> else: the zb RETURN
  FIXED  a zerobas-only template                        -> the RETURN after `set throttle off`
lof (badfnum reuses it) was edited by hand: a RETURN at 4 s in its build_tcl's zb branch;
turning its date_prompt flag on moved every zb line 4 s later and doubled first characters.
Refuses unless every anchor occurs the expected number of times.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZB = 'after time 4 { type "\\\\r" }'            # as it reads inside a '...' literal
NOTE = "  # D-STEP7DATE: zerobas's date question"

edits = {}   # path -> [(old, new, count)]


def add(name, old, new, count=1):
    edits.setdefault(f"probes/disk/{name}", []).append((old, new, count))


PRE_OLD = "pre = 'after time 11 { type \"\\\\r\" }\\n' if cf3300 else \"\""
PRE_NEW = f"pre = ('after time 11 {{ type \"\\\\r\" }}\\n' if cf3300 else\n           '{ZB}\\n'){NOTE}"
for n in ("kill", "name", "eof", "dskf", "kill_wildcard", "files_wildcard"):
    add(f"disk_probe_{n}.py", PRE_OLD, PRE_NEW)

for n, cf in (("maxfiles", "'after time 11 { type \"\\\\r\" }')   # clear the date prompt"),
              ("filewrite", "'after time 11 { type \"\\\\r\" }')   # clear the date prompt"),
              ("merge", "'after time 11 { type \"\\\\r\" }')"),
              ("field", "'after time 11 { type \"\\\\r\" }')"),
              ("mkicvi", "'after time 11 { type \"\\\\r\" }')"),
              ("append", "'after time 11 { type \"\\\\r\" }')"),
              ("printusing_file", "'after time 11 { type \"\\\\r\" }')"),
              ("inputdollar", "'after time 11 { type \"\\\\r\" }')"),
              ("save_ascii", "'after time 11 { type \"\\\\r\" }')"),
              ("load_ascii", "'after time 11 { type \"\\\\r\" }')")):
    old = f"    if cf3300:\n        body.append({cf}\n"
    new = old + f"    else:\n        body.append('{ZB}'){NOTE}\n"
    add(f"disk_probe_{n}.py", old, new)

add("disk_probe_getput.py",
    "        body.append('after time 11 { __inj \"\" }')   # initial CR to reach the prompt\n",
    "        body.append('after time 11 { __inj \"\" }')   # initial CR to reach the prompt\n"
    "    else:\n"
    "        body.append('after time 4 { __inj \"\" }')" + NOTE + "\n")

FIX_OLD = 'f"""set throttle off\n'
FIX_NEW = 'f"""set throttle off\nafter time 4 {{ type "\\\\r" }}\n'
for n, c in (("load_disk", 1), ("load_embedded_nul", 1), ("run_disk", 1),
             ("bload_disk", 2), ("save", 3), ("files", 1)):
    add(f"disk_probe_{n}.py", FIX_OLD, FIX_NEW, c)

add("disk_probe_fileread.py",
    '    return f"""set throttle off\nset __f [open {{{out_path}}} w]\n'
    'proc __hex_v {{a l}} {{ binary scan [debug read_block VRAM $a $l] H* h; return $h }}\n'
    'after time 8  {{ type {{{line}}} }}\n',
    '    return f"""set throttle off\nset __f [open {{{out_path}}} w]\n'
    'proc __hex_v {{a l}} {{ binary scan [debug read_block VRAM $a $l] H* h; return $h }}\n'
    'after time 4 {{ type "\\\\r" }}\n'
    'after time 8  {{ type {{{line}}} }}\n')

add("disk_probe_format.py",
    "    body, t = [], 8\n",
    "    body, t = ['" + ZB + "'], 8" + "  # D-STEP7DATE: an E5-filled disk gets the date question\n")

for path, eds in edits.items():
    p = os.path.join(ROOT, path)
    s = open(p).read()
    for old, new, count in eds:
        if s.count(old) != count:
            sys.exit(f"REFUSED {path}: anchor occurs {s.count(old)}x, want {count}: {old[:70]!r}")
        s = s.replace(old, new)
    open(p, "w").write(s)
print(f"edited {len(edits)} probe(s)")
