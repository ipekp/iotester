#!/usr/bin/env python

import sys
import re
import time
import argparse
import os

# func
def _parse_int(val: str):
    try:
        return int(val)
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(f"invalid int value: {val!r}")
    val = int(val)
    return val
def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="human readable txgs")
    parser.add_argument(
        "-n",
        required=True,
        type=_parse_int,
        help="number of lines to watch",
    )
    parser.add_argument(
        "-t",
        required=True,
        type=_parse_int,
        help="refresh delay in seconds",
    )
    return parser.parse_args(argv)

def get_txg(view:int):
    file = '/proc/spl/kstat/zfs/tank/txgs'
    with open(file, 'r') as f:
        res = f.readlines()
    lines = []
    for line in res:
        lines.append(re.split(r'\s+', line.strip()))
    return lines[-view:] 

def format_rows(out: list):

    header = ['txg','birth','state','ndirty','nread','nwritten','reads','writes','otime','qtime','wtime','stime','BW']
    idx = {name: header.index(name) for name in header}
    for line, row in enumerate(out):
        if float(out[line][idx['stime']]) > 0:
            out[line].append( round( int(out[line][idx['nwritten']]) / float(out[line][idx['stime']]) * 1000, 1) )
        else:
            out[line].append(0.0)
        for col, val in enumerate(row):
            if col in ( idx['ndirty'], idx['nread'], idx['nwritten'] ):
                v = round(int(val) / pow(1024,2))
                v = f'{v}MB'
            elif col in ( idx['wtime'], idx['qtime'] ):
                v = round(int(val) / pow(1000,1))
                v = f'{v}us'
            elif col in ( idx['otime'], idx['stime'] ):
                v = round(int(val) / pow(1000,2))
                v = f'{v}ms'
            else:
                v = val
            out[line][col] = v
    return out

# ez
def print_txg(out):
    header = ['txg','birth','state','ndirty','nread','nwritten','reads','writes','otime','qtime','wtime','stime','BW']
    # ensure all rows are strings
    rows = [[str(c) for c in r] for r in out]
    # compute widths per column
    cols = list(zip(*( [header] + rows )))
    widths = [max(len(str(cell)) for cell in col) for col in cols]
    # format header
    print("\t".join(h.ljust(w) for h, w in zip(header, widths)))
    print("")
    # format rows
    for r in rows:
        print("\t".join(cell.rjust(w) if cell.replace(',','').isdigit() else cell.ljust(w)
                        for cell, w in zip(r, widths)))

def main(argv=None):
    args = parse_args(argv)
    # out = format_rows(get_txg(args.n))
    # print_txg(out)
    try:
        while True:
            os.system('clear')
            out = format_rows(get_txg(args.n))
            print_txg(out)
            # print("\n\nPress Ctrl + c to interrupt")
            time.sleep(args.t)
    except KeyboardInterrupt:
        print("Interrupted by user")
        return 0
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
