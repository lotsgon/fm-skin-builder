#!/usr/bin/env python3
"""
Determine next version based on conventional commits.

Uses git tags and conventional commit messages to calculate the next semantic version.
Follows conventional commits spec: https://www.conventionalcommits.org/

Commit types that trigger version bumps:
- BREAKING CHANGE or ! suffix: Major version bump (e.g., 0.1.0 -> 1.0.0)
- feat: Minor version bump (e.g., 0.1.0 -> 0.2.0)
- fix, perf, refactor: Patch version bump (e.g., 0.1.0 -> 0.1.1)
- Other types (docs, chore, style, test): No version bump

Beta versions:
- Format: X.Y.Z-{build-number} (e.g., 0.3.0-1, 0.3.0-2, etc.)
- Build number starts at 1 for first beta of a new version
- Subsequent betas for same version increment the build number
- Numeric-only to comply with Windows MSI requirements (< 65535)
- "Beta" status indicated by GitHub release tags and R2 beta/ path
"""

import argparse
import re
import subprocess
import sys
from typing import Tuple, Optional


def run_git_command(cmd: list[str]) -> str:
    """Run git command and return output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        sys.exit(1)


def get_latest_tag() -> Optional[str]:
    """Get the latest semver tag, or None if no tags exist."""
    try:
        tags = run_git_command(["git", "tag", "-l", "v*", "--sort=-version:refname"])
        if not tags:
            return None

        # Find first tag that matches semver pattern (with or without pre-release)
        for tag in tags.split("\n"):
            # Match: v0.2.0 or v0.2.0-beta.123 or 0.2.0
            if re.match(r"^v?\d+\.\d+\.\d+", tag):
                # Strip 'v' prefix and any pre-release suffix for version parsing
                version = tag.lstrip("v").split("-")[0]
                return version

        return None
    except Exception:
        return None


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse version string into (major, minor, patch) tuple."""
    # Strip v prefix and any pre-release/metadata
    version_str = version_str.lstrip("v").split("-")[0].split("+")[0]

    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")

    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def get_commits_since_tag(tag: Optional[str]) -> list[str]:
    """Get commit messages since tag (or all commits if no tag)."""
    if tag:
        # Get commits since tag
        cmd = ["git", "log", f"v{tag}..HEAD", "--pretty=format:%s"]
    else:
        # Get all commits
        cmd = ["git", "log", "--pretty=format:%s"]

    commits = run_git_command(cmd)
    return commits.split("\n") if commits else []


def analyze_commits(commits: list[str]) -> str:
    """
    Analyze commits to determine bump type.

    Returns: "major", "minor", "patch", or "none"
    """
    has_breaking = False
    has_feat = False
    has_fix = False

    for commit in commits:
        commit = commit.strip()
        if not commit:
            continue

        # Check for breaking changes
        if "BREAKING CHANGE" in commit or "!" in commit.split(":")[0]:
            has_breaking = True

        # Check for feat
        if commit.startswith("feat"):
            has_feat = True

        # Check for fix/perf/refactor
        if any(commit.startswith(t) for t in ["fix", "perf", "refactor"]):
            has_fix = True

    if has_breaking:
        return "major"
    elif has_feat:
        return "minor"
    elif has_fix:
        return "patch"
    else:
        return "none"


def bump_version(
    current: Tuple[int, int, int],
    bump_type: str,
) -> Tuple[int, int, int]:
    """Bump version based on type."""
    major, minor, patch = current

    if bump_type == "major":
        # For 0.x.y versions, major bump goes to 0.x+1.0 (not 1.0.0)
        # This matches semver expectations for pre-1.0 versions
        if major == 0:
            return (0, minor + 1, 0)
        return (major + 1, 0, 0)
    elif bump_type == "minor":
        return (major, minor + 1, 0)
    elif bump_type == "patch":
        return (major, minor, patch + 1)
    else:
        return current


def get_commit_sha(short: bool = True) -> str:
    """Get current commit SHA."""
    cmd = ["git", "rev-parse", "--short" if short else "", "HEAD"]
    return run_git_command([c for c in cmd if c])


def get_latest_beta_number(version: Tuple[int, int, int]) -> int:
    """
    Get the highest beta number for a specific version.

    Args:
        version: Version tuple (major, minor, patch)

    Returns:
        Highest beta number found, or 0 if no betas exist for this version
    """
    version_str = f"{version[0]}.{version[1]}.{version[2]}"

    try:
        # Get all tags matching this version with beta suffix
        tags = run_git_command(
            ["git", "tag", "-l", f"v{version_str}-*", "--sort=-version:refname"]
        )
        if not tags:
            return 0

        # Find highest beta number
        highest = 0
        for tag in tags.split("\n"):
            # Match pattern: v0.3.0-123
            match = re.match(rf"^v?{re.escape(version_str)}-(\d+)$", tag)
            if match:
                beta_num = int(match.group(1))
                highest = max(highest, beta_num)

        return highest
    except Exception:
        return 0


def get_build_number(version: Optional[Tuple[int, int, int]] = None) -> str:
    """
    Get build number for beta releases.

    For a new version (no existing betas), starts at 1.
    For existing version betas, increments from highest existing beta number.

    Args:
        version: Optional version tuple to check for existing betas
    """
    # If version provided, check for existing beta tags
    if version:
        latest_beta = get_latest_beta_number(version)
        if latest_beta > 0:
            # Increment from existing beta
            return str(latest_beta + 1)
        else:
            # First beta for this version
            return "1"

    # Fallback for old behavior (shouldn't be reached with new code)
    import os

    build_num = os.environ.get("GITHUB_RUN_NUMBER")
    if build_num:
        return build_num

    # Fallback: count commits on current branch
    try:
        count = run_git_command(["git", "rev-list", "--count", "HEAD"])
        return count
    except Exception:
        # Last resort: use timestamp
        import time

        return str(int(time.time()) % 65535)


def main():
    parser = argparse.ArgumentParser(
        description="Determine next version based on conventional commits"
    )
    parser.add_argument(
        "--beta",
        action="store_true",
        help="Generate beta version with build number (e.g., 0.2.0-123 - numeric only for MSI compatibility)",
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="Return current version without bumping",
    )
    parser.add_argument(
        "--bump-type",
        choices=["major", "minor", "patch"],
        help="Force specific bump type (overrides commit analysis)",
    )

    args = parser.parse_args()

    # Get latest tag
    latest_tag = get_latest_tag()

    if latest_tag:
        current_version = parse_version(latest_tag)
    else:
        # No tags yet, start at 0.1.0
        current_version = (0, 0, 0)

    # If --current, just return current version
    if args.current:
        if latest_tag:
            print(latest_tag)
        else:
            print("0.1.0")
        return

    # Determine bump type
    if args.bump_type:
        bump_type = args.bump_type
    else:
        commits = get_commits_since_tag(latest_tag)
        bump_type = analyze_commits(commits)

    # If no changes and no tag exists, start at 0.1.0
    if bump_type == "none" and not latest_tag:
        next_version = (0, 1, 0)
    else:
        next_version = bump_version(current_version, bump_type)

    # Format version
    version_str = f"{next_version[0]}.{next_version[1]}.{next_version[2]}"

    # Add beta suffix if requested
    # Use numeric-only format for MSI compatibility (no "beta" text)
    if args.beta:
        # Pass version to get smart beta numbering (starts at 1 for new versions)
        build_num = get_build_number(next_version)
        version_str = f"{version_str}-{build_num}"

    print(version_str)


if __name__ == "__main__":
    main()
