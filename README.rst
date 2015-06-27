``reversible``
==============

``reversible`` provides a simple abstraction for actions that can be
reversed or rolled back and provides methods to construct, chain, and consume
them in a readable way.

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
