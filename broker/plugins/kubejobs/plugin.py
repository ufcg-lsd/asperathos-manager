# Copyright (c) 2017 UPV-GryCAP & UFCG-LSD.
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

import datetime
import redis
import requests
import six
import threading
import time
import uuid

from broker import exceptions as ex
from broker.plugins.base import GenericApplicationExecutor
from broker.plugins import base
from broker.service import api
from broker.service.api import v10
from broker.utils.framework import monitor
from broker.utils.framework import controller
from broker.utils.framework import visualizer
from broker.utils.ids import ID_Generator
from broker.utils.logger import Log
from broker.utils.plugins import k8s

KUBEJOBS_LOG = Log("KubeJobsPlugin", "logs/kubejobs.log")
application_time_log = Log("Application_time", "logs/application_time.log")


class KubeJobsExecutor(GenericApplicationExecutor):

    def __init__(self, app_id):
        self.id = ID_Generator().get_ID()
        self.app_id = app_id
        self.starting_time = None
        self.rds = None
        self.status = "created"
        self.waiting_time = 600
        self.job_completed = False
        self.terminated = False
        self.visualizer_url = "URL not generated!"
        self.k8s = k8s

    def start_application(self, data):
        try:
            self.validate(data)
            # Download files that contains the items
            jobs = requests.get(data['redis_workload']).text.\
                split('\n')[:-1]

            # If the cluster name is informed in data, active the cluster
            if('cluster_name' in data.keys()):
                v10.activate_cluster(data['cluster_name'], data)

            # Provision a redis database for the job. Die in case of error.
            # TODO(clenimar): configure ``timeout`` via a request param,
            # e.g. api.redis_creation_timeout.
            redis_ip, redis_port = self.k8s.provision_redis_or_die(self.app_id)
            # agent_port = k8s.create_cpu_agent(self.app_id)

            # inject REDIS_HOST in the environment
            data['env_vars']['REDIS_HOST'] = 'redis-%s' % self.app_id

            # inject SCONE_CONFIG_ID in the environment
            # FIXME: make SCONE_CONFIG_ID optional in submission
            data['env_vars']['SCONE_CONFIG_ID'] = data['config_id']

            # create a new Redis client and fill the work queue
            if(self.rds is None):
                self.rds = redis.StrictRedis(host=redis_ip, port=redis_port)

            queue_size = len(jobs)

            # Check if a visualizer will be created
            self.enable_visualizer = data['enable_visualizer']

            # Create all visualizer components
            if self.enable_visualizer:
                # Specify the datasource to be used in the visualization
                datasource_type = data['visualizer_info']['datasource_type']

                if datasource_type == "influxdb":
                    database_data = k8s.create_influxdb(self.app_id)

                    # Gets the redis ip if the value is not explicit in the
                    # config file

                    try:
                        redis_ip = api.redis_ip
                    except AttributeError:
                        redis_ip = api.get_node_cluster(api.k8s_conf_path)

                    database_data.update({"url": redis_ip})
                    data['monitor_info'].update(
                        {'database_data': database_data})
                    data['visualizer_info'].update(
                        {'database_data': database_data})

                data['monitor_info'].update(
                    {'datasource_type': datasource_type})

                KUBEJOBS_LOG.log("Creating Visualization platform")

                data['visualizer_info'].update({
                    'enable_visualizer': data['enable_visualizer'],
                    'plugin': data['monitor_plugin'],
                    'visualizer_plugin': data['visualizer_plugin'],
                    'username': data['username'],
                    'password': data['password']})

                visualizer.start_visualization(
                    api.visualizer_url, self.app_id, data['visualizer_info'])

                self.visualizer_url = visualizer.get_visualizer_url(
                    api.visualizer_url, self.app_id)

                KUBEJOBS_LOG.log(
                    "Dashboard of the job created on: %s" %
                    (self.visualizer_url))

            KUBEJOBS_LOG.log("Creating Redis queue")
            for job in jobs:
                self.rds.rpush("job", job)

            KUBEJOBS_LOG.log("Creating Job")

            self.k8s.create_job(
                self.app_id,
                data['cmd'],
                data['img'],
                data['init_size'],
                data['env_vars'],
                config_id=data["config_id"])

            self.starting_time = datetime.datetime.now()

            # Starting monitor
            data['monitor_info'].update(
                {
                    'number_of_jobs': queue_size,
                    'submission_time': self.starting_time.
                    strftime('%Y-%m-%dT%H:%M:%S.%fGMT'),
                    'redis_ip': redis_ip,
                    'redis_port': redis_port,
                    'enable_visualizer': self.enable_visualizer})  # ,
            # 'cpu_agent_port': agent_port})

            monitor.start_monitor(api.monitor_url, self.app_id,
                                  data['monitor_plugin'],
                                  data['monitor_info'], 2)

            # Starting controller
            data.update({'redis_ip': redis_ip, 'redis_port': redis_port})
            controller.start_controller_k8s(api.controller_url,
                                            self.app_id, data)

            while not self.job_completed and not self.terminated:
                self.update_application_state("ongoing")
                self.job_completed = self.k8s.completed(self.app_id)
                time.sleep(1)

            # Stop monitor, controller and visualizer

            if(self.get_application_state() == "ongoing"):
                self.update_application_state("completed")

            KUBEJOBS_LOG.log("Job finished")

            time.sleep(float(self.waiting_time))

            if self.enable_visualizer:
                visualizer.stop_visualization(
                    api.visualizer_url, self.app_id, data['visualizer_info'])
            monitor.stop_monitor(api.monitor_url, self.app_id)
            controller.stop_controller(api.controller_url, self.app_id)

            self.visualizer_url = "Url is dead!"

            KUBEJOBS_LOG.log("Stoped services")

            # delete redis resources
            if not self.get_application_state() == 'terminated':
                self.k8s.terminate_job(self.app_id)

        except Exception as exception:
            self.update_application_state("error")
            KUBEJOBS_LOG.log("ERROR: %s" % exception)

        KUBEJOBS_LOG.log("Application finished.")

    def get_application_state(self):
        return self.status

    def get_visualizer_url(self):
        return self.visualizer_url

    def get_application_execution_time(self):
        if(self.starting_time is not None):
            return (
                datetime.datetime.now() -
                self.starting_time).total_seconds()
        else:
            return "Job is not running yet!"

    def get_application_start_time(self):
        if(self.starting_time is not None):
            return self.starting_time.strftime('%Y-%m-%dT%H:%M:%S.%fGMT')
        else:
            return "Job is not running yet!"

    def update_application_state(self, state):
        self.status = state

    def terminate_job(self):
        self.k8s.terminate_job(self.app_id)
        self.update_application_state("terminated")
        self.terminated = True

    def stop_application(self):
        self.rds.delete("job")

    def errors(self):
        try:
            self.rds.ping()
        except redis.exceptions.ConnectionError:
            return ()
        return self.rds.lrange("job:errors", 0, -1)

    def validate(self, data):
        data_model = {
            "cmd": list,
            "control_parameters": dict,
            "control_plugin": six.string_types,
            "env_vars": dict,
            "img": six.string_types,
            "init_size": int,
            "monitor_info": dict,
            "monitor_plugin": six.string_types,
            "redis_workload": six.string_types,
            "enable_visualizer": bool
            # The parameters below are only needed if enable_visualizer is True
            # "visualizer_plugin": six.string_types
            # "visualizer_info":dict
        }

        for key in data_model:
            if (key not in data):
                raise ex.BadRequestException(
                    "Variable \"{}\" is missing".format(key))
            if (not isinstance(data[key], data_model[key])):
                raise ex.BadRequestException(
                    "\"{}\" has unexpected variable type: {}. Was expecting {}"
                    .format(key, type(data[key]), data_model[key]))

        if (data["enable_visualizer"]):
            if ("visualizer_plugin" not in data):
                raise ex.BadRequestException(
                    "Variable \"visualizer_plugin\" is missing")

            if (not isinstance(data["visualizer_plugin"], six.string_types)):
                raise ex.BadRequestException(
                    "\"visualizer_plugin\" has unexpected variable type: {}.\
                     Was expecting {}"
                    .format(type(data["visualizer_plugin"]),
                            data_model["visualizer_plugin"]))

            if ("visualizer_info" not in data):
                raise ex.BadRequestException(
                    "Variable \"visualizer_info\" is missing")

            if (not isinstance(data["visualizer_info"], dict)):
                raise ex.BadRequestException(
                    "\"visualizer_info\" has unexpected variable type: {}.\
                    Was expecting {}"
                    .format(type(data["visualizer_info"]),
                            data_model["visualizer_info"]))

        if (not data["init_size"] > 0):
            raise ex.BadRequestException(
                "Variable \"init_size\" should be greater than 0")


class KubeJobsProvider(base.PluginInterface):

    def __init__(self):
        self.id_generator = ID_Generator()

    def get_title(self):
        return 'Kubernetes Batch Jobs Plugin'

    def get_description(self):
        return ('Plugin that allows utilization of '
                'Batch Jobs over a k8s cluster')

    def to_dict(self):
        return {
            'name': self.name,
            'title': self.get_title(),
            'description': self.get_description(),
        }

    def execute(self, data):
        app_id = 'kj-' + str(uuid.uuid4())[0:7]
        executor = KubeJobsExecutor(app_id)

        handling_thread = threading.Thread(target=executor.start_application,
                                           args=(data,))
        handling_thread.start()
        return app_id, executor
