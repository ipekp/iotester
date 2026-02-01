from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class DeviceSpec:
    """Simple description of a device for tests/examples."""
    kind: str                 # e.g. "zram", "loop"
    size: str | int           # e.g. "1G" or 1024*1024*1024
    path: Optional[str] = None  # optional filesystem path or mountpoint


class DeviceBackend(ABC):
    """Abstract device backend interface."""

    @abstractmethod
    def prepare(self, spec: DeviceSpec) -> Any:
        """
        Prepare/allocate the device and return a handle (opaque).
        Should raise on failure.
        """
        raise NotImplementedError

    @abstractmethod
    def teardown(self, device_handle: Any) -> None:
        """Cleanup the device previously returned from prepare()."""
        raise NotImplementedError


class ZramBackend(DeviceBackend):
    """Example backend: pretend to create a zram device."""

    def prepare(self, spec: DeviceSpec) -> dict:
        # In real code you'd create the zram device, format, mount, etc.
        # Return a simple handle (dict) for tests.
        handle = {"kind": "zram", "size": spec.size, "mount": f"/mnt/zram-{id(spec)}"}
        # Logically: system calls would run here
        return handle

    def teardown(self, device_handle: dict) -> None:
        # In real code: unmount and reset zram device.
        device_handle.clear()


class LoopbackBackend(DeviceBackend):
    """Example backend: create a file-backed loop device (fake)."""

    def prepare(self, spec: DeviceSpec) -> dict:
        handle = {"kind": "loop", "path": spec.path or f"/tmp/loop-{id(spec)}"}
        return handle

    def teardown(self, device_handle: dict) -> None:
        device_handle.clear()


def device_backend_for(spec_or_kind: DeviceSpec | str) -> DeviceBackend:
    """
    Return an instantiated DeviceBackend for the provided DeviceSpec or kind string.

    Accepts either a DeviceSpec instance or a simple string like "zram" / "loop".
    """
    kind = spec_or_kind.kind if isinstance(spec_or_kind, DeviceSpec) else spec_or_kind
    kind = (kind or "").lower()

    if kind == "zram":
        return ZramBackend()
    if kind in ("loop", "loopback"):
        return LoopbackBackend()

    raise ValueError(f"unknown device backend kind: {kind}")
