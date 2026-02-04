#!/bin/bash

echo "wog"

for bs in 16 64; do
    for qd in 1 8 32 128; do
# for bs in 16; do
    # for qd in 1; do
		echo "# BS:$bs QD:$qd"
        echo "# Read direction:"
        testname="randread_bs${bs}_qd${qd}"
        cmd="fio --name=$testname --rw=randread --bs=${bs}k --direct=1 \\
        --ioengine=libaio --iodepth=$qd --time_based \\
        --group_reporting"
        echo "$cmd"
        echo "# Write direction:"
        testname="randwrite_bs${bs}_qd${qd}"
        cmd="fio --name=$testname --rw=randwrite --bs=${bs}k --direct=1 \\
        --ioengine=libaio --iodepth=$qd --time_based \\
        --group_reporting"
        echo "$cmd"
        # echo "# Both direction:"
        # testname="randrw_bs${bs}_qd${qd}"
        # cmd="fio --name=$testname --rw=randrw --bs=${bs}k --direct=1 \\
        # --ioengine=libaio --iodepth=$qd --time_based \\
        # --group_reporting --rwmixread=50"
        # echo "$cmd"
    done
done
