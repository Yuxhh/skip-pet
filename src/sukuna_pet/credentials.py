"""Current-user Windows credentials, isolated from preferences and dsh-pet."""

import ctypes
from ctypes import wintypes
import sys
from typing import Protocol


CREDENTIAL_TARGET = "skip-pet/sukuna-pet/deepseek-api-key"


class CredentialBackend(Protocol):
    def read(self) -> str: ...
    def write(self, value: str) -> None: ...
    def delete(self) -> None: ...


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialBackend:
    """Generic credentials belong to the logged-in user; no plaintext fallback."""

    def __init__(self, target: str = CREDENTIAL_TARGET) -> None:
        if sys.platform != "win32":
            raise OSError("Windows credential storage unavailable")
        self._api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        self._target = target
        self._api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                                       wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(_Credential))]
        self._api.CredReadW.restype = wintypes.BOOL
        self._api.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
        self._api.CredWriteW.restype = wintypes.BOOL
        self._api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self._api.CredDeleteW.restype = wintypes.BOOL
        self._api.CredFree.argtypes = [ctypes.c_void_p]
        self._api.CredFree.restype = None

    def read(self) -> str:
        pointer = ctypes.POINTER(_Credential)()
        if not self._api.CredReadW(self._target, 1, 0, ctypes.byref(pointer)):
            if ctypes.get_last_error() == 1168:  # ERROR_NOT_FOUND
                return ""
            raise OSError("Credential read failed")
        try:
            value = pointer.contents
            return ctypes.string_at(value.CredentialBlob, value.CredentialBlobSize).decode("utf-16-le")
        finally:
            self._api.CredFree(pointer)

    def write(self, value: str) -> None:
        encoded = value.encode("utf-16-le")
        if len(encoded) > 2560:
            raise OSError("Credential exceeds Windows storage limit")
        blob = (ctypes.c_ubyte * len(encoded)).from_buffer_copy(encoded)
        credential = _Credential()
        credential.Type = 1  # CRED_TYPE_GENERIC
        credential.TargetName = self._target
        credential.UserName = "deepseek"
        credential.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE, still scoped to current user
        credential.CredentialBlobSize = len(encoded)
        credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
        try:
            if not self._api.CredWriteW(ctypes.byref(credential), 0):
                raise OSError("Credential write failed")
        finally:
            ctypes.memset(blob, 0, len(encoded))

    def delete(self) -> None:
        if not self._api.CredDeleteW(self._target, 1, 0):
            if ctypes.get_last_error() != 1168:
                raise OSError("Credential deletion failed")


class CredentialStore:
    """Load once, then keep the current request credential in process memory.

    After a failed deletion never reread the durable value in this process.
    Callers receive fixed messages, never exception strings or key fragments.
    """

    def __init__(self, backend: CredentialBackend | None = None) -> None:
        self._backend: CredentialBackend | None = backend
        self._value = ""
        self.safely_saved = False
        self.notice = ""
        try:
            if self._backend is None:
                self._backend = WindowsCredentialBackend()
            self._value = self._backend.read()
            self.safely_saved = bool(self._value)
        except Exception:
            self.notice = "安全凭据存储不可用；Key 仅用于本次运行，重启需重新输入。"

    def snapshot(self) -> str:
        return self._value

    def save(self, draft: str) -> None:
        value = draft.strip()
        if not value:
            return
        self._value = value
        self.safely_saved = False
        try:
            if self._backend is None:
                raise OSError("Credential backend unavailable")
            self._backend.write(value)
            self.safely_saved = True
            self.notice = ""
        except Exception:
            self.notice = "未能安全保存；Key 仅用于本次运行，重启需重新输入。"

    def clear(self) -> bool:
        self._value = ""
        self.safely_saved = False
        try:
            if self._backend is None:
                raise OSError("Credential backend unavailable")
            self._backend.delete()
        except Exception:
            self.notice = "运行内存与草稿已清空，但安全存储删除失败；重启可能读到旧 Key，请重试清除。"
            return False
        self.notice = "已清除本机 Key；这不会在 DeepSeek 撤销 Key。"
        return True

    def release(self) -> None:
        """Drop the process credential on application shutdown, retaining storage."""
        self._value = ""
