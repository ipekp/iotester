import logging
import shlex
import subprocess
import os
from output import format_job
import sys
import time

JOB_TIMEOUT = 120

def start_iostat_capture(cmd: str):
# cmd must not include '&' or '2>&1'
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setpgrp
    )
    return proc

def read_all(proc: subprocess.Popen, timeout: int | None = None):
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExprired:
        proc.kill()
        out, err = proc.communicate()
    return proc.returncode, out or "", err or ""


def run_cmd(cmd: list | str,
            check: bool = False,
            capture_output: bool = True,
            text: bool = True,
            timeout: int | None = JOB_TIMEOUT,
            cwd: str | None = None,
            env: dict | None = None
            ):
    # some debugging
    info = cmd
    if isinstance(cmd, str):
        args = shlex.split(cmd)
    else:
        args = list(cmd)
        info = shlex.join(cmd)

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

    logging.info("Cmd: %s (rc %s) (timeout %s)", info, completed.returncode, timeout)
    return completed.returncode, completed.stdout or "", completed.stderr or ""

def run_jobs(cmds: list[str], argv: object):
    out = []
    for cmd in cmds:
        out.append(run_job(cmd, argv))
    return out

def run_job(cmds: str, argv: object):
    iostat_devs = " ".join(argv.devices)
    # argv have been normalized() at this point ...
    # before each task flush cache
    run_cmd("sync", timeout=10)
    run_cmd('echo 3 > sudo tee /proc/sys/vm/drop_caches', timeout=10)
    logging.info("Waiting for 10s")
    time.sleep(10)

    # do NOT include '&' or '2>&1' when you want to capture output
    iostat_cmd = f"iostat -c -d -x -y 1 {argv.runtime} {iostat_devs}"
    iostat_proc = start_iostat_capture(iostat_cmd)

    fio_timeout = argv.runtime
    # +10 safety buffer to let fio finish
    rc_fio, out_fio, err_fio = run_cmd(cmds, timeout=fio_timeout+10)

    rc_iostat, out_iostat, err_iostat = read_all(iostat_proc, timeout=argv.runtime)
    logging.info("Background iostat: %s (timeout %s)", iostat_cmd, argv.runtime)

    # Now out_fio and out_iostat are strings (text=True)
    # logging.debug("fio out head: %s", out_fio[:1000])
    # logging.debug("iostat out head: %s", out_iostat[:1000])

    # parse iostat using out_iostat below (same parsing code as you already have)
    cpu_metrics = {'%user': [], '%system': [], '%iowait': [], '%idle': []}

    dev_metrics = {'r/s': [], 'rkB/s': [], 'r_await': [], 'w/s': [], 'wkB/s':
                   [], 'w_await': [], 'aqu-sz': [], '%util': []}
    lines = out_iostat.splitlines()
    # ... (parsing unchanged) ...
    for idx, line in enumerate(lines):
        if line.startswith('avg-cpu'):
            # parse header
            header_parts = [p.strip() for p in line.split() if p.strip()]
            # get values at next line
            try:
                val_line = lines[idx + 1]
                val_parts = [v.strip().replace(',', '.') for v in val_line.split()]
            # map values to headers
                for col_idx, col in enumerate(header_parts):
                    if col in cpu_metrics:
                        val = float(val_parts[col_idx -1])
                        cpu_metrics[col].append(val)
                        #print(f"Matched {col} (index {col_idx}) to value {val}")
            except (IndexError, ValueError) as e:
                print(f"Error parsing at line {idx}: {e}")
                continue
        if line.startswith('Device'):
            # parse header
            header_parts = [p.strip() for p in line.split() if p.strip()]
            # get values at next line
            try:
                val_line = lines[idx + 1]
                val_parts = [v.strip().replace(',', '.') for v in val_line.split()]
                # map values to headers
                for col_idx, col in enumerate(header_parts):
                    if col in dev_metrics:
                        val = float(val_parts[col_idx])
                        dev_metrics[col].append(val)
                        # print(f"Matched {col} (index {col_idx}) to value {val}")
            except (IndexError, ValueError) as e:
                print(f"Error parsing at line {idx}: {e}")
                continue
    # logging.debug("\nCpu results: %s", cpu_metrics)
    # logging.debug("\nDevice results: %s", dev_metrics)


    averages = {}
    for metric, vals in cpu_metrics.items():
        key = "iostat_" + metric.replace('%', '')
        avg = round(sum(vals) / len(vals), 2) if vals else 0.0
        averages[key] = avg

    for metric, vals in dev_metrics.items():
        key = "iostat_" + metric.replace('%', '')
        key = key.replace('/', '')
        avg = round(sum(vals) / len(vals), 2) if vals else 0.0
        averages[key] = avg

    # print exhaustive out in logs
    logfile = f"logs/{argv.setname}.log"
    with open(logfile, 'a') as f:
        sep = "=" * 10
        f.write(f"{sep} fio out:\n {out_fio}\n")
        f.write(f"{sep} iostat out:\n {out_iostat}\n")
        f.write(f"{sep} Cpu metrics:\n {cpu_metrics}\n")
        f.write(f"{sep} Dev metrics:\n {dev_metrics}\n")
        f.write(f"{sep} Avg iostats:\n {averages}\n")

    # prepare output
    return format_job(out_fio, out_iostat, averages, cmds)
    # return rc_fio, out_fio, err_fio, rc_iostat, out_iostat, err_iostat


