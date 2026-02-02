#!/usr/bin/env python3

import logging
from params import parse_args
from runner import run_jobs
from input import getjobs
from input import normalizecmds

# GLOBALS
JOB_TIMEOUT = 120

# Configure logging DEBUG: 10, INFO: 20, WARNING: 30, ERROR: 40, CRITICAL: 50
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main(argv=None):
    args = parse_args(argv)
    cmds = getjobs(args)
    cmds = normalizecmds(cmds, args)
    run_jobs(cmds, args)
    # format output


if __name__ == "__main__":
    raise SystemExit(main())
