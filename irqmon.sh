#!/bin/bash
# Optimized HBA Interrupt Monitor
HBA_DRIVER="mpt2sas|mpt3sas"

while true; do
    clear
    echo "IRQ  | Vector # | Core ID | Total Interrupts | Driver"
    echo "--------------------------------------------------------"
    grep -E "$HBA_DRIVER" /proc/interrupts | while read -r line; do
        irq=$(echo $line | awk -F: '{print $1}' | xargs)
        # Find which core index has a non-zero value
        core_info=$(echo $line | awk '{for(i=2; i<=NF; i++) if($i > 0 && $i ~ /^[0-9]+$/) print i-2, $i}')
        # Get the friendly name (msix0, msix1, etc)
        name=$(echo $line | awk '{print $NF}')
        
        printf "%-4s | %-8s | %-7s | %-16s | %s\n" "$irq" "${name#*-}" $core_info
    done
    echo -e "\nPress Ctrl+C to exit. Refreshing every 2s..."
    sleep 2
done
