# Copyright (c) 2013 Mirantis Inc.
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

import string
import six
import uuid


class SaharaException(Exception):
    """Base Exception for the Sahara Plugin

    To correctly use this class, inherit from it and define
    a 'message' and 'code' properties.
    """
    code = "UNKNOWN_EXCEPTION"
    message = "An unknown exception occurred"

    def __str__(self):
        return self.message

    def __init__(self, message=None, code=None, inject_error_id=True):
        self.uuid = uuid.uuid4()

        if code:
            self.code = code
        if message:
            self.message = message

        if inject_error_id:
            # Add Error UUID to the message if required
            self.message = (('%(message)s\nError ID: %(id)s')
                            % {'message': self.message, 'id': self.uuid})

        super(SaharaException, self).__init__(
            '%s: %s' % (self.code, self.message))


class NotFoundException(SaharaException):
    code = "NOT_FOUND"
    message_template = "Object '%s' is not found"

    # It could be a various property of object which was not found
    def __init__(self, value, message_template=None):
        self.value = value
        if message_template:
            formatted_message = message_template % value
        else:
            formatted_message = self.message_template % value

        super(NotFoundException, self).__init__(formatted_message)


class RemoteCommandException(SaharaException):
    code = "REMOTE_COMMAND_FAILED"
    message_template = "Error during command execution: \"%s\""

    def __init__(self, cmd, ret_code=None, stdout=None,
                 stderr=None):
        self.cmd = cmd
        self.ret_code = ret_code
        self.stdout = stdout
        self.stderr = stderr

        formatted_message = self.message_template % cmd

        def to_printable(s):
            return "".join(filter(lambda x: x in string.printable, s))

        if ret_code:
            formatted_message = '%s\nReturn code: %s' % (
                formatted_message, six.text_type(ret_code))

        if stderr:
            formatted_message = '%s\nSTDERR:\n%s' % (
                formatted_message, to_printable(stderr))

        if stdout:
            formatted_message = '%s\nSTDOUT:\n%s' % (
                formatted_message, to_printable(stdout))

        super(RemoteCommandException, self).__init__(formatted_message)


class TimeoutException(SaharaException):
    code = "TIMEOUT"
    message_template = ("'%(operation)s' timed out after %(timeout)i "
                        "second(s)")

    def __init__(self, timeout, op_name=None, timeout_name=None):
        if op_name:
            op_name = ("Operation with name '%s'") % op_name
        else:
            op_name = ("Operation")
        formatted_message = self.message_template % {
            'operation': op_name, 'timeout': timeout}

        if timeout_name:
            desc = ("%(message)s and following timeout was violated: "
                    "%(timeout_name)s")
            formatted_message = desc % {
                'message': formatted_message, 'timeout_name': timeout_name}

        super(TimeoutException, self).__init__(formatted_message)


class Forbidden(SaharaException):
    code = "FORBIDDEN"
    message = ("You are not authorized to complete this action")


class UnauthorizedException(Exception):
    code = "UNAUTHORIZED"
    message = ("You are not authorized to complete this action")


class BadRequestException(Exception):

    code = "BAD_REQUEST"
    message = ("Malformed message body")

    def __init__(self, message="Malformed message body"):
        message = message


class MalformedRequestBody(SaharaException):
    code = "MALFORMED_REQUEST_BODY"
    message_template = ("Malformed message body: %(reason)s")

    def __init__(self, reason):
        formatted_message = self.message_template % {"reason": reason}
        super(MalformedRequestBody, self).__init__(formatted_message)


class MaxRetriesExceeded(SaharaException):
    code = "MAX_RETRIES_EXCEEDED"
    message_template = ("Operation %(operation)s wasn't executed correctly "
                        "after %(attempts)d attempts")

    def __init__(self, attempts, operation):
        formatted_message = self.message_template % {'operation': operation,
                                                     'attempts': attempts}

        super(MaxRetriesExceeded, self).__init__(formatted_message)


class ClusterNotCreatedException(SaharaException):
    code = "CLUSTER_NOT_CREATED"
    message = "Cluster could not be created"


class ConfigurationError(SaharaException):
    code = "CONFIGURATION_ERROR"
    message = "The configuration has failed"
