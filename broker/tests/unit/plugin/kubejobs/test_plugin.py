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

import unittest
import requests_mock
import json
import threading

from broker.plugins.kubejobs.plugin import KubeJobsExecutor
from broker.plugins.kubejobs.plugin import KubeJobsProvider

from broker.tests.unit.mocks.k8s_mock import MockKube
from broker.tests.unit.mocks.redis_mock import MockRedis

"""
Class that represents the tests of the KubeJobs plugin
"""


class TestKubeJobsPlugin(unittest.TestCase):

    """
    Set up KubeJobsExecutor objects
    """

    def setUp(self):

        self.job1 = KubeJobsExecutor("kj-000001")
        self.job1.k8s = MockKube("kj-000001")
        self.job1.waiting_time = 0
        self.job2 = KubeJobsExecutor("kj-000002")
        self.job2.k8s = MockKube("kj-000002")
        self.job2.waiting_time = 0

        with open('broker/tests/unit/mocks/body_request.json') as f:
            self.jsonRequest = json.load(f)

    def tearDown(self):
        pass

    """
    Test the start and stop of the KubeJobs plugin
    """

    def test_start_stop_application(self):

        with requests_mock.Mocker() as m:
            m.get("http://test.test", text="content\n")

            m.post(
                "http://0.0.0.0:5001/monitoring/%s" %
                self.job1.app_id, text="")
            m.put(
                "http://0.0.0.0:5001/monitoring/%s/stop" %
                self.job1.app_id, text="")

            m.post(
                "http://0.0.0.0:5000/scaling/%s" %
                self.job1.app_id, text="")
            m.put(
                "http://0.0.0.0:5000/scaling/%s/stop" %
                self.job1.app_id, text="")

            m.post(
                "http://0.0.0.0:5002/visualizing/%s" %
                self.job1.app_id, text="")
            m.put(
                "http://0.0.0.0:5002/visualizing/%s/stop" %
                self.job1.app_id, text="")
            m.get("http://0.0.0.0:5002/visualizing/%s" %
                  self.job1.app_id, text="{'url': 'http://mock.com'}")

            self.job1.rds = MockRedis()

            self.assertEqual(self.job1.get_application_state(), "created")

            thread_job1 = threading.Thread(target=self.job1.start_application,
                                           args=([self.jsonRequest]))

            thread_job1.start()

            next_states_job1 = ["ongoing", "completed"]
            while thread_job1.is_alive():
                current_state = self.job1.get_application_state()
                if current_state in next_states_job1:
                    next_states_job1.remove(current_state)

            self.assertTrue(len(next_states_job1) == 0)

    """
    Test the Get and Update Application State of
    the Kubejobs plugin.
    """

    def test_get_update_application_state(self):
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

    """
    Test that the terminate request works, changing the status to terminated
    and removing the redis resources.
    """

    def test_terminate_job(self):

        with requests_mock.Mocker() as m:
            m.get("http://test.test", text="content\n")

            m.post(
                "http://0.0.0.0:5001/monitoring/%s" %
                self.job2.app_id, text="")
            m.put("http://0.0.0.0:5001/monitoring/%s/stop" % self.job2.app_id)

            m.post(
                "http://0.0.0.0:5000/scaling/%s" %
                self.job2.app_id, text="")
            m.put(
                "http://0.0.0.0:5000/scaling/%s/stop" %
                self.job2.app_id, text="")

            m.post(
                "http://0.0.0.0:5002/visualizing/%s" %
                self.job2.app_id, text="")
            m.put(
                "http://0.0.0.0:5002/visualizing/%s/stop" %
                self.job2.app_id, text="")
            m.get("http://0.0.0.0:5002/visualizing/%s" %
                  self.job2.app_id, text="{'url': 'http://mock.com'}")

            self.job2.rds = MockRedis()

            self.assertEqual(self.job2.get_application_state(), "created")

            thread_job2 = threading.Thread(target=self.job2.start_application,
                                           args=([self.jsonRequest]))
            thread_job2.start()

            while thread_job2.is_alive():
                current_state = self.job2.get_application_state()
                if current_state == "ongoing":
                    self.job2.terminate_job()

            self.assertTrue(self.job2.get_application_state() == "terminated")

            with self.assertRaises(Exception):
                self.job2.k8s.read_namespaced_job("kj-000002")

    """
    Test that the stop request works, removing the queue job of redis.
    """

    def test_stop_job(self):

        with requests_mock.Mocker() as m:
            m.get("http://test.test", text="content\ncontent\ncontent\n")

            m.post(
                "http://0.0.0.0:5001/monitoring/%s" %
                self.job2.app_id, text="")
            m.put("http://0.0.0.0:5001/monitoring/%s/stop" % self.job2.app_id)

            m.post(
                "http://0.0.0.0:5000/scaling/%s" %
                self.job2.app_id, text="")
            m.put(
                "http://0.0.0.0:5000/scaling/%s/stop" %
                self.job2.app_id, text="")

            m.post(
                "http://0.0.0.0:5002/visualizing/%s" %
                self.job2.app_id, text="")
            m.put(
                "http://0.0.0.0:5002/visualizing/%s/stop" %
                self.job2.app_id, text="")
            m.get("http://0.0.0.0:5002/visualizing/%s" %
                  self.job2.app_id, text="{'url': 'http://mock.com'}")

            self.job2.rds = MockRedis()

            self.assertEqual(self.job2.get_application_state(), "created")

            thread_job2 = threading.Thread(target=self.job2.start_application,
                                           args=([self.jsonRequest]))
            thread_job2.start()

            while thread_job2.is_alive():
                current_state = self.job2.get_application_state()
                if current_state == "ongoing" and self.job2.rds.map != {}:
                    self.job2.stop_application()

            self.assertTrue(self.job2.get_application_state() == "completed")

            with self.assertRaises(Exception):
                self.job2.rds.delete("job")


class TestKubeJobsProvider(unittest.TestCase):

    """
    Set up KubeJobsProvider objects
    """

    def setUp(self):
        self.provider1 = KubeJobsProvider()
        self.provider2 = KubeJobsProvider()

    def tearDown(self):
        pass

    """
    Test the Get Title of the KubeJobs Provider
    """

    def test_get_title(self):
        self.assertEqual(self.provider1.get_title(),
                         'Kubernetes Batch Jobs Plugin')
        self.assertEqual(self.provider2.get_title(),
                         'Kubernetes Batch Jobs Plugin')

    """
    Test the Get Description of the KubeJobs Provider
    """

    def test_get_description(self):
        self.assertEqual(
            self.provider1.get_description(),
            'Plugin that allows utilization of Batch Jobs over a k8s cluster')
        self.assertEqual(
            self.provider1.get_description(),
            'Plugin that allows utilization of Batch Jobs over a k8s cluster')

    """
    Test the To Dict of the KubeJobs Provider
    """

    def test_to_dict(self):

        to_dict = self.provider1.to_dict()

        self.assertEqual(to_dict.get("name"),
                         "plugin_interface")
        self.assertEqual(to_dict.get("title"),
                         "Kubernetes Batch Jobs Plugin")
        self.assertEqual(
            to_dict.get("description"),
            'Plugin that allows utilization of Batch Jobs over a k8s cluster')

    """
    """

    def test_execute(self):
        pass


if __name__ == "__main__":
    unittest.main()
