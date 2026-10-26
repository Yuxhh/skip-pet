"""Observed-file integration: roots, health, EOF, rotation and native playback."""

import json
from pathlib import Path

from sukuna_pet.playback import PetApplication
from sukuna_pet.task_bridge import BridgeReader
from bridge_files import envelope


def write_state(directory: Path, health: int, *, status: str = "running",
                boot: str = "first", known: bool = True, child: bool = False,
                lifecycle: str = "active", revision: int | None = None) -> None:
    rows = [dict(agent_id="root", root_id="root", root_turn=1, turn_id=1,
                 known=known, status=status)]
    if child:
        rows.append(dict(agent_id="child", root_id="root", root_turn=1, turn_id=3,
                         known=True, status="running"))
    identity = envelope(boot=boot, start=1000 if boot == "first" else 2000)
    (directory / "dsh-1.jsonl").touch(exist_ok=True)
    (directory / "dsh-1.snapshot.json").write_text(json.dumps(dict(
        identity, health_seq=health, lifecycle=lifecycle, snapshot_seq=health,
        revision=health if revision is None else revision,
        coverage="observed", scope="tracked-agents", agents=rows)), encoding="utf-8")
    (directory / "dsh-1.health.json").write_text(json.dumps(dict(
        identity, health_seq=health, lifecycle=lifecycle)), encoding="utf-8")


def test_root_wait_with_child_work_is_one_running_task(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    write_state(tmp_path, 1, status="waiting", child=True)
    assert reader.poll(0).text == ""
    write_state(tmp_path, 2, status="waiting", child=True)
    summary = reader.poll(1)
    assert (summary.running, summary.waiting, summary.jump) == (1, 0, True)
    write_state(tmp_path, 3, status="waiting")
    summary = reader.poll(2)
    assert (summary.running, summary.waiting, summary.jump) == (0, 1, False)
    assert "回答" in summary.text


def test_health_not_business_silence_controls_disconnect_and_grace(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    write_state(tmp_path, 1)
    reader.poll(0)
    write_state(tmp_path, 2)
    assert reader.poll(1).running == 1
    assert reader.poll(3.99).running == 1
    stale = reader.poll(4)
    assert stale.text == "" and stale.jump
    assert not reader.poll(9).jump
    write_state(tmp_path, 3, boot="replacement", known=False)
    assert not reader.poll(10).jump
    write_state(tmp_path, 4, boot="replacement", known=False)
    summary = reader.poll(11)
    assert summary.partial and not summary.jump and summary.text == ""


def test_unknown_child_does_not_turn_known_root_wait_into_whole_task_wait(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    write_state(tmp_path, 1, status="waiting", child=True)
    reader.poll(0)
    write_state(tmp_path, 2, status="waiting", child=True)
    path = tmp_path / "dsh-1.snapshot.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["agents"][1]["known"] = False
    path.write_text(json.dumps(value), encoding="utf-8")
    summary = reader.poll(1)
    assert summary.partial and summary.waiting == 0 and summary.text == ""


def test_terminal_eof_partial_line_and_snapshot_recovery(tmp_path: Path) -> None:
    reader = BridgeReader(tmp_path)
    log = tmp_path / "dsh-1.jsonl"
    row = dict(envelope(), revision=4, event="turn/end", turn_id=1, status="idle", known=True,
               agent_id="root", root_id="root", root_turn=1, outcome="completed")
    log.write_text(json.dumps(row) + "\n", encoding="utf-8")
    write_state(tmp_path, 1, revision=4)
    reader.poll(0)  # Existing history is skipped.
    write_state(tmp_path, 2, revision=4)
    assert reader.poll(1).completed == 0
    row["revision"] = 5
    encoded = json.dumps(row)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(encoded[:30])
    assert reader.poll(1.1).completed == 0
    assert not reader.poll(1.1).text
    with log.open("a", encoding="utf-8") as stream:
        stream.write(encoded[30:] + "\n")
    write_state(tmp_path, 3, status="idle", revision=5)
    # Resynchronization repairs state; it never replays an old completion.
    assert reader.poll(1.2).completed == 0


def test_task_mode_finishes_cycle_and_keeps_manual_clicks(tmp_path: Path) -> None:
    path = tmp_path / "mode.json"
    pet = PetApplication(settings_path=path)
    pet.select_mode("task")
    pet.advance(500)
    assert pet.view.stage == 0
    pet.set_task_running(True)
    assert pet.view.stage == 1
    pet.advance(100)
    pet.set_task_running(False)
    for _ in range(300):
        pet.advance(16)
    assert pet.view.stage == 0 and pet.view.holding
    assert PetApplication(settings_path=path).mode == "task"
    pet.click()
    pet.advance(500)
    assert pet.view.stage == 1 and pet.view.holding
