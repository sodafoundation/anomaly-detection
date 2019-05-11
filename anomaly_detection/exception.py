# Copyright 2019 The OpenSDS Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six
from anomaly_detection import log
_FATAL_EXCEPTION_FORMAT_ERRORS = False
LOG = log.getLogger(__name__)


class AnomalyDetectionException(Exception):
    message = "An unknown exception occurred."
    code = 500
    headers = {}
    safe = False

    def __init__(self, message=None, detail_data={}, **kwargs):
        self.kwargs = kwargs
        self.detail_data = detail_data

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass
        for k, v in self.kwargs.items():
            if isinstance(v, Exception):
                self.kwargs[k] = six.text_type(v)

        if not message:
            try:
                message = self.message % kwargs

            except Exception:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation.')
                for name, value in kwargs.items():
                    LOG.error("%(name)s: %(value)s", {
                        'name': name, 'value': value})
                if _FATAL_EXCEPTION_FORMAT_ERRORS:
                    raise
                else:
                    # at least get the core message out if something happened
                    message = self.message
        elif isinstance(message, Exception):
            message = six.text_type(message)

        self.msg = message
        super(AnomalyDetectionException, self).__init__(message)


class NotAuthorized(AnomalyDetectionException):
    message = "Not authorized."
    code = 403


class AdminRequired(NotAuthorized):
    message = "User does not have admin privileges."


class PolicyNotAuthorized(NotAuthorized):
    message = "Policy doesn't allow %(action)s to be performed."


class Conflict(AnomalyDetectionException):
    message = "%(err)s"
    code = 409


class Invalid(AnomalyDetectionException):
    message = "Unacceptable parameters."
    code = 400


class NotFound(AnomalyDetectionException):
    message = "Resource could not be found."
    code = 404
    safe = True


class InvalidInput(Invalid):
    message = "Invalid input received: %(reason)s"


class LoopingCallDone(Exception):
    pass
