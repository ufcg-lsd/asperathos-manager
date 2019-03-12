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

import time
import json


def extract_vms_ids(output):
    lines = output.split('\n')
    ids = []
    for i in range(1, len(lines) - 1):
        ids.append(lines[i].split()[0])

    return ids


def get_executors_ip(conn, get_frameworks_url, app_id):
    frameworks_call = ('curl http://' + get_frameworks_url + '/frameworks')

    time.sleep(5)
    stdin, stdout, sterr = conn.exec_command(frameworks_call)

    try:
        output = stdout.read()
        mesos_resp = json.loads(output)
    except Exception as e:
        print(e)
        mesos_resp = {}

    executors_ips = []
    framework = None
    find_fw = False

    # It must to ensure that the application was
    # started before try to get the executors
    while not find_fw:
        for f in mesos_resp['frameworks']:
            if f['name'] == app_id:
                framework = f
                find_fw = True
                break
        if not find_fw:
            stdin, stdout, sterr = conn.exec_command(frameworks_call)
            mesos_resp = json.loads(stdout.read())

        time.sleep(2)

    # Look for app-id into the labels and
    # get the framework that contains it
    for t in framework['tasks']:
        for s in t['statuses']:
            for n in s['container_status']['network_infos']:
                for i in n['ip_addresses']:
                    executors_ips.append(i['ip_address'])

    return executors_ips, framework['webui_url']
