"""Automated PII and Personal Path Leak Scanner.

Prevents hardcoded developer workstation paths (such as 'C:/Users/<name>',
'/home/<name>', '/Users/<name>') from being staged in Git or committed to repository.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Patterns identifying local user home directories across Windows, macOS, and Linux
# Whitelists standard CI runners (e.g. runner, runneradmin, ubuntu, Default, Public)
PATTERNS = [
    (
        re.compile(r"""(?i)[a-z]:[/\\]users[/\\](?!public|default)[a-z0-9_.-]+"""),
        "Windows user home directory path detected",
    ),
    (
        re.compile(r"""/(?:home|Users)/(?!runner|ubuntu|runneradmin|circleci)[a-z0-9_.-]+"""),
        "Unix/macOS user home directory path detected",
    ),
]

IGNORED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".whl",
    ".exe",
    ".pyc",
}

IGNORED_FILES = {
    "scripts/check_pii_leak.py",  # Self-referencing pattern definitions
}


def scan_text(text: str, source_label: str) -> list[str]:
    """Scans text for personal user home directory patterns."""
    findings: list[str] = []
    for line_idx, line in enumerate(text.splitlines(), start=1):
        for pattern, desc in PATTERNS:
            match = pattern.search(line)
            if match:
                matched_str = match.group(0)
                findings.append(
                    f"{source_label}:{line_idx}: {desc} ('{matched_str}')\n  --> {line.strip()}"
                )
    return findings


def scan_staged() -> int:
    """Scans git staged diffs (+ lines) for personal user path leaks."""
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--unified=0", "--no-color"],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as err:
        sys.stderr.write(f"Error running git diff: {err}\n")
        return 1

    current_file = ""
    findings: list[str] = []

    for line in proc.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:]
            if current_file in IGNORED_FILES:
                continue
            if any(current_file.endswith(ext) for ext in IGNORED_EXTENSIONS):
                continue
            for pattern, desc in PATTERNS:
                match = pattern.search(added_content)
                if match:
                    findings.append(
                        f"Staged file '{current_file}': {desc} ('{match.group(0)}')\n  --> {added_content.strip()}"
                    )

    if findings:
        sys.stderr.write("\n[ERROR] PII / Personal Path Leak Detected in Staged Changes!\n\n")
        for f in findings:
            sys.stderr.write(f"  - {f}\n")
        sys.stderr.write(
            "\nPlease replace absolute workstation paths with dynamic environment variables "
            "(e.g., '${env:PLUGIN_HOME}' or '$HOME') before committing.\n\n"
        )
        return 1

    sys.stdout.write("[PASS] Pre-commit check: zero personal path leaks in staged files.\n")
    return 0


def scan_all_tracked(repo_root: Path) -> int:
    """Scans all tracked files in the repository for personal path leaks."""
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as err:
        sys.stderr.write(f"Error listing tracked git files: {err}\n")
        return 1

    findings: list[str] = []
    tracked_files = [f.strip() for f in proc.stdout.splitlines() if f.strip()]

    for rel_path in tracked_files:
        if rel_path in IGNORED_FILES:
            continue
        if any(rel_path.endswith(ext) for ext in IGNORED_EXTENSIONS):
            continue
        file_path = repo_root / rel_path
        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        file_findings = scan_text(content, rel_path)
        findings.extend(file_findings)

    if findings:
        sys.stderr.write("\n[ERROR] PII / Personal Path Leak Detected in Repository!\n\n")
        for f in findings:
            sys.stderr.write(f"  - {f}\n")
        sys.stderr.write(
            "\nPlease sanitize hardcoded workstation paths before merging.\n\n"
        )
        return 1

    sys.stdout.write("[PASS] Repository audit: zero personal path leaks across all tracked files.\n")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Scan repository or staged changes for PII path leaks.")
    parser.add_argument("--staged", action="store_true", help="Scan only git staged changes (for pre-commit).")
    parser.add_argument("--all", action="store_true", help="Scan all git tracked files (for CI/audits).")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    if args.staged:
        return scan_staged()
    return scan_all_tracked(repo_root)


if __name__ == "__main__":
    sys.exit(main())
