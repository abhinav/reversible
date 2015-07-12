from __future__ import absolute_import

import types
import functools

from reversible import core, generator
from .core import _TornadoAction

Return = generator.Return


class _Lift(object):

    __slots__ = ('future',)

    def __init__(self, future):
        self.future = future

    def forwards(self):
        return self.future

    def backwards(self):
        pass


def gen(function, io_loop=None):
    """TODO"""

    @functools.wraps(function)  # TODO: use wrapt instead?
    def new_function(*args, **kwargs):
        try:
            value = function(*args, **kwargs)
        except Return as result:
            return core.SimpleAction(
                lambda ctx: ctx.value,
                lambda _: None,
                result,
            )
        else:
            if isinstance(value, types.GeneratorType):
                # TODO: handle tornado.gen.Return in forwards()
                return generator._GeneratorAction(
                    _TornadoAction(action, io_loop) for action in value
                )
            else:
                return core.SimpleAction(
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
