# -*- coding: utf-8 -*-
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
import os
import shlex

import openmediavault.mkrrdgraph

CONF_FILE = "/etc/openmediavault/tempmon.conf"

COLORS = [
    '#4cd964', '#0bb6ff', '#00df00', '#fdaf00',
    '#ff1300', '#9b59b6', '#e67e22', '#1abc9c',
]


def _load_sensors():
    """Parse /etc/openmediavault/tempmon.conf and return list of sensor dicts."""
    if not os.path.exists(CONF_FILE):
        return []

    raw = {}
    with open(CONF_FILE) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, _, val = line.partition('=')
            # Strip surrounding quotes that the shell conf uses
            raw[key.strip()] = shlex.split(val.strip())[0] if val.strip() else ''

    count = int(raw.get('SENSOR_COUNT', 0))
    sensors = []
    for i in range(count):
        prefix = f'SENSOR_{i}_'
        sensors.append({
            'uuid':       raw.get(f'{prefix}UUID', ''),
            'name':       raw.get(f'{prefix}NAME', f'Sensor {i + 1}'),
            'scriptpath': raw.get(f'{prefix}SCRIPTPATH', ''),
            'instance':   raw.get(f'{prefix}INSTANCE', f'exec-tempmon-{i}'),
        })
    return sensors


class Plugin(openmediavault.mkrrdgraph.IPlugin):
    def create_graph(self, config):
        sensors = _load_sensors()

        for idx, sensor in enumerate(sensors):
            color = COLORS[idx % len(COLORS)]
            instance = sensor['instance']
            title = sensor['name']

            config['instance'] = instance
            config['title_tempmon'] = title
            config['color_tempmon'] = color

            image_filename = '{image_dir}/{instance}-{period}.png'.format(**config)
            rrd_file = '{data_dir}/{instance}/temperature-value.rrd'.format(**config)

            if not os.path.exists(rrd_file):
                openmediavault.mkrrdgraph.copy_placeholder_image(image_filename)
                continue

            args = []
            # yapf: disable
            # pylint: disable=line-too-long
            # autopep8: off
            args.append(image_filename)
            args.extend(config['defaults'])
            args.extend(['--start', config['start']])
            args.extend(['--title', '"{title_tempmon}{title_by_period}"'.format(**config)])
            args.append('--slope-mode')
            args.extend(['--lower-limit', '0'])
            args.extend(['--vertical-label', 'Celsius'])
            args.append('DEF:tavg={data_dir}/{instance}/temperature-value.rrd:value:AVERAGE'.format(**config))
            args.append('DEF:tmin={data_dir}/{instance}/temperature-value.rrd:value:MIN'.format(**config))
            args.append('DEF:tmax={data_dir}/{instance}/temperature-value.rrd:value:MAX'.format(**config))
            args.append('LINE1:tavg{color_tempmon}:"Temperature"'.format(**config))
            args.append('GPRINT:tmin:MIN:"%4.1lf C Min"')
            args.append('GPRINT:tavg:AVERAGE:"%4.1lf C Avg"')
            args.append('GPRINT:tmax:MAX:"%4.1lf C Max"')
            args.append('GPRINT:tavg:LAST:"%4.1lf C Last\\l"')
            args.append('COMMENT:"{last_update}"'.format(**config))
            # autopep8: on
            # yapf: enable
            openmediavault.mkrrdgraph.call_rrdtool_graph(args)

        return 0
