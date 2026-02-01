from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, TextIO
import json, csv, sys, logging

log = logging.getLogger(__name__)

@dataclass
class OutputResult:
    job: Mapping[str, Any]
    result: Mapping[str, Any] | None
    raw_stdout: str
    raw_stderr: str

class OutputBackend(ABC):
    @abstractmethod
    def write(self, out: OutputResult) -> None: ...
    def close(self) -> None: return

# Concrete simple backends (same as before, minimal)
class StdoutBackend(OutputBackend):
    def __init__(self, stream: Optional[TextIO] = None):
        self.stream = stream or sys.stdout
    def write(self, out: OutputResult) -> None:
        name = out.job.get("name", out.job.get("filename", "<job>"))
        self.stream.write(f"Job: {name}\n")
        self.stream.write(out.raw_stdout or "")
        if out.raw_stderr:
            self.stream.write("\nstderr:\n")
            self.stream.write(out.raw_stderr)
        self.stream.write("\n---\n")
        self.stream.flush()

class JsonBackend(OutputBackend):
    def __init__(self, stream: Optional[TextIO] = None, compact: bool = False):
        self.stream = stream or sys.stdout
        self.compact = compact
    def write(self, out: OutputResult) -> None:
        payload = out.result or {}
        if not payload:
            try:
                payload = json.loads(out.raw_stdout) if out.raw_stdout else {}
            except Exception:
                payload = {"raw_stdout": out.raw_stdout}
        if self.compact:
            self.stream.write(json.dumps(payload, separators=(",", ":")) + "\n")
        else:
            self.stream.write(json.dumps(payload, indent=2) + "\n")
        self.stream.flush()

class CsvBackend(OutputBackend):
    def __init__(self, stream: Optional[TextIO] = None, fieldnames: Optional[Sequence[str]] = None):
        self.stream = stream or sys.stdout
        self.fieldnames = list(fieldnames or ["job", "read_iops", "write_iops", "read_bw", "write_bw"])
        self.writer = csv.DictWriter(self.stream, fieldnames=self.fieldnames)
        self.writer.writeheader()
    def _extract(self, out: OutputResult) -> dict:
        data = {"job": out.job.get("name") or out.job.get("filename") or ""}
        res = out.result or {}
        if not res:
            try:
                res = json.loads(out.raw_stdout) if out.raw_stdout else {}
            except Exception:
                res = {}
        jobs = res.get("jobs") if isinstance(res, dict) else []
        if jobs:
            j0 = jobs[0]
            read = j0.get("read", {})
            write = j0.get("write", {})
            data["read_iops"] = read.get("iops")
            data["write_iops"] = write.get("iops")
            data["read_bw"] = read.get("bw")
            data["write_bw"] = write.get("bw")
        for k in self.fieldnames:
            data.setdefault(k, "")
        return data
    def write(self, out: OutputResult) -> None:
        self.writer.writerow(self._extract(out))
        self.stream.flush()

# Composite backend: forwards write() to multiple backends
class CompositeBackend(OutputBackend):
    def __init__(self, backends: Sequence[OutputBackend]):
        self.backends = list(backends)
    def write(self, out: OutputResult) -> None:
        for b in self.backends:
            try:
                b.write(out)
            except Exception:
                log.exception("output backend %s failed", type(b).__name__)
    def close(self) -> None:
        for b in self.backends:
            try:
                b.close()
            except Exception:
                log.exception("closing backend %s failed", type(b).__name__)

# Factory that builds one or more backends based on args
def get_output_backend(args: Any) -> OutputBackend:
    """
    args.output may be a single string or comma-separated types like "stdout,json,csv".
    args.output_file, args.json_file, args.csv_file can override individual paths.
    """
    typ = getattr(args, "output", "stdout")
    types = [t.strip() for t in (typ.split(",") if isinstance(typ, str) else [typ])]

    backends: list[OutputBackend] = []

    for t in types:
        if t in ("stdout", "plain"):
            stream = None
            out_path = getattr(args, "stdout_file", None)
            if out_path:
                stream = open(out_path, "w")
            backends.append(StdoutBackend(stream))
        elif t == "json":
            stream = None
            out_path = getattr(args, "json_file", None) or getattr(args, "output_file", None)
            if out_path:
                stream = open(out_path, "w")
            compact = bool(getattr(args, "compact_json", False))
            backends.append(JsonBackend(stream, compact=compact))
        elif t == "csv":
            stream = None
            out_path = getattr(args, "csv_file", None)
            if out_path:
                stream = open(out_path, "w", newline="")
            fields = getattr(args, "csv_fields", None)
            backends.append(CsvBackend(stream, fieldnames=fields))
        else:
            log.warning("unknown output type %s, skipping", t)

    if not backends:
        log.warning("no valid output backends selected, defaulting to stdout")
        backends = [StdoutBackend()]
    if len(backends) == 1:
        return backends[0]
    return CompositeBackend(backends)
