"""Agreed seam: real plugin files consumed by the public task summary."""
from collections.abc import Callable, Iterator
import os
from pathlib import Path
import subprocess
from time import monotonic, sleep

import pytest

from sukuna_pet.task_bridge import BridgeReader, TaskSummary

Host = Callable[[str, Callable[[TaskSummary], bool]], TaskSummary]


@pytest.fixture
def host(tmp_path: Path) -> Iterator[Host]:
    env = dict(os.environ, SUKUNA_PET_BRIDGE_DIR=str(tmp_path))
    with subprocess.Popen(["node", "tests/bridge_current_state.mjs"], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
                          creationflags=subprocess.CREATE_NO_WINDOW) as child:
        assert child.stdout is not None and child.stdin is not None
        assert child.stdout.readline().strip() == "ready"
        reader = BridgeReader(tmp_path)

        def wait(command: str, predicate: Callable[[TaskSummary], bool]) -> TaskSummary:
            assert child.stdin is not None
            if command:
                child.stdin.write(command + "\n")
                child.stdin.flush()
                assert child.stdout is not None
                assert child.stdout.readline().strip() == f"applied {command}"
            deadline = monotonic() + 5
            summary = reader.poll(monotonic())
            while monotonic() < deadline and not predicate(summary):
                sleep(.1)
                summary = reader.poll(monotonic())
            assert predicate(summary), summary
            return summary

        try:
            wait("", lambda summary: summary.waiting == 1)
            yield wait
        finally:
            child.stdin.write("close\n")
            child.stdin.flush()
            child.wait(timeout=5)
        assert child.returncode == 0


def test_real_approval_uses_approval_copy(host: Host) -> None:
    summary = host("approval", lambda summary: "批准" in summary.text)
    assert summary.waiting == 1 and not summary.jump and "回答" not in summary.text
    summary = host("reload", lambda summary: summary.waiting == 1 and summary.approvals == 1)
    assert not summary.jump and summary.completed == summary.failed == summary.interrupted == 0


def test_child_work_keeps_one_task_running_and_preserves_question(host: Host) -> None:
    summary = host("child", lambda summary: summary.running == 1)
    assert summary.waiting == 0 and summary.jump and "回答" in summary.text


def test_timed_continuation_runs_and_retains_question_after_reload(host: Host) -> None:
    summary = host("continued", lambda summary: summary.running == 1)
    assert summary.questions == 1 and summary.waiting == 0
    summary = host("reload", lambda summary: summary.running == 1 and summary.questions == 1)
    assert summary.completed == 0
    summary = host("answer", lambda summary: summary.questions == 0 and summary.running == 1)
    assert "回答" not in summary.text


def test_nested_wait_does_not_guess_whether_program_is_suspended(host: Host) -> None:
    summary = host("nested", lambda summary: summary.partial)
    assert summary.running == summary.waiting == 0 and not summary.jump and summary.text == ""


def test_machine_answerer_is_not_claimed_as_human_wait(host: Host) -> None:
    summary = host("machine", lambda summary: summary.partial)
    assert summary.waiting == summary.approvals == summary.questions == 0 and summary.text == ""


def test_old_child_and_old_end_cannot_pollute_new_root_turn(host: Host) -> None:
    host("child", lambda summary: summary.running == 1)
    summary = host("new-turn", lambda summary: summary.running == 1 and summary.questions == 0)
    assert not summary.partial
    summary = host("old-end", lambda summary: summary.running == 1)
    assert summary.failed == summary.completed == 0


def test_turn_failure_is_transient_and_not_replayed_after_reload(host: Host) -> None:
    summary = host("fail", lambda summary: summary.failed == 1)
    assert not summary.jump
    summary = host("reload", lambda summary: summary.failed == 0 and not summary.partial)
    assert summary.text == ""


def test_completed_parallel_call_does_not_keep_waiting_task_jumping(host: Host) -> None:
    summary = host("parallel-job", lambda summary: summary.running == 1)
    assert summary.jump and summary.questions == 1
    summary = host("finish-job", lambda summary: summary.waiting == 1)
    assert not summary.jump
    summary = host("post-job", lambda summary: summary.waiting == 1)
    assert not summary.jump
    summary = host("reload", lambda summary: summary.partial)
    assert summary.running == summary.waiting == 0 and summary.text == ""


def test_late_plugin_recovers_existing_question_wait(host: Host, tmp_path: Path) -> None:
    summary = host("", lambda summary: summary.waiting == 1)
    assert not summary.jump and "回答" in summary.text
    assert "PRIVATE_QUESTION" not in next(tmp_path.glob("*.snapshot.json")).read_text()


def test_answer_removal_needs_execution_evidence_before_resuming(host: Host) -> None:
    summary = host("answer", lambda summary: summary.questions == 0)
    assert summary.partial and not summary.jump and summary.running == summary.waiting == 0
    summary = host("question-result", lambda summary: summary.running == 1)
    assert not summary.partial and summary.failed == summary.completed == summary.interrupted == 0


def test_unattributed_approval_cannot_be_assigned_to_current_turn(host: Host) -> None:
    host("new-turn", lambda summary: summary.running == 1)
    summary = host("stale-approval", lambda summary: summary.partial or summary.approvals > 0)
    assert summary.partial and summary.approvals == 0 and not summary.text and not summary.jump
