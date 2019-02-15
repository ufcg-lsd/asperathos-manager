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
from broker.utils.framework import optimizer
from broker.utils.framework import visualizer
from broker.utils.framework import controller
from broker.utils.framework import monitor
from broker import exceptions as ex


API_LOG = Log("APIv10", "logs/APIv10.log")

submissions = {}


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

        authorization = authorizer.get_authorization(api.authorization_url,
                                                    username, password)

        if not authorization['success']:
            API_LOG.log("Unauthorized request")
            raise ex.UnauthorizedException()

    else:
        if data['plugin'] not in api.plugins: raise ex.BadRequestException()
 
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

def end_submission(submission_id, data, hard_finish):

    if 'enable_auth' not in data:
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

    return this_status


def submission_log(submission_id):
    if submission_id not in submissions.keys():
        API_LOG.log("Wrong request")
        raise ex.BadRequestException()

    logs = {'execution':'', 'stderr':'', 'stdout': ''}

    exec_log = open("logs/apps/%s/execution" % submission_id, "r")
    stderr = open("logs/apps/%s/stderr" % submission_id, "r")
    stdout = open("logs/apps/%s/stdout" % submission_id, "r")

    remove_newline = lambda x: x.replace("\n","")
    logs['execution'] = map(remove_newline, exec_log.readlines())
    logs['stderr'] = map(remove_newline, stderr.readlines())
    logs['stdout'] = map(remove_newline, stdout.readlines())

    exec_log.close()
    stderr.close()
    stdout.close()

    return logs


""" Gets the visualizer url of a specific job.

Raises:
    ex.BadRequestException -- Trying to search info about a job that
    has never being submitted in this Asperathos instance.

Returns:
    dict -- Returns a dict with 'visualizer_url' as key and the url
            that gives access to the visualizer platform as value.
"""

def submission_visualizer(submission_id):

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
        visualizer_url = visualizer.get_visualizer_url(api.visualizer_url, submission_id)
    else:
        API_LOG.log("There is no process running in the Visualizer address")

    return {"visualizer_url": visualizer_url}

""" Add a new cluster that can be choose to be the active
   cluster in the Asperathos section in execution time.

Raises:
    ex.BadRequestException -- Missing cluster and authentication fields in request
    ex.UnauthorizedException -- Wrong authentication variables informed

Returns:
    dict -- Returns a dict with the cluster_name, 
    the status of the addition (success or failed) and a
    reason in case of 'failed' status
"""

def add_cluster(data):
    if ('cluster_name' not in data or 'cluster_config' not in data):
        API_LOG.log("Missing cluster fields in request")
        raise ex.BadRequestException("Missing cluster fields in request")

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

    try:
        controller.add_cluster(api.controller_url, data)
        monitor.add_cluster(api.monitor_url, data)
        visualizer.add_cluster(api.visualizer_url, data)
    except Exception:
        API_LOG.log("Error while adding the cluster in the other components")

    conf_name = data['cluster_name']
    conf_content = data['cluster_config']

    if(os.path.isfile("./data/clusters/%s/%s" % (conf_name, conf_name))):
        status = "failed"
        reason = "cluster already exists"
    else:
        os.makedirs("./data/clusters/%s" % (conf_name))
        conf_file = open("./data/clusters/%s/%s" % (conf_name, conf_name), "w")
        conf_file.write(conf_content)
        conf_file.close()
        status = "success"
        reason = ""

    return {"cluster_name": conf_name, "status": status, "reason": reason}


""" Add a certificate to a cluster that can be choose to be the active
   cluster in the Asperathos section in execution time.

Raises:
    ex.BadRequestException -- Missing cluster and authentication fields in request
    ex.UnauthorizedException -- Wrong authentication variables informed

Returns:
    dict -- Returns a dict with the cluster_name, certificate_name, 
    the status of the addition (success or failed) and a
    reason in case of 'failed' status
"""

def add_certificate(cluster_name, data):
    if ('certificate_name' not in data or 'certificate_content' not in data):
        API_LOG.log("Missing fields in request")
        raise ex.BadRequestException("Missing fields in request")

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

    try:
        controller.add_certificate(api.controller_url, cluster_name, data)
        monitor.add_certificate(api.monitor_url, cluster_name, data)
        visualizer.add_certificate(api.visualizer_url, cluster_name, data)
    except Exception:
        API_LOG.log("Error while adding the certificate in the other components")

    certificate_name = data['certificate_name']
    certificate_content = data['certificate_content']

    if(os.path.isdir("./data/clusters/%s" % (cluster_name))):
        if(os.path.isfile("./data/clusters/%s/%s" % (cluster_name, certificate_name))):
            status = "failed"
            reason = "certificate already exists"
        else:
            certificate_file = open("./data/clusters/%s/%s" % (cluster_name, certificate_name), "w")
            certificate_file.write(certificate_content)
            certificate_file.close()
            status = "success"
            reason = ""
    else:
        status = "failed"
        reason = "cluster does not exists"

    return {"cluster_name": cluster_name, "certificate_name": certificate_name, "status": status, "reason": reason}

""" Delete a certificate to a cluster that can be choose to be the active
   cluster in the Asperathos section in execution time.

Raises:
    ex.BadRequestException -- Missing parameters in request
    ex.UnauthorizedException -- Authetication problem

Returns:
    dict -- Returns a dict with the cluster_name, certificate_name, 
    the status of the deletion (success or failed) and a
    reason in case of 'failed' status
"""
def delete_certificate(cluster_name, certificate_name, data):

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
    
    try:
        controller.delete_cluster(api.controller_url, cluster_name, certificate_name, data)
        monitor.delete_cluster(api.monitor_url, cluster_name, certificate_name, data)
        visualizer.delete_cluster(api.visualizer_url, cluster_name, certificate_name, data)
    except Exception:
        API_LOG.log("Error while deleting the certificate in the other components")

    if(os.path.isdir("./data/clusters/%s" % (cluster_name))):
        if(os.path.isfile("./data/clusters/%s/%s" % (cluster_name, certificate_name))):
            os.remove("./data/clusters/%s/%s" % (cluster_name, certificate_name))
            status = "success"
            reason = ""
        else:
            status = "failed"
            reason = "certificate does not exists."
    else:
        status = "failed"
        reason = "cluster does not exists."

    return {"cluster_name": cluster_name, "certificate_name": certificate_name, "status": status, "reason": reason}

""" Delete a cluster that could be choose to be the active
    cluster in the Asperathos section in execution time.

Raises:
    ex.BadRequestException -- Missing parameters in request
    ex.UnauthorizedException -- Authetication problem

Returns:
    dict -- Returns a dict with the cluster_name, 
    the status of the activation (success or failed) and a
    reason in case of 'failed' status
"""
def delete_cluster(cluster_name, data):

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
    
    try:
        controller.delete_cluster(api.controller_url, cluster_name, data)
        monitor.delete_cluster(api.monitor_url, cluster_name, data)
        visualizer.delete_cluster(api.visualizer_url, cluster_name, data)
    except Exception:
        API_LOG.log("Error while deleting the cluster in the other components")

    conf_name = cluster_name

    if(not os.path.isfile("./data/clusters/%s/%s" % (conf_name, conf_name))):
        status = "failed"
        reason = "cluster does not exists in this Asperathos section"
    else:
        # Check if the cluster to be deleted is the currently active
        # if True, empty the config file currently being used.
        if(filecmp.cmp("./data/clusters/%s/%s" % (conf_name, conf_name), api.k8s_conf_path)):
            open(api.k8s_conf_path, 'w').close()

        shutil.rmtree("./data/clusters/%s/" % (conf_name))

        status = "success"
        reason = ""

    return {"cluster_name": conf_name, "status": status, "reason": reason}

""" Activate a cluster to be used in a Asperathos section

Raises:
    ex.BadRequestException -- Missing parameters in request
    ex.UnauthorizedException -- Authetication problem

Returns:
    dict -- Returns a dict with the cluster_name, 
    the status of the activation (success or failed) and a
    reason in case of 'failed' status
"""

def active_cluster(cluster_name, data):

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

    try:
        controller.active_cluster(api.controller_url, cluster_name, data)
        monitor.active_cluster(api.monitor_url, cluster_name, data)
        visualizer.active_cluster(api.visualizer_url, cluster_name, data)
    except Exception:
        API_LOG.log("Error while deleting the cluster into other components")

    conf_name = cluster_name

    if(not os.path.isfile("./data/clusters/%s/%s" % (conf_name, conf_name))):
        status = "failed"
        reason = "cluster does not exists in this Asperathos section"
    else:

        with open("./data/clusters/%s/%s" % (conf_name, conf_name), 'r') as f:
            with open(api.k8s_conf_path, 'w') as f1:
                for line in f:
                    f1.write(line) 
        
        status = "success"
        reason = ""

    return {"cluster_name": conf_name, "status": status, "reason": reason}
