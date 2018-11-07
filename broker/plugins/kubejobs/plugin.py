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

import requests
import redis
import threading
import time
import datetime
import uuid

from broker.plugins.base import GenericApplicationExecutor
from broker.plugins import base
from broker.utils.ids import ID_Generator
from broker.utils.logger import Log
from broker.utils.plugins import k8s
from broker.utils.framework import monitor
from broker.utils.framework import controller
from broker.service import api

LOG = Log("ChronosPlugin", "logs/chronos_plugin.log")
application_time_log = Log("Application_time", "logs/application_time.log")


class KubeJobsExecutor(GenericApplicationExecutor):

    def __init__(self, app_id):
        self.id = ID_Generator().get_ID()
        self.app_id = app_id

    def start_application(self, data):
        try:

            # Download files that contains the items
            jobs = requests.get(data['redis_workload']).text.\
                                split('\n')[:-1]


            # Provision a redis database for the job. Die in case of error.
            # TODO(clenimar): configure ``timeout`` via a request param,
            # e.g. api.redis_creation_timeout.
            redis_ip, redis_port = k8s.provision_redis_or_die(self.app_id)

            rds = redis.StrictRedis(host=redis_ip, port=redis_port)
            queue_size = len(jobs)

            print "Creating Redis queue"
            for job in jobs:
                rds.rpush("job", job)

            print "Creating Job"

            k8s.create_job(self.app_id,
                           data['cmd'], data['img'],
                           data['init_size'], data['env_vars'])

            starting_time = datetime.datetime.now().\
                strftime('%Y-%m-%dT%H:%M:%S.%fGMT')
            
            # Starting monitor
            data['monitor_info'].update({'count_jobs_url': api.count_queue,
                                         'number_of_jobs': queue_size,
                                         'submission_time': starting_time,
                                         'redis_ip': redis_ip,
                                         'redis_port': redis_port,
                                         'graphic_metrics': data['graphic_metrics']})

            monitor.start_monitor(api.monitor_url, self.app_id,
                                  data['monitor_plugin'],
                                  data['monitor_info'], 2)

            # Starting controller
            data.update({'redis_ip': redis_ip, 'redis_port': redis_port})
            controller.start_controller_k8s(api.controller_url,
                                             self.app_id, data)

            job_completed = False

            while not job_completed:
                time.sleep(1)
                job_completed = k8s.completed(self.app_id)

            # Stop monitor and controller
            print "job finished"
            monitor.stop_monitor(api.monitor_url, self.app_id)
            controller.stop_controller(api.controller_url, self.app_id)
            print "stoped services"
            # delete redis resources
            
            time.sleep(float(30))
            k8s.delete_redis_resources(self.app_id)

        except Exception as ex:
            print "ERROR: %s" % ex

        print "Application finished."

class KubeJobsProvider(base.PluginInterface):

    def __init__(self):
        self.id_generator = ID_Generator()

    def get_title(self):
        return 'Kubernetes Batch Jobs Plugin'

    def get_description(self):
        return 'Plugin that allows utilization of Batch Jobs over a k8s cluster'

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

