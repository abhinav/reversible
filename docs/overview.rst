Overview
========

Basics
------

The primary concept in ``reversible`` is an action. An action is any object
that has a ``forwards()`` and a ``backwards()`` method (each taking no
arguments besides the implicit ``self`` argument). The ``forwards`` method
executes the actual operation the action represents. The ``backwards`` method
defines a way to undo the operation executed by the ``forwards`` method. A
simple example of this is,

.. code-block:: python

    class SaveComment(object):

        def __init__(self, post_id, comment_body):
            self.post_id = post_id
            self.comment_body = comment_body
            self.comment_id = None

        def forwards(self):
            self.comment_id = CommentStore.put(
                self.post_id,
                self.comment_body,
            )
            return self.comment_id

        def backwards(self):
            if self.comment_id is not None:
                # comment_id can be None if the forwards() failed to
                # execute.
                CommentStore.delete(self.comment_id)

The library provides the :py:func:`reversible.execute` method to execute such
an action.

.. code-block:: python

    comment_id = reversible.execute(SaveComment(post_id, comment_body))

This in itself is not very interesting. In fact it's probably more work than a
manual ``try-except``. To make defining new actions easier, the
:py:func:`reversible.action` function is provided.

.. code-block:: python

    @reversible.action
    def increment_comment_count(context, post_id):
        post = PostStore.get(post_id)
        old_count = post.comment_count
        post.comment_count += 1
        post.save()
        context['old_count'] = old_count
        return post.comment_count

    @increment_comment_count.backwards
    def decrement_comment_count(context, post_id):
        if 'old_count' in context:
            # If update failed, old_count will not be present.
            post = PostStore.get(post_id)
            post.comment_count = context['old_count']
            post.save()

    # Note that the context argument is implicit. Callers need not
    # provide it.
    new_count = reversible.execute(increment_comment_count(post_id))

From here, you can combine reversible actions into more complex reversible
actions using :py:func:`reversible.gen`. It allows using Python's ``yield``
syntax to combine an arbitrary number of actions together.

.. code-block:: python

    @reversible.gen
    def post_comment(user_id, post_id, comment_body):
        comment_id = yield SaveComment(post_id, comment_body)
        yield increment_comment_count(post_id)
        yield update_comment_list(user_id, comment_id)

If any of the actions in a ``reversible.gen``-based action fail, all actions
that have been executed so far are reverted using their ``backwards`` methods
**in the reverse order**. So the above is approximately equivalent to:

.. code-block:: python

    def post_comment(user_id, post_id, comment_body):
        comment_id = save_comment(post_id, comment_body)
        try:
            increment_comment_count(post_id)
        except Exception:
            delete_comment(comment_id)

        try:
            update_comment_list(user_id, comment_id)
        except Exception:
            decrement_comment_count(post_id)
            delete_comment(comment_id)

Clearly, the manual approach grows ungainly really fast. Especially if you
decided to add a few more steps.

The ``yield`` based approach also makes some more complex use cases possible.
For example,

.. code-block:: python

    @reversible.gen
    def add_timestamps_to_comments(post_id):
        # Under this [silly] scenario, you want to add timestamps to
        # the bodies of all comments, but only if all calls succeed.
        for comment_id in PostStore.get(post_id).comments:
            comment = CommentStore.get(comment_id)
            yield update_comment_body(
                comment_id,
                "\n".join(
                    comment.body, 'Posted:', format_time(comment.time)
                ),
            )

Tornado Support
---------------

``reversible`` also supports use of `Tornado
<http://www.tornadoweb.org/en/stable/>`_-based asynchronous operations within
actions with the :py:mod:`reversible.tornado` module. The module acts as an
almost drop-in replacement for the ``reversible`` module. Recommended usage is
to import it like so,

.. code-block:: python

    import reversible.tornado as reversible


For clarity, any examples that follow will use the full path
(``reversible.tornado``) instead of the module alias.

As with the standard usage of the module, the primary abstraction is an action,
which is any object with a ``forwards()`` and ``backwards()`` method. However,
now those methods can be Tornado coroutines, or other asynchronous operations
that return a ``Future`` as their result.

.. code-block:: python

    class SaveComment(object):

        def __init__(self, post_id, comment_body):
            self.post_id = post_id
            self.comment_body = comment_body
            self.comment_id = None

        @tornado.gen.coroutine
        def forwards(self):
            self.comment_id = yield CommentStore.put(
                self.post_id,
                self.comment_body,
            )
            raise tornado.gen.Return(self.comment_id)

        def backwards(self):
            if self.comment_id is not None:
                # comment_id can be None if the forwards() failed to
                # execute.
                return CommentStore.delete(self.comment_id)

:py:func:`reversible.tornado.execute` executes an action and returns its result
as a Future.

.. code-block:: python

    reversible.tornado.execute(
        SaveComment(42, "hello")
    ).add_done_callback(on_comment_save)

    # The futures just plain Tornado futures so they're yieldable
    # in coroutines

    @tornado.gen.coroutine
    def go():
        try:
            result = yield reversible.tornado.execute(SaveComment(..))
        except CommentStoreException:
            # ...

:py:func:`reversible.tornado.action` can be used to construct actions using
decorators.

.. code-block:: python

    @reversible.tornado.action
    @tornado.gen.coroutine
    def create_order(context, order_details):
        order_id = yield OrderStore.put(order_details)
        context['order_id'] = order_id
        return order_id

    @create_order.backwards
    @tornado.gen.coroutine
    def delete_order(context, order_details):
        if 'order_id' in context:
            # order_id will be absent if create_order failed
            yield OrderStore.delete(context['order_id'])

And :py:func:`reversible.tornado.gen` can be used to chain reversible Tornado
actions together into larger actions.

.. code-block:: python

    @reversible.tornado.gen
    def post_comment(user_id, post_id, comment_body):
        comment_id = yield SaveComment(post_id, comment_body)
        yield increment_comment_count(post_id)
        yield update_comment_list(user_id, comment_id)

Note that this does not look any different from the example of using
``reversible.gen``. Similar to how ``tornado.gen.coroutine`` changes the
meaning of ``yield`` to "transfer control back to the IO loop until the
result of the future is available," ``reversible.tornado.gen`` changes the
meaning of ``yield`` to "attempt to execute this action, and if it is an
asynchronous action, transfer control back to the IO loop until the result
is available."

Changing the definition of ``yield`` like this means you can't simply fall back
to Tornado's definition in the middle of a ``reversible.tornado.gen``. You have
to use :py:func:`reversible.tornado.lift``. This function allows transferring
control to the IO loop until the result of an arbitrary future is available.

.. code-block:: python

    @reversible.tornado.gen
    def foo():
        yield some_action()
        yield reversible.tornado.lift(tornado.gen.sleep(1))
        yield another_action()

It is worth noting that lifted Tornado futures are not real reversible actions.
The system doesn't know how to undo them. If the operation is intended to be
reversible, define it as an actual reversible action instead of lifting the
Tornado future.
