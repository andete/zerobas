#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""agent_wt -- run anything in an ISOLATED zerobas: its own git worktree, its own openMSX home (machine configs,
settings, and PERSISTENT state -- the clock chip's battery memory, SRAM), its own temp root.

Joost 2026-11-23: "having that isolation possible is interesting to have of its own, it means we can isolately run
some test if needed" -- and it lets several agents probe at once, each in its own instance.

    python3 tools/agent_wt.py NAME [--rev REV] [--reset] [--fresh] -- COMMAND ...   # run COMMAND in the instance
    python3 tools/agent_wt.py NAME --env                                  # print the instance's env (to source)
    python3 tools/agent_wt.py NAME --rm                                   # remove the instance

The instance lives at ../zerobas-iso-NAME (a detached worktree at REV, default HEAD; created once, kept between
runs; --reset re-checks it out at REV). Its openMSX home is <worktree>/.omsx-home: `share/` seeded as tools/gate_wt.py
seeds a gate's (machine configs rewritten to the worktree's own build, settings.xml copied, the rest linked) and an
EMPTY `persistent/`, so nothing a run saves reaches the user's ~/.openMSX or another instance. --fresh empties it
again (the old one moves to persistent.prev): a run that must not see what an earlier run saved -- an MSX2's
clock-chip settings decide its boot screen -- starts from it. ZEROBAS_TMP is /tmp/zerobas/iso-NAME (under
probe_tmp's root). COMMAND runs with cwd = the worktree; build there first (`make repack-machine`) -- it is a fresh
checkout.

MEASURED 2026-11-23: probes/bios/spec/xsubbox.asm --row msx2all run solo in one
instance and then in two instances AT ONCE gives three byte-identical files; ~/.openMSX/persistent untouched, all
seven machines' CMOS files in the instance's. And the same probe run against ~/.openMSX differs from a --fresh run in
two Sony HB-F900 reference bytes: a reading CAN depend on the clock-chip state a previous session left behind.

Still shared between instances: the host CPU (emulated time is unaffected; wall-clock subprocess timeouts may need
slack under load) and the two tape probes that `pkill -9 openmsx` host-wide (probes/basic/basic_probe_cas_verify.py,
basic_probe_cas_match_cf3300.py) -- run those alone.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import gate_wt  # noqa: E402
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402 -- the instance's temp root lives under its root, as gate_wt's does


def paths(name):
    wt = os.path.abspath(os.path.join(ROOT, "..", f"zerobas-iso-{name}"))
    return wt, os.path.join(wt, ".omsx-home"), os.path.join(probe_tmp.ROOT, f"iso-{name}")


def git(*a, cwd=ROOT):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)


def ensure(name, rev, reset, fresh=False):
    wt, home, tmp = paths(name)
    if not os.path.isdir(wt):
        r = git("worktree", "add", "--detach", wt, rev)
        if r.returncode:
            sys.exit(f"agent_wt: worktree add failed: {r.stderr.strip()}")
    elif reset:
        git("checkout", "-q", "--detach", "-f", rev, cwd=wt)
        git("reset", "-q", "--hard", rev, cwd=wt)
    share = os.path.join(home, "share")
    if not os.path.isdir(share):
        os.makedirs(home, exist_ok=True)
        gate_wt.WT = wt                     # seed_share rewrites ROOT + "/" to WT + "/" in the machine configs
        gate_wt.seed_share(share)
    pers = os.path.join(home, "persistent")
    if fresh and os.path.isdir(pers):        # --fresh: start from an empty battery; the last state kept one deep
        prev = pers + ".prev"
        shutil.rmtree(prev, ignore_errors=True)
        os.rename(pers, prev)
    os.makedirs(pers, exist_ok=True)
    os.makedirs(tmp, exist_ok=True)
    return wt, home, tmp


def env_of(home, tmp):
    return {"OPENMSX_HOME": home, "OPENMSX_USER_DATA": os.path.join(home, "share"), "ZEROBAS_TMP": tmp,
            "PYTHONUNBUFFERED": "1"}


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    name, rest = argv[0], argv[1:]
    opts = rest[:rest.index("--")] if "--" in rest else rest     # the instance's flags: before `--` only
    if "--rm" in opts:
        wt, home, tmp = paths(name)
        git("worktree", "remove", "--force", wt)
        shutil.rmtree(wt, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"agent_wt: removed {wt}")
        return 0
    rev = opts[opts.index("--rev") + 1] if "--rev" in opts else "HEAD"
    wt, home, tmp = ensure(name, rev, "--reset" in opts, "--fresh" in opts)
    env = env_of(home, tmp)
    if "--env" in opts:
        for k, v in env.items():
            print(f"export {k}={v}")
        print(f"cd {wt}")
        return 0
    if "--" not in rest:
        sys.exit("agent_wt: COMMAND missing (NAME [--rev REV] -- COMMAND ...)")
    cmd = rest[rest.index("--") + 1:]
    # guarded(): a no-op unless COMMAND is itself an openMSX launch (preflight-check, docs/spec-probe-preflight.md)
    return subprocess.run(omsx_preflight.guarded(cmd), cwd=wt, env=dict(os.environ, **env)).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
