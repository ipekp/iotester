#!/bin/bash
# fio and sysstat pkg required

# SETTING

# Should be x2 RAM to avoid the ARC (irrelevant at device tests)
tstfile_size="64G"


usage() {
  cat << HEREDOC
Usage: $(basename "$0") <blk dev> /path duration
Ex: $(basename "$0") /dev/sdX /mnt/testfile 60
Runs fio benchmarks
HEREDOC
}

printsep() {
  printf '%.0s=' {1..80}; echo; echo
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
prepblockdev "$blockdev"
# preptestfile "$testfile" to avoid spending time creating test file ?
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

prepblockdev() {

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

flush_cache(){
  echo "Flushing caches (10sec) ..."
  sync
  echo 3 > /proc/sys/vm/drop_caches
  sleep 10
}

runfio() {

  blockdev="$1"
  file="$2"
  run="$3"

  echo "Testfile=$testfile for duration=$duration (size=$tstfile_size)"

  # ZFS Part
  # Perimeter Tests
  # Min Latency sync write QD=1
  echo "mon.sh $(basename $blockdev) $run > "tmp/min-lat.mon" 2>&1 &"
  exit 1
  mon.sh $(basename $blockdev) $run > "tmp/min-lat.mon" 2>&1 &
  fio --name=min-lat --filename=$file --filesize=$tstfile_size --rw=write --bs=4k --direct=1 \
      --sync=1 --ioengine=libaio --iodepth=1 --runtime=$run --time_based --group_reporting
  cat tmp/min-lat.mon
  flush_cache
  exit

  # Max IOPS ranread QD=128 BS=4K
  fio --name=max-iops --filename=$file --filesize=$tstfile_size --rw=randread --bs=4k --direct=1 \
      --ioengine=libaio --iodepth=128 --runtime=$run --time_based --group_reporting
  flush_cache

  # Max BW QD=32 BS=1M
  fio --name=max-bw --filename=$file --filesize=$tstfile_size --rw=write --bs=1M --direct=1 \
      --ioengine=libaio --iodepth=32 --runtime=$run --time_based --group_reporting
  flush_cache

  # Saturation Matrix both direction and duplex
  # Purpose of finding bottlenecks in the datapath
  # 16K: database workload, look latency
  # 64K: virtualisation workload, look latency
  # 1M: large file manipulation workload, look BW
  for bs in 16 64 1024; do # Simplified BS for clarity
      for qd in 1 4 16 64 128; do
          # Read direction: ARC cache, RCD read cache, QAM reorder IOPS ...
          fio --name=sat_bs${bs}_qd${qd} --filesize=$tstfile_size --filename=$file --rw=randread --rwmixread=70 \
              --bs=${bs}k --direct=1 --ioengine=libaio --iodepth=$qd \
              --runtime=$run --time_based --group_reporting --output-format=json > result_randread_${bs}_${qd}.json
          flush_cache
          # Write direction: RAID geometry, WCE write cache, HBA MSI-X ...
          fio --name=sat_bs${bs}_qd${qd} --filesize=$tstfile_size --filename=$file --rw=randwrite --rwmixread=70 \
              --bs=${bs}k --direct=1 --ioengine=libaio --iodepth=$qd \
              --runtime=$run --time_based --group_reporting --output-format=json > result_randwrite_${bs}_${qd}.json
          flush_cache
          # Both direction: full duplex chokes
          fio --name=sat_bs${bs}_qd${qd} --filesize=$tstfile_size --filename=$file --rw=randrw --rwmixread=70 \
              --bs=${bs}k --direct=1 --ioengine=libaio --iodepth=$qd \
              --runtime=$run --time_based --group_reporting --output-format=json > result_randrw_${bs}_${qd}.json
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
