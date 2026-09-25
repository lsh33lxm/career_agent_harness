from __future__ import annotations

import ctypes
import platform
from ctypes import wintypes
from typing import Protocol

from career_harness.platform.secrets import SecretValue


class WritableSecretStore(Protocol):
    def get(self, name: str) -> SecretValue | None: ...
    def set(self, name: str, value: str) -> None: ...
    def delete(self, name: str) -> None: ...


class MemorySecretStore:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, name: str) -> SecretValue | None:
        value = self._values.get(name)
        return SecretValue(value) if value else None

    def set(self, name: str, value: str) -> None:
        if not value:
            raise ValueError("secret may not be empty")
        self._values[name] = value

    def delete(self, name: str) -> None:
        self._values.pop(name, None)


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialSecretStore:
    _TYPE_GENERIC = 1
    _PERSIST_LOCAL_MACHINE = 2
    _NOT_FOUND = 1168

    def __init__(self, prefix: str = "AgentCareerHarness") -> None:
        if platform.system() != "Windows":
            raise RuntimeError("Windows Credential Manager is only available on Windows")
        self._prefix = prefix
        self._advapi = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        self._advapi.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
        self._advapi.CredWriteW.restype = wintypes.BOOL
        self._advapi.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(_Credential)),
        ]
        self._advapi.CredReadW.restype = wintypes.BOOL
        self._advapi.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self._advapi.CredDeleteW.restype = wintypes.BOOL
        self._advapi.CredFree.argtypes = [ctypes.c_void_p]

    def _target(self, name: str) -> str:
        return f"{self._prefix}/{name}"

    def get(self, name: str) -> SecretValue | None:
        pointer = ctypes.POINTER(_Credential)()
        if not self._advapi.CredReadW(
            self._target(name), self._TYPE_GENERIC, 0, ctypes.byref(pointer)
        ):
            error = ctypes.get_last_error()
            if error == self._NOT_FOUND:
                return None
            raise OSError(error, "Windows Credential Manager read failed")
        try:
            credential = pointer.contents
            raw = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
            return SecretValue(raw.decode("utf-16-le"))
        finally:
            self._advapi.CredFree(pointer)

    def set(self, name: str, value: str) -> None:
        if not value:
            raise ValueError("secret may not be empty")
        raw = value.encode("utf-16-le")
        blob = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        credential = _Credential(
            Type=self._TYPE_GENERIC,
            TargetName=self._target(name),
            CredentialBlobSize=len(raw),
            CredentialBlob=ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte)),
            Persist=self._PERSIST_LOCAL_MACHINE,
            UserName="Agent Career Harness",
        )
        if not self._advapi.CredWriteW(ctypes.byref(credential), 0):
            error = ctypes.get_last_error()
            raise OSError(error, "Windows Credential Manager write failed")

    def delete(self, name: str) -> None:
        if self._advapi.CredDeleteW(self._target(name), self._TYPE_GENERIC, 0):
            return
        error = ctypes.get_last_error()
        if error != self._NOT_FOUND:
            raise OSError(error, "Windows Credential Manager delete failed")
