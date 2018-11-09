# Copyright (c) 2017 LSD - UFCG.
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

from broker.utils import api as u
from broker.service.api import v10 as api


rest = u.Rest('v10', __name__)


""" Run a new submission and returns a submission id.

    Normal response codes: 202
    Error response codes: 400, 401
"""
@rest.post('/submissions')
def run_submission(data):
    return u.render(api.run_submission(data)) 


""" Stop a running submission.

    Normal response codes: 204
    Error response codes: 400, 401
"""
@rest.put('/submissions/<submission_id>/stop')
def stop_submission(submission_id, data):
    return u.render(api.stop_submission(submission_id, data))


""" Terminate a running submission.

    Normal response codes: 204
    Error response codes: 400, 401
"""
@rest.put('/submissions/<submission_id>/terminate')
def terminate_submission(submission_id, data=None):
    return u.render(api.terminate_submission(submission_id, data))
 

""" List all submissions (done or not).

    Normal response codes: 200
    Error response codes: 400, 401
"""
@rest.get('/submissions')
def list_submissions():
    return u.render(api.list_submissions())


""" Show status of a specific submission.

    Normal response codes: 200
    Error response codes: 400
"""
@rest.get('/submissions/<submission_id>')
def submission_status(submission_id):
    return u.render(api.submission_status(submission_id))


""" Show log of a specific submission.
                                                                              
    Normal response codes: 200
    Error response codes: 400
"""
@rest.get('/submissions/<submission_id>/log')
def submission_log(submission_id):
    return u.render(api.submission_log(submission_id))
