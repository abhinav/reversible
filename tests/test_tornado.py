from __future__ import absolute_import

import pytest
tornado = pytest.importorskip('tornado')


import reversible.tornado as reversible


class MyException(Exception):
    pass


@pytest.fixture(params=['sync', 'async'])
def returns_42(request):
    if 'sync' == request.param:
        def forwards():
            return 42
    else:
        @tornado.gen.coroutine
        def forwards():
            return 42
    return forwards


@pytest.fixture(params=['sync', 'async'])
def does_nothing(request):
    if 'sync' == request.param:
        def backwards():
            pass
    else:
        @tornado.gen.coroutine
        def backwards():
            pass
    return backwards


@pytest.fixture(params=['sync', 'async'])
def raises_exception(request):
    if 'sync' == request.param:
        def forwards():
            raise MyException('great sadness')
    else:
        @tornado.gen.coroutine
        def forwards():
            raise MyException('great sadness')
    return forwards


@pytest.fixture(params=['class', 'decorator'])
def successful_action(returns_42, does_nothing, request):
    if request.param == 'class':
        class Action(object):
            def forwards(self):
                return returns_42()

            def backwards(self):
                return does_nothing()

        return Action
    else:
        @reversible.action
        def go(ctx):
            return returns_42()

        @go.backwards
        def rollback(ctx):
            return does_nothing()

        return go


@pytest.fixture(params=['class', 'decorator'])
def failing_action(raises_exception, does_nothing, request):
    if request.param == 'class':
        class Action(object):
            def forwards(self):
                return raises_exception()

            def backwards(self):
                return does_nothing()

        return Action
    else:
        @reversible.action
        def go(ctx):
            return raises_exception()

        @go.backwards
        def rollback(ctx):
            return does_nothing()

        return go


@pytest.fixture(params=['class', 'decorator'])
def rollback_failed_action(raises_exception, request):
    if request.param == 'class':
        class Action(object):
            def forwards(self):
                return raises_exception()

            def backwards(self):
                raise Exception('rollback failed')

        return Action
    else:
        @reversible.action
        def go(ctx):
            return raises_exception()

        @go.backwards
        def rollback(ctx):
            raise Exception('rollback failed')

        return go


@pytest.mark.gen_test
def test_execute_success(successful_action):
    result = yield reversible.execute(successful_action())
    assert 42 == result


@pytest.mark.gen_test
def test_failing_action(failing_action):
    with pytest.raises(MyException) as exc_info:
        yield reversible.execute(failing_action())
    assert 'great sadness' in str(exc_info)


@pytest.mark.gen_test
def test_rollback_fail(rollback_failed_action):
    with pytest.raises(Exception) as exc_info:
        yield reversible.execute(rollback_failed_action())
    assert 'rollback failed' in str(exc_info)


@pytest.mark.gen_test
def test_generator_execute(successful_action):

    @reversible.gen
    def action():
        result = yield successful_action()
        raise reversible.Return(result)

    value = yield reversible.execute(successful_action())
    assert 42 == value
