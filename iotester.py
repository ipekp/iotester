#!/usr/bin/env python3

import logging
import sys
from params import parse_args
from runner import run_jobs

# GLOBALS
JOB_TIMEOUT = 120

# Configure logging DEBUG: 10, INFO: 20, WARNING: 30, ERROR: 40, CRITICAL: 50
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


def getjobs(argv):
    # get the jobfile
    path = argv.jobfile
    
    try:
        with open(path) as f:
            raw_data = f.readlines()
    except Exception as e:
        logging.error("jobfile not found: %s (%s)", path, e)

    cmds = []
    buf = []
    for line in raw_data:
        s = line.strip()
        if not s or s.startswith('#'):
            continue

        if s.endswith('\\'):
            buf.append(s[:-1].rstrip())
            continue
        if buf:
            buf.append(s)
            cmds.append(" ".join(buf))
            buf = []
        else:
            cmds.appends(s)

    if buf:
        cmds.append(" ".join(buf))
    return cmds


def normalizecmds(cmds, argv):
    # Namespace(setname=None, jobfile='jobs.txt', filename=None, filesize=None, runtime=None)
    # recup param list
    norms = []
    for cmd in cmds:
        norm = {}
        parts = cmd.split()
        for part in parts[1:]:      # 1st key is fio
            # replace prefix - or --
            part = part.replace("-", "")
            if "=" in part:
                k = part.split("=")[0]
                v = part.split("=")[1]
                norm[k] = v
            else:
                k = part
                norm[k] = True

        norms.append(norm)
    # Overwrite cli params with argv parameters
    for k, v in vars(argv).items():
        # look for match in commands
        for cmdidx, cmd in enumerate(norms):
            for u, w in cmd.items():
                if v and k == u:
                    # job name fixing
                    # print("Found match", k, "=", v, " with ", u, "=", w)
                    # print("Before: ", u, "=", norms[cmdidx][u])
                    norms[cmdidx][u] = v
                    # print("After: ", u ,"=", norms[cmdidx][u])

    # Prefix jobname with setname
    for k, cmd in enumerate(norms):
        name = cmd.get('name') or f"00{str(k)}"
        norms[k]['name'] = argv.setname.lower().strip() + "_" + name.replace('"', '')

    # create list suitable for subprocess
    res = []
    for norm in norms:
        args = ["fio"]
        for k, v in norm.items():
            key = f"--{k}"
            if v is True or v == "True":
                args.append(f"{key}")
            else:
                args.append(f"{key}={v}")
        res.append(args)
    return res


def main(argv=None):
    args = parse_args(argv)
    cmds = getjobs(args)
    cmds = normalizecmds(cmds, args)
    run_jobs(cmds, args)
    # format output


if __name__ == "__main__":
    raise SystemExit(main())
