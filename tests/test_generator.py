from __future__ import absolute_import

import mock
import pytest

import reversible


@reversible.gen
def empty_action():
    pass


@reversible.gen
def raises_return_immediately(x):
    raise reversible.Return(x)


@reversible.gen
def empty_generator():
    if False:
        yield "some action"
    else:
        return


@pytest.fixture(params=[
    empty_action,
    empty_generator,
    lambda: raises_return_immediately(None),
])
def get_none_action(request):
    return request.param


def test_execute_none_action(get_none_action):
    assert not reversible.execute(get_none_action())


def test_none_action_is_yieldable(get_none_action):
    other_action = mock.Mock()

    @reversible.gen
    def action():
        yield get_none_action()
        yield other_action

    reversible.execute(action())
    other_action.forwards.assert_called_once_with()


def test_none_action_is_yieldable_with_failure(get_none_action):
    before_action = mock.Mock()

    after_action = mock.Mock()
    after_action.forwards.side_effect = Exception('great sadness')

    @reversible.gen
    def action():
        yield before_action
        yield get_none_action()
        yield after_action

    with pytest.raises(Exception) as exc_info:
        reversible.execute(action())

    assert 'great sadness' in str(exc_info)

    before_action.forwards.assert_called_once_with()
    before_action.backwards.assert_called_once_with()


def test_not_a_generator():

    @reversible.gen
    def a():
        return 42

    assert 42 == reversible.execute(a())


def test_raise_return_on_empty():
    assert 42 == reversible.execute(raises_return_immediately(42))


def test_forwards_calls_all_yielded_actions():

    actions = []

    @reversible.gen
    def gen_based_action(count):
        for i in range(count):
            action = mock.MagicMock()
            action.forwards.return_value = i
            actions.append(action)

            result = yield action
            assert i == result

    reversible.execute(gen_based_action(100))

    for action in actions:
        action.forwards.assert_called_once_with()


def test_backwards_is_called_for_executed_actions():

    successful = []

    def successful_action(i):
        action = mock.MagicMock()
        action.forwards.return_value = i
        successful.append(action)
        return action

    failed_action = mock.MagicMock()
    failed_action.forwards.side_effect = Exception("aargh")

    not_called_action = mock.MagicMock()

    @reversible.gen
    def some_action(count):
        for i in range(count):
            yield successful_action(i)
        yield failed_action
        yield not_called_action

    with pytest.raises(Exception) as exc_info:
        reversible.execute(some_action(100))

    assert "aargh" in str(exc_info)

    for action in successful:
        action.forwards.assert_called_once_with()
        action.backwards.assert_called_once_with()

    failed_action.backwards.assert_called_once_with()

    assert not_called_action.forwards.call_count == 0
    assert not_called_action.backwards.call_count == 0


def test_raise_return():

    action = mock.MagicMock()
    action.forwards.return_value = "hello"

    @reversible.gen
    def gen_based_action():
        result = yield action
        assert "hello" == result

        raise reversible.Return("world")

    assert "world" == reversible.execute(gen_based_action())
    action.forwards.assert_called_once_with()
