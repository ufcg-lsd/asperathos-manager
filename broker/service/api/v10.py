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

import os
import shutil
import socket
import filecmp

from broker.plugins import base as plugin_base
from broker.service import api
from broker.utils.logger import Log
from broker.utils.framework import authorizer
from broker.utils.framework import visualizer
from broker import exceptions as ex

API_LOG = Log("APIv10", "logs/APIv10.log")

submissions = {}
clusters = {}
activated_cluster = None

CLUSTER_CONF_PATH = "./data/clusters"


def run_submission(data):
    if ('plugin' not in data or 'plugin_info' not in data):
        API_LOG.log("Missing plugin fields in request")
        raise ex.BadRequestException("Missing plugin fields in request")

    if data['enable_auth']:
        if ('username' not in data or 'password' not in data):
            API_LOG.log("Missing plugin fields in request")
            raise ex.BadRequestException("Missing plugin fields in request")

        username = data['username']
        password = data['password']
        authorization = (authorizer.get_authorization(api.authorization_url,
                                                      username, password))

        if not authorization['success']:
            API_LOG.log("Unauthorized request")
            raise ex.UnauthorizedException()

    if data['plugin'] not in api.plugins:
        API_LOG.log("Plugin \"{}\" is missing.\
        The plugins available are {}".format(data['plugin'], api.plugin))
        raise ex.BadRequestException("Plugin \"{}\" is missing.\
        The plugins available are {}".format(data['plugin'], api.plugin))

    plugin = plugin_base.PLUGINS.get_plugin(data['plugin'])
    submission_data = data['plugin_info']
    submission_data['enable_auth'] = data['enable_auth']
    submission_id, executor = plugin.execute(submission_data)
    submissions[submission_id] = executor

    return {"job_id": submission_id}


def stop_submission(submission_id, data):
    return end_submission(submission_id, data, False)


def terminate_submission(submission_id, data):
    return end_submission(submission_id, data, True)


def submission_errors(submission_id):
    if submission_id not in submissions:
        return None
    return submissions[submission_id].errors()


def end_submission(submission_id, data, hard_finish):

    check_authorization(data)

    if submission_id not in submissions.keys():
        API_LOG.log("Wrong request")
        raise ex.BadRequestException()

    if(hard_finish):
        submissions[submission_id].terminate_job()
    else:
        submissions[submission_id].stop_application()

    return {"job_id": submission_id}


def list_submissions():
    submissions_status = {}

    for id in submissions.keys():
        this_status = {}
        submissions_status[id] = this_status

        this_status['status'] = (submissions[id].
                                 get_application_state())
        this_status['execution_time'] = (submissions[id].
                                         get_application_execution_time())
        this_status['start_time'] = (submissions[id].
                                     get_application_start_time())
        this_status['visualizer_url'] = (submissions[id].
                                         get_visualizer_url())
    return submissions_status


def submission_status(submission_id):
    if submission_id not in submissions.keys():
        API_LOG.log("Wrong request")
        raise ex.BadRequestException()

    # TODO: Update status of application with more informations

    this_status = {}
    this_status['status'] = (submissions[submission_id].
                             get_application_state())

    this_status['execution_time'] = (submissions[submission_id].
                                     get_application_execution_time())

    this_status['start_time'] = (submissions[submission_id].
                                 get_application_start_time())

    this_status['visualizer_url'] = (submissions[submission_id].
                                     get_visualizer_url())

    return {submission_id: this_status}


def submission_log(submission_id):
    if submission_id not in submissions.keys():
        API_LOG.log("Wrong request")
        raise ex.BadRequestException()

    logs = {'execution': '', 'stderr': '', 'stdout': ''}

    exec_log = open("logs/apps/%s/execution" % submission_id, "r")
    stderr = open("logs/apps/%s/stderr" % submission_id, "r")
    stdout = open("logs/apps/%s/stdout" % submission_id, "r")

    def remove_newline(x):
        x.replace("\n", "")
        return x

    logs['execution'] = map(remove_newline, exec_log.readlines())
    logs['stderr'] = map(remove_newline, stderr.readlines())
    logs['stdout'] = map(remove_newline, stdout.readlines())

    exec_log.close()
    stderr.close()
    stdout.close()

    return logs


def submission_visualizer(submission_id):
    """ Gets the visualizer url of a specific job.

    Raises:
        ex.BadRequestException -- Trying to search info about a job that
        has never being submitted in this Asperathos instance.

    Returns:
        dict -- Returns a dict with 'visualizer_url' as key and the url
            that gives access to the visualizer platform as value.
    """
    if submission_id not in submissions.keys():
        API_LOG.log("Wrong request")
        raise ex.BadRequestException()

    visualizer_url = ""

    # Check if the visualizer is active in this Asperathos instance
    # If true, call visualizer API to return the visualizer URL
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    address = api.visualizer_url.split('/')[-1]
    ip = address.split(':')[0]
    port = int(address.split(':')[1])
    result = sock.connect_ex((ip, port))

    if result == 0:
        API_LOG.log("Visualizing Running on port %s" % port)
        visualizer_url = visualizer.get_visualizer_url(api.visualizer_url,
                                                       submission_id)
    else:
        API_LOG.log("There is no process running in the Visualizer address")
        raise ex.BadRequestException("There is no process running \
                                     in the Visualizer address")

    return {"visualizer_url": visualizer_url}


def add_cluster(data):
    """ Add a new cluster that can be choose to be the active
    cluster in the Asperathos section in execution time.

    Raises:
        ex.BadRequestException -- Missing cluster and authentication
        fields in request
        ex.UnauthorizedException -- Wrong authentication variables informed

    Returns:
        dict -- Returns a dict with the cluster_name and
        the status of the addition
    """

    if ('cluster_name' not in data or 'cluster_config' not in data):
        API_LOG.log("Missing cluster fields in request")
        raise ex.BadRequestException("Missing cluster fields in request")

    check_authorization(data)

    conf_name = data['cluster_name']
    conf_content = data['cluster_config']

    if(os.path.isfile("%s/%s/%s" % (CLUSTER_CONF_PATH, conf_name, conf_name))):
        API_LOG.log("Cluster already exists in this Asperathos instance!")
        raise ex.BadRequestException("Cluster already exists \
                                     in this Asperathos instance!")
    else:
        clusters[conf_name] = {'conf_content': conf_content}
        clusters[conf_name]['active'] = False
        os.makedirs("%s/%s" % (CLUSTER_CONF_PATH, conf_name))
        conf_file = open("%s/%s/%s" % (CLUSTER_CONF_PATH,
                                       conf_name, conf_name), "w")
        conf_file.write(conf_content)
        conf_file.close()
        status = "success"

    return {"cluster_name": conf_name, "status": status}


def add_certificate(cluster_name, data):
    """ Add a certificate to a cluster that can be choose to be the active
    cluster in the Asperathos section in execution time.

    Raises:
        ex.BadRequestException -- Missing cluster and
        authentication fields in request
        ex.UnauthorizedException -- Wrong authentication variables informed

    Returns:
        dict -- Returns a dict with the cluster_name, certificate_name and
        the status of the addition
    """

    if ('certificate_name' not in data or 'certificate_content' not in data):
        API_LOG.log("Missing fields in request")
        raise ex.BadRequestException("Missing fields in request")

    check_authorization(data)

    certificate_name = data['certificate_name']
    certificate_content = data['certificate_content']

    if(os.path.isdir("%s/%s" % (CLUSTER_CONF_PATH, cluster_name))):
        if(os.path.isfile("%s/%s/%s" % (CLUSTER_CONF_PATH, cluster_name,
                                        certificate_name))):
            API_LOG.log("Certificate already exists in this \
                         Asperathos instance!")
            raise ex.BadRequestException("Certificate already exists in \
                                         this Asperathos instance!")
        else:
            certificate_file = open("%s/%s/%s" % (CLUSTER_CONF_PATH,
                                    cluster_name, certificate_name), "w")
            certificate_file.write(certificate_content)
            certificate_file.close()

            clusters[cluster_name][certificate_name] = certificate_content

            status = "success"
    else:
        API_LOG.log("Cluster does not exists in this Asperathos instance!")
        raise ex.BadRequestException("Cluster does not exists in this \
                                      Asperathos instance!")

    return {"cluster_name": cluster_name, "certificate_name": certificate_name,
            "status": status}


def delete_certificate(cluster_name, certificate_name, data):
    """ Delete a certificate to a cluster that can be choose to be the active
    cluster in the Asperathos section in execution time.

    Raises:
        ex.BadRequestException -- Missing parameters in request
        ex.UnauthorizedException -- Authetication problem

    Returns:
        dict -- Returns a dict with the cluster_name, certificate_name and
        the status of the deletion
    """
    check_authorization(data)

    if(os.path.isdir("%s/%s" % (CLUSTER_CONF_PATH, cluster_name))):
        if(os.path.isfile("%s/%s/%s" % (CLUSTER_CONF_PATH, cluster_name,
                                        certificate_name))):
            os.remove("%s/%s/%s" % (CLUSTER_CONF_PATH, cluster_name,
                                    certificate_name))

            del clusters[cluster_name][certificate_name]

            status = "success"
        else:
            API_LOG.log("Certificate does not exists in this \
                        Asperathos instance!")
            raise ex.BadRequestException("Certificate does not exists in \
                                         this Asperathos instance!")
    else:
        API_LOG.log("Cluster does not exists in this Asperathos instance!")
        raise ex.BadRequestException("Cluster does not exists in this \
                                     Asperathos instance!")

    return {"cluster_name": cluster_name,
            "certificate_name": certificate_name, "status": status}


def delete_cluster(cluster_name, data):
    """ Delete a cluster that could be choose to be the active
    cluster in the Asperathos section in execution time.

    Raises:
        ex.BadRequestException -- Missing parameters in request
        ex.UnauthorizedException -- Authetication problem

    Returns:
        dict -- Returns a dict with the cluster_name and
        the status of the activation
    """
    check_authorization(data)

    global activated_cluster
    conf_name = cluster_name

    if(not os.path.isfile("%s/%s/%s" % (CLUSTER_CONF_PATH,
                                        conf_name, conf_name))):
        API_LOG.log("Cluster does not exists in this Asperathos instance!")
        raise ex.BadRequestException("Cluster does not exists in this \
                                     Asperathos instance!")
    else:
        # Check if the cluster to be deleted is the currently active
        # if True, empty the config file currently being used.
        if(filecmp.cmp("%s/%s/%s" % (CLUSTER_CONF_PATH, conf_name,
                                     conf_name), api.k8s_conf_path)):
            open(api.k8s_conf_path, 'w').close()

        shutil.rmtree("%s/%s/" % (CLUSTER_CONF_PATH, conf_name))

        del clusters[cluster_name]

        # If this cluster is the active one, clear the
        # activate cluster variable
        if(cluster_name == activated_cluster):
            activated_cluster = None

        status = "success"

    return {"cluster_name": conf_name, "status": status}


def activate_cluster(cluster_name, data):
    """ Activate a cluster to be used in a Asperathos section

    Raises:
        ex.BadRequestException -- Missing parameters in request
        ex.UnauthorizedException -- Authetication problem

    Returns:
        dict -- Returns a dict with the cluster_name and
        the status of the activation
    """
    check_authorization(data)

    global activated_cluster
    conf_name = cluster_name

    if(not os.path.isfile("%s/%s/%s" % (CLUSTER_CONF_PATH,
                                        conf_name, conf_name))):
        API_LOG.log("Cluster does not exists in this Asperathos instance!")
        raise ex.BadRequestException("Cluster does not exists in this \
                                      Asperathos instance!")
    elif(cluster_name == activated_cluster):
        shutil.copyfile("%s/%s/%s" % (CLUSTER_CONF_PATH, conf_name,
                                      conf_name), api.k8s_conf_path)
        API_LOG.log("Cluster already activated in this Asperathos instance!")
        status = "success"
    else:
        shutil.copyfile("%s/%s/%s" % (CLUSTER_CONF_PATH, conf_name,
                                      conf_name), api.k8s_conf_path)
        status = "success"
        clusters[cluster_name]['active'] = True

        # If any cluster was already activated, deactivate it
        if(activated_cluster is not None):
            clusters[activated_cluster]['active'] = False

        # Update the new activate cluster
        activated_cluster = cluster_name

    return {"cluster_name": conf_name, "status": status}


def get_clusters():
    """ Get the list of usable clusters in the Asperathos Manager instance

    Returns:
        dict -- Returns a dict with the cluster_name as key and
        the cluster config content as value.
    """
    return clusters


def get_activated_cluster():
    """ Get the current active cluster in Asperathos Manager instance

    Returns:
        dict -- Returns a dict with the cluster_name as key and
        the cluster config content as value.
    """
    global activated_cluster
    return {activated_cluster: clusters[activated_cluster]}


def delete_submission(submission_id, data):
    """ Delete a done submission from the list of all
    submissions.

    Raises:
        ex.BadRequestException -- Missing parameters in request
        ex.BadRequestException -- Trying to delete a submission
        that does not exists
        ex.UnauthorizedException -- Authetication problem
    """
    check_authorization(data)

    if submission_id in submissions.keys():
        if submissions[submission_id].get_application_state() in \
                            ["completed", "terminated", "error"]:
            del submissions[submission_id]
            API_LOG.log("%s submission deleted from this \
                        Asperathos instance!" % (submission_id))
        else:
            API_LOG.log("%s submission still running in this \
                        Asperathos instance!" % (submission_id))
    else:
        API_LOG.log("Specified submission does not exists in this \
                    Asperathos instance!")
        raise ex.BadRequestException("Specified submission does not exists in \
                                     this Asperathos instance!")


def delete_all_submissions(data):
    """ Delete all done submissions from the list of all
    submissions.

    Raises:
        ex.BadRequestException -- Missing parameters in request
        ex.UnauthorizedException -- Authetication problem
    """
    check_authorization(data)

    for id in submissions.keys():
        delete_submission(id, data)


def check_authorization(data):
    """ Checks the user's need to authenticate to Asperathos

    Raises:
        ex.BadRequestException -- Missing parameters in request
        ex.UnauthorizedException -- Unauthorized request
    """
    if ('enable_auth' not in data):
        API_LOG.log("Missing parameters in request")
        raise ex.BadRequestException()

    enable_auth = data['enable_auth']

    if enable_auth:
        if 'username' not in data or 'password' not in data:
            API_LOG.log("Missing parameters in request")
            raise ex.BadRequestException()

        username = data['username']
        password = data['password']

        authorization = authorizer.get_authorization(api.authorization_url,
                                                     username, password)
        if not authorization['success']:
            API_LOG.log("Unauthorized request")
            raise ex.UnauthorizedException()
