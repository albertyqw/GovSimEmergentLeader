"""B8/B13 enumerate immutable attempts and checksum every raw file."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def build(root):
    root = Path(root)
    runs = []
    for file in sorted(root.rglob("run_meta.json")):
        metadata = json.loads(file.read_text())
        files = [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": digest(path)}
                 for path in sorted(file.parent.rglob("*")) if path.is_file()]
        runs.append({"condition": metadata["condition"], "seed": metadata["seed"],
                     "status": metadata["status"], "run_kind": metadata.get("run_kind"),
                     "commit_hash": metadata["commit_hash"], "directory": str(file.parent.relative_to(root)),
                     "files": files})
    return {"raw_root": str(root), "runs": runs}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--output", default="manifest.json")
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(build(args.root), indent=2) + "\n")


if __name__ == "__main__":
    main()
