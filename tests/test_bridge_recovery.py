"""Transport failures through real files and the public summary boundary."""
import json
import os
from pathlib import Path
import time

import pytest

from sukuna_pet.task_bridge import BridgeReader
from bridge_files import BridgeFiles, agent


def test_gap_hides_text_and_jump_until_new_observed_snapshot(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    files.append(files.event(2, state=agent("waiting")))
    files.health(3)
    summary = reader.poll(2)
    assert summary.text == "" and not summary.jump
    # Independent health cannot repair missing state or invoke disconnect grace.
    files.health(4)
    assert not reader.poll(3).jump
    files.publish(5, 2, [agent("waiting")])
    summary = reader.poll(4)
    assert summary.waiting == 1 and not summary.jump

def test_continuous_events_update_state_and_cannot_revive_prior_turn(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    files.append(files.event(1, state=agent("waiting")))
    assert reader.poll(1.1).waiting == 1
    files.append(files.event(2, state=agent(turn=2)))
    assert reader.poll(1.2).running == 1
    files.append(files.event(3, event="turn/end", state=agent("idle"), outcome="completed"))
    assert reader.poll(1.3).running == 1
    files.append(files.event(4, event="turn/end", state=agent("idle", turn=2), outcome="completed"))
    assert reader.poll(1.4).completed == 1
    files.append(files.event(5, state=agent(turn=2)))
    assert reader.poll(1.5).running == 0
    # A periodic snapshot must not undo the newer live boundary.
    files.publish(3, 4, [agent(turn=2)])
    assert reader.poll(2).running == 0

def test_stop_has_one_grace_deadline_and_resume_requires_new_snapshot(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    files.health(3, "stopped")
    stopped = reader.poll(2)
    assert not stopped.text and stopped.jump
    files.health(4, "stopped")
    assert reader.poll(6).jump
    files.health(5, "stopped")
    assert not reader.poll(7).jump
    assert not reader.poll(8).jump


def test_stalled_channel_reconnect_does_not_reuse_pre_disconnect_snapshot(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    assert reader.poll(4).jump
    files.health(3)
    assert not reader.poll(5).text
    files.publish(4, 0, [agent("waiting")])
    assert reader.poll(6).waiting == 1

@pytest.mark.parametrize("field,value", [("schema_version", 2), ("user_id", "other-user"),
    ("pid", 9), ("capabilities", []), ("profile_id", ""), ("process_start_id", "")])
def test_invalid_identity_cannot_keep_old_state(tmp_path: Path, field: str, value: object) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    path = files.prefix.with_suffix(".health.json")
    health = json.loads(path.read_text(encoding="utf-8"))
    health[field] = value
    path.write_text(json.dumps(health), encoding="utf-8")
    assert not reader.poll(1.2).text
    assert not reader.poll(1.2).jump


def test_replaced_generation_ignores_late_health_snapshot_and_events(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    first = BridgeFiles(tmp_path)
    first.connect(reader)
    replacement = BridgeFiles(tmp_path, boot="replacement", start=2000)
    replacement.publish(1, rows=[agent("waiting")])
    assert not reader.poll(2).text
    replacement.publish(2, rows=[agent("waiting")])
    assert reader.poll(3).waiting == 1
    first.publish(7)
    first.append(first.event(1, event="turn/end", state=agent("idle"), outcome="completed"))
    summary = reader.poll(3.1)
    assert summary.waiting == 1 and summary.completed == 0

@pytest.mark.parametrize("failure", ["half-line", "oversize-record", "oversize-snapshot", "half-snapshot", "buffer-bytes", "buffer-count", "rotation", "truncate-rewrite"])
def test_file_damage_is_unknown_until_new_snapshot(tmp_path: Path, failure: str) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    if failure == "half-line":
        with files.log.open("ab") as stream:
            stream.write(b'{"revision":1')
    elif failure == "oversize-record":
        with files.log.open("ab") as stream:
            stream.write(b'x' * 65537 + b'\n')
    elif failure == "oversize-snapshot":
        files.prefix.with_suffix(".snapshot.json").write_bytes(b' ' * (8 * 1024 * 1024 + 1))
    elif failure == "half-snapshot":
        files.prefix.with_suffix(".snapshot.json").write_bytes(b'{"agents":[')
    elif failure == "buffer-bytes":
        files.log.write_bytes(b'x' * (1024 * 1024 + 1))
    elif failure == "buffer-count":
        with files.log.open("ab") as stream:
            stream.write(b'{}\n' * 1025)
    elif failure == "rotation":
        files.log.rename(str(files.log) + '.1')
        files.append(files.event(1, state=agent("waiting")))
    else:
        files.append(files.event(1, state=agent("waiting")))
        assert reader.poll(1.1).waiting == 1
        files.log.write_bytes(b'x' * 2000)  # Same inode, rewritten beyond the old offset.
    files.health(3)
    summary = reader.poll(2)
    assert not summary.text and not summary.jump
    # Start a clean log and publish a current observation; never replay a damaged suffix.
    files.log.write_bytes(b'')
    reader.poll(2.1)
    files.publish(4, 10, [agent("waiting")])
    assert reader.poll(3).waiting == 1


def test_other_instance_keeps_running_while_damaged_instance_is_hidden(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    first = BridgeFiles(tmp_path)
    second = BridgeFiles(tmp_path, pid=2)
    first.publish(1)
    second.publish(1)
    reader.poll(0)
    first.publish(2)
    second.publish(2)
    assert reader.poll(1).running == 2
    first.append(first.event(3))
    summary = reader.poll(1.1)
    assert summary.running == 1 and summary.jump and summary.partial

def test_same_size_in_place_rewrite_cannot_keep_old_state(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    files.append(files.event(1, state=agent("waiting")))
    assert reader.poll(1.1).waiting == 1
    size = files.log.stat().st_size
    files.log.write_bytes(b' ' * (size - 1) + b'\n')
    assert reader.poll(1.2).text == ""

def test_end_age_is_bounded_and_other_wait_survives_banner_expiry(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    files.append(files.event(1, state=agent("waiting", root="other")))
    files.append(files.event(2, event="turn/end", state=agent("idle"), outcome="completed"))
    summary = reader.poll(1.1)
    assert summary.completed == 1 and summary.waiting == 1
    for health in range(3, 12):
        files.health(health)
        summary = reader.poll(float(health))
    assert summary.completed == 0 and summary.waiting == 1
    # An end that sat on disk for nine seconds cannot get a fresh eight seconds.
    old_end = files.event(3, event="turn/end", state=agent("idle", root="other"), outcome="failed")
    old_end["emitted_at"] -= 9
    files.append(old_end)
    assert reader.poll(11.1).failed == 0


def test_duplicate_end_does_not_extend_banner_and_snapshot_boundary_skips_history(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    end = files.event(1, event="turn/end", state=agent("idle"), outcome="completed")
    files.append(end)
    assert reader.poll(1.1).completed == 1
    files.append(end)
    files.health(3)
    assert reader.poll(2).completed == 1
    files.publish(4, 1, [agent("idle")])
    assert reader.poll(3).completed == 1
    late_reader = BridgeReader(tmp_path)
    assert late_reader.poll(3).completed == 0
    files.publish(5, 1, [agent("idle")])
    assert late_reader.poll(4).completed == 0
    files.health(6)
    assert reader.poll(9.1).completed == 0

def test_cleanup_only_expired_owned_stopped_generation(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    stopped = BridgeFiles(tmp_path, pid=1)
    stopped.publish(1, lifecycle="stopped")
    active = BridgeFiles(tmp_path, pid=2)
    active.publish(1)
    foreign = BridgeFiles(tmp_path, pid=3)
    foreign.identity["user_id"] = "other-user"
    foreign.publish(1, lifecycle="stopped")
    unknown = BridgeFiles(tmp_path, pid=4)
    unknown.identity["schema_version"] = 77
    unknown.publish(1, lifecycle="stopped")
    for file in tmp_path.iterdir():
        os.utime(file, (time.time() - 90000,) * 2)
    reader.poll(0)
    assert not stopped.prefix.with_suffix(".snapshot.json").exists()
    assert not stopped.prefix.with_suffix(".health.json").exists()
    for files in (active, foreign, unknown):
        assert files.prefix.with_suffix(".snapshot.json").exists()
        assert files.prefix.with_suffix(".health.json").exists()

def test_unseen_older_generation_cannot_replace_current_pid(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    current = BridgeFiles(tmp_path, boot="current", start=2000)
    current.connect(reader)
    old = BridgeFiles(tmp_path, boot="unseen-old", start=1000)
    old.publish(10, rows=[agent("waiting")])
    assert reader.poll(1.1).running == 1
    old.publish(11, rows=[agent("waiting")])
    assert reader.poll(1.2).running == 1

def test_sleep_resume_discards_backlog_before_rechecking_current_snapshot(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    files.append(files.event(1, event="turn/end", state=agent("idle"), outcome="completed"))
    files.publish(7, 1, [agent("idle")])
    # No consumer polls during a five-second suspension; the producer kept going.
    summary = reader.poll(6)
    assert summary.completed == 0 and not summary.text

def test_recovery_snapshot_must_cover_highest_seen_revision(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    files.append(files.event(10, state=agent("waiting")))
    assert not reader.poll(1.1).text
    files.publish(3, 1, [agent()])
    assert not reader.poll(2).text
    files.publish(4, 10, [agent("waiting")])
    assert reader.poll(3).waiting == 1

def test_unidentified_round_never_earns_disconnect_jump_grace(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.publish(1, rows=[agent(turn=0)])
    reader.poll(0)
    files.publish(2, rows=[agent(turn=0)])
    assert not reader.poll(1).jump
    assert not reader.poll(4).jump

@pytest.mark.parametrize("corruption", ["missing-revision", "unknown-event", "invalid-end", "invalid-outcome"])
def test_malformed_live_record_is_unknown_without_crashing_reader(tmp_path: Path, corruption: str) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    row = files.event(1)
    if corruption == "missing-revision":
        del row["revision"]
    elif corruption == "unknown-event":
        row["event"] = "not-a-state-event"
    else:
        row["event"] = "turn/end"
        row["outcome"] = "completed" if corruption == "invalid-end" else "not-an-outcome"
        row["status"] = "running" if corruption == "invalid-end" else "idle"
    files.append(row)
    summary = reader.poll(1.1)
    assert summary.partial and not summary.text and not summary.jump
    files.publish(3, 1, [agent("waiting")])
    assert reader.poll(2).waiting == 1

def test_omitting_ended_root_in_snapshot_does_not_erase_round_watermark(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    files.append(files.event(1, event="turn/end", state=agent("idle"), outcome="completed"))
    assert reader.poll(1.1).completed == 1
    files.publish(3, 2, [])
    assert reader.poll(2).running == 0
    files.append(files.event(3))
    assert reader.poll(2.1).running == 0


def test_overflow_skips_to_consistent_cursor_and_recovers_without_log_rewrite(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    for revision in range(1, 2500):
        files.append(files.event(revision, state=agent("waiting")))
    assert files.log.stat().st_size > 1024 * 1024
    assert not reader.poll(1.1).text
    files.publish(3, 2499, [agent("waiting")])
    assert reader.poll(2).waiting == 1

def test_old_idle_child_in_observed_registry_does_not_block_recovery(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    files = BridgeFiles(tmp_path)
    files.connect(reader)
    files.append(files.event(1, state=agent(turn=2)))
    assert reader.poll(1.1).running == 1
    files.append(files.event(3, state=agent(turn=2)))
    assert not reader.poll(1.2).text
    child = dict(agent("idle"), agent_id="old-child", turn_id=3)
    files.publish(3, 3, [agent(turn=2), child])
    assert reader.poll(2).running == 1
