import logging
from unittest.mock import Mock

import pytest  # type: ignore
from slack_bolt import Ack, Complete, Fail, Say

from listeners.functions import handle_behavior_options,jira_conn

test_logger = logging.getLogger(__name__)
jira_conn = Mock()

class TestHandleButtonBehaviorOptions:
    def setup_method(self):
        self.fake_ack = Mock(Ack)
        self.fake_complete = Mock(Complete)

    def test_handle_behavior_options(self):
        handle_behavior_options(ack=self.fake_ack, complete=self.fake_complete)

        self.fake_ack.assert_called_once()
        self.fake_complete.assert_called_once()
        kwargs = self.fake_complete.call_args.kwargs
        assert "options" in kwargs["outputs"]
        assert isinstance(kwargs["outputs"]["options"], list)

    def test_handle_behavior_options_with_exception(self):
        self.fake_complete.side_effect = Exception("test exception")

        with pytest.raises(Exception) as _:
            handle_behavior_options(ack=self.fake_ack, complete=self.fake_complete)

        self.fake_ack.assert_called_once()
        self.fake_complete.assert_called_once()


class TestHandleSampleStep:
    def setup_method(self):
        self.fake_inputs = {"user_id": "U1234", "button_behavior": "2"}
        self.fake_say = Mock(Say)
        self.fake_fail = Mock(Fail)

