# Copyright (c) 2019 UFCG-LSD.
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

from broker.solution.linkedlist import LinkedList
from broker.service.job_cleaner_daemon import JobCleanerDaemon
class TestIDGenerator(unittest.TestCase):

    """
    Set up IDGenerator objects
    """

    def setUp(self):
        self.obj1 = LinkedList()

    def tearDown(self):
        pass

    """
    Test ID Generation of the KubeJobsProvider
    """

    def test_add_element(self):

        element1 = JobCleanerDaemon('kj-123123', 10)
        element2 = JobCleanerDaemon('kj-321321', 10)
        element3 = JobCleanerDaemon('kj-321111', 15)
        element4 = JobCleanerDaemon('kj-321222', 5)

        self.obj1.insert(element1)
        self.obj1.insert(element2)
        self.obj1.insert(element3)
        self.obj1.insert(element4)
        self.obj1.insert(JobCleanerDaemon('kj-321111', 15))
        self.obj1.insert(JobCleanerDaemon('kj-321111', 0))        
        self.obj1.insert(JobCleanerDaemon('kj-321111', 100))
        # self.obj1.insert(JobCleanerDaemon('kj-321111', ))  

        print self.obj1.to_list()
        self.assertEqual(1,2)



if __name__ == "__main__":
    unittest.main()
