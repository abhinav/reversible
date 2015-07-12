from __future__ import absolute_import

import pytest
tornado = pytest.importorskip('tornado')


import reversible.tornado as reversible


@pytest.fixture(params=['sync', 'async'])
def simple_forwards(request):
    if 'sync' == request.param:
        def forwards():
            return 42
    else:
        @tornado.gen.coroutine
        def forwards():
            return 42
    return forwards


@pytest.fixture(params=['sync', 'async'])
def simple_backwards(request):
    if 'sync' == request.param:
        def backwards():
            pass
    else:
        @tornado.gen.coroutine
        def backwards():
            pass
    return backwards


@pytest.fixture(params=['class', 'decorator'])
def simple_action(simple_forwards, simple_backwards, request):
    if request.param == 'class':
        class Action(object):
            def forwards(self):
                return simple_forwards()

            def backwards(self):
                return simple_backwards()

        return Action
    else:
        @reversible.action
        def go(ctx):
            return simple_forwards()

        @go.backwards
        def rollback(ctx):
            return simple_backwards()

        return go


@pytest.mark.gen_test
def test_simple_execute(simple_action):
    result = yield reversible.execute(simple_action())
    assert 42 == result


@pytest.mark.gen_test
def test_generator_execute(simple_action):

    @reversible.gen
    def action():
        result = yield simple_action()
        raise reversible.Return(result)

    value = yield reversible.execute(simple_action())
    assert 42 == value
