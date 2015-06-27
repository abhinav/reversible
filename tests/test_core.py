from __future__ import absolute_import

import mock
import pytest

import reversible


class TestExecute(object):

    def test_calls_forwards(self):
        action = mock.MagicMock()
        action.forwards.return_value = 42

        assert 42 == reversible.execute(action)
        action.forwards.assert_called_once_with()

    def test_calls_backwards_for_failures(self):
        action = mock.MagicMock()
        action.forwards.side_effect = Exception('great sadness')

        with pytest.raises(Exception) as exc_info:
            reversible.execute(action)

        assert 'great sadness' in str(exc_info)
        action.forwards.assert_called_once_with()
        action.backwards.assert_called_once_with()

    def test_raises_backwards_exception(self):
        action = mock.MagicMock()
        action.forwards.side_effect = Exception('great sadness')
        action.backwards.side_effect = Exception('backwards failed')

        with pytest.raises(Exception) as exc_info:
            reversible.execute(action)

        assert 'backwards failed' in str(exc_info)
        action.forwards.assert_called_once_with()
        action.backwards.assert_called_once_with()


class TestActionBuilder(object):

    def test_forwards_is_called(self):

        @reversible.action
        def some_action(context, x):
            assert x == 42
            return 32

        @some_action.backwards
        def reverse_some_action(context, x):
            assert False, "Shouldn't be called"

        assert 32 == reversible.execute(some_action(42))

    def test_backwards_is_called_on_failure(self):

        @reversible.action
        def some_action(context, x):
            raise NotImplementedError

        backwards = some_action.backwards(mock.Mock())

        with pytest.raises(NotImplementedError):
            reversible.execute(some_action(42))

        backwards.assert_called_once_with(mock.ANY, 42)

    def test_alternative_context(self):

        @reversible.action(context_class=list)
        def action(context):
            context.append('hello')
            raise Exception('undo me')

        @action.backwards
        def undo_action(context):
            assert context == ['hello']

        for i in range(5):
            with pytest.raises(Exception) as exc_info:
                reversible.execute(action())
            assert 'undo me' in str(exc_info)

    def test_with_two_backwards_fail(self):

        @reversible.action
        def some_action(context, x):
            assert False

        @some_action.backwards
        def reverse_some_action(context, x):
            assert False

        with pytest.raises(ValueError):

            @some_action.backwards
            def reverse_some_action_again(x):
                assert False

    def test_call_without_backwards(self):

        @reversible.action
        def some_action(context, x):
            assert True

        with pytest.raises(ValueError):
            some_action(42)
