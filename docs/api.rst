API Reference
=============

.. py:module:: reversible

Construction and composition
----------------------------

.. autofunction:: reversible.action

.. autofunction:: reversible.gen

Execution
---------

.. autofunction:: reversible.execute

Types
-----

.. autoclass:: reversible.Return

Tornado Support
---------------

.. py:module:: reversible.tornado

Construction and composition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: reversible.tornado.action(forwards=None, context_class=None)

   Decorator to build functions. See :py:func:`reversible.action` for details.

.. autofunction:: reversible.tornado.gen

.. autofunction:: reversible.tornado.lift

Execution
~~~~~~~~~

.. autofunction:: reversible.tornado.execute

Types
~~~~~

.. py:class:: reversible.tornado.Return

   Used to return values from :py:func:`reversible.tornado.gen` generators in
   versions of Python older than 3.3.

   See also :py:class:`reversible.Return`.
