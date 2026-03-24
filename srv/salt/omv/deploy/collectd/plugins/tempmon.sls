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

configure_collectd_conf_tempmon_plugin:
  file.managed:
    - name: "/etc/collectd/collectd.conf.d/tempmon.conf"
    - contents: |
        LoadPlugin exec
        <Plugin exec>
            Exec "nobody" "/usr/share/openmediavault-tempmon/scripts/collectd-tempmon"
        </Plugin>
