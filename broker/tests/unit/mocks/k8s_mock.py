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


class Job():
    """
    Class that represents a mock of the Job object
    """

    def __init__(self, active):
        """ Constructor of the mock of a Job object

        Returns:
            Job: The simulation of a Job object
        """
        self.status = Status(active)


class Condition():

    def __init__(self):

        self.type = "Complete"


class Status():
    """
    Class that represents a mock of the Status object
    """

    def __init__(self, active):
        """ Constructor of the mock of a Status object

        Args:
            active (string): Representing status of the object.

        Returns:
            Status: The simulation of a Status object
        """
        self.active = active
        self.conditions = [Condition()]


class MockKube():
    """
    Class that represents a mock of the k8s object
    """

    def __init__(self, app_id, replicas=1, namespace="default"):
        """ Constructor of the mock of a k8s object

        Args:
            app_id (string): Representing id of the application.
            replicas (int): Representing number of replicas of the application
            namespace (string): Representing the namespace of the application

        Returns:
            MockKube: A mock of a k8s object
        """
        self.jobs = {namespace: {app_id: replicas}}

    def read_namespaced_job(self, name, namespace="default"):
        """ Function that simulates the read of a namespaced job

        Args:
            name (string): Representing name of the job.
            namespace (string): Representing the namespace of the job

        Returns:
            Job: The simulation of the Job object searched
        """
        out = Job(self.jobs[namespace][name])
        return out

    def create_job(self, app_id, cmd, img, init_size,
                   env_vars, config_id=""):
        """ Function that simulates the creation of a job

        Args:
            app_id (string): Representing id of the application
            cmd (string): Representing the command executed
            img (string): Representing the image of the application
            init_size (string): Representing the size of the application
            env_vars (string): Representing the environmental variables of
                            the application
            config_id (string): Representing the config id of the application

        Returns:
            None
        """
        pass

    def provision_redis_or_die(self, app_id):
        """ Function that simulates the provision of death of
        the redis

        Args:
            app_id (string): Representing id of the application

        Returns:
            tuple: Representing the redis_ip and node_port
        """
        return (None, None)

    def completed(self, app_id):
        """ Function that gets the status of completion of
        a job.

        Args:
            app_id (string): Representing id of the application

        Returns:
            bool: Representing the status of completion
            of the job
        """
        return True

    def delete_redis_resources(self, app_id):
        """ Function that simulates a deletion of the
        redis resources

        Args:
            app_id (string): Representing id of the application

        Returns:
            None
        """
        pass

    def terminate_job(self, app_id):
        """ Function that simulates a termination
        of the job.

        Args:
            app_id (string): Representing id of the application

        Returns:
            None
        """
        pass

    def create_influxdb(app_id, database_name="asperathos",
                        img="influxdb", namespace="default",
                        visualizer_port=8086, timeout=60):
        """ Function that simulates a InfluxDB creation.

        Args:
            app_id (string): Representing id of the application

        Returns:
            None
        """
        return {"port": 1234, "name": database_name}

    def get_job_status(self, app_id, namespace="default"):
        """ Function that simulates a request to job status.

        Args:
            app_id (string): Representing id of the application

        Returns:
            None
        """
        sts = Status(None)
        return sts
