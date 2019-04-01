# Copyright (c) 2018 UFCG-LSD.
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
import time

import kubernetes as kube
import redis

from broker.service import api
from influxdb import InfluxDBClient
from broker.utils.logger import Log

KUBEJOBS_LOG = Log("KubeJobsPlugin", "logs/kubejobs.log")


def create_job(app_id, cmd, img, init_size, env_vars,
               config_id="",
               cas_addr="",
               scone_heap="200M",
               las_addr="172.17.0.1:18766",
               scone_hw="hw",
               scone_queues="4",
               scone_version="1",
               isgx="dev-isgx",
               devisgx="/dev/isgx",
               ):

    kube.config.load_kube_config(api.k8s_conf_path)

    obj_meta = kube.client.V1ObjectMeta(
        name=app_id)

    envs = []

    for key in env_vars.keys():

        var = kube.client.V1EnvVar(
                name=key,
                value=env_vars[key])

        envs.append(var)

    isgx = kube.client.V1VolumeMount(
        mount_path="/dev/isgx",
        name=isgx
    )

    devisgx = kube.client.V1Volume(
        name="dev-isgx",
        host_path=kube.client.V1HostPathVolumeSource(
            path=devisgx
        )
    )

    container_spec = kube.client.V1Container(
        command=cmd,
        env=envs,
        image=img,
        image_pull_policy="Always",
        name=app_id,
        tty=True,
        volume_mounts=[isgx],
        security_context=kube.client.V1SecurityContext(
            privileged=True
        ))
    pod_spec = kube.client.V1PodSpec(
        containers=[container_spec],
        restart_policy="OnFailure",
        volumes=[devisgx])
    pod = kube.client.V1PodTemplateSpec(
        metadata=obj_meta,
        spec=pod_spec)
    job_spec = kube.client.V1JobSpec(
        parallelism=init_size,
        template=pod)
    job = kube.client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=obj_meta,
        spec=job_spec)

    batch_v1 = kube.client.BatchV1Api()
    batch_v1.create_namespaced_job("default", job)

    return job


def provision_redis_or_die(app_id, namespace="default",
                           redis_port=6379, timeout=60):
    """Provision a redis database for the workload being executed.

    Create a redis-master Pod and expose it through a NodePort Service.
    Once created this method waits ``timeout`` seconds until the
    database is Ready, failing otherwise.
    """

    # load kubernetes config
    kube.config.load_kube_config(api.k8s_conf_path)

    # name redis instance as ``redis-{app_id}``
    name = "redis-%s" % app_id

    # create the Pod object for redis
    redis_pod_spec = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": name,
            "labels": {
                "app": name
            }
        },
        "spec": {
            "containers": [{
                "name": "redis-master",
                "image": "redis",
                "env": [{
                    "name": "MASTER",
                    "value": str(True)
                }],
                "ports": [{
                    "containerPort": redis_port
                }]
            }]
        }
    }

    # create the Service object for redis
    redis_svc_spec = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name
        },
        "spec": {
            "ports": [{
                "port": redis_port,
                "targetPort": redis_port
            }],
            "selector": {
                "app": name
            },
            "type": "NodePort"
        }
    }

    # create Pod and Service
    CoreV1Api = kube.client.CoreV1Api()
    node_port = None
    try:
        # TODO(clenimar): improve logging
        KUBEJOBS_LOG.log("creating pod...")
        CoreV1Api.create_namespaced_pod(
            namespace=namespace, body=redis_pod_spec)
        KUBEJOBS_LOG.log("creating service...")
        s = CoreV1Api.create_namespaced_service(
            namespace=namespace, body=redis_svc_spec)
        node_port = s.spec.ports[0].node_port
    except kube.client.rest.ApiException as e:
        KUBEJOBS_LOG.log(e)

    KUBEJOBS_LOG.log("created redis Pod and Service: %s" % name)

    # Gets the redis ip if the value is not explicit in the config file
    try:
        redis_ip = api.redis_ip
    except AttributeError:
        redis_ip = api.get_node_cluster(api.k8s_conf_path)

    # wait until the redis instance is Ready
    # (ie. accessible via the Service)
    # if it takes longer than ``timeout`` seconds, die
    redis_ready = False
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(5)
        KUBEJOBS_LOG.log("trying redis on %s:%s..." % (redis_ip, node_port))
        try:
            r = redis.StrictRedis(host=redis_ip, port=node_port)
            if r.info()['loading'] == 0:
                redis_ready = True
                KUBEJOBS_LOG.log("connected to redis on %s:%s!"
                                 % (redis_ip, node_port))
                break
        except redis.exceptions.ConnectionError:
            KUBEJOBS_LOG.log("redis is not ready yet")

    if redis_ready:
        return redis_ip, node_port
    else:
        KUBEJOBS_LOG.log("timed out waiting for redis to be available.")
        KUBEJOBS_LOG.log("redis address: %s:%d" % (name, node_port))
        KUBEJOBS_LOG.log("clean resources and die!")
        delete_redis_resources(app_id=app_id)
        # die!
        raise Exception("Could not provision redis")


def completed(app_id, namespace="default"):
    job_api = kube.client.BatchV1Api()
    job = job_api.read_namespaced_job_status(name=app_id, namespace=namespace)
    return job.status.completion_time is not None


def delete_redis_resources(app_id, namespace="default"):
    """Delete redis resources (Pod and Service) for a given ``app_id``"""

    # load kubernetes config
    kube.config.load_kube_config(api.k8s_conf_path)

    CoreV1Api = kube.client.CoreV1Api()

    KUBEJOBS_LOG.log("deleting redis resources for job %s" % app_id)
    name = "redis-%s" % app_id
    # create generic ``V1DeleteOptions``
    delete = kube.client.V1DeleteOptions()
    CoreV1Api.delete_namespaced_pod(
        name=name, namespace=namespace, body=delete)
    CoreV1Api.delete_namespaced_service(
        name=name, namespace=namespace, body=delete)


def terminate_job(app_id, namespace="default"):

    kube.config.load_kube_config(api.k8s_conf_path)

    batch_v1 = kube.client.BatchV1Api()

    delete = kube.client.V1DeleteOptions(propagation_policy='Foreground')

    delete_redis_resources(app_id)
    batch_v1.delete_namespaced_job(
        name=app_id, namespace=namespace, body=delete)


def create_influxdb(app_id, database_name="asperathos",
                    img="influxdb", namespace="default",
                    visualizer_port=8086, timeout=60):

    kube.config.load_kube_config(api.k8s_conf_path)

    influx_pod_spec = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "influxdb-%s" % app_id,
            "labels": {
                "app": "influxdb-%s" % app_id
            }
        },
        "spec": {
            "containers": [{
                "name": "influxdb-master",
                "image": img,
                "env": [{
                    "name": "MASTER",
                    "value": str(True)
                }],
                "ports": [{
                    "containerPort": visualizer_port
                }]
            }]
        }
    }

    influx_svc_spec = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "influxdb-%s" % app_id,
            "labels": {
                "app": "influxdb-%s" % app_id
            }
        },
        "spec": {
            "ports": [{
                "protocol": "TCP",
                "port": visualizer_port,
                "targetPort": visualizer_port
            }],
            "selector": {
                "app": "influxdb-%s" % app_id
            },
            "type": "NodePort"
        }
    }

    CoreV1Api = kube.client.CoreV1Api()
    node_port = None

    # Gets the redis ip if the value is not explicitic in the config file
    try:
        redis_ip = api.redis_ip
    except AttributeError:
        redis_ip = api.get_node_cluster(api.k8s_conf_path)

    try:
        KUBEJOBS_LOG.log("Creating InfluxDB Pod...")
        CoreV1Api.create_namespaced_pod(
            namespace=namespace, body=influx_pod_spec)
        KUBEJOBS_LOG.log("Creating InfluxDB Service...")
        s = CoreV1Api.create_namespaced_service(
            namespace=namespace, body=influx_svc_spec)
        ready = False
        attempts = timeout
        while not ready:
            read = CoreV1Api.read_namespaced_pod_status(name="influxdb-%s"
                                                        % app_id,
                                                        namespace=namespace)
            node_port = s.spec.ports[0].node_port

            if read.status.phase == "Running" and node_port is not None:
                try:
                    # TODO change redis_ip to node_ip
                    client = InfluxDBClient(redis_ip, node_port, 'root',
                                            'root', database_name)
                    client.create_database(database_name)
                    KUBEJOBS_LOG.log("InfluxDB is ready!!")
                    ready = True
                except Exception:
                    KUBEJOBS_LOG.log("InfluxDB is not ready yet...")
            else:
                attempts -= 1
                if attempts > 0:
                    time.sleep(1)
                else:
                    raise Exception("InfluxDB cannot be started!"
                                    "Time limite exceded...")
            time.sleep(1)

        influxdb_data = {"port": node_port, "name": database_name}
        return influxdb_data
    except kube.client.rest.ApiException as e:
        KUBEJOBS_LOG.log(e)
