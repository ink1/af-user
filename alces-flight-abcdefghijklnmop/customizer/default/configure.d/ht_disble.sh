#!/usr/bin/env bash

_logical_cpu_count() {
    lscpu | grep "^CPU(s):" | awk '{print $2;}'
}

_physical_cpu_count() {
    local lscpu_output cores_per_socket sockets
    lscpu_output="$(lscpu)"
    cores_per_socket=$(echo "${lscpu_output}" | grep "^Core(s) per socket:" | awk '{print $4;}')
    sockets=$(echo "${lscpu_output}" | grep "^Socket(s):" | awk '{print $2;}')
    echo $((${sockets}*${cores_per_socket}))
}

_disable_ht() {
    local i
    for i in $(seq 0 $(($(_physical_cpu_count)-1))); do
        echo 1 > /sys/devices/system/cpu/cpu$i/online
    done
    for i in $(seq $(_physical_cpu_count) $(($(_logical_cpu_count)-1))); do
        echo 0 > /sys/devices/system/cpu/cpu$i/online
    done
}

if [ "$2" = "slave" ]; then
  _disable_ht
fi

