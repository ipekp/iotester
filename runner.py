import logging
import sys
import shlex
import subprocess
from params import parse_args

JOB_TIMEOUT = 120

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

    logging.info("Cmd: %s (timeout %s)", info, timeout)

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

# does all the running
def run_jobs(cmds: list[str], argv: object):

    # background iostat monitoring
    iostat_devs = " ".join(argv.devices)

    iostat_cmd = f"iostat -c -d -x -y 1 {argv.runtime} {iostat_devs} 2>&1 &"
    rc, out, err = run_cmd(iostat_cmd, timeout=argv.runtime+5)

    # parse iostat
    cpu_metrics = {'%user': [], '%system': [], '%iowait': [], '%idle': []}

    dev_metrics = {'r/s': [], 'rkB/s': [], 'r_await': [], 'w/s': [], 'wkB/s':
                   [], 'w_await': [], 'aqu-sz': [], '%util': []}

    lines = out.splitlines()

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
    logging.debug("\nCpu results: %s", cpu_metrics)
    logging.debug("\nDevice results: %s", dev_metrics)

    # tot = 0
    # for s in cpu_metrics['%user']:
    #     tot += s
    # print(round (tot/len(cpu_metrics['%user']),2) )

    # extract keys
    averages = {}
    for metric in cpu_metrics:
        cm = "fio_" + metric.replace('%', '')
        tot = 0.00
        for s in cpu_metrics[metric]:  #list
            tot += s
        avg = round(tot/len(metric), 2)
        averages[cm] = avg
    
    for metric in dev_metrics:
        cm = "iostat_" + metric.replace('%', '')
        tot = 0.00
        for s in dev_metrics[metric]:  #list
            tot += s
        avg = round(tot/len(metric), 2)
        averages[cm] = avg

    print(averages)
    # rc, out, err = run_cmd(cmds[0])
    # print(out)
