Releases
========

0.2.1 (unreleased)
------------------

- Nothing changed yet.


0.2.0 (2015-07-18)
------------------

- Add support for Tornado-based actions. With usage of the module
  :py:mod:`reversible.tornado`, the ``forwards`` and ``backwards`` methods can
  now be asynchronous. See :ref:`tornado-support-overview` for details.


0.1.1 (2015-07-11)
------------------

- Fix bug where :py:func:`reversible.gen` couldn't handle functions that were
  not generators and still returned a result.


0.1.0 (2015-07-01)
------------------

- Initial release.
