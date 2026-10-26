"""Real-file protocol fixture shared by public bridge integration tests."""
import hashlib
import json
import os
from pathlib import Path
import time

from sukuna_pet.task_bridge import BridgeReader


def digest(path: Path) -> str:
    return hashlib.sha256(os.path.normcase(str(path.resolve())).encode()).hexdigest()


def envelope(*, pid: int = 1, boot: str = "first", start: int = 1000) -> dict:
    return dict(schema_version=1, owner="@sukuna-pet/dsh-bridge", user_id=digest(Path.home()),
                profile_id=digest(Path.cwd()), instance_id=f"instance-{start}", pid=pid,
                process_start_id=str(start), boot_id=boot, boot_started_at=start + 10, host_version="0.2.1-rc.2",
                plugin_version="0.2.0", capabilities=["observed-state", "snapshot-boundary",
                "contiguous-events", "independent-health"])


def agent(status: str = "running", *, turn: int = 1, root: str = "root") -> dict:
    return dict(agent_id=root, root_id=root, root_turn=turn, turn_id=turn,
                status=status, known=True, question_ids=[], approval_ids=[])


class BridgeFiles:
    def __init__(self, directory: Path, **identity: object) -> None:
        self.directory = directory
        self.identity = envelope(**identity)
        self.prefix = directory / f"dsh-{self.identity['pid']}"
        self.log = self.prefix.with_suffix(".jsonl")
        self.log.touch(exist_ok=True)
        self.seq = 0

    def publish(self, health: int, revision: int = 0, rows: list | None = None,
                lifecycle: str = "active") -> None:
        self.seq += 1
        value = dict(self.identity, revision=revision, health_seq=health, snapshot_seq=self.seq,
                     lifecycle=lifecycle, coverage="observed", scope="tracked-agents",
                     agents=rows if rows is not None else [agent()])
        self.prefix.with_suffix(".snapshot.json").write_text(json.dumps(value), encoding="utf-8")
        self.health(health, lifecycle)

    def health(self, health: int, lifecycle: str = "active") -> None:
        self.prefix.with_suffix(".health.json").write_text(json.dumps(dict(
            self.identity, health_seq=health, lifecycle=lifecycle)), encoding="utf-8")

    def event(self, revision: int, *, event: str = "agent/state", state: dict | None = None,
              **extra: object) -> dict:
        return dict(self.identity, revision=revision, event=event, emitted_at=time.time(),
                    **(state if state is not None else agent()), **extra)

    def append(self, row: dict) -> None:
        with self.log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")

    def connect(self, reader: BridgeReader) -> None:
        self.publish(1)
        assert not reader.poll(0).text
        self.publish(2)
        assert reader.poll(1).running == 1


