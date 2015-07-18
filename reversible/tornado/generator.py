from __future__ import absolute_import

import sys
import types
import functools

from tornado.gen import Return

from reversible.core import SimpleAction
from reversible.generator import _GeneratorAction
from reversible.generator import Return as _Return

from .core import _TornadoAction

_RETURNS = (Return, _Return)

Return = Return


class _Lift(object):

    __slots__ = ('future',)

    def __init__(self, future):
        self.future = future

    def forwards(self):
        return self.future

    def backwards(self):
        pass


def _map_generator(f, generator):
    """Apply ``f`` to the results of the given bi-directional generator.

    Unfortunately, generator comprehension (``f(x) for x in gen``) does not
    work for as expected for bi-directional generators. It won't send
    exceptions and results back.

    This function implements a map function for generators that sends values
    and exceptions back and forth as expected.
    """
    item = next(generator)
    while True:
        try:
            result = yield f(item)
        except Exception:
            item = generator.throw(*sys.exc_info())
        else:
            item = generator.send(result)


class _TornadoGeneratorAction(object):

    __slots__ = ('action',)

    def __init__(self, generator, io_loop=None):
        self.action = _GeneratorAction(
            _map_generator(
                functools.partial(_TornadoAction, io_loop=io_loop),
                generator,
            )
        )

    def forwards(self):
        try:
            return self.action.forwards()
        except _RETURNS as result:
            return getattr(result, 'value', None)

    def backwards(self):
        return self.action.backwards()


def gen(function, io_loop=None):
    """Allows using a generator to chain together reversible actions.

    This function is very similar to :py:func:`reversible.gen` except that it
    may be used with actions whose ``forwards`` and/or ``backwards`` methods
    are couroutines. Specifically, if either of those methods return futures
    the generated action will stop execution until the result of the future is
    available.

    .. code-block:: python

        @reversible.tornado.gen
        @tornado.gen.coroutine
        def save_comment(ctx, comment):
            ctx['comment_id'] = yield async_http_client.fetch(
                # ...
            )
            raise tornado.gen.Return(ctx['comment_id'])

        @save_comment.backwards
        def delete_comment(ctx, comment):
            # returns a Future
            return async_http_client.fetch(...)

        @reversible.tornado.gen
        def post_comment(post, comment, client):
            try:
                comment_id = yield save_comment(comment)
            except CommentStoreException:
                # Exceptions thrown by actions may be caught by the
                # action.
                yield queue_save_comment_request(comment)
            else:
                yield update_comment_count(post)
                update_cache()

    :param function:
        The generator function. This generator must yield action objects. The
        ``forwards`` and/or ``backwards`` methods on the action may be
        asynchronous operations returning coroutines.
    :param io_loop:
        IOLoop used to execute asynchronous operations. Defaults to the
        current IOLoop if omitted.
    :returns:
        An action executable via :py:func:`reversible.tornado.execute` and
        yieldable in other instances of :py:func:`reversible.tornado.gen`.
    """

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
    """Returns the result of a Tornado Future inside a generator-based action.

    Inside a :py:func:`reversible.tornado.gen` context, the meaning of
    ``yield`` changes to "execute this possibly asynchronous action and return
    the result." However sometimes it is necessary to execute a standard
    Tornado coroutine. To make this possible, the ``lift`` method is made
    available.

    .. code-block:: python

        @reversible.tornado.gen
        def my_action():
            request = yield build_request_action()
            try:
                response = yield reversible.tornado.lift(
                    AsyncHTTPClient().fetch(request)
                )
            except HTTPError:
                # ...

            raise reversible.tornado.Return(response)

    Note that operations executed through lift are assumed to be
    non-reversible. If the operations are intended to be reversible, a
    reversible action must be constructed.

    :param future:
        Tornado future whose result is required. When the returned object is
        yielded, action execution will stop until the future's result is
        available or the future fails. If the future fails, its exception will
        be propagated back at the yield point.
    :returns:
        An action yieldable inside a :py:func:`reversible.tornado.gen`
        context.
    """
    return _Lift(future)


__all__ = ['gen', 'Return', 'lift']
