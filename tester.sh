#!/bin/bash
# fio and sysstat pkg required

# TODO retrieve run parameters

# SETTING

## Should be x2 RAM to avoid the ARC (irrelevant at device tests)
tstfile_size="20G"
tstprefix=$(date +%Y-%m-%d_%H%M%S)
# INIT
rm -rf tmp && mkdir tmp



usage() {
  cat << HEREDOC
Usage: $(basename "$0") <blk dev> /path duration
Ex: $(basename "$0") /dev/sdX /mnt/testfile 60
Runs fio benchmarks
HEREDOC
}

printsep() {
  if [[ -z $1 ]]; then
    printf '%.0s=' {1..60}; echo; echo
  else
    printf '%.0s=' {1..60}; echo
    printf '%.0s=' {1..28}; printf '%s' $1; printf '%.0s=' {1..18}; echo
    printf '%.0s=' {1..60}; echo; echo
  fi
}

errquit() {
    printf "%s\n" "ERROR: $*" >&2
    exit 1
}

main() {

[[ "$#" -lt 1 ]] && errquit "$(usage)"

blockdev="$1"
testfile="${2:=/tank/testfile}"
duration="${3:=60}"

echo "Testing $blockdev on $testfile for $duration seconds ..."
printsep

isblockdev "$blockdev"
runfio $blockdev $testfile $duration

}

isblockdev(){
# isn't /dev/sda
# is part of interl or hitachi
# INTEL SSDSC2KG24

  blockdev="$1"

  if [[ $(echo "$blockdev" | grep -i sda | wc -l) == 1 || ! -b "$blockdev" ]]
  then  
    errquit "Blockdev "$blockdev" must not be empty or contain sda" "$(usage)"
  fi
}

prezfs() {

  fdisk -l "$blockdev"
  printsep
  echo "Verify partition alignment"
  # ZFS
  if [[ $(mount -l | grep tank | wc -l) -eq 0 ]]; then
    # User confirmation
    printsep
    read -r -p "WARNING: This will irreversibly erase ALL data on $blockdev. Type 'Y' to confirm: " CONFIRM
    if [[ "$CONFIRM" != "Y" ]] ; then
      echo "Aborted."
      exit 0
    fi
    echo "Initializing pool on $blockdev..."
    zpool create -f -o ashift=12 tank "$blockdev"
    zpool upgrade tank
    zfs set atime=off tank
    zfs set compression=lz4 tank
    zfs set relatime=off tank
    printsep
    zpool status -v tank
    printsep
  fi
}

preptestfile() {
  $file="$1"
  if [ ! -f $file ]; then
      echo "Pre-allocating 64GB file..."
      head -c $(( 1024 * 1024 * 1024 * 64 )) /dev/random >$file
  fi
}

waitfor_mon(){
  res=$1
  echo "Waiting for mon.sh to exit ..."
  for i in {1..10}
  do
    [[ $(cat tmp/$res.mon | wc -l) -gt 10 ]] && break
    sleep 1  
  done
}

flush_cache(){
  sync
  echo 3 > /proc/sys/vm/drop_caches
  printsep 
  echo "FLUSHING CACHES"
  sleep 10
}

runfio() {
  run_fio_zfs_tests "$1" "$2" "$3"
  # run_fio_raw_tests "$1" "$2" "$3"
}

preraw() {

  if [[ $(fdisk -l "$blockdev" | grep gpt | wc -l) -eq 1 ]]; then
    dev=$1
    # User confirmation
    printsep
    read -r -p "WARNING: Delete all partitions on $blockdev ? Type 'Y' to confirm: " CONFIRM
    if [[ "$CONFIRM" != "Y" ]] ; then
      echo "Aborted."
      exit 0
    fi
    zpool destroy -f tank > /dev/null 2>&1
    umount -f $dev > /dev/null 2>&1
    sgdisk --zap-all $dev > /dev/null 2>&1
  fi
}

run_fio_zfs_tests() {

  blockdev="$1"
  file="$2"
  run="$3"

  prezfs "$blockdev"

  #####################################
  ### OWN TESTING
  #####################################

  # testname="zfs-min-lat"
  # cmd=(fio --name="$testname" --filename="$blockdev" \
  #   --rw=write --bs=4k --direct=1 \
  #   --sync=1 --ioengine=libaio --iodepth=8 --runtime="$run" \
  #   --output-format=normal,json --time_based \
  #   --group_reporting --output="results/${tstprefix}_$testname.json"
  #     )

  # Min Latency sync write QD=1
  # Measuring datapath RTT, getting optimal latency
  testname="zfs-min-lat"
  cmd=(fio --name=$testname --filename=$file \
    --filesize=$tstfile_size --rw=randread --bs=4k --direct=1 \
    --ioengine=libaio --iodepth=4 \
    --runtime=$run --time_based --group_reporting \
    --output="results/${tstprefix}_$testname.json" \
    --output-format=normal,json
  )
  exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"

  exit 1

  # Max IOPS ranread QD=128 BS=4K
  testname="zfs-max-iops"
  cmd=(fio --name=max-iops --filename=$file \
    --filesize=$tstfile_size --rw=randread --bs=4k --direct=1 \
    --ioengine=libaio --iodepth=128 \
    --runtime=$run --time_based --group_reporting)
  exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"

  # Max BW QD=32 BS=1M
  # Measuring BW
  testname="zfs-max-iops"
  cmd=(fio --name=max-bw --filename=$file \
    --filesize=$tstfile_size --rw=write --bs=1M --direct=1 \
    --ioengine=libaio --iodepth=32 --runtime=$run \
    --time_based --group_reporting)
  exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"

  # Saturation Matrix both direction and duplex
  # Purpose of finding bottlenecks in the datapath
  # 4K: rare small DB writes, mostly to measure the datapath latency
  # 16K: database workload, look latency
  # 64K: virtualisation workload, look latency
  # 1M: large file manipulation workload, look BW
  for bs in 4 16 64 1024; do
      for qd in 1 2 4 8 16 64 128; do
          # Read direction: ARC cache, RCD read cache, QAM reorder IOPS ...
          testname="zfs_randread_bs${bs}_qd${qd}"
          cmd=(fio --name=$testname \
            --filesize=$tstfile_size --filename=$file \
            --rw=randread --bs=${bs}k --direct=1 \
            --ioengine=libaio --iodepth=$qd \
            --runtime=$run --time_based --group_reporting \
            --output-format=normal,json)
          exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"
          
          # Write direction: Write caches (WCE, HBA), HBA MSI-X ...
          testname="zfs_randwrite_bs${bs}_qd${qd}"
          cmd=(fio --name=$testname --filesize=$tstfile_size \
            --filename=$file --rw=randwrite \
            --bs=${bs}k --direct=1 --ioengine=libaio --iodepth=$qd \
            --runtime=$run --time_based --group_reporting \
            --output-format=normal,json)
          exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"
          
          # Both direction: full duplex chokes
          testname="zfs_randrw_bs${bs}_qd${qd}"
          cmd=(fio --name=$testname --filesize=$tstfile_size \
            --filename=$file --rw=randrw --bs=${bs}k --direct=1 \
            --ioengine=libaio --iodepth=$qd \
            --runtime=$run --time_based --group_reporting \
            --output-format=normal,json)
          exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"

          echo "single pass"
          exit 1
      done
  done
}

exec_fio() {

  # total args: command array..., testname, filename, duration
  local total=$#
  if (( total < 4 )); then
    echo "usage: exec_fio <cmd...> testname filename duration" >&2
    return 2
  fi

  local testname="${@: -3:1}"
  local filename="${@: -2:1}"
  local duration="${@: -1:1}"
  local -a cmd=( "${@:1:$(( total-3 ))}" )

  printsep "$testname"
  echo "Running & monitoring:"
  printsep
  echo "${cmd[*]}"
  printsep

  ./mon.sh "$(basename "$filename")" "$duration" > "tmp/${tstprefix}_$testname.mon" 2>&1 &
  MON_PID=$!

  # run command, capture stdout+stderr
  out=$("${cmd[@]}" 2>&1)

  printf '%s\n' "$out"
  flush_cache
  printsep

  # stop/wait monitor
  if kill -0 "$MON_PID" 2>/dev/null; then
    kill "$MON_PID" 2>/dev/null || true
    wait "$MON_PID" 2>/dev/null || true
  fi
  echo && cat "tmp/${tstprefix}_$testname.mon" >> "results/${tstprefix}_$testname.json"

  return $rc
}

run_fio_raw_tests() {

  blockdev="$1"
  file="$2"
  run="$3"
  
  preraw $blockdev
  printsep
  fdisk -l $blockdev

  # ZFS Part
  # Perimeter Tests
  # Min Latency sync write QD=1
  testname="raw-min-lat"
  cmd=(fio --name="$testname" --filename="$blockdev" \
    --rw=write --bs=4k --direct=1 \
    --sync=1 --ioengine=libaio --iodepth=1 --runtime="$run" \
    --output-format=normal --time_based \
    --group_reporting)

  exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"

  # Max IOPS ranread QD=128 BS=4K
  testname="raw-max-iops"
  cmd=(fio --name=max-iops --filename=$blockdev \
    --rw=randread --bs=4k --direct=1 \
    --ioengine=libaio --iodepth=128 \
    --runtime=$run --time_based --group_reporting)

  exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"

  # Max BW QD=32 BS=1M
  testname="raw-max-bw"
  cmd=(fio --name=$testname --filename=$blockdev \
    --rw=write --bs=1M --direct=1 \
    --ioengine=libaio --iodepth=32 \
    --runtime=$run --time_based --group_reporting)

  exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"

  # Saturation Matrix both direction and duplex
  # Purpose of finding bottlenecks in the datapath
  # 16K: database workload, look latency
  # 64K: virtualisation workload, look latency
  # 1M: large file manipulation workload, look BW
  for bs in 16 64 1024; do # Simplified BS for clarity
      for qd in 1 4 16 64 128; do
          # Read direction: ARC cache, RCD read cache, QAM reorder IOPS ...
          testname="sat_randread_bs${bs}_qd${qd}"
          cmd=(fio --name=sat_bs${bs}_qd${qd} \
            --filename=$blockdev --rw=randread --rwmixread=70 \
            --bs=${bs}k --direct=1 --ioengine=libaio --iodepth=$qd \
            --runtime=$run --time_based --group_reporting \
            --output-format=json)
          exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"
         
          # Write direction: RAID geometry, WCE write cache, HBA MSI-X ...
          testname="sat_randwrite_bs${bs}_qd${qd}"
          cmd=(fio --name=sat_bs${bs}_qd${qd} -filename=$blockdev \
            --rw=randwrite --rwmixread=70 \
            --bs=${bs}k --direct=1 --ioengine=libaio --iodepth=$qd \
            --runtime=$run --time_based --group_reporting \
            --output-format=json)

          exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"
          
          # Both direction: full duplex chokes
          testname="sat_randrw_bs${bs}_qd${qd}"
          cmd=(fio --name=sat_bs${bs}_qd${qd} --filename=$blockdev \
            --rw=randrw --rwmixread=70 \
            --bs=${bs}k --direct=1 --ioengine=libaio --iodepth=$qd \
            --runtime=$run --time_based --group_reporting \
            --output-format=json)
          
          exec_fio "${cmd[@]}" "$testname" "$blockdev" "$run"

      done
  done
}


main $1 $2 $3

exit 1

######################


# ZFS characterization script

# Ensure the file exists so we don't measure "allocation" time during reads


# Saturation Matrix
for bs in 4 64 1024; do # Simplified BS for clarity
    for qd in 1 4 16 64 128; do
        # We use a mix to see where the HBA "chokes"
        fio --name=sat_bs${bs}_qd${qd} --filename=$file --rw=randrw --rwmixread=70 \
            --bs=${bs}k --direct=1 --ioengine=libaio --iodepth=$qd \
            --runtime=$run --time_based --group_reporting --output-format=json > result_${bs}_${qd}.json
    done
done
