import sys
from runner import run_cmd

def run_jobs(cmd: list[str], argv: object):

    # background iostat monitoring
    iostat_devs = " ".join(argv.devices)

    iostat_cmd = f"iostat -c -d -x -y 1 {argv.runtime} {iostat_devs}"
    rc, out, err = run_cmd(iostat_cmd, timeout=argv.runtime)

    # parse iostat
    cpu_metrics = {'%user': [], '%system': [], '%iowait': [], '%idle': []}

    dev_metrics = {'r/s': [], 'rkB/s': [], 'r_await': [], 'w/s': [], 'wkB/s':
                   [], 'w_await': [], 'aqu-sz': [], '%util': []}

    lines = out.decode().splitlines()

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
            # print(header_parts)
            # get values at next line
            try:
                val_line = lines[idx + 1]
                val_parts = [v.strip().replace(',', '.') for v in val_line.split()]
                print(val_parts)
            # map values to headers
                for col_idx, col in enumerate(header_parts):
                    if col in dev_metrics:
                        val = float(val_parts[col_idx])
                        dev_metrics[col].append(val)
                        # print(f"Matched {col} (index {col_idx}) to value {val}")
            except (IndexError, ValueError) as e:
                print(f"Error parsing at line {idx}: {e}")
                continue
    #print("\nCpu results", cpu_metrics)
    print("\nDevice results", dev_metrics)
    sys.exit(1)
