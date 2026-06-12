"""Tests for protocol.py — MessageType, AgentConfig, WSMessage, results."""

import pytest
from agora_agent_sdk.protocol import (
    AgentConfig,
    MessageType,
    WSMessage,
    RegistrationResult,
    MotionResult,
    SpeechResult,
    VoteResult,
    TaskNode,
)


class TestMessageType:
    def test_agent_to_coordinator_types(self):
        assert MessageType.REGISTER.value == "REGISTER"
        assert MessageType.SPEAK.value == "SPEAK"
        assert MessageType.VOTE.value == "VOTE"
        assert MessageType.HEARTBEAT.value == "HEARTBEAT"
        assert MessageType.TASK_STARTED.value == "TASK_STARTED"
        assert MessageType.TASK_PROGRESS.value == "TASK_PROGRESS"
        assert MessageType.TASK_COMPLETED.value == "TASK_COMPLETED"
        assert MessageType.TASK_FAILED.value == "TASK_FAILED"
        assert MessageType.NEW_MOTION.value == "NEW_MOTION"

    def test_coordinator_to_agent_types(self):
        assert MessageType.WELCOME.value == "WELCOME"
        assert MessageType.SPEECH_ADDED.value == "SPEECH_ADDED"
        assert MessageType.VOTE_CONFIRMED.value == "VOTE_CONFIRMED"
        assert MessageType.TASK_ASSIGNED.value == "TASK_ASSIGNED"
        assert MessageType.HEARTBEAT_ACK.value == "HEARTBEAT_ACK"
        assert MessageType.ERROR.value == "ERROR"

    def test_devils_advocate_types(self):
        assert MessageType.DEVILS_ADVOCATE_REQUEST.value == (
            "DEVILS_ADVOCATE_REQUEST"
        )
        assert MessageType.DEVILS_ADVOCATE_RESPONSE.value == (
            "DEVILS_ADVOCATE_RESPONSE"
        )


class TestAgentConfig:
    def test_defaults(self):
        cfg = AgentConfig()
        assert cfg.max_concurrent_tasks == 2
        assert cfg.heartbeat_interval_seconds == 30
        assert cfg.tpm_limit == 10000
        assert cfg.auto_accept_tasks is False


class TestWSMessage:
    def test_basic_construction(self):
        msg = WSMessage(type=MessageType.HEARTBEAT)
        assert msg.type == MessageType.HEARTBEAT
        assert msg.payload == {}
        assert msg.motion_id is None


class TestResultModels:
    def test_registration_result(self):
        r = RegistrationResult(agent_id="a1", agent_token="tok")
        assert r.status == "ok"

    def test_motion_result(self):
        r = MotionResult(motion_id="m1")
        assert r.status == "ok"

    def test_speech_result(self):
        r = SpeechResult()
        assert r.success is True

    def test_vote_result(self):
        r = VoteResult(confirmed=True)
        assert r.success is True
        assert r.confirmed is True

    def test_task_node(self):
        t = TaskNode(task_id="t1", title="Do work")
        assert t.parent_id is None
