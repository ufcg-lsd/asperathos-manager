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

from broker.utils.ids import ID_Generator

"""
Class that represents the tests of the ID Generator
"""


class TestIDGenerator(unittest.TestCase):

    """
    Set up IDGenerator objects
    """

    def setUp(self):
        self.obj1 = ID_Generator()

    def tearDown(self):
        pass

    """
    Test ID Generation of the KubeJobsProvider
    """

    def test_get_ID(self):
        self.assertEqual(self.obj1.id, 0)
        self.assertEqual(self.obj1.get_ID(), str(0))
        self.assertEqual(self.obj1.id, 1)
        self.assertEqual(self.obj1.get_ID(), str(1))
        self.assertEqual(self.obj1.id, 2)


if __name__ == "__main__":
    unittest.main()
