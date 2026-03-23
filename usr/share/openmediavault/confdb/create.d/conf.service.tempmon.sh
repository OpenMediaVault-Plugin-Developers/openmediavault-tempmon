#!/usr/bin/env dash
#
# Copyright (C) 2022-2026 openmediavault plugin developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

set -e

. /usr/share/openmediavault/scripts/helper-functions

if ! omv_config_exists "/config/services/tempmon"; then
    # Fresh install — create the sensors container
    omv_config_add_node "/config/services" "tempmon"
    omv_config_add_node "/config/services/tempmon" "sensors"
elif omv_config_exists "/config/services/tempmon/script" && \
     ! omv_config_exists "/config/services/tempmon/sensors"; then
    # Old flat format detected — add sensors container.
    # Sensors must be re-added via the UI after upgrading.
    omv_config_add_node "/config/services/tempmon" "sensors"
fi

exit 0
