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
from flask_cors import CORS

rest = u.Rest('v10', __name__)

CORS(rest, expose_headers='Authorization')


@rest.post('/submissions')
def run_submission(data):
    """ Run a new submission and returns a submission id.

    Normal response codes: 202
    Error response codes: 400, 401
    """
    return u.render(api.run_submission(data))


@rest.put('/submissions/<submission_id>/stop')
def stop_submission(submission_id, data):
    """ Stop a running submission.

    Normal response codes: 204
    Error response codes: 400, 401
    """
    return u.render(api.stop_submission(submission_id, data))


@rest.put('/submissions/<submission_id>/terminate')
def terminate_submission(submission_id, data):
    """ Terminate a running submission.

    Normal response codes: 204
    Error response codes: 400, 401
    """
    return u.render(api.terminate_submission(submission_id, data))


@rest.get('/submissions')
def list_submissions():
    """ List all submissions (done or not).

    Normal response codes: 200
    Error response codes: 400, 401
    """
    return u.render(api.list_submissions())


@rest.get('/submissions/<submission_id>')
def submission_status(submission_id):
    """ Show status of a specific submission.

    Normal response codes: 200
    Error response codes: 400
    """
    return u.render(api.submission_status(submission_id))


@rest.get('/submissions/<submission_id>/errors')
def submission_errors(submission_id):
    """ Show the errors in an execution.

    Normal response codes: 200
    Error response codes: 400, 401
    """
    return u.render(api.submission_errors(submission_id))


@rest.get('/submissions/<submission_id>/log')
def submission_log(submission_id):
    """ Show log of a specific submission.

    Normal response codes: 200
    Error response codes: 400
    """
    return u.render(api.submission_log(submission_id))


@rest.get('/submissions/<submission_id>/visualizer')
def submission_visualizer(submission_id):
    """ Return the visualizer URL of a specific submission.

    Normal response codes: 200
    Error response codes: 400
    """
    return u.render(api.submission_visualizer(submission_id))


@rest.post('/submissions/cluster')
def add_cluster(data):
    """ Add a new cluster reference in the Asperathos section.

    Normal response codes: 202
    Error response codes: 400, 401
    """
    return u.render(api.add_cluster(data))


@rest.post('/submissions/cluster/<cluster_name>/certificate')
def add_certificate(cluster_name, data):
    """ Add a certificate to a cluster reference in the Asperathos section.

    Normal response codes: 202
    Error response codes: 400, 401
    """
    return u.render(api.add_certificate(cluster_name, data))


@rest.delete('/submissions/cluster/<cluster_name>/\
             certificate/<certificate_name>/delete')
def delete_certificate(cluster_name, certificate_name, data):
    """ Delete a certificate to a cluster reference in the Asperathos section.

    Normal response codes: 202
    Error response codes: 400, 401
    """
    return u.render(api.delete_certificate(cluster_name,
                                           certificate_name, data))


@rest.delete('/submissions/cluster/<cluster_name>/delete')
def delete_cluster(cluster_name, data):
    """ Delete a cluster reference in the Asperathos section.

    Normal response codes: 202
    Error response codes: 400, 401
    """
    return u.render(api.delete_cluster(cluster_name, data))


@rest.put('/submissions/cluster/<cluster_name>/activate')
def activate_cluster(cluster_name, data):
    """ Start to use the informed cluster as active cluster
    in the Asperathos section.

    Normal response codes: 200
    Error response codes: 400
    """
    return u.render(api.activate_cluster(cluster_name, data))


@rest.get('/submissions/cluster')
def get_clusters():
    """ Get the list of usable clusters in a
    Asperathos Manager instance

    Normal response codes: 200
    Error response codes: 400
    """
    return u.render(api.get_clusters())


@rest.get('/submissions/cluster/activate')
def get_activated_cluster():
    """ Get the current active cluster in a
    Asperathos Manager instance

    Normal response codes: 200
    Error response codes: 400
    """
    return u.render(api.get_activated_cluster())


@rest.delete('/submissions/<submission_id>/delete')
def delete_submission(submission_id, data):
    """ Delete a done submission for the list of
    all submissions

    Normal response codes: 200
    Error response codes: 400
    """
    return u.render(api.delete_submission(submission_id, data))


@rest.delete('/submissions/delete')
def delete_all_submissions(data):
    """ Delete all done submissions from the list of all
    submissions.

    Normal response codes: 200
    Error response codes: 400
    """
    return u.render(api.delete_all_submissions(data))
