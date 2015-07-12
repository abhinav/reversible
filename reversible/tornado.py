from __future__ import absolute_import

import sys
import types
import functools

import greenlet
from tornado.ioloop import IOLoop
from tornado.concurrent import Future, is_future

from . import core, generator


def _maybe_async(fn):

    @functools.wraps(fn)
    def new_fn(self, *args, **kwargs):
        current = greenlet.getcurrent()
        assert current.parent is not None, (
            "TornadoAction can only be used from inside a child greenlet."
        )

        result = fn(self, *args, **kwargs)
        if not is_future(result):
            # If the function doesn't return a future, its exeption or result
            # is available to the caller right away. No need to switch control
            # with greenlets.
            return result

        def callback(future):
            if future.exception():
                self.io_loop.add_callback(
                    current.throw,
                    future.exc_info(),
                )
            else:
                self.io_loop.add_callback(
                    current.switch,
                    future.result()
                )

        # Otherwise, switch to parent and schedule to switch back when the
        # result is available.
        result.add_done_callback(callback)
        return current.parent.switch()

    return new_fn


class _TornadoAction(object):
    """Provides synchronous APIs for asynchronous actions.

    This class wraps actions that may have asynchronous ``forwards`` or
    ``backwards`` to have synchronous APIs. It does so by using greenlets to
    switch control back to the IOLoop when it runs asynchronous operations.
    When the result of the asynchronous operation is available, control is
    switched back.
    """

    __slots__ = ('action', 'io_loop')

    def __init__(self, action, io_loop=None):
        self.action = action
        self.io_loop = io_loop or IOLoop.current()

    @_maybe_async
    def forwards(self):
        return self.action.forwards()

    @_maybe_async
    def backwards(self):
        return self.action.backwards()


def execute(action, io_loop=None):
    """Execute the given action and return a Future with the result.

    The ``forwards`` and ``backwards`` methods for the action may be
    synchronous or asynchronous. If asynchronous, the method must return a
    Future that will resolve to its result.

    See :py:func:`reversible.execute` for more details on the behavior of
    ``execute``.

    :returns:
        A future containing the result of executing the action.
    """

    if not io_loop:
        io_loop = IOLoop.current()

    output = Future()

    def call():
        try:
            result = core.execute(_TornadoAction(action, io_loop))
        except Exception:
            output.set_exc_info(sys.exc_info())
        else:
            output.set_result(result)

    io_loop.add_callback(greenlet.greenlet(call).switch)
    return output


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


action = core.action
Return = generator.Return


__all__ = ['action', 'execute', 'gen', 'Return']
