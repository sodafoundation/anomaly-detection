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
import abc
import collections
import copy
import functools
import itertools
import re
from configparser import ConfigParser, NoOptionError, NoSectionError

import six


class Error(Exception):
    """Base class for cfg exceptions."""

    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        return self.msg


class AttributeError(Exception):
    """ Attribute not found. """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(*args, **kwargs): # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass


class NoSuchOptError(Error, AttributeError):
    """Raised if an opt which doesn't exist is referenced."""

    def __init__(self, opt_name, group=None):
        self.opt_name = opt_name
        self.group = group

    def __str__(self):
        group_name = 'DEFAULT' if self.group is None else self.group.name
        return "no such option %s in group [%s]" % (self.opt_name, group_name)


class RequiredOptError(Error):
    """Raised if an option is required but no value is supplied by the user."""

    def __init__(self, opt_name, group=None):
        self.opt_name = opt_name
        self.group = group

    def __str__(self):
        group_name = 'DEFAULT' if self.group is None else self.group.name
        return "value required for option %s in group [%s]" % (self.opt_name,
                                                               group_name)


class ConfigSourceValueError(Error, ValueError):
    """Raised if a config source value does not match its opt type."""
    pass


class ConfigFileValueError(ConfigSourceValueError):
    """Raised if a config file value does not match its opt type."""
    pass


class NoSuchGroupError(Error):
    """Raised if a group which doesn't exist is referenced."""

    def __init__(self, group_name):
        self.group_name = group_name

    def __str__(self):
        return "no such group [%s]" % self.group_name


@six.add_metaclass(abc.ABCMeta)
class ConfigType(object):
    def __init__(self, type_name='unknown type'):
        self.type_name = type_name

    NONE_DEFAULT = '<None>'

    def format_defaults(self, default, sample_default=None):
        """Return a list of formatted default values.

        """
        if sample_default is not None:
            if isinstance(sample_default, six.string_types):
                default_str = sample_default
            else:
                default_str = self._formatter(sample_default)
        elif default is None:
            default_str = self.NONE_DEFAULT
        else:
            default_str = self._formatter(default)
        return [default_str]

    def quote_trailing_and_leading_space(self, str_val):
        if not isinstance(str_val, six.string_types):
            str_val = six.text_type(str_val)
        if str_val.strip() != str_val:
            return '"%s"' % str_val
        return str_val

    @abc.abstractmethod
    def _formatter(self, value):
        pass


class Boolean(ConfigType):
    TRUE_VALUES = ['true', '1', 'on', 'yes']
    FALSE_VALUES = ['false', '0', 'off', 'no']

    def __init__(self, type_name='boolean value'):
        super(Boolean, self).__init__(type_name=type_name)

    def __call__(self, value):
        if isinstance(value, bool):
            return value

        s = value.lower()
        if s in self.TRUE_VALUES:
            return True
        elif s in self.FALSE_VALUES:
            return False
        else:
            raise ValueError('Unexpected boolean value %r' % value)

    def __repr__(self):
        return 'Boolean'

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def _formatter(self, value):
        return str(value).lower()


class Number(ConfigType):
    def __init__(self, num_type, type_name, min=None, max=None, choices=None):
        super(Number, self).__init__(type_name=type_name)

        if min is not None and max is not None and max < min:
            raise ValueError('Max value is less than min value')

        if choices is not None:
            if not all(isinstance(choice, tuple) for choice in choices):
                choices = [(choice, None) for choice in choices]

            self.choices = collections.OrderedDict(choices)
        else:
            self.choices = None

        invalid_choices = [c for c in self.choices or []
                           if (min is not None and min > c)
                           or (max is not None and max < c)]
        if invalid_choices:
            raise ValueError("Choices %s are out of bounds [%s..%s]"
                             % (invalid_choices, min, max))

        self.min = min
        self.max = max
        self.num_type = num_type

    def __call__(self, value):
        if not isinstance(value, self.num_type):
            s = str(value).strip()
            if s == '':
                return None
            value = self.num_type(value)

        if self.choices is None:
            if self.min is not None and value < self.min:
                raise ValueError('Should be greater than or equal to %g' %
                                 self.min)
            if self.max is not None and value > self.max:
                raise ValueError('Should be less than or equal to %g' %
                                 self.max)
        else:
            if value not in self.choices:
                raise ValueError('Valid values are %r, but found %g' % (
                                 self.choices, value))
        return value

    def __repr__(self):
        props = []
        if self.choices is not None:
            props.append("choices={!r}".format(list(self.choices.keys())))
        else:
            if self.min is not None:
                props.append('min=%g' % self.min)
            if self.max is not None:
                props.append('max=%g' % self.max)

        if props:
            return self.__class__.__name__ + '(%s)' % ', '.join(props)
        return self.__class__.__name__

    def __eq__(self, other):
        return (
            (self.__class__ == other.__class__) and
            (self.min == other.min) and
            (self.max == other.max) and
            (set([x for x in self.choices or []]) ==
                set([x for x in other.choices or []]) if
             self.choices and other.choices else
             self.choices == other.choices)
        )

    def _formatter(self, value):
        return six.text_type(value)


class Integer(Number):
    def __init__(self, min=None, max=None, type_name='integer value',
                 choices=None):
        super(Integer, self).__init__(int, type_name, min=min, max=max,
                                      choices=choices)


class Float(Number):
    def __init__(self, min=None, max=None, type_name='floating point value'):
        super(Float, self).__init__(float, type_name, min=min, max=max)


class String(ConfigType):
    def __init__(self, choices=None, quotes=False, regex=None,
                 ignore_case=False, max_length=None,
                 type_name='string value'):
        super(String, self).__init__(type_name=type_name)
        if choices and regex:
            raise ValueError("'choices' and 'regex' cannot both be specified")

        self.ignore_case = ignore_case
        self.quotes = quotes
        self.max_length = max_length or 0

        if choices is not None:
            if not all(isinstance(choice, tuple) for choice in choices):
                choices = [(choice, None) for choice in choices]

            self.choices = collections.OrderedDict(choices)
        else:
            self.choices = None

        self.lower_case_choices = None
        if self.choices is not None and self.ignore_case:
            self.lower_case_choices = [c.lower() for c in self.choices]

        self.regex = regex
        if self.regex is not None:
            re_flags = re.IGNORECASE if self.ignore_case else 0

            # Check if regex is a string or an already compiled regex
            if isinstance(regex, six.string_types):
                self.regex = re.compile(regex, re_flags)
            else:
                self.regex = re.compile(regex.pattern, re_flags | regex.flags)

    def __call__(self, value):
        value = str(value)
        if self.quotes and value:
            if value[0] in "\"'":
                if value[-1] != value[0]:
                    raise ValueError('Non-closed quote: %s' % value)
                value = value[1:-1]

        if 0 < self.max_length < len(value):
            raise ValueError("Value '%s' exceeds maximum length %d" %
                             (value, self.max_length))

        if self.regex and not self.regex.search(value):
            raise ValueError("Value %r doesn't match regex %r" %
                             (value, self.regex.pattern))

        if self.choices is None:
            return value

        # Check for case insensitive
        processed_value, choices = ((value.lower(), self.lower_case_choices)
                                    if self.ignore_case else
                                    (value, self.choices.keys()))
        if processed_value in choices:
            return value

        raise ValueError(
            'Valid values are [%s], but found %s' % (
                ', '.join([str(v) for v in self.choices]),
                repr(value)))

    def __repr__(self):
        details = []
        if self.choices is not None:
            details.append("choices={!r}".format(list(self.choices.keys())))
        if self.regex:
            details.append("regex=%r" % self.regex.pattern)
        if details:
            return "String(%s)" % ",".join(details)
        return 'String'

    def __eq__(self, other):
        return (
            (self.__class__ == other.__class__) and
            (self.quotes == other.quotes) and
            (self.regex == other.regex) and
            (set([x for x in self.choices or []]) ==
                set([x for x in other.choices or []]) if
             self.choices and other.choices else
             self.choices == other.choices)
        )

    def _formatter(self, value):
        return self.quote_trailing_and_leading_space(value)


class List(ConfigType):

    def __init__(self, item_type=None, bounds=False, type_name='list value'):
        super(List, self).__init__(type_name=type_name)

        if item_type is None:
            item_type = String()

        if not callable(item_type):
            raise TypeError('item_type must be callable')
        self.item_type = item_type
        self.bounds = bounds

    def __call__(self, value):
        if isinstance(value, (list, tuple)):
            return list(six.moves.map(self.item_type, value))

        s = value.strip().rstrip(',')
        if self.bounds:
            if not s.startswith('['):
                raise ValueError('Value should start with "["')
            if not s.endswith(']'):
                raise ValueError('Value should end with "]"')
            s = s[1:-1]
        if s:
            values = s.split(',')
        else:
            values = []
        if not values:
            return []

        result = []
        while values:
            value = values.pop(0)
            while True:
                first_error = None
                try:
                    validated_value = self.item_type(value.strip())
                    break
                except ValueError as e:
                    if not first_error:
                        first_error = e
                    if len(values) == 0:
                        raise first_error

                value += ',' + values.pop(0)

            result.append(validated_value)

        return result

    def __repr__(self):
        return 'List of %s' % repr(self.item_type)

    def __eq__(self, other):
        return (
            (self.__class__ == other.__class__) and
            (self.item_type == other.item_type)
        )

    def _formatter(self, value):
        fmtstr = '[{}]' if self.bounds else '{}'
        if isinstance(value, six.string_types):
            return fmtstr.format(value)
        if isinstance(value, list):
            value = [
                self.item_type._formatter(v)
                for v in value
            ]
            return fmtstr.format(','.join(value))
        return fmtstr.format(self.item_type._formatter(value))


class Opt(object):
    def __init__(self, name, typ=None, default=None, help=None, secret=False, required=False, ):
        if name.startswith('_'):
            raise ValueError('illegal name %s with prefix _' % (name,))
        self.name = name

        if typ is None:
            typ = String()

        if not callable(typ):
            raise TypeError('type must be callable')
        self.type = typ
        self.default = default
        self.help = help
        self.secret = secret
        self.required = required
        self._check_default()

    def _default_is_ref(self):
        """Check if default is a reference to another var."""
        if isinstance(self.default, six.string_types):
            tmpl = self.default.replace(r'\$', '').replace('$$', '')
            return '$' in tmpl
        return False

    def _check_default(self):
        if (self.default is not None
                and not self._default_is_ref()):
            try:
                self.type(self.default)
            except Exception:
                raise ValueError("Error processing default value %(default)s for Opt type of %(opt)s."
                                 % {'default': self.default, 'opt': self.type})

    def _vars_for_cmp(self):
        v = dict(vars(self))
        return v

    def _get_from_namespace(self, namespace, group_name):
        """Retrieves the option value from a _Namespace object.

        :param namespace: a _Namespace object
        :param group_name: a group name
        """
        if group_name is None:
            group_name = 'DEFAULT'
        return namespace.get(group_name, self.name)

    def __ne__(self, another):
        return self._vars_for_cmp() != another._vars_for_cmp()

    def __eq__(self, another):
        return self._vars_for_cmp() == another._vars_for_cmp()

    __hash__ = object.__hash__


class BoolOpt(Opt):
    def __init__(self, name, **kwargs):
        super(BoolOpt, self).__init__(name, typ=Boolean(), **kwargs)


class IntOpt(Opt):
    def __init__(self, name, min=None, max=None, **kwargs):
        super(IntOpt, self).__init__(name, typ=Integer(min, max), **kwargs)


class FloatOpt(Opt):
    def __init__(self, name, min=None, max=None, **kwargs):
        super(FloatOpt, self).__init__(name, typ=Float(min, max), **kwargs)


class StrOpt(Opt):
    def __init__(self, name, choices=None, quotes=None,
                 regex=None, ignore_case=False, max_length=None, **kwargs):
        super(StrOpt, self).__init__(name,
                                     typ=String(
                                         choices=choices,
                                         quotes=quotes,
                                         regex=regex,
                                         ignore_case=ignore_case,
                                         max_length=max_length),
                                     **kwargs)


class ListOpt(Opt):
    def __init__(self, name, item_type=None, bounds=None, **kwargs):
        super(ListOpt, self).__init__(name, typ=List(item_type=item_type, bounds=bounds), **kwargs)


class OptGroup(object):

    def __init__(self, name, title=None, help=None):
        """Constructs an OptGroup object."""
        self.name = name
        self.title = "%s options" % name if title is None else title
        self.help = help

        self._opts = {}  # dict of dicts of (opt:, override:, default:)

    def _get_generator_data(self):
        return {
            'help': self.help or '',
        }

    def _register_opt(self, opt):
        self._opts[opt.name] = opt
        return True

    def _unregister_opt(self, opt):
        """Remove an opt from this group.

        :param opt: an Opt object
        """
        if opt.dest in self._opts:
            del self._opts[opt.name]

    def __str__(self):
        return self.name


def _normalize_group_name(group_name):
    if group_name == 'DEFAULT':
        return group_name
    return group_name.lower()


class ConfigOpts(collections.Mapping):
    def __init__(self):
        """Construct a ConfigOpts object."""
        self._opts = {}  # dict of dicts of (opt:, override:, default:)
        self._groups = {}
        self._args = None
        self._namespace = None
        self.__cache = {}
        self._config_opts = []
        self._validate_default_values = False
        self._sources = []
        self._ext_mgr = None

    def __clear_cache(f):
        @functools.wraps(f)
        def __inner(self, *args, **kwargs):
            if kwargs.pop('clear_cache', True):
                result = f(self, *args, **kwargs)
                self.__cache.clear()
                return result
            else:
                return f(self, *args, **kwargs)

        return __inner

    @__clear_cache
    def clear(self):
        self._args = None
        self._namespace = None
        # Keep _mutate_hooks
        self._validate_default_values = False
        self.unregister_opts(self._config_opts)

    def get_config_file(self):
        for i, arg in enumerate(self._args):
            if arg == '--config-file':
                if len(self._args) > i+1:
                    return self._args[i+1]
            if arg.startswith('--config-file='):
                key, sep, val = arg.partion("=")
                return val
        else:
            return None

    def __call__(self, args):
        self._args = args
        self._config_file = self.get_config_file()
        if self._config_file is not None:
            self._namespace = ConfigParser()
            if not self._namespace.read(self._config_file):
                raise Error('Read config files "%s" error' % self._config_file)

    def __getattr__(self, name):
        """Look up an option value and perform string substitution.

        :param name: the opt name (or 'dest', more precisely)
        :returns: the option value (after string substitution) or a GroupAttr
        :raises: ValueError or NoSuchOptError
        """
        try:
            return self._get(name)
        except ValueError:
            raise
        except Exception:
            raise NoSuchOptError(name)

    def __getitem__(self, key):
        """Look up an option value and perform string substitution."""
        return self.__getattr__(key)

    def __contains__(self, key):
        """Return True if key is the name of a registered opt or group."""
        return key in self._opts or key in self._groups

    def __iter__(self):
        """Iterate over all registered opt and group names."""
        for key in itertools.chain(list(self._opts.keys()),
                                   list(self._groups.keys())):
            yield key

    def __len__(self):
        """Return the number of options and option groups."""
        return len(self._opts) + len(self._groups)

    def reset(self):
        """Clear the object state and unset overrides and defaults."""
        self._unset_defaults_and_overrides()
        self.clear()

    @__clear_cache
    def register_opt(self, opt, group=None, cli=False):
        """Register an option schema.
        """
        if group is not None:
            group = self._get_group(group, autocreate=True)
            return group._register_opt(opt)

        self._opts[opt.name] = opt
        return True

    @__clear_cache
    def register_opts(self, opts, group=None):
        """Register multiple option schemas at once."""
        for opt in opts:
            self.register_opt(opt, group, clear_cache=False)

    def register_group(self, group):
        """Register an option group.
        """
        if group.name in self._groups:
            return

        self._groups[group.name] = copy.copy(group)

    def _get_group(self, group_or_name, autocreate=False):
        """Looks up a OptGroup object.
        """
        group = group_or_name if isinstance(group_or_name, OptGroup) else None
        group_name = group.name if group else group_or_name

        if group_name not in self._groups:
            if not autocreate:
                raise NoSuchGroupError(group_name)

            self.register_group(group or OptGroup(name=group_name))

        return self._groups[group_name]

    class GroupAttr(collections.Mapping):

        """Helper class.

        Represents the option values of a group as a mapping and attributes.
        """

        def __init__(self, conf, group):
            """Construct a GroupAttr object.

            :param conf: a ConfigOpts object
            :param group: an OptGroup object
            """
            self._conf = conf
            self._group = group

        def __getattr__(self, name):
            """Look up an option value and perform template substitution."""
            return self._conf._get(name, self._group)

        def __getitem__(self, key):
            """Look up an option value and perform string substitution."""
            return self.__getattr__(key)

        def __contains__(self, key):
            """Return True if key is the name of a registered opt or group."""
            return key in self._group._opts

        def __iter__(self):
            """Iterate over all registered opt and group names."""
            for key in self._group._opts.keys():
                yield key

        def __len__(self):
            """Return the number of options and option groups."""
            return len(self._group._opts)

    def _get_opt_info(self, opt_name, group=None):
        """Return the (opt, override, default) dict for an opt.

        :param opt_name: an opt name/dest
        :param group: an optional group name or OptGroup object
        :raises: NoSuchOptError, NoSuchGroupError
        """
        if group is None:
            opts = self._opts
        else:
            group = self._get_group(group)
            opts = group._opts
        return opts[opt_name]

    def _convert_value(self, value, opt):
        return opt.type(value)

    def _get(self, name, group=None):
        if isinstance(group, OptGroup):
            key = (group.name, name)
        else:
            key = (group, name)
        try:
            return self.__cache[key]
        except KeyError:
            pass
        value = self._do_get(name, group)
        self.__cache[key] = value
        return value

    def _do_get(self, name, group=None):
        if group is None and name in self._groups:
            return self.GroupAttr(self, self._get_group(name))
        opt = self._get_opt_info(name, group)

        def convert(value):
            return self._convert_value(value, opt)

        group_name = group.name if group else None
        if self._namespace is not None:
            try:
                return convert(opt._get_from_namespace(self._namespace, group_name))
            except (NoOptionError, NoSectionError):
                pass
            except ValueError:
                raise
        if opt.default is not None:
            return convert(opt.default)
        return None

    @__clear_cache
    def set_default(self, name, default, group=None):
        """Override an opt's default value.
        """
        opt = self._get_opt_info(name, group)
        opt.default = self._convert_value(default, opt)


CONF = ConfigOpts()
