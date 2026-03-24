# Copyright (C) 2022-2026 openmediavault plugin developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

{% set sensors = salt['omv_conf.get']('conf.service.tempmon.sensor') %}
{% set chart_sensors = sensors | selectattr('chart') | list %}
{% set widget_sensors = sensors | selectattr('widget') | list %}
{% set colors = ["#4cd964", "#0bb6ff", "#00df00", "#fdaf00", "#ff1300", "#9b59b6", "#e67e22", "#1abc9c"] %}
{% set widget_dir = '/usr/share/openmediavault/workbench/dashboard.d' %}
{% set component_dir = '/usr/share/openmediavault/workbench/component.d' %}
{% set route_dir = '/usr/share/openmediavault/workbench/route.d' %}
{% set nav_dir = '/usr/share/openmediavault/workbench/navigation.d' %}

# Write the sensor config file consumed by the collectd exec script
configure_tempmon_conf:
  file.managed:
    - name: /etc/openmediavault/tempmon.conf
    - source:
      - salt://{{ tpldir }}/files/tempmon.conf.j2
    - context:
        sensors: {{ sensors | json }}
    - template: jinja

# Write each sensor's temperature script
{% for s in sensors %}
{% if s.script and s.scriptpath %}
configure_tempmon_sensor_script_{{ s.uuid }}:
  file.managed:
    - name: {{ s.scriptpath }}
    - contents: |
        {{ s.script | indent(8) }}
    - mode: "0755"
{% endif %}
{% endfor %}

# Grant nobody passwordless sudo for each sensor script so collectd exec can read privileged sensors
configure_tempmon_sudoers:
  file.managed:
    - name: /etc/sudoers.d/openmediavault-tempmon
    - mode: "0440"
    - contents: |
{%- for s in sensors %}
{%- if s.script and s.scriptpath %}
        nobody ALL=(root) NOPASSWD: {{ s.scriptpath }}
{%- endif %}
{%- endfor %}

# Generate individual gauge widget for each ungrouped widget sensor
{% for s in widget_sensors %}
{% if not s.widgetgroup %}
configure_tempmon_widget_yaml_{{ s.uuid }}:
  file.managed:
    - name: {{ widget_dir }}/tempmon-widget-{{ s.uuid }}.yaml
    - source:
      - salt://{{ tpldir }}/files/dashboard-widget.yaml.j2
    - context:
        widget_id: "{{ s.uuid }}"
        title: "{{ s.name | replace('"', '\\"') }}"
        sensors: {{ [s] | json }}
        colors: {{ colors | json }}
    - template: jinja
{% endif %}
{% endfor %}

# Generate combined bar chart widget for each named sensor group
{% for group_name, group_sensors in widget_sensors | groupby('widgetgroup') %}
{% if group_name %}
{% set slug = group_name | replace(' ', '-') | lower %}
{% set group_sensors_list = group_sensors | list %}
configure_tempmon_widget_group_{{ slug }}:
  file.managed:
    - name: {{ widget_dir }}/tempmon-widget-group-{{ slug }}.yaml
    - source:
      - salt://{{ tpldir }}/files/dashboard-widget.yaml.j2
    - context:
        widget_id: "{{ group_sensors_list[0].uuid }}"
        title: "{{ group_name | replace('"', '\\"') }}"
        sensors: {{ group_sensors_list | json }}
        colors: {{ colors | json }}
    - template: jinja
{% endif %}
{% endfor %}

# Remove stale widget YAML files for sensors that no longer exist or have widget disabled
purge_stale_tempmon_widget_yaml_files:
  file.tidied:
    - name: "{{ widget_dir }}"
    - matches:
      - "tempmon-widget-.*\\.yaml"
{%- if widget_sensors %}
    - exclude:
{%- for s in widget_sensors %}
{%- if not s.widgetgroup %}
      - "tempmon-widget-{{ s.uuid }}.yaml"
{%- endif %}
{%- endfor %}
{%- for group_name, _ in widget_sensors | groupby('widgetgroup') %}
{%- if group_name %}
{%- set slug = group_name | replace(' ', '-') | lower %}
      - "tempmon-widget-group-{{ slug }}.yaml"
{%- endif %}
{%- endfor %}
{%- endif %}
    - rmdirs: False
    - rmlinks: True

# Generate the RRD diagnostics page files when chart sensors are configured
{% if chart_sensors %}
configure_tempmon_rrd_component:
  file.managed:
    - name: {{ component_dir }}/omv-diagnostics-performance-statistics-tempmon-rrd-page.yaml
    - source:
      - salt://{{ tpldir }}/files/rrd-component.yaml.j2
    - context:
        chart_sensors: {{ chart_sensors | json }}
    - template: jinja

configure_tempmon_rrd_route:
  file.managed:
    - name: {{ route_dir }}/diagnostics.performance-statistics.tempmon.yaml
    - source:
      - salt://{{ tpldir }}/files/rrd-route.yaml.j2
    - template: jinja

configure_tempmon_rrd_navigation:
  file.managed:
    - name: {{ nav_dir }}/diagnostics.performance-statistics.tempmon.yaml
    - source:
      - salt://{{ tpldir }}/files/rrd-navigation.yaml.j2
    - template: jinja

{% else %}
# Remove the RRD diagnostics page files when no chart sensors are configured
remove_tempmon_rrd_component:
  file.absent:
    - name: {{ component_dir }}/omv-diagnostics-performance-statistics-tempmon-rrd-page.yaml

remove_tempmon_rrd_route:
  file.absent:
    - name: {{ route_dir }}/diagnostics.performance-statistics.tempmon.yaml

remove_tempmon_rrd_navigation:
  file.absent:
    - name: {{ nav_dir }}/diagnostics.performance-statistics.tempmon.yaml
{% endif %}

# Rebuild the workbench now that YAML files may have changed
omv_mkworkbench:
  cmd.run:
    - name: "omv-mkworkbench all"
    - onchanges:
      - file: purge_stale_tempmon_widget_yaml_files
{%- for s in widget_sensors %}
{%- if not s.widgetgroup %}
      - file: configure_tempmon_widget_yaml_{{ s.uuid }}
{%- endif %}
{%- endfor %}
{%- for group_name, _ in widget_sensors | groupby('widgetgroup') %}
{%- if group_name %}
{%- set slug = group_name | replace(' ', '-') | lower %}
      - file: configure_tempmon_widget_group_{{ slug }}
{%- endif %}
{%- endfor %}
{%- if chart_sensors %}
      - file: configure_tempmon_rrd_component
      - file: configure_tempmon_rrd_route
      - file: configure_tempmon_rrd_navigation
{%- else %}
      - file: remove_tempmon_rrd_component
      - file: remove_tempmon_rrd_route
      - file: remove_tempmon_rrd_navigation
{%- endif %}

{% set perfstats = salt['omv_conf.get']('conf.system.monitoring.perfstats') %}
{% if chart_sensors and perfstats.enable | to_bool %}
generate_tempmon_rrd_graphs:
  cmd.run:
    - name: /usr/sbin/omv-mkrrdgraph
{% endif %}
