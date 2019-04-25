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
import sys
import threading
from anomaly_detection import log
from anomaly_detection import utils

LOG = log.getLogger(__name__)


class DBAPI(object):
    """Initialize the chosen DB API backend.
    """
    def __init__(self, backend_name, backend_mapping=None, lazy=False):

        self._backend = None
        self._backend_name = backend_name
        self._backend_mapping = backend_mapping or {}
        self._lock = threading.Lock()

        if not lazy:
            self._load_backend()

    def _load_backend(self):
        with self._lock:
            if not self._backend:
                # Import the untranslated name if we don't have a mapping
                backend_path = self._backend_mapping.get(self._backend_name,
                                                         self._backend_name)
                LOG.debug('Loading backend %(name)r from %(path)r',
                          {'name': self._backend_name,
                           'path': backend_path})
                print(backend_path)
                backend_mod = utils.import_module(backend_path)
                self._backend = backend_mod.get_backend()

    def __getattr__(self, key):
        if not self._backend:
            self._load_backend()
        return getattr(self._backend, key)

    @classmethod
    def from_config(cls, conf, backend_mapping=None, lazy=False):
        """Initialize DBAPI instance given a config instance.
        """
        return cls(backend_name=conf.database.backend,
                   backend_mapping=backend_mapping,
                   lazy=lazy)


class Config:
    class Database:
        backend = "sqlalchemy"
    database = Database


# TODO: Add support for other types of databases in a plugin model
_BACKEND_MAPPING = {'sqlalchemy': 'anomaly_detection.db.sqlalchemy.api'}

IMPL = DBAPI.from_config(Config, backend_mapping=_BACKEND_MAPPING, lazy=True)


def training_create(context, training_values):
    return IMPL.training_create(context, training_values)


def training_get(context, training_id):
    return IMPL.training_get(context, training_id)


def init_db():
    IMPL.init_db()
