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


class MockRedis():
    def __init__(self):
        self.map = {}

    def rpush(self, metric_queue, metric):
        if self.map.get(metric_queue) == None:
            self.map[metric_queue] = []
        
        self.map[metric_queue].append(metric)
    
    def rpop(self, metric_queue):    
        try:
            return self.map.get(metric_queue).pop(0)
        except Exception as e:
            print e 

    def delete(self, queue_name):
        
        self.map.pop(queue_name)
    
