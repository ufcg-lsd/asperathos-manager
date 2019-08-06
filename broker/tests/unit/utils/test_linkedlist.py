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

from broker.utils.linkedlist import LinkedList
from broker.utils.accumulated_sum_linked_list import AccumulatedSumLinkedList
from broker.service.job_cleaner_daemon import JobRepr


class TestLinkedList(unittest.TestCase):

    """
    Set up linkedlist object
    """

    def setUp(self):
        self.linkedlist = LinkedList()
        self.accumulated_sum_linked_list = AccumulatedSumLinkedList()

    def tearDown(self):
        pass

    """
    Test element insertion in linkedlist
    """

    def test_insert_element(self):

        element1 = JobRepr('kj-123123', 10)
        element2 = JobRepr('kj-321321', 10)
        element3 = JobRepr('kj-321111', 15)
        element4 = JobRepr('kj-321222', 5)
        element5 = JobRepr('kj-321222', 100)

        self.accumulated_sum_linked_list.insert(element1)
        self.accumulated_sum_linked_list.insert(element2)
        self.accumulated_sum_linked_list.insert(element3)
        self.accumulated_sum_linked_list.insert(element4)
        self.accumulated_sum_linked_list.insert(element5)

        remaining_time_list = [5, 5, 5, 85]
        app_ids_list = [['kj-321222'],
                        ['kj-123123', 'kj-321321'],
                        ['kj-321111'],
                        ['kj-321222']]

        obj_to_list = self.accumulated_sum_linked_list.to_list()

        for i in range(len(obj_to_list)):
            self.assertEqual(remaining_time_list[i],
                             obj_to_list[i].get_remaining_time())

            for j in range(len(app_ids_list[i])):
                self.assertTrue(app_ids_list[i][j] in
                                obj_to_list[i].get_app_ids())

    def test_push_element(self):

        element1 = JobRepr('kj-123123', 10)
        element2 = JobRepr('kj-321321', 10)
        element3 = JobRepr('kj-321111', 15)
        element4 = JobRepr('kj-321222', 5)
        element5 = JobRepr('kj-321222', 100)

        self.linkedlist.push(element1)
        self.linkedlist.push(element2)
        self.linkedlist.push(element3)
        self.linkedlist.push(element4)
        self.linkedlist.push(element5)

        remaining_time_list = [10, 10, 15, 5, 100]
        obj_to_list = self.linkedlist.to_list()

        app_ids_list = [['kj-123123'],
                        ['kj-321321'],
                        ['kj-321111'],
                        ['kj-321222'],
                        ['kj-321222']]

        for i in range(len(obj_to_list)):
            self.assertEqual(remaining_time_list[i],
                             obj_to_list[i].get_remaining_time())

            for j in range(len(app_ids_list[i])):
                self.assertTrue(app_ids_list[i][j] in
                                obj_to_list[i].get_app_ids())

    def test_pop_element(self):

        objs = [JobRepr('kj-123123', 10),
                JobRepr('kj-321321', 10),
                JobRepr('kj-321111', 15),
                JobRepr('kj-321222', 5),
                JobRepr('kj-321222', 100)]

        for obj in objs:
            self.linkedlist.push(obj)

        size = 5

        for i in range(size):
            self.assertEqual(self.linkedlist.pop().value, objs[i])
            size -= 1
            self.assertEqual(self.linkedlist.size(), size)

    def test_size(self):

        self.assertTrue(self.linkedlist.is_empty())
        self.assertEqual(self.linkedlist.size(), 0)

        self.linkedlist.push(0)
        self.linkedlist.push(50)

        self.assertFalse(self.linkedlist.is_empty())
        self.assertEqual(self.linkedlist.size(), 2)

        self.linkedlist.pop()
        self.assertFalse(self.linkedlist.is_empty())
        self.assertEqual(self.linkedlist.size(), 1)

        self.linkedlist.pop()
        self.assertTrue(self.linkedlist.is_empty())
        self.assertEqual(self.linkedlist.size(), 0)


if __name__ == "__main__":
    unittest.main()
