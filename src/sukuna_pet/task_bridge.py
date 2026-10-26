"""Observed DSH file state, read off the animation thread.

File discovery, byte cursors and startup EOF follow dsh-pet's DshMonitor /
ByteOffsetTailer (34d810b1, MIT). Snapshots and explicit health are additions.
Coverage remains 'observed': they do not assert authoritative host wait recovery.
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import threading
from time import monotonic
from typing import Any


def bridge_directory() -> Path:
    override = os.environ.get("SUKUNA_PET_BRIDGE_DIR")
    if override:
        return Path(override)
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share"))) / "sukuna-pet/bridge/dsh"


@dataclass(frozen=True)
class TaskSummary:
    running: int = 0
    waiting: int = 0
    partial: bool = False
    jump: bool = False
    completed: int = 0
    failed: int = 0
    interrupted: int = 0

    @property
    def text(self) -> str:
        parts: list[str] = []
        for count, word in ((self.completed, "办完"), (self.failed, "失败"), (self.interrupted, "中断")):
            if count:
                parts.append(f"{count} 个{word}")
        if self.running:
            parts.append(f"{self.running} 个还在办")
        if self.waiting:
            parts.append(f"小鬼，{self.waiting} 个等你回答")
        if not parts:
            return ""
        if not (self.completed or self.failed or self.interrupted):
            if self.running == 1 and not self.waiting:
                return "已查清的，还在办。" if self.partial else "哼，还在办。等着。"
            if self.waiting == 1 and not self.running:
                return ("已查清的，" if self.partial else "") + "话说清楚，小鬼。等你回答。"
        return ("已查清的，" if self.partial else "哼，") + "。".join(parts) + "。"


@dataclass
class _Writer:
    boot: str
    health: int
    changed_at: float
    verified: bool = False
    active: bool = True
    agents: list[dict[str, Any]] = field(default_factory=list)


class BridgeReader:
    """Poll only our bounded files; combine roots without counting children twice."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._writers: dict[Path, _Writer] = {}
        self._tails: dict[Path, tuple[int, int, bytes]] = {}
        self._ends: dict[tuple[str, str, int], tuple[str, float, Path]] = {}
        self._last_end_revision: dict[str, int] = {}

    def poll(self, now: float) -> TaskSummary:
        for path in self.directory.glob("dsh-*.snapshot.json"):
            self._snapshot(path, now)
        for path in self.directory.glob("dsh-*.jsonl"):
            self._tail(path, now)
        groups: dict[tuple[str, str, int], list[str]] = {}
        partial = False
        jump = False
        healthy: set[Path] = set()
        for path, writer in self._writers.items():
            fresh = writer.verified and writer.active and now - writer.changed_at < 3
            if fresh:
                healthy.add(path)
            known_running = any(row.get("known") is True and row.get("status") == "running"
                                for row in writer.agents)
            if writer.verified and known_running:
                # Explicit exit confirms immediately; otherwise detection takes 3s.
                deadline = writer.changed_at + (8 if writer.active else 5)
                jump |= fresh or now < deadline
            if not fresh:
                continue
            for row in writer.agents:
                root, turn = row.get("root_id"), row.get("root_turn")
                identity = ((writer.boot, root, turn)
                            if isinstance(root, str) and isinstance(turn, int) and not isinstance(turn, bool) and turn > 0
                            else None)
                if row.get("known") is not True:
                    partial = True
                    if identity is not None and row.get("status") in ("running", "waiting"):
                        groups.setdefault(identity, []).append("unknown")
                    continue
                if row.get("status") not in ("running", "waiting"):
                    continue
                if identity is None:
                    partial = True
                    continue
                groups.setdefault(identity, []).append(row["status"])
        running = sum("running" in states for states in groups.values())
        waiting = sum("running" not in states and "unknown" not in states and "waiting" in states
                      for states in groups.values())
        for key, (_, until, path) in list(self._ends.items()):
            if now >= until or path not in healthy:
                del self._ends[key]
        outcomes = [value[0] for key, value in self._ends.items() if key not in groups]
        return TaskSummary(running, waiting, partial, jump or running > 0,
                           outcomes.count("completed"), outcomes.count("failed"),
                           outcomes.count("interrupted"))

    def _snapshot(self, path: Path, now: float) -> None:
        try:
            if path.stat().st_size > 8 * 1024 * 1024:
                return
            value = json.loads(path.read_bytes())
            if not isinstance(value, dict) or value.get("schema") != 1 or value.get("coverage") != "observed":
                return
            boot, health, rows = value.get("boot_id"), value.get("health_seq"), value.get("agents")
            if not isinstance(boot, str) or len(boot) > 64 or type(health) is not int:
                return
            if not isinstance(rows, list) or len(rows) > 4096 or not all(isinstance(row, dict) for row in rows):
                return
            writer = self._writers.get(path)
            if writer is None or writer.boot != boot:
                self._writers[path] = _Writer(boot, health, now, agents=rows,
                                             active=value.get("lifecycle") == "active")
                # Old generation completion banners cannot survive a replacement.
                self._ends = {key: item for key, item in self._ends.items() if item[2] != path}
                return
            if health > writer.health:
                writer.health = health
                writer.changed_at = now
                writer.verified = True
                writer.agents = rows
                writer.active = value.get("lifecycle") == "active"
        except (OSError, ValueError, UnicodeError):
            return

    def _tail(self, path: Path, now: float) -> None:
        try:
            stat = path.stat()
            previous = self._tails.get(path)
            if previous is None:
                self._tails[path] = stat.st_ino, stat.st_size, b""
                return  # Match reference: no historical completion replay.
            inode, offset, pending = previous
            if inode != stat.st_ino or stat.st_size < offset:
                offset, pending = 0, b""
            with path.open("rb") as stream:
                stream.seek(offset)
                chunk = stream.read(1024 * 1024)
                offset = stream.tell()
            lines = (pending + chunk).split(b"\n")
            pending = lines.pop()
            self._tails[path] = stat.st_ino, offset, pending if len(pending) <= 65536 else b""
            snapshot = path.with_suffix(".snapshot.json")
            writer = self._writers.get(snapshot)
            for line in lines:
                if len(line) > 65536:
                    continue
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeError):
                    continue
                if not isinstance(row, dict) or row.get("schema") != 1 or row.get("event") != "turn/end":
                    continue
                if writer is None or row.get("boot_id") != writer.boot or not writer.verified:
                    continue
                # A child finishing is not the whole user request finishing.
                if row.get("agent_id") != row.get("root_id"):
                    continue
                revision = row.get("revision")
                if type(revision) is not int or revision <= self._last_end_revision.get(writer.boot, -1):
                    continue
                root, turn, outcome = row.get("root_id"), row.get("root_turn"), row.get("outcome")
                if not isinstance(root, str) or type(turn) is not int or outcome not in ("completed", "failed", "interrupted"):
                    continue
                self._last_end_revision[writer.boot] = revision
                self._ends[(writer.boot, root, turn)] = outcome, now + 8, snapshot
        except OSError:
            return


class TaskMonitor:
    """Own a daemon reader, publishing immutable summaries through a short lock."""

    def __init__(self, directory: Path | None = None) -> None:
        self._reader = BridgeReader(directory if directory is not None else bridge_directory())
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._summary = TaskSummary()
        self._thread = threading.Thread(target=self._run, name="sukuna-dsh-reader", daemon=True)
        self._thread.start()

    @property
    def summary(self) -> TaskSummary:
        with self._lock:
            return self._summary

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                summary = self._reader.poll(monotonic())
            except OSError:
                summary = TaskSummary()
            with self._lock:
                self._summary = summary
            self._stop.wait(.2)

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1)
