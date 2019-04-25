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
import argparse
import sys
import os
from anomaly_detection import log
from anomaly_detection.db import api


def args(*args, **kwargs):
    def _decorator(func):
        func.__dict__.setdefault('args', []).insert(0, (args, kwargs))
        return func

    return _decorator


class DbCommands(object):
    def __init__(self):
        pass

    @args('version', nargs='?', default=None,
          help='Database version')
    def sync(self, version=None):
        print("do Dbcommand.sync(version=%s)." % version)
        api.init_db()


def methods_of(obj):
    result = []
    for i in dir(obj):
        if callable(getattr(obj, i)) and not i.startswith('_'):
            result.append((i, getattr(obj, i)))
    return result


def fetch_func_args(func, matchargs):
    fn_args = []
    for args, kwargs in getattr(func, 'args', []):
        arg = args[0]
        fn_args.append(getattr(matchargs, arg))

    return fn_args


CATEGORIES = {
    'db': DbCommands
}


def add_command_parsers(subparsers):
    for category in CATEGORIES:
        command_object = CATEGORIES[category]()

        parser = subparsers.add_parser(category)
        parser.set_defaults(command_object=command_object)

        category_subparsers = parser.add_subparsers(dest='action')
        category_subparsers.required = True

        for (action, action_fn) in methods_of(command_object):
            parser = category_subparsers.add_parser(action)

            action_kwargs = []
            for args, kwargs in getattr(action_fn, 'args', []):
                parser.add_argument(*args, **kwargs)

            parser.set_defaults(action_fn=action_fn)
            parser.set_defaults(action_kwargs=action_kwargs)


def main():

    script_name = sys.argv[0]
    if len(sys.argv) < 2:
        print(script_name + " category action [<args>]")
        print("Available categories:")
        for category in CATEGORIES:
            print("\t%s" % category)
        sys.exit(2)

    cmd = os.path.basename(script_name)
    top_parser = argparse.ArgumentParser(prog=cmd)
    subparsers = top_parser.add_subparsers()
    add_command_parsers(subparsers)

    log.setup(log.Config, "anomaly_detection")

    match_args = top_parser.parse_args(sys.argv[1:])
    fn = match_args.action_fn
    fn_args = fetch_func_args(fn, match_args)
    # do the match func
    fn(*fn_args)


if __name__ == '__main__':
    sys.exit(main())
