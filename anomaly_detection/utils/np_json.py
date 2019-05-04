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
import base64
import json

import numpy as np


def to_json(obj):
    if isinstance(obj, (np.ndarray, np.generic)):
        if isinstance(obj, np.ndarray):
            return {
                '__ndarray__': base64.b64encode(obj.tostring()),
                'dtype': obj.dtype.str,
                'shape': obj.shape,
            }
        elif isinstance(obj, (np.bool_, np.number)):
            return {
                '__npgeneric__': base64.b64encode(obj.tostring()),
                'dtype': obj.dtype.str,
            }
    if isinstance(obj, set):
        return {'__set__': list(obj)}
    if isinstance(obj, tuple):
        return {'__tuple__': list(obj)}
    if isinstance(obj, complex):
        return {'__complex__': obj.__repr__()}
    if isinstance(obj, bytes):
        return {'__bytes__': base64.b64encode(obj).decode()}
    # Let the base class default method raise the TypeError
    raise TypeError('Unable to serialise object of type {}'.format(type(obj)))


def from_json(obj):
    # check for numpy
    if isinstance(obj, dict):
        if '__ndarray__' in obj:
            return np.fromstring(
                base64.b64decode(obj['__ndarray__']),
                dtype=np.dtype(obj['dtype'])
            ).reshape(obj['shape'])
        if '__npgeneric__' in obj:
            return np.fromstring(
                base64.b64decode(obj['__npgeneric__']),
                dtype=np.dtype(obj['dtype'])
            )[0]
        if '__set__' in obj:
            return set(obj['__set__'])
        if '__tuple__' in obj:
            return tuple(obj['__tuple__'])
        if '__complex__' in obj:
            return complex(obj['__complex__'])
        if '__bytes__' in obj:
            return base64.b64decode(obj['__bytes__'])
    return obj


# over-write the load(s)/dump(s) functions
def load(*args, **kwargs):
    kwargs['object_hook'] = from_json
    return json.load(*args, **kwargs)


def loads(*args, **kwargs):
    kwargs['object_hook'] = from_json
    return json.loads(*args, **kwargs)


def dump(*args, **kwargs):
    kwargs['default'] = to_json
    return json.dump(*args, **kwargs)


def dumps(*args, **kwargs):
    kwargs['default'] = to_json
    return json.dumps(*args, **kwargs)
