from __future__ import absolute_import

import pytest
tornado = pytest.importorskip('tornado')


import reversible.tornado as reversible


class MyException(Exception):
    pass


class RollbackFailException(Exception):
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
def successful_with_rollback_fail_action(does_nothing, request):
    if request.param == 'class':
        class Action(object):
            def forwards(self):
                return does_nothing()

            def backwards(self):
                raise RollbackFailException('rollback failed')

        return Action
    else:
        @reversible.action
        def go(ctx):
            return does_nothing()

        @go.backwards
        def rollback(ctx):
            raise RollbackFailException('rollback failed')

        return go


@pytest.fixture(params=['class', 'decorator'])
def rollback_failed_action(raises_exception, request):
    if request.param == 'class':
        class Action(object):
            def forwards(self):
                return raises_exception()

            def backwards(self):
                raise RollbackFailException('rollback failed')

        return Action
    else:
        @reversible.action
        def go(ctx):
            return raises_exception()

        @go.backwards
        def rollback(ctx):
            raise RollbackFailException('rollback failed')

        return go


@pytest.fixture(params=['delay', 'instant_coroutine', 'maybe_future'])
def make_future(request):
    if request.param == 'delay':

        @tornado.gen.coroutine
        def mk(v=None, exc=None):
            yield tornado.gen.sleep(0.01)
            if exc is None:
                raise tornado.gen.Return(v)
            else:
                raise exc

    elif request.param == 'instant_coroutine':

        @tornado.gen.coroutine
        def mk(v=None, exc=None):
            if exc is None:
                return v
            else:
                raise exc

    else:

        def mk(v=None, exc=None):
            future = tornado.gen.Future()
            if exc is None:
                future.set_result(v)
            else:
                future.set_exception(exc)
            return future

    return mk


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
    with pytest.raises(RollbackFailException) as exc_info:
        yield reversible.execute(rollback_failed_action())
    assert 'rollback failed' in str(exc_info)


@pytest.mark.gen_test
def test_generator_execute_success(successful_action):

    @reversible.gen
    def action():
        result = yield successful_action()
        raise reversible.Return(result)

    value = yield reversible.execute(action())
    assert 42 == value


@pytest.mark.gen_test
def test_generator_execute_failure(failing_action):

    @reversible.gen
    def action():
        yield failing_action()
        pytest.fail('Should not reach here')

    with pytest.raises(MyException) as exc_info:
        yield reversible.execute(action())

    assert 'great sadness' in str(exc_info)


@pytest.mark.gen_test
def test_generator_execute_failure_catch(failing_action):

    @reversible.gen
    def action():
        try:
            yield failing_action()
        except MyException:
            raise tornado.gen.Return(100)

    result = yield reversible.execute(action())
    assert 100 == result


@pytest.mark.gen_test
def test_generator_rollback_fail(
    successful_with_rollback_fail_action,
    failing_action
):

    @reversible.gen
    def action():
        yield successful_with_rollback_fail_action()
        yield failing_action()
        pytest.fail('Should not reach here')

    with pytest.raises(RollbackFailException) as exc_info:
        yield reversible.execute(action())

    assert 'rollback failed' in str(exc_info)


@pytest.mark.gen_test
def test_generator_lift(make_future, successful_action):

    @reversible.gen
    def action():
        yield successful_action()
        value = yield reversible.lift(make_future(42))

        raise reversible.Return(value)

    value = yield reversible.execute(action())
    assert 42 == value


@pytest.mark.gen_test
def test_generator_lift_with_failing_future(make_future, successful_action):

    @reversible.gen
    def action():
        yield successful_action()
        yield reversible.lift(
            make_future(exc=MyException('future failed'))
        )

    with pytest.raises(MyException) as exc_info:
        yield reversible.execute(action())

    assert 'future failed' in str(exc_info)


@pytest.mark.gen_test
def test_generator_lift_with_rollback(make_future, failing_action):

    @reversible.gen
    def action():
        value = yield reversible.lift(make_future(42))
        assert value == 42

        yield failing_action()

    with pytest.raises(MyException) as exc_info:
        yield reversible.execute(action())

    assert 'great sadness' in str(exc_info)
