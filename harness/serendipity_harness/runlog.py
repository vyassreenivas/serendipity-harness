"""Run folders and the append-only run log.

Every stage writes its outputs into one run folder and appends one line per
event to log.jsonl. Nothing in a run folder is overwritten by a later run.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tomllib

from . import __version__

HARNESS = Path(__file__).resolve().parents[1]
ROOT = HARNESS.parent


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def machine() -> dict:
    """The computer a run was made on: model, chip and memory. No names or serial numbers."""
    info = {"system": platform.system(), "machine": platform.machine()}
    if platform.system() == "Darwin":
        def sysctl(key):
            out = subprocess.run(["sysctl", "-n", key], capture_output=True, text=True)
            return out.stdout.strip()
        info.update(model=sysctl("hw.model"), chip=sysctl("machdep.cpu.brand_string"),
                    memory_gb=round(int(sysctl("hw.memsize") or 0) / 2**30))
    return info


def load_config(path: Path | None = None) -> dict:
    with open(path or HARNESS / "project.toml", "rb") as f:
        return tomllib.load(f)


class Run:
    def __init__(self, run_dir: Path):
        self.dir = run_dir
        self.log_path = run_dir / "log.jsonl"

    @classmethod
    def create(cls, config_path: Path | None = None) -> "Run":
        config_path = config_path or HARNESS / "project.toml"
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = HARNESS / "runs" / run_id
        run_dir.mkdir(parents=True)
        shutil.copy(config_path, run_dir / "project.toml")
        run = cls(run_dir)
        run.log("run_created", harness_version=__version__,
                python=sys.version.split()[0], platform=platform.platform(), computer=machine(),
                config_sha256=sha256(config_path),
                question_files={p.name: sha256(p) for p in sorted((HARNESS / "question").glob("*"))
                                if p.is_file()})
        return run

    def config(self) -> dict:
        return load_config(self.dir / "project.toml")

    def log(self, event: str, **fields) -> None:
        record = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "event": event, **fields}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def write_json(self, name: str, data) -> Path:
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return path

    def read_json(self, name: str):
        return json.loads((self.dir / name).read_text(encoding="utf-8"))
