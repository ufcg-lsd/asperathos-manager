
# Copyright (c) 2017 UFCG-LSD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import requests
from broker.service import api
from broker.utils import logger

KUBEJOBS_LOG = logger.Log("KubeJobsPlugin", "logs/kubejobs.log")


def _get_monitor_data(plugin_info, collect_period=10):
    start_monitor_dict = {
        # 'plugin': plugin,
        'plugin_info': plugin_info,
        'collect_period': collect_period
    }
    start_monitor_body = json.dumps(start_monitor_dict)
    return start_monitor_body


def get_job_report(monitor_url, app_id, plugin, plugin_info):
    request_url = monitor_url + '/monitoring/' + app_id + '/report'
    headers = {'Content-type': 'application/json'}
    data = _get_monitor_data(plugin, plugin_info)
    resp = requests.get(request_url, data=data, headers=headers)
    return resp.status_code, json.loads(resp.text)


def get_detailed_report(monitor_url, app_id, plugin, plugin_info):
    request_url = monitor_url + '/monitoring/' + app_id + '/report/detailed'
    headers = {'Content-type': 'application/json'}
    KUBEJOBS_LOG.log("Getting monitor data")
    data = _get_monitor_data(plugin, plugin_info)
    KUBEJOBS_LOG.log("Requesting report")
    resp = requests.get(request_url, data=data, headers=headers)
    KUBEJOBS_LOG.log("Got report")
    return json.loads(resp.text)


def start_monitor(monitor_url, app_id, plugin_info, collect_period):
    request_url = monitor_url + '/monitoring/' + app_id
    headers = {'Content-type': 'application/json'}
    # plugin = plugin_info['plugin']
    data = _get_monitor_data(plugin_info, collect_period)
    requests.post(request_url, data=data, headers=headers)


def stop_monitor(monitor_url, app_id):
    request_url = monitor_url + '/monitoring/' + app_id + "/stop"
    headers = {'Content-type': 'application/json'}
    requests.put(request_url, headers=headers)


def install_plugin(source, plugin):
    payload = {
        "install_source": source,
        "plugin_source": plugin
    }
    return requests.post("{}/plugins".format(api.monitor_url),
                         json=payload)
