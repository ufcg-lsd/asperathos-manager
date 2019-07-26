# Copyright (c) 2017 UFGG-LSD.
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

import configparser
import kubernetes as kube
from broker.utils.logger import Log

API_LOG = Log("APIv10", "logs/APIv10.log")
CONFIG_PATH = "./data/conf"

try:
    # Conf reading
    config = configparser.RawConfigParser()
    config.read('./broker.cfg')

    """ Services configuration """
    monitor_url = config.get('services', 'monitor_url')
    controller_url = config.get('services', 'controller_url')
    visualizer_url = config.get('services', 'visualizer_url')
    authorization_url = config.get('services', 'authorization_url')
    optimizer_url = config.get('services', 'optimizer_url')

    """ General configuration """
    host = config.get("general", "host")
    port = config.getint('general', 'port')
    plugins = config.get('general', 'plugins').split(',')
    cleaner_interval = config.getint('general', 'cleaner_interval',
                                     fallback=1)

    """ Validate if really exists a section to listed plugins """
    for plugin in plugins:
        if plugin != '' and plugin not in config.sections():
            raise Exception("plugin '%s' section missing" % plugin)

    if 'persistence' in config.sections():
        if(config.has_option('persistence', 'plugin_name')):
            plugin_name = config.get('persistence', 'plugin_name')
        if(config.has_option('persistence', 'persistence_ip')):
            persistence_ip = config.get('persistence', 'persistence_ip')
        if(config.has_option('persistence', 'persistence_port')):
            persistence_port = config.get('persistence', 'persistence_port')
        if(config.has_option('persistence', 'local_database_path')):
            local_database_path = config.get('persistence',
                                             'local_database_path')
    # Setting a default persistence type
    else:
        plugin_name = 'sqlite'
        local_database_path = 'local_database/db.db'

    if 'kubejobs' in plugins:

        # Setting default values for the necessary variables
        k8s_conf_path = CONFIG_PATH

        # If explicitly stated in the cfg file, overwrite the variables
        if(config.has_section('kubejobs')):

            if(config.has_option('kubejobs', 'k8s_conf_path')):
                k8s_conf_path = config.get('kubejobs', 'k8s_conf_path')
            if(config.has_option('kubejobs', 'count_queue')):
                count_queue = config.get('kubejobs', 'count_queue')
            if(config.has_option('kubejobs', 'redis_ip')):
                redis_ip = config.get('kubejobs', 'redis_ip')

except Exception as e:
    print(e)
    API_LOG.log("Error: %s" % e)
    quit()


def get_node_cluster(k8s_conf_path):
    """ Gets the IP address of one slave node contained
    in a Kubernetes cluster. The k8s API aways returns information
    about the master node followed by the information of the slaves.
    Therefore, in order to avoid get the IP of the master node,
    this function always get the last node listed by the API.
    Raises:
        Exception -- It was not possible to connect with the
        Kubernetes cluster.
    Returns:
        string -- The node IP
    """
    try:
        kube.config.load_kube_config(k8s_conf_path)
        CoreV1Api = kube.client.CoreV1Api()
        for node in CoreV1Api.list_node().items:
            is_ready = \
                [s for s in node.status.conditions
                 if s.type == 'Ready'][0].status == 'True'
            if is_ready:
                node_info = node
        node_ip = node_info.status.addresses[0].address
        return node_ip
    except Exception:
        API_LOG.log("Connection with the cluster %s \
                    was not successful" % k8s_conf_path)
