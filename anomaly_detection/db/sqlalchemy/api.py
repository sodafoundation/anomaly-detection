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

import copy
import sys
import warnings
from functools import wraps

import sqlalchemy.orm
from sqlalchemy.orm import load_only
from sqlalchemy.sql import func

from anomaly_detection import exception
from anomaly_detection.db.sqlalchemy import models
from anomaly_detection.utils import uuid, config as cfg

CONF = cfg.CONF


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


_DEFAULT_SQL_CONNECTION = 'sqlite://'
_FACADE = None

CONF.set_default("connection", _DEFAULT_SQL_CONNECTION, group="database")


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = EngineFacade(CONF.database.connection)
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

def authorize_tenant_context(context, tenant_id):
    if is_user_context(context):
        if not context.tenant_id:
            raise exception.NotAuthorized()
        elif context.tenant_id != tenant_id:
            raise exception.NotAuthorized()

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
            query to match the context's tenant_id.
    """
    session = kwargs.get('session') or get_session()
    read_deleted = kwargs.get('read_deleted') or context.read_deleted
    tenant_only = kwargs.get('tenant_only')

    if not issubclass(model, models.ModelBase):
        raise TypeError("model should be a subclass of ModelBase")

    query = session.query(model) if not args else session.query(*args)
    if read_deleted in ('no', 'n', False):
        query = query.filter_by(deleted=False)
    elif read_deleted in ('yes', 'y', True):
        query = query.filter_by(deleted=True)
    else:
        raise Exception("Unrecognized read_deleted values '%s'" % read_deleted)

    if tenant_only and is_user_context(context):
        query = query.filter_by(tenant_id=context.tenant_id)
    return query


def ensure_model_dict_has_id(model_dict):
    if not model_dict.get('id'):
        model_dict['id'] = uuid.generate_uuid()
    return model_dict


def process_sort_params(sort_keys, sort_dirs, default_keys=None, default_dir='asc'):
    if default_keys is None:
        default_keys = ['created_at', 'id']

    # Determine direction to use for when adding default keys
    if sort_dirs and len(sort_dirs):
        default_dir_value = sort_dirs[0]
    else:
        default_dir_value = default_dir

    # Create list of keys (do not modify the input list)
    if sort_keys:
        result_keys = list(sort_keys)
    else:
        result_keys = []

    # If a list of directions is not provided, use the default sort direction
    # for all provided keys.
    if sort_dirs:
        result_dirs = []
        # Verify sort direction
        for sort_dir in sort_dirs:
            if sort_dir not in ('asc', 'desc'):
                msg = "Unknown sort direction, must be 'desc' or 'asc'."
                raise exception.InvalidInput(reason=msg)
            result_dirs.append(sort_dir)
    else:
        result_dirs = [default_dir_value for _sort_key in result_keys]

    # Ensure that the key and direction length match
    while len(result_dirs) < len(result_keys):
        result_dirs.append(default_dir_value)
    # Unless more direction are specified, which is an error
    if len(result_dirs) > len(result_keys):
        msg = "Sort direction array size exceeds sort key array size."
        raise exception.InvalidInput(reason=msg)

    # Ensure defaults are included
    for key in default_keys:
        if key not in result_keys:
            result_keys.append(key)
            result_dirs.append(default_dir_value)

    return result_keys, result_dirs


def is_orm_value(obj):
    """Check if object is an ORM field or expression."""
    return isinstance(obj, (sqlalchemy.orm.attributes.InstrumentedAttribute,
                            sqlalchemy.sql.expression.ColumnElement))


# TODO: add filter and marker features.
def _pagination_query(context, session, model, limit=None, offset=None,
                      sort_keys=None, sort_dirs=None):

    sort_keys, sort_dirs = process_sort_params(sort_keys, sort_dirs)
    query = model_query(context, model, session=session)
    # Add sorting
    for current_sort_key, current_sort_dir in zip(sort_keys, sort_dirs):
        sort_dir_func = {
            'asc': sqlalchemy.asc,
            'desc': sqlalchemy.desc,
        }[current_sort_dir]

        try:
            sort_key_attr = getattr(model, current_sort_key)
        except AttributeError:
            raise exception.InvalidInput(reason='Invalid sort key')
        if not is_orm_value(sort_key_attr):
            raise exception.InvalidInput(reason='Invalid sort key')
        query = query.order_by(sort_dir_func(sort_key_attr))

    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    return query


def get_count(context, model, tenant_only=True):
    session = get_session()
    with session.begin():
        query = model_query(context, model, func.count(model.id),
                            session=session, tenant_only=tenant_only)
        if query is None:
            return 0
        result = query.first()
        return result[0] or 0


def _training_get_query(context, session=None):
    return model_query(context, models.Training, tenant_only=True, session=session)


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
def training_delete(context, training_id):
    session = get_session()
    with session.begin():
        training_ref = training_get(context, training_id, session)
        training_ref.delete(session)


@require_context
def training_get(context, training_id, session=None):
    result = _training_get_query(context, session).filter_by(id=training_id).first()

    if result is None:
        raise exception.NotFound()

    return result


@require_admin_context
def training_get_all(context, limit=None, offset=None,
                     sort_keys=None, sort_dirs=None):
    session = get_session()
    with session.begin():
        query = _pagination_query(context, session, models.Training,
                                  limit=limit, offset=offset,
                                  sort_keys=sort_keys, sort_dirs=sort_dirs)
        if query is None:
            return []
        return query.all()


@require_context
def training_get_all_by_tenant(context, tenant_id):
    query = model_query(context, models.Training).filter_by(tenant_id=tenant_id)
    if query is None:
        return []
    return query.all()


def _performance_get_query(context, session=None):
    return model_query(context, models.Performance, tenant_only=True, session=session)


@require_context
def performance_create(context, performance_values):
    values = copy.deepcopy(performance_values)
    values = ensure_model_dict_has_id(values)
    session = get_session()
    performance_ref = models.Performance()
    performance_ref.update(values)
    with session.begin():
        performance_ref.save(session=session)
        return performance_get(context, performance_ref['id'], session=session)


@require_context
def performance_delete(context, performance_id):
    session = get_session()
    with session.begin():
        performance_ref = performance_get(context, performance_id, session)
        performance_ref.delete(session)


@require_context
def performance_get(context, performance_id, session=None):
    result = _performance_get_query(context, session).filter_by(id=performance_id).first()

    if result is None:
        raise exception.NotFound()

    return result


@require_context
def performance_get_all(context, fields=None, limit=None, offset=None,
                        sort_keys=None, sort_dirs=None):
    session = get_session()
    with session.begin():
        query = _pagination_query(context, session, models.Performance,
                                  limit=limit, offset=offset,
                                  sort_keys=sort_keys, sort_dirs=sort_dirs)
        if query is None:
            return []
        if fields is not None:
            query = query.options(load_only(*fields))
        return query.all()


@require_context
def performance_get_count(context):
    return get_count(context, models.Performance, tenant_only=False)


def init_db():
    engine = get_engine()
    models.Base.metadata.create_all(engine)


