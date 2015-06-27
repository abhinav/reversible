from __future__ import absolute_import

import logging


log = logging.getLogger('reversible')


def execute(action):
    """
    Execute the given action.

    An action is any object with a ``forwards()`` and ``backwards()`` method.

    .. code-block:: python

        class CreateUser(object):

            def __init__(self, userinfo):
                self.userinfo = userinfo
                self.user_id  = None

            def forwards(self):
                self.user_id = UserStore.create(userinfo)
                return self.user_id

            def backwards(self):
                if self.user_id is not None:
                    # user_id will be None if creation failed
                    UserStore.delete(self.user_id)

    If the ``forwards`` method succeeds, the action is considered successful.
    If the method fails, the ``backwards`` method is called to revert any
    effect it might have had on the system.

    In addition to defining classes, actions may be built using the
    :py:func:`reversible.action` decorator. Actions may be composed together
    using the :py:func:`reversible.gen` decorator.

    :param action:
        The action to execute.
    :returns:
        The value returned by the ``forwards()`` method of the action.
    :raises:
        The exception raised by the ``forwards()`` method if rollback
        succeeded. Otherwise, the exception raised by the ``backwards()``
        method is raised.
    """
    # TODO this should probably be a class to configure logging, etc. The
    # global execute can refer to the "default" instance of the executor.
    try:
        return action.forwards()
    except Exception:
        log.exception('%s failed to execute. Rolling back.', action)
        try:
            action.backwards()
        except Exception:
            log.exception('%s failed to roll back.', action)
            raise
        else:
            raise


class SimpleAction(object):
    """
    An action that simply calls the specified functions with the context.
    """

    __slots__ = ('_forwards', '_backwards', '_context')

    def __init__(self, forwards, backwards, context):
        self._forwards = forwards
        self._backwards = backwards
        self._context = context

    def forwards(self):
        return self._forwards(self._context)

    def backwards(self):
        return self._backwards(self._context)

    def __str__(self):
        return "<SimpleAction %s, %s, %s>" % (
            self._forwards, self._backwards, self._context
        )

    __repr__ = __str__


class ActionBuilder(object):
    """Builds an action in two steps."""

    __slots__ = ('_forwards', '_backwards', '_context_class')

    def __init__(self, forwards, context_class):
        self._forwards = forwards
        self._backwards = None
        self._context_class = context_class

    def __call__(self, *args, **kwargs):
        if self._backwards is None:
            raise ValueError('All actions must have a backwards action.')

        return SimpleAction(
            lambda ctx: self._forwards(ctx, *args, **kwargs),
            lambda ctx: self._backwards(ctx, *args, **kwargs),
            self._context_class(),
        )

    def backwards(self, backwards):
        """Decorator to specify the ``backwards`` action."""

        if self._backwards is not None:
            raise ValueError('Backwards action already specified.')

        self._backwards = backwards
        return backwards

    def __str__(self):
        return "<ActionBuilder %s, %s>" % (self._forwards, self._backwards)

    __repr__ = __str__


def action(forwards=None, context_class=None):
    """
    Decorator to build functions.

    This decorator can be applied to a function to build actions. The
    decorated function becomes the ``forwards`` implementation of the action.
    The first argument of the ``forwards`` implementation is a context object
    that can be used to share state between the forwards and backwards
    implementations. This argument is passed implicitly by ``reversible`` and
    callers of the function shouldn't provide it.

    .. code-block:: python

        @reversible.action
        def create_order(context, order_details):
            order_id = OrderStore.put(order_details)
            context['order_id'] = order_id
            return order_id

    The ``.backwards`` attribute of the decorated function can itself be used
    as a decorator to specify the ``backwards`` implementation of the action.

    .. code-block:: python

        @create_order.backwards
        def delete_order(context, order_details):
            if 'order_id' in context:
                # order_id will be absent if create_order failed
                OrderStore.delete(context['order_id'])

        # Note that the context argument was not provided here. It's added
        # implicitly by the library.
        action = create_order(order_details)
        order_id = reversible.execute(action)

    Both, the ``forwards`` and ``backwards`` implementations will be called
    with the same arguments. Any information that needs to be sent from
    ``forwards`` to ``backwards`` must be added to the context object.

    The context object defaults to a dictionary. An alternative context
    constructor may be provided using the ``context_class`` argument. It will
    be called with no arguments to construct the context object.

    .. code-block:: python

        @reversible.action(context_class=UserInfo)
        def create_user(user_info, user_details):
            user_info.user_id = UserStore.put(user_details)
            return user_info

    Note that a backwards action is required. Attempts to use the action
    without specifying a way to roll back will fail.

    :param forwards:
        The function will be treated as the ``forwards`` implementation.
    :param context_class:
        Constructor for context objects. A single action call will have its
        own context object and that object will be implictly passed as the
        first argument to both, the ``forwards`` and the ``backwards``
        implementations.
    """
    context_class = context_class or dict

    def decorator(_forwards):
        return ActionBuilder(_forwards, context_class)

    if forwards is not None:
        return decorator(forwards)
    else:
        return decorator


__all__ = ['action', 'execute']
