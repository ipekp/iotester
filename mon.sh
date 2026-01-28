#!/bin/bash
# Hardcoded configuration
DEVICE="$1"
DURATION=$2
METRICS="r/s rkB/s r_await w/s wkB/s w_await aqu-sz %util"

if [[ ! -b "$DEVICE" ]]
then  
  #echo "$DEVICE is not BLK"
  DEVICE="sdb"
fi

# -c for CPU, -d for Device, -x for extended, -y to skip first boot report
iostat -c -d -x -y 1 "$DURATION" | awk -v dev="$DEVICE" -v target_metrics="$METRICS" '
BEGIN {
    split(target_metrics, m_list, " ")
    # Track when we are in a CPU block vs Device block
    in_cpu = 0
}

# 1. Identify and process CPU block
/avg-cpu:/ { in_cpu = 1; next }
in_cpu && NF == 6 && !/avg-cpu/ {
    cpu_count++
    cpu_user += $1
    cpu_sys  += $3
    cpu_iowait += $4
    cpu_idle += $6
    in_cpu = 0 # CPU block is only one line
}

# 2. Identify and map Device header columns
/Device/ {
    for (i=1; i<=NF; i++) {
        header[i] = $i
        for (m in m_list) {
            if ($i == m_list[m]) col_map[m_list[m]] = i
        }
    }
}

# 3. Process the hardcoded device row
$1 == dev {
    dev_count++
    for (m in col_map) {
        val = $(col_map[m])
        d_sum[m] += val
        if (dev_count == 1 || val < d_min[m]) d_min[m] = val
        if (dev_count == 1 || val > d_max[m]) d_max[m] = val
    }
}

END {
    if (dev_count == 0) { print "Error: No data found for " dev; exit }

    # Print CPU Results
    printf "\n=== CPU STATISTICS (Global) ===\n"
    printf "%-15s | %-10s\n", "Metric", "Average"
    printf "-------------------------------\n"
    printf "%-15s | %-10.2f%%\n", "%user", cpu_user/cpu_count
    printf "%-15s | %-10.2f%%\n", "%system", cpu_sys/cpu_count
    printf "%-15s | %-10.2f%%\n", "%iowait", cpu_iowait/cpu_count
    printf "%-15s | %-10.2f%%\n", "%idle", cpu_idle/cpu_count

    # Print Device Results
    printf "\n=== DEVICE STATISTICS (%s) ===\n", dev
    printf "%-15s | %-10s | %-10s | %-10s\n", "Metric", "Average", "Min", "Max"
    printf "---------------------------------------------------------\n"
    for (m in col_map) {
        printf "%-15s | %-10.2f | %-10.2f | %-10.2f\n", m, d_sum[m]/dev_count, d_min[m], d_max[m]
    }
}'
