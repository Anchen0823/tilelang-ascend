# Copyright (c) Tile-AI Organization.
# Licensed under the MIT License.

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


INSTALLER = Path(__file__).resolve().parents[3] / "install_ascend.sh"
BASH = shutil.which("bash")
STUBS = """\
python3() { echo 'Python 3.12.0'; }
pip() {
    printf 'pip:%s\\n' "$3"
    case "$3" in
        requirements-build.txt) return "$BUILD_REQUIREMENTS_STATUS" ;;
        requirements.txt) return "$RUNTIME_REQUIREMENTS_STATUS" ;;
        *) exit 99 ;;
    esac
}
git() {
    echo 'git:reached'
    exit 77
}
"""


@unittest.skipUnless(BASH, "Bash is required")
class InstallRequirementsTest(unittest.TestCase):
    def test_requirements_installation(self) -> None:
        scenarios = [
            (7, 0, 1, ["pip:requirements-build.txt"], "Python build requirements"),
            (0, 7, 1, ["pip:requirements-build.txt", "pip:requirements.txt"], "Python requirements"),
            (0, 0, 77, ["pip:requirements-build.txt", "pip:requirements.txt", "git:reached"], ""),
        ]
        with tempfile.TemporaryDirectory() as temp:
            stubs = Path(temp) / "stubs.sh"
            stubs.write_text(STUBS, encoding="utf-8", newline="\n")
            for build_status, runtime_status, exit_code, expected, error in scenarios:
                with self.subTest(build_status=build_status, runtime_status=runtime_status):
                    result = subprocess.run(
                        [
                            BASH,
                            "--noprofile",
                            "--norc",
                            "-c",
                            'source "$1" || exit 96; installer=$2; shift 2; source "$installer"',
                            "bash",
                            stubs.as_posix(),
                            INSTALLER.as_posix(),
                        ],
                        cwd=temp,
                        env={
                            **os.environ,
                            "BASH_ENV": "",
                            "ENV": "",
                            "BUILD_REQUIREMENTS_STATUS": str(build_status),
                            "RUNTIME_REQUIREMENTS_STATUS": str(runtime_status),
                        },
                        capture_output=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=10,
                    )
                    events = [
                        line for line in result.stdout.splitlines() if line.startswith(("pip:", "git:"))
                    ]
                    self.assertEqual(result.returncode, exit_code, result.stdout + result.stderr)
                    self.assertEqual(events, expected)
                    if error:
                        self.assertIn(error, result.stdout + result.stderr)
                        self.assertNotIn("installed successfully", result.stdout)
