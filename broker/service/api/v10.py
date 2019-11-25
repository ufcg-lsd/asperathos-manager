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

import filecmp
import json
import os
import shutil
import socket
import datetime
import threading

from broker.service import plugin_service
from broker.persistence import check_basic_plugins
from broker.persistence.etcd_db import plugin as etcd
from broker.persistence.sqlite import plugin as sqlite
from broker.service import api
from broker.utils.logger import Log
from broker.utils.framework import authorizer
from broker.utils.framework import visualizer
from broker import exceptions as ex
from broker.service.job_cleaner_daemon import JobCleanerDaemon

API_LOG = Log("APIv10", "logs/APIv10.log")

clusters = {}
activated_cluster = None

SSH_KEY_PATH = '/root/.ssh/id_rsa.pub'

CLUSTER_CONF_PATH = "./data/clusters"


def setup_database():
    if api.plugin_name == 'etcd':
        return (etcd.Etcd3JobPersistence(api.persistence_ip,
                                         api.persistence_port),
                etcd.Etcd3PluginPersistence(api.persistence_ip,
                                            api.persistence_port))
    elif api.plugin_name == 'sqlite':
        return (sqlite.SqliteJobPersistence(),
                sqlite.SqlitePluginPersistence())

    else:
        raise Exception('Unknown database name')


db_connector, plugin_connector = setup_database()
check_basic_plugins(plugin_connector)


def restore_submissions_backup(db_connector):
    return db_connector.get_all()


submissions = restore_submissions_backup(db_connector)
job_cleaner_svc = JobCleanerDaemon(submissions)


def delete_jobs_resources_or_activate_cleaner_svc():
    finished_jobs = db_connector.get_finished_jobs()
    for job_id in finished_jobs:
        job = finished_jobs[job_id]
        now = datetime.datetime.now()
        elapsed_time = (now - job.finish_time)
        if elapsed_time.total_seconds() >= job.job_resources_lifetime:
            try:
                job.delete_job_resources()
            except Exception:
                job.del_resources_authorization = False
                job.persist_state()
        else:
            new_time = int(job.job_resources_lifetime -
                           elapsed_time.total_seconds())
            job_cleaner_svc.insert_element(job.app_id, new_time)


delete_jobs_resources_or_activate_cleaner_svc()


def create_thread(job):
    thread = threading.Thread(target=job.wait_job_finish)
    thread.daemon = True
    thread.start()


def recover_ongoing_jobs_thread(jobs):
    for key in jobs:
        job = jobs[key]
        if not job.job_completed and not job.terminated:
            create_thread(job)


recover_ongoing_jobs_thread(submissions)


def synchronize_jobs_with_the_cluster(jobs):
    for key in jobs:
        jobs[key].synchronize()


synchronize_jobs_with_the_cluster(submissions)


def install_plugin(data):
    plugin_repo = data.get('plugin_source')
    source = data.get('install_source')
    name = data.get('plugin_name')
    module = data.get('plugin_module')
    component = data.get('component')

    plugin_connector.put(plugin_name=name, source=source,
                         plugin_source=plugin_repo,
                         component=component,
                         plugin_module=module)

    if component == plugin_service.Components.MANAGER:
        installed = plugin_service.install_plugin(source, plugin_repo)
        if not installed:
            return {"message": "Error installing plugin"}, 400
        else:
            return {"message": "Plugin installed successfully"}, 200
    elif component == plugin_service.Components.VISUALIZER:
        response = plugin_service.install_in_visualizer(source, plugin_repo)
        return response.json(), response.status_code
    elif component == plugin_service.Components.MONITOR:
        response = plugin_service.install_in_monitor(source, plugin_repo)
        return response.json(), response.status_code
    elif component == plugin_service.Components.CONTROLLER:
        response = plugin_service.install_in_controller(source, plugin_repo)
        return response.json(), response.status_code


def get_ssh_key():
    with open(SSH_KEY_PATH) as f:
        key = f.read()

    return {"key": key.strip()}


def get_all_plugins():
    return [p.to_dict()
            for p in plugin_connector.get_all()]


def run_submission(data):
    plugin_service.check_submission(plugin_connector, data)
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

    plugin = plugin_service.get_plugin(data['plugin'])
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

    if submission_id not in submissions:
        API_LOG.log("Wrong request")
        raise ex.BadRequestException()

    if(hard_finish):
        submissions[submission_id].terminate_job()
    else:
        submissions[submission_id].stop_application()

    return {"job_id": submission_id}


def list_submissions():
    submissions_status = {}
    for key in submissions:

        submission = submissions.get(key)
        submission.synchronize()
        submissions_status[key] = \
            json.loads(submission.__repr__())

    return submissions_status


def submission_status(submission_id):
    if submission_id not in submissions:
        API_LOG.log("Wrong request")
        raise ex.BadRequestException()

    # TODO: Update status of application with more informations

    return json.loads(submissions.
                      get(submission_id).__repr__())


def submission_report(submission_id):
    if submission_id not in submissions:
        API_LOG.log("Wrong request")
        raise ex.BadRequestException()

    return submissions.get(submission_id).get_detailed_report()


def submission_log(submission_id):
    if submission_id not in submissions:
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
    if submission_id not in submissions:
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
    response = {"message": "There is no active cluster"}
    if (activate_cluster != None):
        response = {activated_cluster: clusters[activated_cluster]}
    return response


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
    if submission_id in submissions:
        submission = submissions[submission_id]

        delete_authorized = submission.del_resources_authorization
        job_isnt_ongoing = submission.get_application_state() != "ongoing"
        if job_isnt_ongoing and not delete_authorized:

            db_connector.delete(submission_id)
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
    db_connector.delete_all()

    for key in submissions.keys():
        delete_submission(key, data)


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
