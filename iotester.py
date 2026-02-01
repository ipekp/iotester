#!/usr/bin/env python3
# Requires: fio and iostat (sysstat)

import sys
import logging
from input import parse_args, load_jobs
from normalize import normalize_jobs
from device import device_backend_for
from runner import Runner
from output import get_output_backend
## from insight import InsightEngine

# GLOBALS
JOB_TIMEOUT = 120

def setup_logging(level=logging.INFO):
    fmt="%(asctime)s - %(levelname)s  %(name)s:  %(message)s"
    logging.basicConfig(level=level, format=fmt)

def main(argv=None):
    args = parse_args(argv)
    setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    try:
        raw_jobs = load_jobs(args.jobfile)
        jobs = normalize_jobs(raw_jobs, args)
        

        out = get_output_backend(args)
        print(out)
        sys.exit(1)

        runner = Runner(cmd_runner=None)
        ## insight = InsightEngine()

        for job in jobs:
            backend = device_backend_for(job.device)
            dev = backend.prepare(job)
            try:
                result = runner.run(job, device=dev)
                print(result)
                # out.write(job, result)
            finally:
                backend.teardown(dev)
        return 0
    except Exception as e:
        logging.exception("fatal error: ", e)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())


sys.exit(1)





