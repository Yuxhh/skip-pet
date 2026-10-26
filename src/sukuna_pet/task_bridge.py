"""Observed DSH file state, read off the animation thread.

File discovery, byte cursors and startup EOF follow dsh-pet's DshMonitor /
ByteOffsetTailer (34d810b1, MIT). Snapshots and explicit health are additions.
Coverage remains 'observed': they do not assert authoritative host wait recovery.
"""

from dataclasses import dataclass, field
from heapq import nlargest
import json
import os
from pathlib import Path
import threading
from time import monotonic, time
from typing import Any, Iterator


from .bridge_cleanup import cleanup_retired
from .bridge_protocol import (Identity, RECORD_BYTES, SNAPSHOT_BYTES, BUFFER_BYTES,
                              BUFFER_RECORDS, integer, path_id, state_row)


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
    identity: Identity
    health: int
    changed_at: float
    verified: bool = False
    active: bool = True
    trusted: bool = False
    revision: int = -1
    snapshot_seq: int = -1
    rejected_snapshot: tuple[int, int] | None = None
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    turns: dict[str, int] = field(default_factory=dict)
    ended: set[tuple[str, int]] = field(default_factory=set)
    grace_until: float = 0
    disconnected: bool = False
    closed: bool = False
    last_snapshot: tuple[int, int] | None = None
    gap_seen: int = 0
    required_revision: int = 0


@dataclass
class _Tail:
    inode: int
    offset: int
    pending: bytes = b""
    anchor: bytes = b""


class BridgeReader:
    """Consume bounded files off the GUI thread; unknown state never drives motion."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._user = path_id(Path.home())
        self._cleanup_at = float("-inf")
        self._writers: dict[Path, _Writer] = {}
        self._tails: dict[Path, _Tail] = {}
        self._retired: dict[Path, set[Identity]] = {}
        self._ends: dict[tuple[Identity, str, int], tuple[str, float, Path]] = {}

    def poll(self, now: float) -> TaskSummary:
        if now >= self._cleanup_at:
            cleanup_retired(self.directory, self._user, time())
            self._cleanup_at = now + 60
        # Like the reference, prioritize recent writers and cap retained cursors.
        candidates = nlargest(128, self._candidates())
        recent: dict[Path, int] = {}
        for stamp, prefix in candidates:
            recent[prefix] = max(recent.get(prefix, 0), stamp)
        prefixes = set(sorted(recent, key=lambda prefix: recent[prefix], reverse=True)[:64])
        self._writers = {key: value for key, value in self._writers.items() if key in prefixes}
        self._tails = {key: value for key, value in self._tails.items() if key in prefixes}
        self._retired = {key: value for key, value in self._retired.items() if key in prefixes}
        self._ends = {key: value for key, value in self._ends.items() if value[2] in prefixes}
        for prefix in sorted(prefixes):
            if not prefix.name.removeprefix("dsh-").isdigit():
                continue
            self._cursor(prefix)
            previous = self._writers.get(prefix)
            if previous is not None and now - previous.changed_at >= 3:
                self._disconnect(prefix, previous, now)
            self._health(prefix, now)
            writer = self._writers.get(prefix)
            if writer is None:
                continue
            if now - writer.changed_at >= 3 or not writer.active:
                self._disconnect(prefix, writer, now)
            self._tail(prefix, writer, now)
            self._snapshot(prefix, writer)
        return self._summary(now)

    def _candidates(self) -> Iterator[tuple[int, Path]]:
        for pattern in ("dsh-*.health.json", "dsh-*.snapshot.json"):
            for path in self.directory.glob(pattern):
                try:
                    if not path.is_symlink() and not path.is_junction():
                        yield path.stat().st_mtime_ns, path.with_suffix("").with_suffix("")
                except OSError:
                    continue

    def _cursor(self, prefix: Path) -> None:
        if prefix in self._tails:
            return
        try:
            log = prefix.with_suffix(".jsonl")
            if log.is_symlink() or log.is_junction():
                raise OSError("linked log")
            with log.open("rb") as stream:
                stat = os.fstat(stream.fileno())
                stream.seek(max(0, stat.st_size - 64))
                self._tails[prefix] = _Tail(stat.st_ino, stat.st_size, anchor=stream.read(64))
        except OSError:
            self._tails[prefix] = _Tail(0, 0)

    def _read(self, path: Path, limit: int) -> dict[str, Any]:
        if path.is_symlink() or path.is_junction():
            raise OSError("linked bridge file")
        with path.open("rb") as stream:
            value = stream.read(limit + 1)
        if len(value) > limit:
            raise ValueError("capacity")
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("object required")
        return parsed

    def _identity(self, value: dict[str, Any], prefix: Path) -> Identity | None:
        return Identity.read(value, int(prefix.name.removeprefix("dsh-")), self._user)

    def _health(self, prefix: Path, now: float) -> None:
        try:
            value = self._read(prefix.with_suffix(".health.json"), RECORD_BYTES)
            identity = self._identity(value, prefix)
            if identity is None or not integer(value.get("health_seq"), 1):
                if prefix in self._writers:
                    self._invalidate(prefix, self._writers[prefix])
                return
            if value.get("lifecycle") not in ("active", "stopped"):
                return
            writer = self._writers.get(prefix)
            if identity in self._retired.get(prefix, set()):
                return
            if writer is not None and identity != writer.identity and identity.order <= writer.identity.order:
                return
            if writer is None or writer.identity != identity:
                if len(self._retired.get(prefix, set())) >= 128:
                    if writer is not None:
                        self._invalidate(prefix, writer)
                    return
                if writer is not None:
                    self._retired.setdefault(prefix, set()).add(writer.identity)
                    self._clear_ends(prefix)
                self._writers[prefix] = _Writer(identity, value["health_seq"], now,
                                                active=value["lifecycle"] == "active")
                return
            if writer.closed:
                return
            if value["lifecycle"] == "stopped":
                writer.active = False
                writer.closed = True
            if value["health_seq"] > writer.health:
                writer.health = value["health_seq"]
                writer.changed_at = now
                writer.verified = True
                writer.active = value["lifecycle"] == "active"
                gap = value.get("gap_revision", 0)
                if not integer(gap):
                    self._invalidate(prefix, writer)
                elif gap > writer.gap_seen:
                    writer.gap_seen = gap
                    writer.required_revision = max(writer.required_revision, gap)
                    if gap > writer.revision:
                        self._invalidate(prefix, writer)
                if writer.active:
                    writer.disconnected = False
        except (OSError, ValueError, UnicodeError, RecursionError):
            return

    def _invalidate(self, prefix: Path, writer: _Writer) -> None:
        writer.trusted = False
        writer.grace_until = 0
        self._clear_ends(prefix)
        try:
            stat = prefix.with_suffix(".snapshot.json").stat()
            writer.rejected_snapshot = stat.st_mtime_ns, stat.st_size
        except OSError:
            writer.rejected_snapshot = None

    def _clear_ends(self, prefix: Path) -> None:
        self._ends = {key: item for key, item in self._ends.items() if item[2] != prefix}

    def _disconnect(self, prefix: Path, writer: _Writer, now: float) -> None:
        if writer.disconnected:
            return
        writer.disconnected = True
        running = writer.trusted and any(
            row["known"] and row["status"] == "running" and row["root_turn"] > 0
            and row["root_turn"] == writer.turns.get(row["root_id"])
            and (row["root_id"], row["root_turn"]) not in writer.ended
            for row in writer.agents.values())
        confirmed = writer.changed_at + 3 if writer.active else now
        writer.grace_until = confirmed + 5 if running else 0
        writer.trusted = False
        writer.verified = False
        try:
            stat = prefix.with_suffix(".snapshot.json").stat()
            writer.rejected_snapshot = stat.st_mtime_ns, stat.st_size
        except OSError:
            pass
        self._clear_ends(prefix)

    def _snapshot(self, prefix: Path, writer: _Writer) -> None:
        if not writer.verified or writer.disconnected or not writer.active:
            return
        path = prefix.with_suffix(".snapshot.json")
        try:
            stat = path.stat()
            token = stat.st_mtime_ns, stat.st_size
            if writer.trusted and token == writer.last_snapshot:
                return
            value = self._read(path, SNAPSHOT_BYTES)
            identity = self._identity(value, prefix)
            if identity in self._retired.get(prefix, set()):
                return
            if identity is not None and identity != writer.identity and identity.order <= writer.identity.order:
                return
            if (identity != writer.identity
                    or value.get("coverage") != "observed" or value.get("scope") != "tracked-agents"
                    or value.get("lifecycle") != "active"
                    or not integer(value.get("revision")) or not integer(value.get("snapshot_seq"), 1)
                    or not integer(value.get("health_seq"), 1)):
                raise ValueError("untrusted snapshot")
            rows = value.get("agents")
            if (not isinstance(rows, list) or len(rows) > 4096 or not all(state_row(row) for row in rows)
                    or len({row["agent_id"] for row in rows}) != len(rows)):
                raise ValueError("untrusted coverage")
            revision, sequence = value["revision"], value["snapshot_seq"]
            if revision < max(writer.revision, writer.required_revision) or sequence < writer.snapshot_seq:
                return
            if writer.trusted and revision == writer.revision:
                writer.last_snapshot = token
                writer.snapshot_seq = sequence
                return
            if writer.rejected_snapshot == token:
                return
            # Snapshot rebasing never replays buffered or historical end banners.
            if any(row["root_turn"] < writer.turns.get(row["root_id"], 0)
                   or ((row["root_id"], row["root_turn"]) in writer.ended and row["status"] != "idle")
                   for row in rows):
                raise ValueError("snapshot regresses a completed/newer turn")
            writer.agents = {row["agent_id"]: row for row in rows}
            writer.turns = {}
            for row in rows:
                root = row["root_id"]
                writer.turns[root] = max(writer.turns.get(root, 0), row["root_turn"])
            writer.ended = {(root, turn) for root, turn in writer.ended if writer.turns.get(root) == turn}
            writer.last_snapshot = token
            writer.revision, writer.snapshot_seq = revision, sequence
            writer.trusted = True
            writer.grace_until = 0
            writer.rejected_snapshot = None
        except (OSError, ValueError, UnicodeError, RecursionError):
            self._invalidate(prefix, writer)

    def _tail(self, prefix: Path, writer: _Writer, now: float) -> None:
        tail = self._tails[prefix]
        try:
            path = prefix.with_suffix(".jsonl")
            if path.is_symlink() or path.is_junction():
                raise OSError("linked log")
            with path.open("rb") as stream:
                stat = os.fstat(stream.fileno())
                stream.seek(max(0, tail.offset - len(tail.anchor)))
                rewritten = bool(tail.anchor and stream.read(len(tail.anchor)) != tail.anchor)
                if tail.inode != stat.st_ino or stat.st_size < tail.offset or rewritten:
                    if tail.inode:
                        self._invalidate(prefix, writer)
                    tail.inode, tail.offset, tail.pending = stat.st_ino, 0, b""
                stream.seek(tail.offset)
                chunk = stream.read(BUFFER_BYTES + 1)
                tail.offset = stream.tell()
                stream.seek(max(0, tail.offset - 64))
                tail.anchor = stream.read(min(64, tail.offset))
            if len(chunk) + len(tail.pending) > BUFFER_BYTES:
                tail.offset, tail.pending = stat.st_size, b""
                self._invalidate(prefix, writer)
                return
            lines = (tail.pending + chunk).split(b"\n")
            tail.pending = lines.pop()
            if (tail.pending and chunk) or len(lines) > BUFFER_RECORDS:
                self._invalidate(prefix, writer)
            if len(tail.pending) > RECORD_BYTES:
                tail.offset, tail.pending = stat.st_size, b""
            if len(lines) > BUFFER_RECORDS:
                return
            for line in lines:
                if not line:
                    continue
                if len(line) + 1 > RECORD_BYTES:
                    self._invalidate(prefix, writer)
                    continue
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError("object required")
                    identity = self._identity(row, prefix)
                    if identity != writer.identity:
                        if identity is not None and identity.order <= writer.identity.order:
                            continue
                        if identity not in self._retired.get(prefix, set()):
                            self._invalidate(prefix, writer)
                        continue
                    if "revision" not in row:
                        raise ValueError("revision required")
                    revision = row["revision"]
                    if not integer(revision, 1):
                        raise ValueError("revision required")
                    if revision <= writer.revision:
                        continue
                    if revision != writer.revision + 1:
                        writer.required_revision = max(writer.required_revision, revision)
                        self._invalidate(prefix, writer)
                        continue
                    if writer.trusted and not writer.disconnected:
                        self._apply(prefix, writer, row, now)
                        writer.revision = revision
                except (ValueError, UnicodeError, RecursionError):
                    self._invalidate(prefix, writer)
        except OSError:
            self._invalidate(prefix, writer)

    def _apply(self, prefix: Path, writer: _Writer, row: dict[str, Any], now: float) -> None:
        event = row.get("event")
        if event in ("bridge/started", "bridge/stopped"):
            if event == "bridge/stopped":
                writer.active = False
                self._disconnect(prefix, writer, now)
            return
        if event not in ("agent/state", "agent/removed", "turn/end", "approval/asked", "approval/decided") or not state_row(row):
            raise ValueError("unrecognized state")
        root, turn = row["root_id"], row["root_turn"]
        current = writer.turns.get(root, -1)
        if turn < current or (root, turn) in writer.ended:
            return
        if turn > current:
            writer.agents = {key: item for key, item in writer.agents.items() if item["root_id"] != root}
            writer.turns[root] = turn
            writer.ended = {key for key in writer.ended if key[0] != root}
        previous = writer.agents.get(row["agent_id"])
        if previous and row["turn_id"] < previous["turn_id"]:
            return
        if event == "agent/removed":
            writer.agents.pop(row["agent_id"], None)
        else:
            writer.agents[row["agent_id"]] = row
        if event == "turn/end" and row["agent_id"] == root:
            writer.ended.add((root, turn))
            writer.agents = {key: item for key, item in writer.agents.items() if item["root_id"] != root}
            outcome = row.get("outcome")
            emitted = row.get("emitted_at")
            age = time() - float(emitted) if isinstance(emitted, (int, float)) and not isinstance(emitted, bool) else float("inf")
            if outcome in ("completed", "failed", "interrupted") and -1 <= age < 8:
                self._ends[(writer.identity, root, turn)] = outcome, now + 8 - max(0, age), prefix
        if len(writer.agents) > 4096 or len(writer.turns) > 4096 or len(self._ends) > 4096:
            raise ValueError("state capacity")

    def _summary(self, now: float) -> TaskSummary:
        groups: dict[tuple[Identity, str, int], list[str]] = {}
        partial = False
        jump = False
        healthy: set[Path] = set()
        for prefix, writer in self._writers.items():
            jump |= now < writer.grace_until
            if not writer.trusted or writer.disconnected:
                partial |= not writer.closed
                continue
            healthy.add(prefix)
            for row in writer.agents.values():
                if row["known"] and row["status"] == "idle":
                    continue
                identity = writer.identity, row["root_id"], row["root_turn"]
                if row["root_turn"] != writer.turns.get(row["root_id"]):
                    continue
                if not row["known"] or row["root_turn"] <= 0:
                    partial = True
                    if row["status"] in ("running", "waiting"):
                        groups.setdefault(identity, []).append("unknown")
                elif row["status"] in ("running", "waiting"):
                    groups.setdefault(identity, []).append(row["status"])
        running = sum("running" in states for states in groups.values())
        waiting = sum("running" not in states and "unknown" not in states and "waiting" in states
                      for states in groups.values())
        for key, (_, until, prefix) in list(self._ends.items()):
            if now >= until or prefix not in healthy:
                del self._ends[key]
        outcomes = [value[0] for key, value in self._ends.items() if key not in groups]
        return TaskSummary(running, waiting, partial, jump or running > 0,
                           outcomes.count("completed"), outcomes.count("failed"), outcomes.count("interrupted"))


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
