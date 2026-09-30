"""Tests for privacy-safe numerical runtime provenance."""

import configparser
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from holoforge.core.provenance import (
    UNKNOWN,
    backend_fields,
    git_source_state,
    package_source_digest,
    package_source_files,
    runtime_versions,
)


ROOT = Path(__file__).resolve().parents[1]


class RuntimeProvenanceTests(unittest.TestCase):
    def test_runtime_fingerprint_is_complete_and_stable(self) -> None:
        first = runtime_versions()
        second = runtime_versions()
        for field in (
            "holoforge",
            "python",
            "python_implementation",
            "byteorder",
            "platform_system",
            "platform_machine",
            "numpy",
            "scipy",
            "numerical_build_sha256",
            "longdouble_epsilon",
            "numpy_blas",
            "numpy_lapack",
            "scipy_blas",
            "scipy_lapack",
            "holoforge_source_sha256",
            "holoforge_git_commit",
            "holoforge_git_src_modified",
        ):
            self.assertIn(field, first)
            self.assertIsInstance(first[field], str)
            self.assertTrue(first[field])
        self.assertEqual(first, second)
        self.assertRegex(first["numerical_build_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(first["holoforge_source_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(
            first["holoforge_git_commit"], r"^(?:[0-9a-f]{40}|[0-9a-f]{64}|unknown)$"
        )
        self.assertIn(first["holoforge_git_src_modified"], {"true", "false", UNKNOWN})
        self.assertGreater(float(first["longdouble_epsilon"]), 0.0)

    def test_runtime_fingerprint_contains_no_private_identity_fields(self) -> None:
        provenance = runtime_versions()
        combined = " ".join(provenance).lower()
        for forbidden in (
            "username",
            "hostname",
            "password",
            "secret",
            "token",
            "credential",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertFalse(
            any(
                re.match(r"^(?:/|~|[A-Za-z]:[\\/])", value)
                for value in provenance.values()
            )
        )


class BackendFieldTests(unittest.TestCase):
    def test_only_library_names_and_versions_are_read(self) -> None:
        report = {
            "Build Dependencies": {
                "blas": {
                    "name": "scipy-openblas",
                    "version": "0.3.29",
                    "lib directory": "/opt/private/lib",
                    "include directory": "/opt/private/include",
                },
                "lapack": {"name": "Accelerate", "version": "unknown"},
            }
        }
        self.assertEqual(
            backend_fields("numpy", report),
            {"numpy_blas": "scipy-openblas 0.3.29", "numpy_lapack": "accelerate"},
        )

    def test_missing_or_path_like_reports_become_unknown(self) -> None:
        self.assertEqual(
            backend_fields("scipy", None),
            {"scipy_blas": UNKNOWN, "scipy_lapack": UNKNOWN},
        )
        report = {"Build Dependencies": {"blas": {"name": "/usr/lib/libblas"}}}
        self.assertEqual(
            backend_fields("scipy", report),
            {"scipy_blas": UNKNOWN, "scipy_lapack": UNKNOWN},
        )


class SourceDigestTests(unittest.TestCase):
    def test_digest_tracks_source_and_data_bytes_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "holoforge"
            (package / "data").mkdir(parents=True)
            (package / "__pycache__").mkdir()
            (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
            (package / "data" / "reference.json").write_text("{}", encoding="utf-8")
            first = package_source_digest(package)
            self.assertRegex(first, r"^[0-9a-f]{64}$")

            (package / "__pycache__" / "cached.py").write_text("x", encoding="utf-8")
            (package / "notes.txt").write_text("ignored", encoding="utf-8")
            self.assertEqual(package_source_digest(package), first)

            (package / "data" / "reference.json").write_text(
                '{"a": 1}', encoding="utf-8"
            )
            self.assertNotEqual(package_source_digest(package), first)

    def test_empty_package_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(package_source_digest(Path(directory)), UNKNOWN)

    def test_digested_files_are_exactly_those_a_wheel_installs(self) -> None:
        """A checkout and a wheel of the same source must share one digest.

        The digest depends only on relative paths and contents, so this holds
        when the checkout's digested file set equals the wheel's installed set:
        the modules of every package plus the declared package data.
        """

        package = ROOT / "src" / "holoforge"
        config = configparser.ConfigParser()
        config.read(ROOT / "setup.cfg", encoding="utf-8")
        patterns = [
            line.strip()
            for line in config["options.package_data"]["holoforge"].splitlines()
            if line.strip()
        ]

        def is_package(directory: Path) -> bool:
            parts = directory.relative_to(package).parts
            chain = [package.joinpath(*parts[:depth]) for depth in range(len(parts) + 1)]
            return all((item / "__init__.py").is_file() for item in chain)

        directories = [package] + [
            path
            for path in package.rglob("*")
            if path.is_dir() and "__pycache__" not in path.parts
        ]
        expected = {
            module.relative_to(package).as_posix()
            for directory in directories
            if is_package(directory)
            for module in directory.glob("*.py")
        }
        for pattern in patterns:
            expected |= {
                path.relative_to(package).as_posix()
                for path in package.glob(pattern)
                if path.is_file()
            }
        self.assertTrue(any(name.endswith(".json") for name in expected))
        self.assertEqual(set(package_source_files(package)), expected)


@unittest.skipUnless(shutil.which("git"), "Git is not available")
class GitSourceStateTests(unittest.TestCase):
    def _git(self, root: Path, *arguments: str) -> None:
        subprocess.run(
            ("git", "-C", str(root), *arguments),
            check=True,
            capture_output=True,
        )

    def _commit_all(self, root: Path) -> None:
        self._git(root, "add", "-A")
        self._git(
            root,
            "-c",
            "user.name=HoloForge Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "-m",
            "fixture",
        )

    def test_checkout_reports_commit_and_source_modification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "src" / "holoforge"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "README.md").write_text("fixture\n", encoding="utf-8")
            self._git(root, "init", "-q")
            self._commit_all(root)

            commit, modified = git_source_state(package)
            self.assertRegex(commit, r"^[0-9a-f]{40}$")
            self.assertEqual(modified, "false")

            (root / "README.md").write_text("outside src\n", encoding="utf-8")
            self.assertEqual(git_source_state(package), (commit, "false"))

            (package / "__init__.py").write_text("VALUE = 2\n", encoding="utf-8")
            self.assertEqual(git_source_state(package), (commit, "true"))

    def test_package_inside_another_repository_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "other.txt").write_text("unrelated\n", encoding="utf-8")
            self._git(root, "init", "-q")
            self._commit_all(root)

            installed = root / "venv" / "site-packages" / "holoforge"
            installed.mkdir(parents=True)
            (installed / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
            self.assertEqual(git_source_state(installed), (UNKNOWN, UNKNOWN))

            untracked = root / "src" / "holoforge"
            untracked.mkdir(parents=True)
            (untracked / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
            self.assertEqual(git_source_state(untracked), (UNKNOWN, UNKNOWN))

    def test_directory_outside_git_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "src" / "holoforge"
            package.mkdir(parents=True)
            self.assertEqual(git_source_state(package), (UNKNOWN, UNKNOWN))


if __name__ == "__main__":
    unittest.main()
