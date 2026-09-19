"""Copy worker inputs into a new workspace; never copy evaluator material."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


SOURCE = Path(__file__).resolve().parent


def prepare(destination, case_id, condition="baseline"):
    destination = Path(destination)
    if case_id not in {"case-%02d" % number for number in range(1, 7)}:
        raise ValueError("Select one of case-01 through case-06")
    if condition not in ("baseline", "evidence-index"):
        raise ValueError("Unknown condition")
    if destination.exists():
        raise ValueError("Use a new destination; existing work is never overwritten")
    worker = SOURCE / "worker"
    if any(path.is_symlink() for path in worker.rglob("*")):
        raise ValueError("Worker input must not contain symlinks")
    destination.mkdir(parents=True)
    for name in ("task.md", "spectral.py"):
        shutil.copy2(worker / name, destination / name)
    shutil.copytree(worker / case_id, destination / case_id)
    if condition == "evidence-index":
        shutil.copy2(SOURCE.parents[2] / "tools/claim_evidence.py", destination / "claim_evidence.py")
    manifest = {
        str(path.relative_to(destination)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(destination.rglob("*")) if path.is_file()
    }
    (destination / "input-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--condition", choices=("baseline", "evidence-index"), default="baseline")
    args = parser.parse_args()
    try:
        manifest = prepare(args.destination, args.case, args.condition)
    except (OSError, ValueError) as error:
        parser.exit(2, str(error) + "\n")
    print(json.dumps({"copied_files": len(manifest), "evaluation_run": False}))


if __name__ == "__main__":
    main()
