#!/bin/bash

# --- DIRTY DATA (RAM) CALCULATIONS ---
# ZFS uses zfs_dirty_data_max as the absolute hard limit.
# zfs_dirty_data_max_percent is used at boot to calculate the default max, 
# but the 'max' file is the actual source of truth for the kernel.
dirty_max_bytes=$(cat /sys/module/zfs/parameters/zfs_dirty_data_max)
dirty_max_mb=$(( $dirty_max_bytes / 1024 / 1024 ))

# Soft wall: At this % of dirty_max, ZFS starts background syncing (flushing to disk)
sync_percent=$(cat /sys/module/zfs/parameters/zfs_dirty_data_sync_percent)
dirty_data_sync_mb=$(( $dirty_max_mb * $sync_percent / 100 ))

# Delay wall: At this % of dirty_max, ZFS injects artificial latency to slow down the app
delay_percent=$(cat /sys/module/zfs/parameters/zfs_delay_min_dirty_percent)
delay_start_mb=$(( $dirty_max_mb * $delay_percent / 100 ))

# TXG Timeout: How long ZFS will wait before forcing a sync regardless of size
txg_timeout=$(cat /sys/module/zfs/parameters/zfs_txg_timeout)

# --- THROUGHPUT & AGGREGATION ---
# Estimated bandwidth ZFS tries to maintain to stay under the txg_timeout
global_bw=$(( $dirty_max_mb / $txg_timeout ))

aggr_limit=$(cat /sys/module/zfs/parameters/zfs_vdev_aggregation_limit)
aggr_limit_kb=$(( $aggr_limit / 1024 ))
aggr_limit_nonrota=$(cat /sys/module/zfs/parameters/zfs_vdev_aggregation_limit_non_rotating)
aggr_limit_nonrota_kb=$(( $aggr_limit_nonrota / 1024 ))

# --- I/O SCHEDULER QUEUES (Active Request Limits per VDEV) ---
# These define how many concurrent IOs are sent to the H730P/disks
sync_read_min=$(cat /sys/module/zfs/parameters/zfs_vdev_sync_read_min_active)
sync_read_max=$(cat /sys/module/zfs/parameters/zfs_vdev_sync_read_max_active)
sync_write_min=$(cat /sys/module/zfs/parameters/zfs_vdev_sync_write_min_active)
sync_write_max=$(cat /sys/module/zfs/parameters/zfs_vdev_sync_write_max_active)

async_read_min=$(cat /sys/module/zfs/parameters/zfs_vdev_async_read_min_active)
async_read_max=$(cat /sys/module/zfs/parameters/zfs_vdev_async_read_max_active)
async_write_min=$(cat /sys/module/zfs/parameters/zfs_vdev_async_write_min_active)
async_write_max=$(cat /sys/module/zfs/parameters/zfs_vdev_async_write_max_active)

scrub_min=$(cat /sys/module/zfs/parameters/zfs_vdev_scrub_min_active)
scrub_max=$(cat /sys/module/zfs/parameters/zfs_vdev_scrub_max_active)
trim_min=$(cat /sys/module/zfs/parameters/zfs_vdev_trim_min_active)
trim_max=$(cat /sys/module/zfs/parameters/zfs_vdev_trim_max_active)

# --- OUTPUT ---
echo "=========================================================="
echo " ZFS WRITE THROTTLE & FLOW CONTROL"
echo "=========================================================="
echo "Hard Wall (Max Dirty Data):  $dirty_max_mb MB"
echo "Delay Wall (Start Throttling): $delay_start_mb MB ($delay_percent% of max)"
echo "Soft Wall (Start Syncing):    $dirty_data_sync_mb MB ($sync_percent% of max)"
echo "TXG Timeout:                  $txg_timeout seconds"
echo "Theoretical Global BW:        $global_bw MB/s"
echo "----------------------------------------------------------"
echo " AGGREGATION LIMITS (Request Splicing)"
echo "----------------------------------------------------------"
echo "Standard Aggregation:         ${aggr_limit_kb} KB"
echo "SSD/Non-Rotational:           ${aggr_limit_nonrota_kb} KB"
echo "----------------------------------------------------------"
echo " VDEV I/O CONCURRENCY (Queue Depth per VDEV)"
echo "----------------------------------------------------------"
printf "%-15s | %-10s | %-10s\n" "Queue Type" "Min Active" "Max Active"
printf "%-15s | %-10s | %-10s\n" "Sync Read" "$sync_read_min" "$sync_read_max"
printf "%-15s | %-10s | %-10s\n" "Sync Write" "$sync_write_min" "$sync_write_max"
printf "%-15s | %-10s | %-10s\n" "Async Read" "$async_read_min" "$async_read_max"
printf "%-15s | %-10s | %-10s\n" "Async Write" "$async_write_min" "$async_write_max"
printf "%-15s | %-10s | %-10s\n" "Scrub" "$scrub_min" "$scrub_max"
printf "%-15s | %-10s | %-10s\n" "Trim" "$trim_min" "$trim_max"
echo "=========================================================="
