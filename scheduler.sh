#!/bin/bash

dirty_max=$( cat /sys/module/zfs/parameters/zfs_dirty_data_max )
dirty_max=$(( $dirty_max / (1024*1024) ))
dirty_max_percent=$( cat /sys/module/zfs/parameters/zfs_dirty_data_max_percent )
txg_timeout=$( cat /sys/module/zfs/parameters/zfs_txg_timeout )
dirty_data_sync_percent=$( cat /sys/module/zfs/parameters/zfs_dirty_data_sync_percent )
delay_min_dirty_percent=$( cat /sys/module/zfs/parameters/zfs_delay_min_dirty_percent )
global_bw=$(( dirty_max / txg_timeout ))

# sync static 50% of phydisk QD
sync_read_max=$( cat /sys/module/zfs/parameters/zfs_vdev_sync_read_max_active)
sync_read_min=$( cat /sys/module/zfs/parameters/zfs_vdev_sync_read_min_active)
sync_write_min=$( cat /sys/module/zfs/parameters/zfs_vdev_sync_write_min_active)
sync_write_max=$( cat /sys/module/zfs/parameters/zfs_vdev_sync_write_max_active)

async_write_min=$( cat /sys/module/zfs/parameters/zfs_vdev_async_write_min_active)
async_write_max=$( cat /sys/module/zfs/parameters/zfs_vdev_async_write_max_active)
async_read_min=$( cat /sys/module/zfs/parameters/zfs_vdev_async_read_min_active)
async_read_max=$( cat /sys/module/zfs/parameters/zfs_vdev_async_read_max_active)

scrub_min=$( cat /sys/module/zfs/parameters/zfs_vdev_scrub_min_active)
scrub_max=$( cat /sys/module/zfs/parameters/zfs_vdev_scrub_max_active)
trim_min=$( cat /sys/module/zfs/parameters/zfs_vdev_trim_min_active)
trim_max=$( cat /sys/module/zfs/parameters/zfs_vdev_trim_max_active)

echo "Flow settings:"
echo "Global BW: $global_bw MB/s"
echo "Delay injection at: $delay_min_dirty_percent %"
echo "Hard wall at: $dirty_max_percent %"
echo "Sync prio:"
echo "W: ($sync_write_min/$sync_write_max) - R: ($sync_read_min/$sync_read_max)"
echo "Async prio:"
echo "W: ($async_write_min/$async_write_max) - R: ($async_read_min/$async_read_max)"
echo "Rest:"
echo "scrub: ($scrub_min/$scrub_max) - trim: ($trim_min/$trim_max)"
