#!/usr/bin/env python3

import argparse
import logging
import sys
import re
import subprocess
import shlex

# GLOBALS
JOB_TIMEOUT = 120

# Configure logging DEBUG: 10, INFO: 20, WARNING: 30, ERROR: 40, CRITICAL: 50
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# basic functions
def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="iotester CLI wrapper")
    parser.add_argument(
        "-n",
        "--setname",
        required=False,
        help="unique set name",
    )
    parser.add_argument(
        "-j",
        "--jobfile",
        required=True,
        help="file containing fio commands",
    )
    parser.add_argument(
        "-f",
        "--filename",
        required=False,
        help="FS test file name")

    parser.add_argument(
        "-s",
        "--filesize",
        required=False,
        help="FS test file size to be written"
    )
    parser.add_argument(
        "-t",
        "--runtime",
        required=False,
        help="test runtime in seconds"
    )
    return parser.parse_args(argv)


def getjobs(path):
    # get the jobfile
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


def normalizecmds(argv, cmds):
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
    # apply argv over it
    # Note: shell params have priority over bash CLI
    for cmd in norms:
        for k, v in cmd.items():
            # print(k, "=", v)
            if hasattr(argv, k):
                val = getattr(argv, k)
                if val:
                    cmd[k] = val

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


def run_cmd(cmd: list | str,
            check: bool = False,
            capture_output: bool = True,
            text: bool = True,
            timeout: int | None = JOB_TIMEOUT,
            cwd: str | None = None,
            env: dict | None = None
            ):

    if isinstance(cmd, str):
        args = shlex.split(cmd)
    else:
        args = list(cmd)

    try:
        completed = subprocess.run(
                args,
                check=check,
                capture_output=capture_output,
                text=text,
                timeout=timeout,
                cwd=cwd,
                env=env
        )
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout or "", e.stderr or ""
    except subprocess.TimeoutExpired as e:
        return -1, e.stdout or "", e.stderr or f"Timeout after {timeout}s"
    except Exception as e:
        return -1, "", str(e)
    return completed.returncode, completed.stdout or "", completed.stderr or ""

def prepare_tests(argv):

    cmds = getjobs(argv.jobfile)
    cmds = normalizecmds(argv, cmds)
    # print(cmds)
    # rc, out, err = run_cmd(["ls", "-rtlh", "/tmp"])
    rc, out, err = run_cmd("bash", "-c", "sleep 2 && echo done", timeout=1)
    print("rc:", rc, "out:", out, "err:", err)
    sys.exit(1)

    # foreach cli command decorate them
    # store in cmd list given to some seq execution


def main(argv=None):
    args = parse_args(argv)
    cmds = prepare_tests(args)


if __name__ == "__main__":
    raise SystemExit(main())
