"""Validation of our versioned, identity-only observed-state wire format."""

from dataclasses import dataclass
import hashlib
import os
import math
from pathlib import Path
from typing import Any

OWNER = "@sukuna-pet/dsh-bridge"
RECORD_BYTES = 64 * 1024
SNAPSHOT_BYTES = 8 * 1024 * 1024
BUFFER_BYTES = 1024 * 1024
BUFFER_RECORDS = 1024
CAPABILITIES = {"observed-state", "snapshot-boundary", "contiguous-events", "independent-health"}


def path_id(path: Path) -> str:
    return hashlib.sha256(os.path.normcase(str(path.resolve())).encode()).hexdigest()


def integer(value: Any, minimum: int = 0) -> bool:
    return type(value) is int and minimum <= value <= 2**53 - 1


def identifier(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 256


@dataclass(frozen=True)
class Identity:
    user: str
    profile: str
    instance: str
    pid: int
    start: str
    boot: str
    loaded: int

    @property
    def order(self) -> tuple[float, int]:
        return float(self.start), self.loaded

    @classmethod
    def read(cls, value: dict[str, Any], pid: int, user: str) -> "Identity | None":
        if (type(value.get("schema_version")) is not int or value["schema_version"] != 1
                or value.get("owner") != OWNER or value.get("user_id") != user
                or not integer(value.get("pid"), 1) or value["pid"] != pid):
            return None
        fields = ("profile_id", "instance_id", "process_start_id", "boot_id", "host_version", "plugin_version")
        if not all(identifier(value.get(key)) for key in fields):
            return None
        try:
            start = float(value["process_start_id"])
        except ValueError:
            return None
        if not math.isfinite(start) or start <= 0 or not integer(value.get("boot_started_at"), 1):
            return None
        capabilities = value.get("capabilities")
        if (not isinstance(capabilities, list) or len(capabilities) > 32
                or not all(isinstance(item, str) for item in capabilities)
                or not CAPABILITIES.issubset(capabilities)):
            return None
        return cls(user, value["profile_id"], value["instance_id"], pid,
                   value["process_start_id"], value["boot_id"], value["boot_started_at"])


def state_row(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return (all(identifier(value.get(key)) for key in ("agent_id", "root_id"))
            and all(integer(value.get(key)) for key in ("root_turn", "turn_id"))
            and value.get("status") in ("idle", "running", "waiting")
            and type(value.get("known")) is bool)
