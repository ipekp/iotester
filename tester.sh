#!/bin/bash
# fio and sysstat pkg required

# TODO retrieve run parameters

# SETTING
rm -rf tmp && mkdir tmp

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
  sleep 10
}

runfio() {
  # run_fio_zfs_tests "$1" "$2" "$3"
  run_fio_raw_tests "$1" "$2" "$3"
}

removeparts() {
  dev=$1
  zpool destroy -f tank 2>&1
  umount -f $dev 2>&1
  sgdisk --zap-all $dev 2>&1
}

run_fio_zfs_tests() {

  blockdev="$1"
  file="$2"
  run="$3"

  # ZFS Part
  # Perimeter Tests
  # Min Latency sync write QD=1
  testname="min-lat"
  printsep "Running $testname"
  ./mon.sh $(basename $blockdev) $run > "tmp/$testname.mon" 2>&1 &
  fio --name=$testname --filename=$file --filesize=$tstfile_size --rw=write --bs=4k --direct=1 \
      --sync=1 --ioengine=libaio --iodepth=1 --runtime=$run --time_based --group_reporting
  flush_cache
  printsep
  waitfor_mon $testname && cat tmp/$testname.mon

  # Max IOPS ranread QD=128 BS=4K
  testname="max-iops"
  printsep "Running $testname"
  ./mon.sh $(basename $blockdev) $run > "tmp/$testname.mon" 2>&1 &
  fio --name=max-iops --filename=$file --filesize=$tstfile_size --rw=randread --bs=4k --direct=1 \
      --ioengine=libaio --iodepth=128 --runtime=$run --time_based --group_reporting
  flush_cache
  printsep
  waitfor_mon $testname && cat tmp/$testname.mon

  # Max BW QD=32 BS=1M
  testname="max-iops"
  printsep "Running $testname"
  ./mon.sh $(basename $blockdev) $run > "tmp/$testname.mon" 2>&1 &
  fio --name=max-bw --filename=$file --filesize=$tstfile_size --rw=write --bs=1M --direct=1 \
      --ioengine=libaio --iodepth=32 --runtime=$run --time_based --group_reporting
  flush_cache
  printsep
  waitfor_mon $testname && cat tmp/$testname.mon
  exit 1

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

run_fio_raw_tests() {

  blockdev="$1"
  file="$2"
  run="$3"

  removeparts $blockdev
  printsep
  fdisk -l $blockdev

  # ZFS Part
  # Perimeter Tests
  # Min Latency sync write QD=1
  testname="raw-min-lat"
  printsep "Running $testname"
  ./mon.sh $(basename $blockdev) $run > "tmp/$testname.mon" 2>&1 &
  fio --name=$testname --filename=$file --filesize=$tstfile_size --rw=write --bs=4k --direct=1 \
      --sync=1 --ioengine=libaio --iodepth=1 --runtime=$run --time_based --group_reporting
  flush_cache
  printsep
  waitfor_mon $testname && cat tmp/$testname.mon

  # Max IOPS ranread QD=128 BS=4K
  testname="raw-max-iops"
  printsep "Running $testname"
  ./mon.sh $(basename $blockdev) $run > "tmp/$testname.mon" 2>&1 &
  fio --name=max-iops --filename=$file --filesize=$tstfile_size --rw=randread --bs=4k --direct=1 \
      --ioengine=libaio --iodepth=128 --runtime=$run --time_based --group_reporting
  flush_cache
  printsep
  waitfor_mon $testname && cat tmp/$testname.mon

  # Max BW QD=32 BS=1M
  testname="raw-max-bw"
  printsep "Running $testname"
  ./mon.sh $(basename $blockdev) $run > "tmp/$testname.mon" 2>&1 &
  fio --name=$testname --filename=$file --filesize=$tstfile_size --rw=write --bs=1M --direct=1 \
      --ioengine=libaio --iodepth=32 --runtime=$run --time_based --group_reporting
  flush_cache
  printsep
  waitfor_mon $testname && cat tmp/$testname.mon
  exit 1

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
