#!/usr/bin/env python3

import logging
from params import parse_args
from input import getjobs
from input import normalizecmds
from runner import run_jobs
from output import tocsv

# GLOBALS
JOB_TIMEOUT = 120

# Configure logging DEBUG: 10, INFO: 20, WARNING: 30, ERROR: 40, CRITICAL: 50
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main(argv=None):
    # args = parse_args(argv)
    # cmds = getjobs(args)
    # cmds = normalizecmds(cmds, args)
    # output = run_jobs(cmds, args)
    output = [{'jobname': 'set1_ONETWOTREE', 'bs': '4k', 'qd': '4', 'fio_sys_cpu': 84.53, 'fio_usr_cpu': 15.43, 'iops': 217781.42, 'BW_MBs': 217781.42, 'clat_avg_us': 14.31, 'clat_p99_us': 18.05, 'clat_ratio': 1.26, 'slat_avg_us': 3.7, 'lat_avg_us': 18.07, 'iostat_user': 3.22, 'iostat_system': 7.48, 'iostat_iowait': 0.02, 'iostat_util': 18.18, 'iostat_aqu-sz': 0.18, 'iostat_ws': 0.3, 'iostat_rs': 214589.8}, {'jobname': 'set1_ONETWOTREE', 'bs': '4k', 'qd': '4', 'fio_sys_cpu': 84.53, 'fio_usr_cpu': 15.43, 'iops': 217781.42, 'BW_MBs': 217781.42, 'clat_avg_us': 14.31, 'clat_p99_us': 18.05, 'clat_ratio': 1.26, 'slat_avg_us': 3.7, 'lat_avg_us': 18.07, 'iostat_user': 4.55, 'iostat_system': 8.67, 'iostat_iowait': 0.01, 'iostat_util': 69.06, 'iostat_aqu-sz': 0.69, 'iostat_ws': 73870.2, 'iostat_rs': 0.0}]
    output = tocsv(output)
    print(output)
    # 
    # format_job("", "", "")


if __name__ == "__main__":
    raise SystemExit(main())
