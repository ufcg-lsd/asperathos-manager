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



def provision_redis_or_die(app_id, namespace="default", redis_port=6379, timeout=60):
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
        print("creating pod...")
        CoreV1Api.create_namespaced_pod(
            namespace=namespace, body=redis_pod_spec)
        print("creating service...")
        s = CoreV1Api.create_namespaced_service(
            namespace=namespace, body=redis_svc_spec)
        node_port = s.spec.ports[0].node_port
    except kube.client.rest.ApiException as e:
        print(e)

    print("created redis Pod and Service: %s" % name)

    # FIXME(clenimar): get node ip from k8s api instead of config
    redis_ip = api.redis_ip

    # wait until the redis instance is Ready
    # (ie. accessible via the Service)
    # if it takes longer than ``timeout`` seconds, die
    redis_ready = False
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(5)
        print("trying redis on %s:%s..." % (redis_ip, node_port))
        try:
            r = redis.StrictRedis(host=redis_ip, port=node_port)
            if r.info()['loading'] == 0:
                redis_ready = True
                print("connected to redis on %s:%s!" % (redis_ip, node_port))
                break
        except redis.exceptions.ConnectionError:
            print("redis is not ready yet")

    if redis_ready:
        return redis_ip, node_port
    else:
        print("timed out waiting for redis to be available.")
        print("redis address: %s:%d" % (name, node_port))
        print("clean resources and die!")
        delete_redis_resources(app_id=app_id)
        # die!
        raise Exception("Could not provision redis")

def completed(app_id, namespace="default"):
    job_api = kube.client.BatchV1Api()
    job = job_api.read_namespaced_job_status(name=app_id, namespace=namespace)
    return job.status.completion_time != None

def delete_redis_resources(app_id, namespace="default"):
    """Delete redis resources (Pod and Service) for a given ``app_id``"""

    # load kubernetes config
    kube.config.load_kube_config(api.k8s_conf_path)

    CoreV1Api = kube.client.CoreV1Api()

    print("deleting redis resources for job %s" % app_id)
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