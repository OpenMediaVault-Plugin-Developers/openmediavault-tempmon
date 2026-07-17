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
import re
import shlex
from collections import defaultdict

import openmediavault.mkrrdgraph

CONF_FILE = "/etc/openmediavault/tempmon.conf"

COLORS = [
    '#4cd964', '#0bb6ff', '#00df00', '#fdaf00',
    '#ff1300', '#9b59b6', '#e67e22', '#1abc9c',
]

UNIT_LABELS = {
    'C': '°C',
    'F': '°F',
    'RPM': 'RPM',
    'V': 'V',
    'mV': 'mV',
    '%': '%',
}

VALUE_LABELS = {
    'C': 'Temperature',
    'F': 'Temperature',
    'RPM': 'Speed',
    'V': 'Voltage',
    'mV': 'Voltage',
    '%': 'Value',
}


def _unit_label(unit):
    return UNIT_LABELS.get(unit, '°C')


def _value_label(unit):
    return VALUE_LABELS.get(unit, 'Value')


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
            'widgetgroup': raw.get(f'{prefix}WIDGETGROUP', ''),
            'unit':       raw.get(f'{prefix}UNIT', 'C'),
        })
    return sensors


class Plugin(openmediavault.mkrrdgraph.IPlugin):
    def create_graph(self, config):
        sensors = _load_sensors()

        for idx, sensor in enumerate(sensors):
            color = COLORS[idx % len(COLORS)]
            instance = sensor['instance']
            title = sensor['name']
            unit = _unit_label(sensor['unit'])

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
            args.extend(['--vertical-label', unit])
            args.append('DEF:tavg={data_dir}/{instance}/temperature-value.rrd:value:AVERAGE'.format(**config))
            args.append('DEF:tmin={data_dir}/{instance}/temperature-value.rrd:value:MIN'.format(**config))
            args.append('DEF:tmax={data_dir}/{instance}/temperature-value.rrd:value:MAX'.format(**config))
            args.append('LINE1:tavg{}:"{}"'.format(color, _value_label(sensor['unit'])))
            args.append('GPRINT:tmin:MIN:"%4.1lf {} Min"'.format(unit))
            args.append('GPRINT:tavg:AVERAGE:"%4.1lf {} Avg"'.format(unit))
            args.append('GPRINT:tmax:MAX:"%4.1lf {} Max"'.format(unit))
            args.append('GPRINT:tavg:LAST:"%4.1lf {} Last\\l"'.format(unit))
            args.append('COMMENT:"{last_update}"'.format(**config))
            # autopep8: on
            # yapf: enable
            openmediavault.mkrrdgraph.call_rrdtool_graph(args)

        # Build combined overlay graph for each named group with 2+ sensors
        groups = defaultdict(list)
        for sensor in sensors:
            if sensor['widgetgroup']:
                groups[sensor['widgetgroup']].append(sensor)

        for group_name, group_sensors in groups.items():
            if len(group_sensors) < 2:
                continue

            slug = re.sub(r'[^a-zA-Z0-9-]', '-', group_name).lower()
            config['instance'] = 'exec-tempmon-group-{}'.format(slug)
            image_filename = '{image_dir}/{instance}-{period}.png'.format(**config)

            available = [
                s for s in group_sensors
                if os.path.exists('{data_dir}/{instance}/temperature-value.rrd'.format(
                    data_dir=config['data_dir'], instance=s['instance']))
            ]

            if not available:
                openmediavault.mkrrdgraph.copy_placeholder_image(image_filename)
                continue

            args = []
            args.append(image_filename)
            args.extend(config['defaults'])
            args.extend(['--start', config['start']])
            args.extend(['--title', '"{}{}"'.format(group_name, config['title_by_period'])])
            args.append('--slope-mode')
            args.extend(['--lower-limit', '0'])
            args.extend(['--vertical-label', _unit_label(available[0]['unit'])])
            for idx, s in enumerate(available):
                color = COLORS[idx % len(COLORS)]
                rrd_file = '{data_dir}/{instance}/temperature-value.rrd'.format(
                    data_dir=config['data_dir'], instance=s['instance'])
                args.append('DEF:tavg{}={}:value:AVERAGE'.format(idx, rrd_file))
                args.append('LINE1:tavg{}{}:"{}"'.format(
                    idx, color, s['name'].replace('"', '\\"')))
                args.append('GPRINT:tavg{}:LAST:"%4.1lf {}\\l"'.format(idx, _unit_label(s['unit'])))
            args.append('COMMENT:"{last_update}"'.format(**config))
            openmediavault.mkrrdgraph.call_rrdtool_graph(args)

        return 0
