# Copyright (c) 2017 UFCG-LSD and UPV-GRyCAP.
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

from broker import exceptions as ex
from broker.plugins import base
from broker.service import api
from broker.utils.framework import optimizer
from broker.utils.framework import monitor
from broker.utils.framework import controller
from broker.utils.plugins import mesos
from broker.utils import ssh
from broker.utils.logger import Log, configure_logging
from broker.plugins.base import GenericApplicationExecutor

from uuid import uuid4

import time
import threading

plugin_log = Log("Spark-Mesos_Plugin", "logs/mesos_plugin.log")
configure_logging()


class SparkMesosApplicationExecutor(GenericApplicationExecutor):

    def __init__(self, app_id, frameworks_url):
        self.application_state = "None"
        self.state_lock = threading.RLock()
        self.application_time = -1
        self.start_time = -1
        self.app_id = app_id
        self.frameworks_url = frameworks_url

    def get_application_state(self):
        with self.state_lock:
            state = self.application_state
        return state

    def update_application_state(self, state):
        with self.state_lock:
            self.application_state = state

    def get_application_execution_time(self):
        return self.application_time

    def get_application_start_time(self):
        return self.start_time

    def start_application(self, data):
        try:
            self.update_application_state("Running")
            plugin_log.log("%s | Starting application execution" %
                           (time.strftime("%H:%M:%S")))

            binary_url = str(data['binary_url'])
            execution_class = str(data['execution_class'])
            execution_parameters = str(data['execution_parameters'])
            expected_time = int(data['expected_time'])
            number_of_jobs = int(data['number_of_jobs'])
            starting_cap = int(data['starting_cap'])

            # Optimizer integration
            app_name = data['app_name']
            days = 0

            if app_name.lower() == 'bulma':
                if 'days' in data.keys():
                    days = data['days']
                else:
                    self._log("""%s | 'days' parameter missing"""
                              % (time.strftime("%H:%M:%S")))
                    raise ex.ConfigurationError()

            cores, vms = optimizer.get_info(api.optimizer_url,
                                            expected_time,
                                            app_name,
                                            days)
            optimizer_command = ''
            if cores >= 0:
                optimizer_command = ' --total-executor-cores %d ' % cores

            plugin_log.log("%s | Submission id: %s" %
                           (time.strftime("%H:%M:%S"), self.app_id))

            plugin_log.log("%s | Connecting with Mesos cluster..." %
                           (time.strftime("%H:%M:%S")))

            conn = ssh.get_connection(api.mesos_url, api.cluster_username,
                                      api.cluster_password,
                                      api.cluster_key_path)

            plugin_log.log("%s | Connected with Mesos cluster" %
                           (time.strftime("%H:%M:%S")))

            # Execute all the spark needed commands
            # to run an spark job from command line
            if execution_class != "" and execution_class is not None:
                # If the class field is empty, it means that the
                # job binary is python
                binary_path = '~/exec_bin.jar'
                spark_run = ('sudo %s --name %s '
                             + '--master mesos://%s:%s '
                             + optimizer_command
                             + '--class %s %s %s')
            else:
                binary_path = '~/exec_bin.py'
                spark_run = ('sudo %s --name %s '
                             + '--master mesos://%s:%s '
                             + optimizer_command
                             + '%s %s %s')

            plugin_log.log("%s | Download the binary to cluster" %
                           (time.strftime("%H:%M:%S")))

            try:
                stdin, stdout, stderr = conn.exec_command('wget %s -O %s' %
                                                          (binary_url,
                                                           binary_path))

                plugin_log.log("%s | Waiting for download the binary..." %
                               (time.strftime("%H:%M:%S")))

                # TODO: Fix possible wget error
                stdout.read()
                plugin_log.log("%s | Binary downloaded" %
                               (time.strftime("%H:%M:%S")))

            except Exception:
                plugin_log.log("%s | Error downloading binary" %
                               (time.strftime("%H:%M:%S")))
                self.update_application_state("Error")
                return "Error"

            i, o, e = conn.exec_command(spark_run % (api.spark_path,
                                                     self.app_id,
                                                     api.mesos_url,
                                                     api.mesos_port,
                                                     execution_class,
                                                     binary_path,
                                                     execution_parameters))

            # Discovery ips of the executors from Mesos
            # and discovery the ids on KVM using the ips
            list_vms_one = ('onevm list --user %s --password %s --endpoint %s'
                            % (api.one_username,
                               api.one_password,
                               api.one_url))

            stdin, stdout, stderr = conn.exec_command(list_vms_one)

            list_response = stdout.read()

            vms_ips, master = mesos.get_executors_ip(
                conn, self.frameworks_url, self.app_id
            )
            plugin_log.log("%s | Master: %s"
                           % (time.strftime("%H:%M:%S"), master))

            plugin_log.log("%s | Executors: %s"
                           % (time.strftime("%H:%M:%S"), vms_ips))

            vms_ids = mesos.extract_vms_ids(list_response)
            plugin_log.log("%s | Executors IDs: %s"
                           % (time.strftime("%H:%M:%S"), vms_ids))

            executors_vms_ids = []
            for ip in vms_ips:
                for id in vms_ids:
                    vm_info_one = ('onevm show %s '
                                   '--user %s '
                                   '--password %s '
                                   '--endpoint %s' % (id, api.one_username,
                                                      api.one_password,
                                                      api.one_url))

                    stdin, stdout, stderr = conn.exec_command(vm_info_one)
                    if ip in stdout.read():
                        executors_vms_ids.append(id)
                        break

            plugin_log.log("%s | Executors IDs: %s" %
                           (time.strftime("%H:%M:%S"), executors_vms_ids))

            # Set up the initial configuration of cpu cap
            controller.setup_environment(api.controller_url, executors_vms_ids,
                                         starting_cap, data)

            info_plugin = {"spark_submisson_url": master,
                           "expected_time": expected_time,
                           "number_of_jobs": number_of_jobs}

            plugin_log.log("%s | Starting monitor" %
                           (time.strftime("%H:%M:%S")))
            monitor.start_monitor(api.monitor_url, self.app_id,
                                  'spark-mesos', info_plugin, 2)

            plugin_log.log("%s | Starting controller" %
                           (time.strftime("%H:%M:%S")))
            controller.start_controller(api.controller_url,
                                        self.app_id,
                                        executors_vms_ids,
                                        data)

            # This command locks the plugin execution
            # until the execution be done
            print(o.read())

            plugin_log.log("%s | Stopping monitor" %
                           (time.strftime("%H:%M:%S")))
            monitor.stop_monitor(api.monitor_url, self.app_id)

            plugin_log.log("%s | Stopping controller" %
                           (time.strftime("%H:%M:%S")))
            controller.stop_controller(api.controller_url, self.app_id)

            plugin_log.log("%s | Remove binaries" %
                           (time.strftime("%H:%M:%S")))
            conn.exec_command('rm -rf ~/exec_bin.*')

            plugin_log.log("%s | Finished application execution" %
                           (time.strftime("%H:%M:%S")))

            self.update_application_state("OK")
            return 'OK'

        except Exception:
            plugin_log.log(Exception)
            self.update_application_state("Error")


class SparkMesosProvider(base.PluginInterface):
    def __init__(self):
        self.running_application = SparkMesosApplicationExecutor(None, None)

    def get_title(self):
        return 'Spark-Mesos on Open Nebula plugin for BigSea framework'

    def get_description(self):
        return 'It runs an spark application on a Mesos cluster'

    def to_dict(self):
        return {
            'name': self.name,
            'title': self.get_title(),
            'description': self.get_description(),
        }

    def busy(self):
        application_state = self.running_application.get_application_state()
        if application_state == "Running":
            return True
        else:
            return False

    def execute(self, data):
        if not self.busy():
            frameworks_url = "%s:%s" % (api.mesos_url,
                                        api.mesos_port)

            app_id = "app-spark-mesos-" + str(uuid4())[:8]
            executor = SparkMesosApplicationExecutor(app_id, frameworks_url)
            handling_thread = threading.Thread(
                target=executor.start_application, args=(data,)
            )
            handling_thread.start()

        else:
            plugin_log.log("%s | Cluster busy" % (time.strftime("%H:%M:%S")))
            return ("", None)

        self.running_application = executor
        return (app_id, executor)
