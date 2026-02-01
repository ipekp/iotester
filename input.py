# Inputs CLI or file or w/e
import argparse
import logging

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="iotester CLI wrapper")
    parser.add_argument(
        "-n",
        "--setname",
        required=False,
        help="unique set name",
    )
    # @TODO nothing prints debugging just yet
    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        help="Sets logging level to DEBUG",
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

def load_jobs(path):
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
