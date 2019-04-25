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

from anomaly_detection.db.sqlalchemy import models
from anomaly_detection import exception
from anomaly_detection.utils import uuid
from functools import wraps
import sqlalchemy.orm
import copy
import warnings
import sys


class Session(sqlalchemy.orm.session.Session):
    """Custom Session class to avoid SqlAlchemy Session monkey patching."""


class EngineFacade(object):
    def __init__(self, sql_connection, slave_connection=None, autocommit=True,
                 expire_on_commit=False, _conf=None, _factory=None, **kwargs):

        engine_kwargs = {
            'idle_timeout': kwargs.get('idle_timeout', 3600),
        }

        maker_kwargs = {
            'autocommit': autocommit,
            'expire_on_commit': expire_on_commit
        }
        self._engine = self._create_engine(sql_connection=sql_connection, **engine_kwargs)
        self._session_maker = self._get_maker(engine=self._engine, **maker_kwargs)
        if slave_connection:
            self._slave_engine = self._create_engine(sql_connection=sql_connection, **engine_kwargs)
            self._slave_session_maker = self._get_maker(engine=self._engine, **maker_kwargs)
        else:
            self._slave_engine = None
            self._slave_session_maker = None

    @staticmethod
    def _create_engine(sql_connection, idle_timeout=3600):
        engine_args = {
            "pool_recycle": idle_timeout,
            'convert_unicode': True,
        }
        engine = sqlalchemy.create_engine(sql_connection, **engine_args)
        return engine

    @staticmethod
    def _get_maker(engine, autocommit=True, expire_on_commit=False):
        maker = sqlalchemy.orm.sessionmaker(bind=engine,
                                            class_=Session,
                                            autocommit=autocommit,
                                            expire_on_commit=expire_on_commit)
        return maker

    def get_engine(self, use_slave=False):
        if use_slave:
            return self._slave_engine
        return self._engine

    def get_session(self, use_slave=False, **kwargs):
        if use_slave:
            return self._slave_session_maker(**kwargs)
        return self._session_maker(**kwargs)


_DEFAULT_SQL_CONNECTION = 'sqlite:///anomaly_detection.db'
_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = EngineFacade(_DEFAULT_SQL_CONNECTION)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def get_backend():
    """The backend is this module itself."""

    return sys.modules[__name__]


def is_admin_context(context):
    """Indicates if the request context is an administrator."""
    if not context:
        warnings.warn('Use of empty request context is deprecated',
                      DeprecationWarning)
        raise Exception('die')
    return context.is_admin


def is_user_context(context):
    """Indicates if the request context is a normal user."""
    if not context:
        return False
    if context.is_admin:
        return False
    if not context.user_id or not context.tenant_id:
        return False
    return True


def require_admin_context(f):
    """Decorator to require admin request context.

    The first argument to the wrapped function must be the context.

    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_admin_context(args[0]):
            raise exception.AdminRequired()
        return f(*args, **kwargs)
    return wrapper


def require_context(f):
    """Decorator to require *any* user or admin context.

    This does no authorization for user or project access matching, see
    :py:func:`authorize_project_context` and
    :py:func:`authorize_user_context`.

    The first argument to the wrapped function must be the context.

    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_admin_context(args[0]) and not is_user_context(args[0]):
            raise exception.NotAuthorized()
        return f(*args, **kwargs)
    return wrapper


def model_query(context, model, *args, **kwargs):
    """Query helper that accounts for context's `read_deleted` field.

    :param context: context to query under
    :param model: model to query. Must be a subclass of ModelBase.
    :param session: if present, the session to use
    :param read_deleted: if present, overrides context's read_deleted field.
    :param tenant_only: if present and context is user-type, then restrict
            query to match the context's project_id.
    """
    session = kwargs.get('session') or get_session()
    read_deleted = kwargs.get('read_deleted') or context.read_deleted
    project_only = kwargs.get('project_only')

    if not issubclass(model, models.ModelBase):
        raise TypeError("model should be a subclass of ModelBase")

    query = session.query(model, *args)
    if read_deleted in ('no', 'n', False):
        query = query.filter_by(deleted=False)
    elif read_deleted in ('yes', 'y', True):
        query = query.filter_by(deleted=True)
    else:
        raise Exception("Unrecognized read_deleted values '%s'" % read_deleted)

    if project_only and is_user_context(context):
        query = query.filter_by(tenant_id=context.tenant_id)
    return query


def ensure_model_dict_has_id(model_dict):
    if not model_dict.get('id'):
        model_dict['id'] = uuid.generate_uuid()
    return model_dict


def _training_get_query(context, session=None):
    if session is None:
        session = get_session()
    return model_query(context, models.Training, session=session)


@require_context
def training_create(context, training_values):
    values = copy.deepcopy(training_values)
    values = ensure_model_dict_has_id(values)
    session = get_session()
    training_ref = models.Training()
    training_ref.update(values)
    with session.begin():
        training_ref.save(session=session)
        return training_get(context, training_ref['id'], session=session)


@require_context
def training_get(context, training_id, session=None):
    result = _training_get_query(context, session).filter_by(id=training_id).first()

    if result is None:
        raise exception.NotFound()

    return result


def init_db():
    engine = get_engine()
    models.Base.metadata.create_all(engine)


