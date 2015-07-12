from __future__ import absolute_import

import sys
import types
import functools
from collections import deque

from .core import SimpleAction


class Return(Exception):
    """Used to return values from :py:func:`reversible.gen`.

    Generators that use :py:func:`reversible.gen` to compose actions can throw
    this exception to return a result.

    .. code-block:: python

        @reversible.gen
        def foo():
            a = yield f()
            b = yield g()
            raise reversible.Return(a + b)

    This exception is not needed with Python 3.3 or newer; a return statement
    is enough.
    """

    __slot__ = ('value',)

    def __init__(self, value):
        super(Return, self).__init__()
        self.value = value


class _GeneratorAction(object):

    __slots__ = ('generator', 'executed')

    def __init__(self, generator):
        self.generator = generator
        self.executed = deque()

    def forwards(self):
        try:
            action = next(self.generator)
            while True:
                # TODO: make sure action is not none
                self.executed.append(action)
                try:
                    result = action.forwards()
                except Exception:
                    action = self.generator.throw(*sys.exc_info())
                else:
                    action = self.generator.send(result)
        except (StopIteration, Return) as result:
            return getattr(result, 'value', None)

    def backwards(self):
        while self.executed:
            self.executed.pop().backwards()


def gen(function):
    """
    Allows using a generator to chain together reversible actions.

    This decorator may be added to a generator that yields reversible actions
    (any object with a ``.forwards()`` and ``.backwards()`` method). These may
    be constructed manually or via :py:func:`reversible.action`. The decorated
    function, when called, will return another reversible action that runs all
    yielded actions and if any of them fails, rolls back all actions that had
    been executed *in the reverse order*.

    Values can be returned by raising the :py:class:`reversible.Return`
    exception, or if using Python 3.3 or newer, by simply using the ``return``
    statement.

    For example,

    .. code-block:: python

        @reversible.gen
        def submit_order(order):
            # CreateOrder is a class that declares a forwards() and
            # backwards() method. The forwards() method returns the
            # order_id. It is propagated back to the yield point.
            order_id = yield CreateOrder(order.cart)

            # If get_payment_info throws an exception, the order will
            # be deleted and the exeception will be re-raised to the
            # caller.
            payment_info = PaymentStore.get_payment_info(order.user_id)

            try:
                # charge_order is a function that returns an action.
                # It is easy to create such a function by using
                # reversible.action as a decorator.
                total = yield charge_order(payment_info, order_id)
            except InsufficientFundsException:
                # Exceptions thrown by a dependency's forwards()
                # method are propagated at the yield point. It's
                # possible to handle them and prevent rollback for
                # everything else.
                send_insufficient_funds_email(order_id, order.user_id)
            else:
                yield update_receipt(order_id, total)
                send_receipt(order_id)

            # The order ID is the result of this action.
            raise reversible.Return(order_id)

        order_id = reversible.execute(submit_order(order))

        # If another action based on reversible.gen calls
        # submit_order, it can simply do:
        #
        #    order_id = yield submit_order(order_details)

    When an action fails, its ``backwards`` method and the ``backwards``
    methods of all actions executed so far will be called in reverse of the
    order in which the ``forwards`` methods were called.

    If any of the ``backwards`` methods fail, rollback will be aborted.

    :param function:
        The generator function. This generator must yield action objects.
    :returns:
        A function that, when called, produces an action object that executes
        actions and functions as yielded by the generator.
    """

    @functools.wraps(function)  # TODO: use wrapt instead?
    def new_function(*args, **kwargs):
        try:
            value = function(*args, **kwargs)
        except Return as result:
            return SimpleAction(
                lambda ctx: ctx.value,
                lambda _: None,
                result,
            )
        else:
            if isinstance(value, types.GeneratorType):
                return _GeneratorAction(value)
            else:
                return SimpleAction(
                    lambda _: value,
                    lambda _: None,
                    None,
                )

    return new_function


__all__ = ['gen', 'Return']
