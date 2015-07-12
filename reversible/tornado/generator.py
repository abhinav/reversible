from __future__ import absolute_import

import types
import functools

from reversible import core, generator
from .core import _TornadoAction

Return = generator.Return


def gen(function, io_loop=None):

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
                # Wrap all yielded actions with _TornadoAction
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


__all__ = ['gen', 'Return']
