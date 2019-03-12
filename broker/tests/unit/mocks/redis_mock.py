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

"""
Class that represents a mock of the redis object
"""


class MockRedis():

    """ Constructor of the mock of a redis object

    Returns:
        MockRedis: The simulation of a redis object
    """

    def __init__(self):
        self.map = {}

    """ Function the simulates the push of a job in the
        redis queue

    Args:
        metric_queue (string): Representing the metric queue
        metric (Object): Representing the metric to be pushed in the
                         queue.

    Returns:
        None
    """

    def rpush(self, metric_queue, metric):
        if self.map.get(metric_queue) is None:
            self.map[metric_queue] = []

        self.map[metric_queue].append(metric)

    """ Function the simulates the pop of a job from the
        redis queue

    Args:
        metric_queue (string): Representing the metric queue

    Returns:
        Object: Representing the metric pop from the queue
    """

    def rpop(self, metric_queue):
        try:
            return self.map.get(metric_queue).pop(0)
        except Exception as e:
            print(e)

    """ Function the simulates the deletion of a
        redis queue

    Args:
        queue_name (string): Representing the name of the queue to
                             be deleted.

    Returns:
        None
    """

    def delete(self, queue_name):
        self.map.pop(queue_name)
