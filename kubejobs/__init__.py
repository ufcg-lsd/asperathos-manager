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
import json
import redis
import requests
import six
import threading
import time
import uuid

from broker.service import api
from broker.plugins import base
from broker.persistence.etcd_db import plugin as etcd
from broker.persistence.sqlite import plugin as sqlite
from broker.utils import ids
from broker.utils import logger
from broker.utils.plugins import k8s
from broker.utils.framework import monitor, controller, visualizer
from broker import exceptions as ex


KUBEJOBS_LOG = logger.Log("KubeJobsPlugin", "logs/kubejobs.log")
application_time_log = \
    logger.Log("Application_time", "logs/application_time.log")
WAITING_TIME_DEFAULT = 600


class KubeJobsExecutor(base.GenericApplicationExecutor):

    def __init__(self, app_id, starting_time=None,
                 redis=None, status='created',
                 job_completed=False,
                 terminated=False,
                 visualizer_url="URL not generated!",
                 enable_visualizer=False):

        self.waiting_time_before_delete_job_resources = \
                WAITING_TIME_DEFAULT
        self.id = ids.ID_Generator().get_ID()
        self.app_id = app_id
        self.starting_time = starting_time
        self.rds = redis
        self.status = status
        self.job_completed = job_completed
        self.terminated = terminated
        self.visualizer_url = visualizer_url
        self.k8s = k8s
        self.db_connector = self.get_db_connector()
        self.enable_visualizer = enable_visualizer

    def __repr__(self):
        return json.dumps({
            "app_id": self.app_id,
            "starting_time": str(self.get_application_start_time()),
            "status": self.status,
            "visualizer_url": self.visualizer_url
        })

    def __reduce__(self):
        return (rebuild, (self.app_id,
                          self.starting_time,
                          self.status,
                          self.visualizer_url))

    def get_db_connector(self):
        if (api.plugin_name == "etcd"):
            return etcd.Etcd3JobPersistence(api.persistence_ip,
                                            api.persistence_port)

        elif (api.plugin_name == "sqlite"):
            return sqlite.SqliteJobPersistence()

    def start_application(self, data):
        try:
            self.persist_state()
            self.validate(data)
            self.activate_related_cluster(data)
            self.update_env_vars(data)
            redis_ip, redis_port = self.setup_redis()
            database_data, datasource_type = self.setup_visualizer(data)
            self.update_visualizer_info(data, database_data, redis_ip)
            self.start_visualization(data)
            self.persist_state()
            queue_size = self.push_jobs_to_redis(data)
            self.trigger_job(data)
            self.persist_state()
            self.update_monitor_info(data, database_data, datasource_type,
                                     queue_size, redis_ip, redis_port)
            self.start_monitoring(data)
            self.add_redis_info_to_data(data, redis_ip, redis_port)
            self.start_controlling(data)
            self.wait_job_finish(check_interval=1)
            self.change_state_to_completed()
            self.delete_job_resources(data)

        except Exception as ex:
            self.terminated = True
            self.update_application_state("error")
            KUBEJOBS_LOG.log("ERROR: %s" % ex)

        KUBEJOBS_LOG.log("Application finished.")

    def add_redis_info_to_data(self, data, redis_ip, redis_port):
        data.update({'redis_ip': redis_ip, 'redis_port': redis_port})

    def change_state_to_completed(self):
        if(self.get_application_state() == "ongoing"):
            self.update_application_state("completed")
        KUBEJOBS_LOG.log("Job finished")

    def get_workload(self, data):
        # Download files that contains the items
        jobs = requests.get(data['redis_workload']).text.\
            split('\n')[:-1]

        return jobs

    def activate_related_cluster(self, data):
        # If the cluster name is informed in data, active the cluster
        if('cluster_name' in data.keys()):
            api.v10.activate_cluster(data['cluster_name'], data)

    def update_env_vars(self, data):
        # inject REDIS_HOST in the environment
        data['env_vars']['REDIS_HOST'] = 'redis-%s' % self.app_id

        # inject SCONE_CONFIG_ID in the environment
        # FIXME: make SCONE_CONFIG_ID optional in submission
        data['env_vars']['SCONE_CONFIG_ID'] = data['config_id']

    def setup_redis(self):
        # Provision a redis database for the job. Die in case of error.
        redis_ip, redis_port = self.k8s.provision_redis_or_die(self.app_id)

        # create a new Redis client and fill the work queue
        if(self.rds is None):
            self.rds = redis.StrictRedis(host=redis_ip, port=redis_port)

        return redis_ip, redis_port

    def setup_visualizer(self, data):
        KUBEJOBS_LOG.log("Creating Visualization platform...")
        self.enable_visualizer = data['enable_visualizer']

        if self.enable_visualizer:
            datasource_type = data['visualizer_info']['datasource_type']

        database_data = self.setup_datasource(datasource_type)

        return database_data, datasource_type

    def setup_datasource(self, datasource_type):
        if datasource_type == "influxdb":
            database_data = self.k8s.create_influxdb(self.app_id)

        return database_data

    def update_visualizer_info(self, data, database_data, redis_ip):

        database_data.update({"url": redis_ip})
        data['visualizer_info'].\
            update({'database_data': database_data,
                    'enable_visualizer': data['enable_visualizer'],
                    'plugin': data['monitor_plugin'],
                    'visualizer_plugin': data['visualizer_plugin'],
                    'username': data['username'],
                    'password': data['password']})

    def update_monitor_info(self, data, database_data,
                            datasource_type, queue_size,
                            redis_ip, redis_port):

        schedule_strategy, heuristic_options = \
            self._get_control_parameters(data)

        data['monitor_info'].\
            update({'database_data': database_data,
                    'datasource_type': datasource_type,
                    'number_of_jobs': queue_size,
                    'submission_time': self.starting_time.
                    strftime('%Y-%m-%dT%H:%M:%S.%fGMT'),
                    'redis_ip': redis_ip,
                    'redis_port': redis_port,
                    'enable_visualizer': self.enable_visualizer,
                    'scaling_strategy': schedule_strategy,
                    'heuristic_options': heuristic_options
                    })
        # 'cpu_agent_port': agent_port})

    def _get_control_parameters(self, data):

        control_parameters = data['control_parameters']
        schedule_strategy = 'default'
        heuristic_options = None
        if 'schedule_strategy' in control_parameters:
            schedule_strategy = control_parameters['schedule_strategy']

        if 'heuristic_options' in control_parameters:
            heuristic_options = control_parameters['heuristic_options']

        return schedule_strategy, heuristic_options

    def start_visualization(self, data):
        visualizer.start_visualization(
            api.visualizer_url, self.app_id, data['visualizer_info'])

        self.visualizer_url = visualizer.get_visualizer_url(
                    api.visualizer_url, self.app_id)

        KUBEJOBS_LOG.log(
            "Dashboard of the job created on: %s" %
            (self.visualizer_url))

    def push_jobs_to_redis(self, data):

        jobs = self.get_workload(data)
        KUBEJOBS_LOG.log("Creating Redis queue")
        for job in jobs:
            self.rds.rpush("job", job)

        return len(jobs)

    def trigger_job(self, data):
        KUBEJOBS_LOG.log("Creating Job")

        self.k8s.create_job(self.app_id,
                            data['cmd'],
                            data['img'],
                            data['init_size'],
                            data['env_vars'],
                            config_id=data["config_id"])

        KUBEJOBS_LOG.log("Job running...")
        self.update_application_state("ongoing")
        self.starting_time = datetime.datetime.now()

    def start_monitoring(self, data, collect_period=1):
        monitor.start_monitor(api.monitor_url, self.app_id,
                              data['monitor_plugin'],
                              data['monitor_info'], collect_period)

    def start_controlling(self, data):
        controller.start_controller_k8s(api.controller_url,
                                        self.app_id, data)

    def wait_job_finish(self, check_interval=1):
        while not self.job_completed and not self.terminated:
            self.synchronize()
            time.sleep(check_interval)

    def delete_job_resources(self, data):
        time.sleep(self.waiting_time_before_delete_job_resources)
        if self.enable_visualizer:
            visualizer.stop_visualization(api.visualizer_url,
                                          self.app_id,
                                          data['visualizer_info'])

        monitor.stop_monitor(api.monitor_url, self.app_id)
        controller.stop_controller(api.controller_url,
                                   self.app_id)

        self.visualizer_url = "Url is dead!"
        KUBEJOBS_LOG.log("Stoped services")

        # delete redis resources
        if not self.get_application_state() == 'terminated':
            self.k8s.terminate_job(self.app_id)

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
        self.persist_state()

    def terminate_job(self):
        self.k8s.terminate_job(self.app_id)
        self.update_application_state("terminated")

    def stop_application(self):
        self.rds.delete("job")

    def errors(self):
        try:
            self.rds.ping()
        except redis.exceptions.ConnectionError:
            return ()
        return self.rds.lrange("job:errors", 0, -1)

    def persist_state(self):
        self.db_connector.\
            put(self.app_id, self)

    def synchronize(self):
        """ Infer the job state from job status in Kubernetes.
        If a job is active in Kubernetes, its state is 'ongoing'.
        If a job is not active in Kubernetes, it can be
        'completed' or 'failed'.
        If an exception has been thrown, the job does not exist,
        so its state is 'not found'.

        Returns:
        None -
        """
        try:
            current_status = self.k8s.get_job_status(self.app_id)
            if current_status.active is not None:
                self.update_application_state("ongoing")
            else:
                condition = current_status.conditions.pop().type
                if condition == 'Complete':
                    self.update_application_state("completed")
                    self.job_completed = True
                else:
                    self.update_application_state("failed")
                    self.terminated = True
        except Exception:
            final_states = ['completed', 'failed', 'error', 'created']
            if self.status not in final_states:

                self.update_application_state('not found')

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
        self.id_generator = ids.ID_Generator()

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


def rebuild(app_id, starting_time, status, visualizer_url):
    obj = KubeJobsExecutor(app_id=app_id,
                           starting_time=starting_time,
                           status=status,
                           visualizer_url=visualizer_url)
    return obj


PLUGIN = KubeJobsProvider
