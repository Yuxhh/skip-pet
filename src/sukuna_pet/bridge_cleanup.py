"""Conservative retention: only explicitly retired, recognized local generations."""

import json
import os
from pathlib import Path

from .bridge_protocol import BUFFER_BYTES, Identity, RECORD_BYTES, SNAPSHOT_BYTES, read_envelope


def cleanup_retired(directory: Path, user: str, wall_time: float) -> None:
    """Budget sixteen retired candidates; active, unknown and linked files stay put.

    Explicit stopped health AND a matching stopped snapshot prove plugin-generation
    retirement. An absent PID alone cannot prove file ownership or a particular boot.
    """
    budget = 16
    for health_file in directory.glob("dsh-*.health.json"):
        try:
            if wall_time - health_file.stat().st_mtime <= 86400:
                continue
            budget -= 1
            if budget < 0:
                break
            prefix = health_file.with_suffix("").with_suffix("")
            pid_text = prefix.name.removeprefix("dsh-")
            if not pid_text.isdigit():
                continue
            health = read_envelope(health_file, RECORD_BYTES)
            identity = Identity.read(health, int(pid_text), user)
            if identity is None or health.get("lifecycle") != "stopped":
                continue
            snapshot_file = prefix.with_suffix(".snapshot.json")
            if wall_time - snapshot_file.stat().st_mtime <= 86400:
                continue
            snapshot = read_envelope(snapshot_file, SNAPSHOT_BYTES)
            if (Identity.read(snapshot, int(pid_text), user) != identity
                    or snapshot.get("lifecycle") != "stopped"):
                continue
            paths = [prefix.with_suffix(".jsonl"), prefix.with_suffix(".jsonl.1"),
                     snapshot_file, health_file]
            for path in paths:
                if path.is_symlink() or path.is_junction() or not path.is_file():
                    continue
                before = path.stat()
                if wall_time - before.st_mtime <= 86400:
                    continue
                if path.name.endswith((".jsonl", ".jsonl.1")):
                    if before.st_size > 2 * BUFFER_BYTES:
                        continue
                    with path.open("rb") as stream:
                        valid = True
                        while line := stream.readline(RECORD_BYTES + 1):
                            if len(line) > RECORD_BYTES or not line.endswith(b"\n"):
                                valid = False
                                break
                            value = json.loads(line)
                            if not isinstance(value, dict) or Identity.read(value, int(pid_text), user) != identity:
                                valid = False
                                break
                    if not valid:
                        continue
                # Recheck replacement/publication before deleting; never follow links.
                current = path.stat()
                if (before.st_ino, before.st_mtime_ns, before.st_size) == (
                        current.st_ino, current.st_mtime_ns, current.st_size):
                    os.unlink(path)
        except (OSError, ValueError, UnicodeError, RecursionError):
            continue
