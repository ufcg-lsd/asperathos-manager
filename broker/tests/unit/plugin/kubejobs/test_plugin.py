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

import copy
import json
import requests_mock
import unittest
import datetime

from broker import exceptions as ex
from kubejobs import KubeJobsExecutor
from kubejobs import KubeJobsProvider
from broker.service import api
from broker.tests.unit.mocks.k8s_mock import MockKube
from broker.tests.unit.mocks.persistence_mock import PersistenceMock
from broker.tests.unit.mocks.redis_mock import MockRedis
from broker.persistence.sqlite import plugin as sqlite


class TestKubeJobsPlugin(unittest.TestCase):
    """
    Class that represents the tests of the KubeJobs plugin
    """

    def setUp(self):
        """
        Set up KubeJobsExecutor objects
        """

        self.job_id1 = "kj-000001"
        self.job_id2 = "kj-000002"

        self.job1 = KubeJobsExecutor(self.job_id1)
        self.job1.k8s = MockKube(self.job_id1)
        self.job1.waiting_time_before_delete_job_resources = 0
        self.job1.db_connector = PersistenceMock()
        self.job1.rds = MockRedis()
        self.job2 = KubeJobsExecutor(self.job_id2)
        self.job2.k8s = MockKube(self.job_id2)
        self.job2.waiting_time_before_delete_job_resources = 0
        self.job2.db_connector = PersistenceMock()

        with open('broker/tests/unit/mocks/body_request.json') as f:
            self.jsonRequest = json.load(f)

    def tearDown(self):
        pass

    def test_repr(self):
        """
        Test that repr function return the correct representation
        of the object
        """
        job1_repr = {'app_id': self.job_id1,
                     'status': 'created',
                     'visualizer_url': "URL not generated!"
                     }

        job1 = json.loads(self.job1.__repr__())
        job1.pop('starting_time')
        self.assertEqual(job1, job1_repr)

    def test_get_db_connector(self):
        """
        Verify that get_db_connector returns the default persistence
        connector (Sqlite)
        """
        self.assertTrue(isinstance(self.job1.get_db_connector(),
                                   sqlite.SqlitePersistence))

    def test_get_workload(self):
        """
        Verify that the workload has been pulled correctly
        """
        data = {"redis_workload": "http://workload.com"}
        jobs = ["job1.com", "job2.com", "job3.com"]
        with requests_mock.Mocker() as m:
            m.get("http://workload.com", text="job1.com\njob2.com\njob3.com\n")

            self.assertEqual(self.job1.get_workload(data), jobs)

    def test_update_env_vars(self):
        """
        Verify that the enviroment variables has been updated
        """

        data = {'env_vars': {},
                'config_id': '123'}

        data_after = {'env_vars': {
                                    'REDIS_HOST': 'redis-' + self.job_id1,
                                    'SCONE_CONFIG_ID': '123'

                                   },
                      'config_id': '123'
                      }
        self.job1.update_env_vars(data)
        self.assertEqual(data, data_after)

    def test_setup_redis(self):
        """
        Verify that redis has been created and connected
        """
        self.assertEqual(self.job1.setup_redis(), ("0.0.0.0", "2364"))

    def test_setup_visualizer(self):
        """
        Verify that visualizer components has been created and connected
        """
        datasource_type = "influxdb"
        data = {'enable_visualizer': True,
                'visualizer_info':
                    {'datasource_type': datasource_type}
                }

        database_data = {'port': 1234, 'name': 'asperathos'}
        self.assertEqual(self.job2.setup_visualizer(data),
                         (database_data, datasource_type))

    def test_setup_datasource(self):
        """
        Verify that the influx database has been created and connected
        """
        datasource_type = "influxdb"
        database_data = {'port': 1234, 'name': 'asperathos'}
        self.assertEqual(self.job2.setup_datasource(datasource_type),
                         database_data)

    def test_update_visualizer_info(self):
        """
        Verify that the visualizer informations has been updated
        """
        redis_ip = "2364"
        database_data = {}
        data = {"visualizer_info": {},
                'enable_visualizer': True,
                'monitor_plugin': 'kubejobs',
                'visualizer_plugin': 'k8s-grafana',
                'username': 'asperathos',
                'password': 'asp'
                }

        database_data_after = {'url': redis_ip}
        visualizer_info_after = {'database_data': database_data,
                                 'enable_visualizer': True,
                                 'visualizer_plugin': 'k8s-grafana',
                                 'plugin': 'kubejobs',
                                 'username': 'asperathos',
                                 'password': 'asp'
                                 }

        self.job1.update_visualizer_info(data, database_data, redis_ip)
        self.assertEqual(data.get('visualizer_info'), visualizer_info_after)
        self.assertEqual(database_data, database_data_after)

    def test_update_monitor_info(self):
        """
        Verify that the monitor informations has been updated
        """
        data = {'monitor_info': {},
                'control_parameters': {
                    'schedule_strategy': '',
                    'heuristic_options': ''
                    }
                }
        database_data = {}
        datasource_type = 'influxdb'
        queue_size = 10
        redis_ip = '0.0.0.0'
        redis_port = '2364'

        monitor_info_after = {'database_data': database_data,
                              'datasource_type': datasource_type,
                              'number_of_jobs': queue_size,
                              'redis_ip': redis_ip,
                              'redis_port': redis_port,
                              'enable_visualizer': False,
                              'scaling_strategy': '',
                              'heuristic_options': ''
                              }

        now = datetime.datetime.now()
        self.job1.starting_time = now
        monitor_info_after.\
            update({'submission_time':
                    now.strftime('%Y-%m-%dT%H:%M:%S.%fGMT')})

        self.job1.update_monitor_info(data, database_data, datasource_type,
                                      queue_size, redis_ip, redis_port)
        self.assertEqual(data.get('monitor_info'), monitor_info_after)

    def test_start_visualization(self):
        """
        Verify that start visalization request has done without errors,
        and that visualizer url has been updated
        """
        with requests_mock.Mocker() as m:
            m.post(api.visualizer_url + '/visualizing/'
                   + self.job_id1, text="")
            m.get(api.visualizer_url + '/visualizing/' + self.job_id1,
                  text="{'url': 'http://visualizer-url'}")

            data = {'visualizer_info': {}}
            self.job1.start_visualization(data)
            self.assertEqual(self.job1.get_visualizer_url(),
                             "http://visualizer-url")

    def test_push_jobs_to_redis(self):
        """
        Verify that workload has been pushed to redis
        """
        data = {"redis_workload": "http://workload.com"}
        with requests_mock.Mocker() as m:
            m.get("http://workload.com", text="job1.com\njob2.com\njob3.com\n")

            length = self.job1.push_jobs_to_redis(data)
            self.assertEqual(length, 3)

    def test_trigger_job(self):
        """
        Verify that the job has been triggered
        """
        data = {'cmd': ['python', 'job.py'],
                'img': 'dockerhub.com/image:latest',
                'init_size': 1,
                'env_vars': {'VAR1': 123},
                'config_id': 12321
                }
        self.job1.trigger_job(data)
        self.assertEqual(self.job1.get_application_state(), 'ongoing')

    def test_start_monitoring(self):
        """
        Verify that start monitoring request has done without errors
        """
        data = {'monitor_info': {},
                'monitor_plugin': 'kubejobs'
                }
        with requests_mock.Mocker() as m:
            m.post(api.monitor_url + '/monitoring/' + self.job_id1, text="")
            self.job1.start_monitoring(data)

    def test_start_controlling(self):
        """
        Verify that start controlling request has done without errors
        """
        data = {}
        with requests_mock.Mocker() as m:
            m.post(api.controller_url + '/scaling/' + self.job_id1, text="")
            self.job1.start_controlling(data)

    def test_delete_job_resources(self):
        """
        Verify that stop monitoring, scaling and visualizing
        request has done without errors,
        """
        data = {'visualizer_info': {}}
        with requests_mock.Mocker() as m:
            m.put(api.visualizer_url + '/visualizing/'
                  + self.job_id1 + '/stop', text="")
            m.put(api.monitor_url + '/monitoring/'
                  + self.job_id1 + '/stop', text="")
            m.put(api.controller_url + '/scaling/'
                  + self.job_id1 + '/stop', text="")

            self.job1.delete_job_resources(data)

    def test_get_update_application_state(self):
        """
        Test the Get and Update Application State of
        the Kubejobs plugin.
        """
        self.assertEqual(self.job1.get_application_state(), "created")

        self.job1.update_application_state("ongoing")
        self.assertFalse(self.job1.get_application_state() == "created")
        self.assertEqual(self.job1.get_application_state(), "ongoing")

        self.job1.update_application_state("completed")
        self.assertFalse(self.job1.get_application_state() == "ongoing")
        self.assertEqual(self.job1.get_application_state(), "completed")

        self.assertEqual(self.job2.get_application_state(), "created")

        self.job2.update_application_state("ongoing")
        self.assertFalse(self.job2.get_application_state() == "created")
        self.assertEqual(self.job2.get_application_state(), "ongoing")

        self.job2.update_application_state("terminated")
        self.assertFalse(self.job2.get_application_state() == "ongoing")
        self.assertEqual(self.job2.get_application_state(), "terminated")

    def test_terminate_job(self):
        """
        Test that the terminate request works, changing
        the status to terminated and removing the redis resources.
        """
        self.job2.terminate_job()
        self.assertEqual('terminated', self.job2.get_application_state())

    def test_wrong_request_body(self):
        """
        Asserts that a BadRequestException will occur
        if one of the parameters is missing
        Args: None
        Returns: None
        """

        request_error_counter = len(self.jsonRequest)
        for key in self.jsonRequest:
            parameters_test = copy.deepcopy(self.jsonRequest)
            del parameters_test[key]
            try:
                self.job1.validate(parameters_test)
            except ex.BadRequestException:
                request_error_counter -= 1

        # The number 6 is due to the 4 parameters that doesn't require any
        # validation inside the plugin, these are:
        # enable_auth, password, username, config_id
        # And the other 2 that are optional, only needed if enable_visualizer
        # is set to true, wich not happen in this case
        # visualizer_plugin,visualizer_info
        self.assertEqual(request_error_counter, 6)

    def test_state_change(self):

        data = {'cmd': ['python', 'job.py'],
                'img': 'dockerhub.com/image:latest',
                'init_size': 1,
                'env_vars': {'VAR1': 123},
                'config_id': 12321
                }

        self.assertEqual(self.job1.get_application_state(), 'created')
        self.job1.trigger_job(data)
        self.assertEqual(self.job1.get_application_state(), 'ongoing')
        self.job1.change_state_to_completed()
        self.assertEqual(self.job1.get_application_state(), 'completed')


class TestKubeJobsProvider(unittest.TestCase):

    def setUp(self):
        """
        Set up KubeJobsProvider objects
        """
        self.provider1 = KubeJobsProvider()
        self.provider2 = KubeJobsProvider()

    def tearDown(self):
        pass

    def test_get_title(self):
        """
        Test the Get Title of the KubeJobs Provider
        """
        self.assertEqual(self.provider1.get_title(),
                         'Kubernetes Batch Jobs Plugin')
        self.assertEqual(self.provider2.get_title(),
                         'Kubernetes Batch Jobs Plugin')

    def test_get_description(self):
        """
        Test the Get Description of the KubeJobs Provider
        """
        self.assertEqual(
            self.provider1.get_description(),
            'Plugin that allows utilization of Batch Jobs over a k8s cluster')
        self.assertEqual(
            self.provider2.get_description(),
            'Plugin that allows utilization of Batch Jobs over a k8s cluster')

    def test_to_dict(self):
        """
        Test the To Dict of the KubeJobs Provider
        """
        to_dict = self.provider1.to_dict()

        self.assertEqual(to_dict.get("name"),
                         "plugin_interface")
        self.assertEqual(to_dict.get("title"),
                         "Kubernetes Batch Jobs Plugin")
        self.assertEqual(
            to_dict.get("description"),
            'Plugin that allows utilization of Batch Jobs over a k8s cluster')


if __name__ == "__main__":
    unittest.main()
