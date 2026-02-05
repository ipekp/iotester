#!/bin/bash
# Pin mpt3sas MSI-X vectors to NUMA Node 1 (Cores 28-43)
# ADJUST START_CORE BASED ON YOUR LSCPU OUTPUT
# j crois que c SPDK l'ancetre de DPDK

START_CORE=28
VECTORS=$(grep "mpt2sas\|mpt3sas" /proc/interrupts | awk -F: '{print $1}' | xargs)

i=0
for irq in $VECTORS; do
    TARGET_CORE=$((START_CORE + i))
    # Set the affinity (writing core ID to smp_affinity_list is easier than hex masks)
    echo $TARGET_CORE > /proc/irq/$irq/smp_affinity_list
    echo "Pinned IRQ $irq to Core $TARGET_CORE"
    ((i++))
done
