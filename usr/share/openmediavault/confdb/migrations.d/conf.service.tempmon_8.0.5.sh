#!/bin/sh

set -e

. /usr/share/openmediavault/scripts/helper-functions

xpath="/config/services/tempmon/sensors/sensor"

count=$(omv_config_get_count "${xpath}")
index=1
while [ ${index} -le ${count} ]; do
    sensor="${xpath}[position()=${index}]"
    if ! omv_config_exists "${sensor}/unit"; then
        omv_config_add_key "${sensor}" "unit" "C"
    fi
    index=$((index+1))
done

exit 0
