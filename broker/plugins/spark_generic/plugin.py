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

import os
import subprocess
import time
import threading
import uuid

from broker import exceptions as ex
from broker.plugins import base
from broker.service import api
from broker.utils import hdfs
from broker.utils import remote
from broker.utils import spark
from broker.utils.logger import Log, configure_logging

from broker.utils.ids import ID_Generator
from broker.plugins.base import GenericApplicationExecutor

plugin_log = Log("SparkGeneric_Plugin", "logs/sparkgeneric_plugin.log")
application_time_log = Log("Application_Time", "logs/application_time.log")
instances_log = Log("Instances", "logs/instances.log")

configure_logging()


class SparkGenericApplicationExecutor(GenericApplicationExecutor):

    def __init__(self, app_id, master_ip):
        self.application_state = "None"
        self.state_lock = threading.RLock()
        self.application_time = -1
        self.start_time = -1
        self.app_id = app_id
        self.master = master_ip

        self._verify_existing_log_paths(app_id)
        self._clean_log_files(app_id)

        self.running_log = Log("Running_Application_%s" % app_id,
                               "logs/apps/%s/execution" % app_id)

        self.stdout = Log("stdout_%s" % app_id, "logs/apps/%s/stdout" % app_id)
        self.stderr = Log("stderr_%s" % app_id, "logs/apps/%s/stderr" % app_id)

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

    def start_application(self, data, spark_applications_ids, app_id):
        try:
            self.update_application_state("Running")

            # Broker Parameters
            key_path = api.key_path
            remote_hdfs = api.remote_hdfs
            number_of_attempts = api.number_of_attempts
            master_ip = self.master

            # User Request Parameters
            args = data['args']
            main_class = data['main_class']
            dependencies = data['dependencies']
            job_binary_url = data['job_binary_url']

            self._log("%s | Master is %s" % (time.strftime("%H:%M:%S"),
                                             master_ip))

            job_status = self._hdfs_spark_execution(
                master_ip, remote_hdfs, key_path, args, job_binary_url,
                main_class, dependencies, spark_applications_ids,
                number_of_attempts)

            self._log("%s | Finished application execution" %
                      time.strftime("%H:%M:%S"))

            return job_status

        except KeyError as ke:
            self._log("%s | Parameter missing in submission: %s, "
                      "please check the config file" %
                      (time.strftime("%H:%M:%S"), str(ke)))

            self._log("%s | Finished application execution with error" %
                      (time.strftime("%H:%M:%S")))

            self.update_application_state("Error")

        except Exception:
            self._log("%s | Unknown error, please report to administrators "
                      "of WP3 infrastructure" % (time.strftime("%H:%M:%S")))

            self._log("%s | Finished application execution with error" %
                      (time.strftime("%H:%M:%S")))

            self.update_application_state("Error")

    def get_application_time(self):
        return self.application_time

    def _hdfs_spark_execution(self, master, remote_hdfs, key_path, args,
                              job_bin_url, main_class, dependencies,
                              spark_applications_ids, number_of_attempts):

        job_exec_id = str(uuid.uuid4())[0:7]
        self._log("%s | Job execution ID: %s" %
                  (time.strftime("%H:%M:%S"), job_exec_id))

        # Defining params
        local_path = '/tmp/spark-jobs/' + job_exec_id + '/'

        job_binary_path = hdfs.get_path(job_bin_url)

        # Create temporary job directories
        self._log("%s | Create temporary job directories" %
                  time.strftime("%H:%M:%S"))
        self._mkdir(local_path)

        # Create cluster directories
        self._log("%s | Creating cluster directories" %
                  time.strftime("%H:%M:%S"))
        remote.execute_command(master, key_path,
                               'mkdir -p %s' % local_path)

        # Get job binary from hdfs
        self._log("%s | Get job binary from hdfs" %
                  time.strftime("%H:%M:%S"))
        remote.copy_from_hdfs(master, key_path, remote_hdfs,
                              job_binary_path, local_path)

        # Enabling event log on cluster
        self._log("%s | Enabling event log on cluster" %
                  time.strftime("%H:%M:%S"))
        self._enable_event_log(master, key_path, local_path)

        # Submit job
        self._log("%s | Starting job" %
                  time.strftime("%H:%M:%S"))

        local_binary_file = (local_path + remote.list_directory(key_path,
                                                                master,
                                                                local_path))

        spark_job = self._submit_job(master, key_path, main_class,
                                     dependencies, local_binary_file, args)

        spark_app_id = spark.get_running_app(master,
                                             spark_applications_ids,
                                             number_of_attempts)

        if spark_app_id is None:
            self._log("%s | Error on submission of application, "
                      "please check the config file" %
                      time.strftime("%H:%M:%S"))

            (output, err) = spark_job.communicate()
            self.stdout.log(output)
            self.stderr.log(err)

            raise ex.ConfigurationError()

        spark_applications_ids.append(spark_app_id)

        (output, err) = spark_job.communicate()

        self.stdout.log(output)
        self.stderr.log(err)

        self._log("%s | Copy log from cluster" % (time.strftime("%H:%M:%S")))
        event_log_path = local_path + 'eventlog/'
        self._mkdir(event_log_path)

        remote_event_log_path = 'ubuntu@%s:%s%s' % (master, local_path,
                                                    spark_app_id)

        remote.copy(key_path, remote_event_log_path, event_log_path)

        spark_applications_ids.remove(spark_app_id)

        self.update_application_state("OK")

        return 'OK'

    def _submit_job(self, remote_instance, key_path, main_class,
                    dependencies, job_binary_file, args):
        args_line = ''
        for arg in args:
            args_line += arg + ' '

        spark_submit = ('/opt/spark/bin/spark-submit '
                        '--packages %(dependencies)s '
                        '--class %(main_class)s '
                        '--master spark://%(master)s:7077 '
                        '%(job_binary_file)s %(args)s ' %
                        {'dependencies': dependencies,
                         'main_class': main_class,
                         'master': remote_instance,
                         'job_binary_file': 'file://' + job_binary_file,
                         'args': args_line})

        if main_class == '':
            spark_submit = spark_submit.replace('--class', '')

        if dependencies == '':
            spark_submit = spark_submit.replace('--packages', '')

        job = remote.execute_command_popen(remote_instance,
                                           key_path,
                                           spark_submit)

        return job

    def _enable_event_log(self, master, key_path, path):
        enable_event_log_command = (
            "echo -e 'spark.executor.extraClassPath "
            "/usr/lib/hadoop-mapreduce/hadoop-openstack.jar\n"
            "spark.eventLog.enabled true\n"
            "spark.eventLog.dir "
            "file://%(path)s' > "
            "/opt/spark/conf/spark-defaults.conf" % {'path': path}
        )

        remote.execute_command(master, key_path, enable_event_log_command)

    def _log(self, string):
        plugin_log.log(string)
        self.running_log.log(string)

    def _verify_existing_log_paths(self, app_id):
        if not os.path.exists('logs'):
            os.mkdir('logs')
        elif not os.path.exists('logs/apps'):
            os.mkdir('logs/apps')
        if not os.path.exists('logs/apps/%s' % app_id):
            os.mkdir('logs/apps/%s' % app_id)

    def _clean_log_files(self, app_id):
        open("logs/apps/%s/execution" % app_id, "w").close()
        open("logs/apps/%s/stdout" % app_id, "w").close()
        open("logs/apps/%s/stderr" % app_id, "w").close()

    def _mkdir(self, path):
        subprocess.call('mkdir -p %s' % path, shell=True)


class SparkGenericProvider(base.PluginInterface):

    def __init__(self):
        self.applications = []
        self.spark_applications_ids = []
        self.id_generator = ID_Generator()
        self.masters = {}

    def get_title(self):
        return 'Spark Generic'

    def get_description(self):
        return 'Plugin that allows utilization of Spark clusters to run jobs'

    def to_dict(self):
        return {
            'name': self.name,
            'title': self.get_title(),
            'description': self.get_description(),
        }

    def update_running_clusters(self):
        for application in self.applications:
            state = application.get_application_state()
            if state == "Running":
                self.masters[application.master] = True
            else:
                self.masters[application.master] = False

    def execute(self, data):
        self.update_running_clusters()

        for ip in api.masters_ips:
            if ip not in self.masters:
                self.masters[ip] = False

        set_masters = set(self.masters.values())
        if len(set_masters) == 1 and True in set_masters:
            plugin_log.log("%s | All clusters busy" %
                           time.strftime("%H:%M:%S"))
            return ('', None)

        else:
            for master, status in self.masters.iteritems():
                if not status:
                    master_ip = master
                    self.masters[master] = True
                    break

            app_id = str(uuid.uuid4())[0:7]
            executor = SparkGenericApplicationExecutor(app_id, master_ip)

            handling_thread = threading.Thread(
                target=executor.start_application,
                args=(data,
                      self.spark_applications_ids,
                      app_id)
            )

            handling_thread.start()

            self.applications.append(executor)
            return (app_id, executor)
