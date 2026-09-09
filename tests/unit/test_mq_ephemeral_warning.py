"""
`quantum mq publish` discarded every message and reported success.

_get_broker() defaults to the in-memory adapter, which lives inside THIS
process and dies with it. Every `quantum mq` invocation is its own process, so
publish wrote into a broker that was discarded a moment later and consume
created a fresh empty one. Both printed success. Nothing said the messages
were going nowhere.

The adapter is still useful in-process (a .q that publishes and subscribes in
one run), so this warns rather than refusing — but it warns unmissably, and
only for the actions that are meaningless within a single process.
"""

import pytest

from quantum.cli import mq


class TestTheBrokerIsMarked:
    def test_the_memory_broker_is_flagged_ephemeral(self, monkeypatch):
        monkeypatch.delenv("QUANTUM_MQ_BROKER", raising=False)
        broker = mq._get_broker()
        assert getattr(broker, "_is_ephemeral_cli_broker", False) is True


class TestTheWarning:
    def test_it_fires_for_a_cross_process_action(self, capsys):
        broker = mq._get_broker()
        mq._warn_if_ephemeral(broker, "mq publish")
        out = capsys.readouterr().out
        assert "WARN" in out
        assert "lost" in out
        assert "QUANTUM_MQ_BROKER" in out

    def test_it_is_silent_for_a_real_broker(self, capsys):
        class RealBroker:
            pass
        mq._warn_if_ephemeral(RealBroker(), "mq publish")
        assert capsys.readouterr().out == ""

    def test_it_names_the_action(self, capsys):
        mq._warn_if_ephemeral(mq._get_broker(), "mq consume")
        assert "mq consume" in capsys.readouterr().out
