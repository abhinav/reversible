from __future__ import absolute_import

import sys
import functools

import greenlet
from tornado.ioloop import IOLoop
from tornado.concurrent import Future, is_future

from reversible.core import action
from reversible.core import execute as _execute


action = action


def _maybe_async(fn):

    @functools.wraps(fn)
    def new_fn(self, *args, **kwargs):
        result = fn(self, *args, **kwargs)
        if not is_future(result):
            # If the function doesn't return a future, its exeption or result
            # is available to the caller right away. No need to switch control
            # with greenlets.
            return result

        current = greenlet.getcurrent()
        assert current.parent is not None, (
            "TornadoAction can only be used from inside a child greenlet."
        )

        def callback(future):
            if future.exception():
                self.io_loop.add_callback(current.throw, *future.exc_info())
            else:
                self.io_loop.add_callback(current.switch, future.result())

        # Otherwise, switch to parent and schedule to switch back when the
        # result is available.

        # A note about add_done_callback: It executes the callback right away
        # if the future has already finished executing. That's a problem
        # because we don't want the greenlet switch back to current to happen
        # until we've switched to parent first. So, io_loop.add_callback is
        # used to schedule the future callback. This ensures that we switch to
        # parent first.
        self.io_loop.add_callback(result.add_done_callback, callback)
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

    The ``forwards`` and/or ``backwards`` methods for the action may be
    synchronous or asynchronous. If asynchronous, that method must return a
    Future that will resolve to its result.

    See :py:func:`reversible.execute` for more details on the behavior of
    ``execute``.

    :param action:
        The action to execute.
    :param io_loop:
        IOLoop through which asynchronous operations will be executed. If
        omitted, the current IOLoop is used.
    :returns:
        A future containing the result of executing the action.
    """

    if not io_loop:
        io_loop = IOLoop.current()

    output = Future()

    def call():
        try:
            result = _execute(_TornadoAction(action, io_loop))
        except Exception:
            output.set_exc_info(sys.exc_info())
        else:
            output.set_result(result)

    io_loop.add_callback(greenlet.greenlet(call).switch)
    return output


__all__ = ['action', 'execute']
