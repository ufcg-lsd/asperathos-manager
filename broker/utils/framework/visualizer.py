# Copyright (c) 2018 UFCG-LSD.
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

import ast
import json
import requests


def start_visualization(visualizer_url, app_id, data):

    request_url = visualizer_url + '/visualizing/' + app_id
    headers = {'Content-type': 'application/json'}
    visualizer_body = json.dumps(data)

    requests.post(request_url, data=visualizer_body, headers=headers)


def stop_visualization(visualizer_url, app_id, data):

    request_url = visualizer_url + '/visualizing/' + app_id + '/stop'
    headers = {'Content-type': 'application/json'}

    visualizer_data = {}
    visualizer_data['plugin'] = data['plugin']
    visualizer_data['visualizer_plugin'] = data['visualizer_plugin']
    visualizer_data['datasource_type'] = data['datasource_type']
    visualizer_body = json.dumps(visualizer_data)

    requests.put(request_url, data=visualizer_body, headers=headers)


def get_visualizer_url(visualizer_url, app_id):

    request_url = visualizer_url + '/visualizing/' + app_id
    headers = {'Content-type': 'application/json'}

    response_data = requests.get(request_url, headers=headers)

    url = (ast.literal_eval(response_data.text))['url']

    return url
