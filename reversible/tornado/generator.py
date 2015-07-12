from __future__ import absolute_import

import types
import functools

from tornado.gen import Return

from reversible.core import SimpleAction
from reversible.generator import _GeneratorAction
from reversible.generator import Return as _Return

from .core import _TornadoAction

_RETURNS = (Return, _Return)


class _Lift(object):

    __slots__ = ('future',)

    def __init__(self, future):
        self.future = future

    def forwards(self):
        return self.future

    def backwards(self):
        pass


class _TornadoGeneratorAction(object):

    __slots__ = ('action',)

    def __init__(self, generator, io_loop=None):
        self.action = _GeneratorAction(
            _TornadoAction(action, io_loop) for action in generator
        )

    def forwards(self):
        try:
            return self.action.forwards()
        except _RETURNS as result:
            return getattr(result, 'value', None)

    def backwards(self):
        return self.action.backwards()


def gen(function, io_loop=None):
    """TODO"""

    @functools.wraps(function)  # TODO: use wrapt instead?
    def new_function(*args, **kwargs):
        try:
            value = function(*args, **kwargs)
        except _RETURNS as result:
            return SimpleAction(
                lambda ctx: ctx.value,
                lambda _: None,
                result,
            )
        else:
            if isinstance(value, types.GeneratorType):
                return _TornadoGeneratorAction(value, io_loop)
            else:
                return SimpleAction(
                    lambda _: value,
                    lambda _: None,
                    None,
                )

    return new_function


def lift(future):
    """Returns the result of a Tornado Future inside ``gen``.

    Inside a :py:func:`reversible.tornado.gen` context, the meaning of
    ``yield`` changes to "execute this action and return the result." However,
    it may be necessary to execute a standard Tornado coroutine as well. To
    make this possible, the ``lift`` method is made available.

    .. code-block:: python

        import reversible.tornado as reversible

        @reversible.gen
        def my_action():
            request = yield build_request_action()
            response = yield reversible.lift(
                http_client.fetch(request)
            )

            raise reversible.Return(response)

    Note that actions executed through lift are assumed to be non-reversible.
    """
    return _Lift(future)


__all__ = ['gen', 'Return', 'lift']
