"""Credential lifecycle at the store and operating-system boundaries."""

import subprocess
import sys
from uuid import uuid4

import pytest

from sukuna_pet.credentials import CredentialStore, WindowsCredentialBackend


class CredentialVault:
    """External vault double, including service failures that contain sensitive text."""

    def __init__(self) -> None:
        self.value = ""
        self.fail_read = False
        self.fail_write = False
        self.fail_delete = False

    def read(self) -> str:
        if self.fail_read:
            raise OSError("private-vault-detail")
        return self.value

    def write(self, value: str) -> None:
        if self.fail_write:
            raise OSError(value)
        self.value = value

    def delete(self) -> None:
        if self.fail_delete:
            raise OSError(self.value)
        self.value = ""


def test_saved_key_survives_store_restart_and_blank_does_not_replace_it() -> None:
    vault = CredentialVault()
    store = CredentialStore(vault)
    store.save("unit-credential")
    store.save("  ")
    restored = CredentialStore(vault)
    assert restored.snapshot() == "unit-credential" and restored.safely_saved
    assert restored.clear()
    assert not restored.snapshot() and not restored.safely_saved
    assert not CredentialStore(vault).snapshot()


def test_backend_failures_keep_key_in_memory_without_claiming_safe_storage() -> None:
    vault = CredentialVault()
    vault.fail_read = vault.fail_write = True
    store = CredentialStore(vault)
    store.save("unit-runtime-only")
    assert store.snapshot() == "unit-runtime-only"
    assert not store.safely_saved and "重启" in store.notice
    assert "unit-runtime-only" not in store.notice + repr(store)
    assert "private-vault-detail" not in store.notice
    store.release()
    assert not store.snapshot() and not CredentialStore(vault).snapshot()


def test_failed_delete_never_restores_old_runtime_key_and_can_be_retried() -> None:
    vault = CredentialVault()
    store = CredentialStore(vault)
    store.save("unit-durable")
    vault.fail_delete = True
    assert not store.clear()
    assert not store.snapshot() and not store.safely_saved
    assert "删除失败" in store.notice and "unit-durable" not in store.notice
    # Explicitly report durable risk; this process does not lazily reload it.
    assert CredentialStore(vault).snapshot() == "unit-durable"
    assert not store.snapshot()
    vault.fail_delete = False
    assert store.clear() and not CredentialStore(vault).snapshot()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Credential Manager")
def test_windows_current_user_credential_roundtrip_in_another_process() -> None:
    target = f"skip-pet/tests/{uuid4()}"
    backend = WindowsCredentialBackend(target)
    try:
        assert not backend.read()
        backend.write("unit-os-credential")
        code = ("from sukuna_pet.credentials import WindowsCredentialBackend; "
                "import sys; "
                "assert WindowsCredentialBackend(sys.argv[1]).read() == 'unit-os-credential'")
        process = subprocess.run([sys.executable, "-c", code, target], capture_output=True)
        assert process.returncode == 0, "child process could not read isolated test credential"
        backend.delete()
        assert not WindowsCredentialBackend(target).read()
    finally:
        backend.delete()
