#!/usr/bin/env python3

import argparse
import logging
import sys
import re

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
        required=False,
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


def prepare_tests(argv):

    # get the jobfile
    try:
        with open(argv.jobfile) as f:
            raw_data = f.readlines()
    except Exception as e:
        logging.error("jobfile not found: {argv.jobfile} {e.message}")

    # extract jobs from
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

    print("=========")
    print(cmds)
    print("=========")

    sys.exit(1)
    # foreach cli command decorate them
    # store in cmd list given to some seq execution


def main(argv=None):
    args = parse_args(argv)
    cmds = prepare_tests(args)


if __name__ == "__main__":
    raise SystemExit(main())
