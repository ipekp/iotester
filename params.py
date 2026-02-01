import argparse
import re
import os
import stat


def is_block_device(path: str) -> bool:
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return False
    return stat.S_ISBLK(st.st_mode)


def _parse_devices(val: str):
    if not val:
        raise argparse.ArgumentTypeError("empty device list")
    parts = [p.strip() for p in val.split(",") if p.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("no devices found")
    bad = [p for p in parts if not re.match(r"^[a-zA-Z0-9/_-]+$", p)]
    if bad:
        raise argparse.ArgumentTypeError(f"invalid device names: {', '.join(bad)}")

    for p in parts:
        if not is_block_device(p):
            raise argparse.ArgumentTypeError(f"{p} is not a block device")

    return parts


def _parse_filesize(val: str):
    # Accept formats like 1G, 512M, 1024, etc.
    m = re.fullmatch(r"(\d+)([KkMmGgTt])?", val)
    if not m:
        raise argparse.ArgumentTypeError("filesize must be a number optionally followed by K/M/G/T")
    num, unit = m.groups()
    return val  # keep original string (or convert to bytes if you prefer)


def _parse_runtime(val: str):
    try:
        v = int(val)
    except ValueError:
        raise argparse.ArgumentTypeError("runtime must be an integer number of seconds")
    if v <= 0:
        raise argparse.ArgumentTypeError("runtime must be > 0")
    return v

# basic functions
# TODO add jobfile exists tests
def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="iotester CLI wrapper")
    parser.add_argument(
        "-n",
        "--setname",
        required=True,
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
        required=True,
        help="FS test file name")

    parser.add_argument(
        "-s",
        "--filesize",
        required=True,
        type=_parse_filesize,
        help="FS test file size to be written"
    )
    parser.add_argument(
        "-t",
        "--runtime",
        required=True,
        type=_parse_runtime,
        help="test runtime in seconds"
    )
    parser.add_argument(
        "-d",
        "--devices",
        required=True,
        type=_parse_devices,
        help="block device(s) to monitor -d=sda,sdb"
    )
    return parser.parse_args(argv)
