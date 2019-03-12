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

import time
import json
import requests
from requests.auth import HTTPBasicAuth


class ManagerChronos():

    def __init__(self, url, user, passwd):
        if (url[-1] == '/'):
            url = url[:-1]
        self.url = url  # + '/v1'
        self.user = user
        self.passwd = passwd
        self.auth = HTTPBasicAuth(user, passwd)
        self.max_retries = 100

    # Returns JSON with information of a target job
    def getInfo(self, jobName):
        url = self.url + '/scheduler/jobs/search?name=' + jobName
        response = None
        retries = 0
        ok = False
        while ((self.max_retries > retries) and (not ok)):
            retries += 1
            try:
                response = requests.request('GET', url, auth=self.auth)
                ok = True
            except requests.exceptions.ConnectionError:
                print(url + ': Connection refused, waiting 5 seconds...')
                time.sleep(5)
        if ok:
            if (response.status_code == 200):
                info = json.loads(str(response.text[1:-1]))
                return info
            else:
                print('ERROR: ' + str(response.status_code) + ' -> '
                      + jobName + ' does not exist')
        else:
            print('ERROR: Cannot connect to ' + url)
        return {}

    # Adding a Docker Job
    def sendJob(self, job):
        url = self.url + '/scheduler/iso8601'
        head = {'Content-type': 'application/json'}
        response = None
        retries = 0
        ok = False
        while ((self.max_retries > retries) and (not ok)):
            retries += 1
            try:
                # auth=(self.user, self.passwd)
                response = requests.post(url, headers=head,
                                         data=json.dumps(job),
                                         auth=self.auth)
                ok = True
            except requests.exceptions.ConnectionError:
                print(url + ': Connection refused, waiting 5 seconds...')
                time.sleep(5)
        if ok:
            if (response.status_code == 204):
                print('Successfully created job: ' + job['name'])
                return True
            else:
                print('ERROR: ' + str(response.status_code) +
                      ' when trying to create a Docker job: ' + job['name'])
        else:
            print('ERROR: Cannot connect to ' + url)
        return False

    # Deleting a Job
    def deleteJob(self, jobName):
        url = self.url + '/scheduler/job/' + jobName
        response = None
        retries = 0
        ok = False
        while self.max_retries > retries and not ok:
            retries += 1
            try:
                response = requests.request('DELETE', url, auth=self.auth)
                ok = True
            except requests.exceptions.ConnectionError:
                print(url + ': Connection refused, waiting 5 seconds...')
                time.sleep(5)
        if ok:
            if (response.status_code == 204):
                print('Successfully deleted job: ' + jobName)
                return True
            else:
                print('ERROR: ' + str(response.status_code) +
                      ' when trying to delete ' + jobName)
        else:
            print('ERROR: Cannot connect to ' + url)
        return False

    # Manually Starting a Job --> Job must exists
    def startJob(self, jobName):
        url = self.url + '/scheduler/job/' + jobName
        response = None
        retries = 0
        ok = False
        while self.max_retries > retries and not ok:
            retries += 1
            try:
                response = requests.request('PUT', url, auth=self.auth)
                ok = True
            except requests.exceptions.ConnectionError:
                print(url + ': Connection refused, waiting 5 seconds...')
                time.sleep(5)
        if ok:
            if (response.status_code == 204):
                print('Successfully started job: ' + jobName)
                return True
            else:
                print('ERROR: ' + str(response.status_code) +
                      ' when trying to start a Docker job: ' + jobName)
        else:
            print('ERROR: Cannot connect to ' + url)
        return False
