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
import threading

from anomaly_detection.utils import config as cfg
from anomaly_detection import log
from anomaly_detection import utils

LOG = log.getLogger(__name__)
CONF = cfg.CONF

db_opts = [
    cfg.StrOpt('backend',
               default='sqlalchemy',
               help='The back end to use for the database.'),
    cfg.StrOpt('connection',
               help='The SQLAlchemy connection string to use to connect to '
                    'the database.',
               secret=True)
]
CONF.register_opts(db_opts, group='database')


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


# TODO: Add support for other types of databases in a plugin model
_BACKEND_MAPPING = {'sqlalchemy': 'anomaly_detection.db.sqlalchemy.api'}

IMPL = DBAPI.from_config(CONF, backend_mapping=_BACKEND_MAPPING, lazy=True)


def training_create(context, training_values):
    return IMPL.training_create(context, training_values)


def training_delete(context, training_id):
    return IMPL.training_delete(context, training_id)


def training_get(context, training_id):
    return IMPL.training_get(context, training_id)


def training_get_all(context):
    return IMPL.training_get_all(context)


def training_get_all_by_tenant(context, tenant_id):
    return IMPL.training_get_all_by_tenant(context, tenant_id)


def performance_create(context, performance_values):
    return IMPL.performance_create(context, performance_values)


def performance_delete(context, performance_id):
    return IMPL.performance_delete(context, performance_id)


def performance_get(context, performance_id):
    return IMPL.performance_get(context, performance_id)


def performance_get_all(context, fields=None, limit=None, offset=None,
                        sort_keys=None, sort_dirs=None):
    return IMPL.performance_get_all(context, fields=fields, limit=limit, offset=offset,
                                    sort_keys=sort_keys, sort_dirs=sort_dirs)


def performance_get_count(context):
    return IMPL.performance_get_count(context)


def init_db():
    IMPL.init_db()
