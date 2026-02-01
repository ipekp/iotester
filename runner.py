from __future__ import annotations
import subprocess
import logging
from dataclasses import dataclass
from typing import Iterable, Mapping, Any, Callable, Tuple

log = logging.getLogger(__name__)

@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    meta: Mapping[str, Any] | None = None

# Type of command runner: accepts list[str] (cmd) and optional kwargs, returns (rc, stdout, stderr)
CmdRunner = Callable[[Iterable[str]], Tuple[int, str, str]]

def default_cmd_runner(cmd: Iterable[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(list(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr

class Runner:
    """
    Responsible for executing a job against a prepared device.
    Designed for injection of cmd_runner for testability.
    """

    def __init__(self, cmd_runner: CmdRunner | None = None):
        self.cmd_runner = cmd_runner or default_cmd_runner

    def _build_command(self, job: Mapping[str, Any], device: object) -> list[str]:
        """
        Construct the command to run for a job.
        Reasonable defaults are assumed: job contains "cmd" (list/str) or is built from job fields.
        """
        if "cmd" in job:
            cmd = job["cmd"]
            if isinstance(cmd, str):
                return [cmd]
            return list(cmd)
        # Example default: call an external tool with filename and size
        return [
            "iotest-tool",
            "--file", job.get("filename", "/tmp/testfile"),
            "--size", str(job.get("filesize", "1G")),
            "--device", getattr(device, "path", str(device) if device is not None else ""),
        ]

    def run(self, job: Mapping[str, Any], device: object | None = None) -> RunResult:
        """
        Execute the job; return RunResult. Exceptions from cmd_runner are caught and surfaced as non-zero result.
        """
        cmd = self._build_command(job, device)
        log.info("running job %s with cmd: %s", job.get("name", "<unnamed>"), cmd)
        try:
            rc, out, err = self.cmd_runner(cmd)
        except Exception as exc:
            log.exception("command runner raised")
            return RunResult(returncode=255, stdout="", stderr=str(exc))
        meta = {"cmd": cmd, "job": job.get("name")}
        return RunResult(returncode=rc, stdout=out, stderr=err, meta=meta)
