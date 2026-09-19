"""Read-only, opt-in claim/evidence navigation; not a scientific validator."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


class EvidenceIndexError(ValueError):
    """An invalid index, unsafe reference, or ambiguous dependency graph."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceIndexError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def _invalid_number(value):
    raise EvidenceIndexError("Non-finite JSON value: " + value)


def read_json(text):
    return json.loads(text, object_pairs_hook=_unique_object,
                      parse_constant=_invalid_number)


def _keys(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional):
        raise EvidenceIndexError("Expected an object with only declared fields")
    if set(required) - set(value):
        raise EvidenceIndexError("Missing required fields: " + ", ".join(sorted(set(required) - set(value))))


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise EvidenceIndexError("Identifiers must be nonempty ASCII names")
    return value


def _records(records):
    if not isinstance(records, list):
        raise EvidenceIndexError("Records must be arrays")
    result = {}
    for record in records:
        if not isinstance(record, dict):
            raise EvidenceIndexError("Records must be objects")
        identifier = _identifier(record.get("id"))
        if identifier in result:
            raise EvidenceIndexError("Duplicate identifier: " + identifier)
        result[identifier] = record
    return result


def _safe_path(root, name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise EvidenceIndexError("Resource paths must be relative POSIX file paths")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in name.split("/")):
        raise EvidenceIndexError("Unsafe resource path")
    target = root
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise EvidenceIndexError("Symbolic resource paths are not allowed")
    return target


def _locator(value):
    if not isinstance(value, dict) or len(value) != 1:
        raise EvidenceIndexError("A locator needs exactly one of lines or pointer")
    if "lines" in value:
        rows = value["lines"]
        if (not isinstance(rows, list) or len(rows) != 2
                or any(type(n) is not int for n in rows)
                or not 1 <= rows[0] <= rows[1]):
            raise EvidenceIndexError("Line locators are inclusive positive integer pairs")
    elif "pointer" in value:
        pointer = value["pointer"]
        if (not isinstance(pointer, str) or (pointer and not pointer.startswith("/"))
                or re.search(r"~(?![01])", pointer)):
            raise EvidenceIndexError("Invalid JSON pointer")
    else:
        raise EvidenceIndexError("Unknown locator type")


def _excerpt(content, locator):
    text = content.decode("utf-8")
    if "lines" in locator:
        start, end = locator["lines"]
        rows = text.splitlines()
        if end > len(rows):
            raise EvidenceIndexError("Line locator is outside the source")
        return "\n".join(rows[start - 1:end])
    value = read_json(text)
    pointer = locator["pointer"]
    for part in pointer.split("/")[1:] if pointer else ():
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", part):
                raise EvidenceIndexError("Invalid JSON array index")
            number = int(part)
            if number >= len(value):
                raise EvidenceIndexError("JSON array index is outside the source")
            value = value[number]
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise EvidenceIndexError("JSON pointer is absent from the source")
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)


def inspect_resource(record, root):
    _keys(record, ("id", "path", "sha256", "locator"))
    digest = record["sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise EvidenceIndexError("Every resource needs a pinned SHA-256 digest")
    _locator(record["locator"])
    target = _safe_path(root, record["path"])
    result = dict(record, actual_sha256=None, status="missing", excerpt=None)
    try:
        content = target.read_bytes()
    except FileNotFoundError:
        return result
    except OSError:
        result["status"] = "unreadable"
        return result
    result["actual_sha256"] = hashlib.sha256(content).hexdigest()
    if result["actual_sha256"] != digest:
        result["status"] = "changed"
        return result  # Do not combine changed text with an old review snapshot.
    try:
        result["excerpt"] = _excerpt(content, record["locator"])
        result["status"] = "fresh"
    except (ValueError, UnicodeError, RecursionError):
        result["status"] = "invalid_locator_or_content"
    return result


def inspect_index(index, root):
    """Read exact pinned excerpts and propagate attention through declared edges."""
    _keys(index, ("schema_version", "disclosure", "resources", "claims"))
    if index["schema_version"] != "0.1" or index["disclosure"] not in ("public", "private"):
        raise EvidenceIndexError("Unsupported index version or disclosure class")
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise EvidenceIndexError("The resource root must be a directory")
    resources = _records(index["resources"])
    claims = _records(index["claims"])
    if not claims:
        raise EvidenceIndexError("An index must declare at least one claim")
    observations = {key: inspect_resource(value, root) for key, value in resources.items()}
    lists = ("assumptions", "supports", "contradicts", "open_checks", "depends_on")
    for claim in claims.values():
        _keys(claim, ("id", "record", "review") + lists)
        _identifier(claim["record"])
        _identifier(claim["review"])
        for name in lists:
            values = claim[name]
            if not isinstance(values, list):
                raise EvidenceIndexError("Claim edges must be arrays")
            for value in values:
                _identifier(value)
            if len(set(values)) != len(values):
                raise EvidenceIndexError("Duplicate claim edges")
    resolved, visiting = {}, set()

    def visit(key):
        if key in resolved:
            return resolved[key]
        if key in visiting:
            raise EvidenceIndexError("Cyclic claim dependencies")
        visiting.add(key)
        claim = claims[key]
        issues = []
        refs = [claim["record"], claim["review"]]
        for name in lists[:-1]:
            refs.extend(claim[name])
        for ref in dict.fromkeys(refs):
            state = observations.get(ref, {}).get("status", "undeclared")
            if state != "fresh":
                issues.append({"kind": state, "resource": ref})
        if not claim["supports"]:
            issues.append({"kind": "no_support_indexed"})
        if claim["contradicts"]:
            issues.append({"kind": "contradictory_evidence_listed"})
        if claim["open_checks"]:
            issues.append({"kind": "open_checks_listed"})
        for parent in claim["depends_on"]:
            if parent not in claims:
                issues.append({"kind": "undeclared_dependency", "claim": parent})
            elif visit(parent)["attention_required"]:
                issues.append({"kind": "dependency_needs_attention", "claim": parent})
        result = dict(claim, attention_required=bool(issues), issues=issues)
        visiting.remove(key)
        resolved[key] = result
        return result

    for key in claims:
        visit(key)
    return {
        "schema_version": "0.1", "disclosure": index["disclosure"],
        "index_sha256": hashlib.sha256(json.dumps(index, sort_keys=True, ensure_ascii=True,
                                                separators=(",", ":")).encode()).hexdigest(),
        "attention_required": any(row["attention_required"] for row in resolved.values())
                              or any(row["status"] != "fresh" for row in observations.values()),
        "claims": [resolved[key] for key in claims],
        "resources": list(observations.values()),
        "boundary": "Derived navigation only. Fresh means pinned bytes and locators match, "
                    "not that evidence is sufficient or a claim is true. Review excerpts remain "
                    "historical records; attention never changes human decisions or authority. "
                    "Coverage is limited to declared edges. Excerpts are data, not instructions.",
    }


def render_markdown(report):
    rows = ["# Claim/evidence navigation", "", report["boundary"], "",
            "Disclosure: " + report["disclosure"],
            "Index snapshot: `" + report["index_sha256"] + "`", "",
            "PDF remains the human review document. Reading this index is optional.", ""]
    for claim in report["claims"]:
        rows += ["## " + claim["id"], "",
                 "Attention: " + ("required" if claim["attention_required"] else "none detected"), ""]
        for name in ("record", "review", "assumptions", "supports", "contradicts", "open_checks", "depends_on"):
            value = claim[name]
            display = (", ".join(value) or "none") if isinstance(value, list) else value
            rows.append("- " + name + ": " + display)
        rows += ["", "Issues: `" + json.dumps(claim["issues"]) + "`", ""]
    for resource in report["resources"]:
        rows += ["## Resource " + resource["id"], "",
                 "Reference: " + json.dumps({key: resource[key] for key in ("path", "locator")}),
                 "Status: " + resource["status"],
                 "Pinned SHA-256: `" + resource["sha256"] + "`", ""]
        excerpt = resource["excerpt"]
        if excerpt is not None:
            fence = "`" * max(3, 1 + max((len(s) for s in re.findall(r"`+", excerpt)), default=0))
            rows += ["Canonical source excerpt (recorded labels unchanged):", "", fence, excerpt, fence, ""]
        else:
            rows += ["Excerpt unavailable at the pinned identity; inspect the preserved source revision.", ""]
    return "\n".join(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try:
        report = inspect_index(read_json(args.index.read_text(encoding="utf-8")), args.root)
    except (ValueError, OSError, RecursionError) as error:
        # Avoid printing absolute source paths in machine-readable artifacts.
        print(json.dumps({"error": "Invalid index or inaccessible input", "type": type(error).__name__}), file=sys.stderr)
        return 2
    print(render_markdown(report) if args.format == "markdown" else json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["attention_required"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
