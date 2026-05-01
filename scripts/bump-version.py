#!/usr/bin/env python3
"""
Bump version across the Yggdrasil ecosystem.
Usage: python bump-version.py [patch|minor|major]
"""
import datetime
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()


def get_current_version() -> str:
    """Read the latest released version from CHANGELOG.md."""
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    content = changelog_path.read_text(encoding="utf-8")
    # Find first version header that is NOT Unreleased
    match = re.search(r"## \[(\d+\.\d+\.\d+)\]", content)
    if not match:
        raise RuntimeError("Could not find current version in CHANGELOG.md")
    return match.group(1)


def get_file_patterns(current_version: str):
    """Build regex patterns using the actual current version."""
    v = re.escape(current_version)
    return {
        "Asgard/Hermes-Lilith/Lilith/main.py": [
            (rf'(print\("Lilith v){v}', r"\g<1>{new_version}"),
        ],
        "Asgard/lilith-api/lilith_api/main.py": [
            (rf'(version="){v}(")', r"\g<1>{new_version}\g<2>"),
        ],
        "Asgard/lilith-cli/lilith_cli/main.py": [
            (rf'(print\("Lilith v){v}', r"\g<1>{new_version}"),
        ],
        "Asgard/lilith-cli/tests/test_cli.py": [
            (rf'("){v}(" in result\.stdout)', r'"{new_version}"\g<2>'),
        ],
        "Asgard/Lilith/src/api/server.py": [
            (rf'(version="){v}(")', r"\g<1>{new_version}\g<2>"),
        ],
        "Alfheim/ui-seed/package.json": [
            (rf'("version": "){v}(")', r"\g<1>{new_version}\g<2>"),
        ],
    }


def bump_changelog(new_version: str) -> None:
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    with open(changelog_path, "r", encoding="utf-8", newline="") as f:
        content = f.read()
    today = datetime.date.today().isoformat()

    # Extract Unreleased body
    unreleased_match = re.search(
        r"## \[Unreleased\]\n\n(.*?)\n(?=## \[)",
        content,
        re.DOTALL,
    )

    if not unreleased_match:
        print("WARNING: Could not find [Unreleased] section in CHANGELOG.md")
        return

    unreleased_body = unreleased_match.group(1).strip()

    # Build replacement
    new_unreleased = "## [Unreleased]\n\n### Added\n\n### Changed\n\n### Removed\n"
    new_version_section = f"## [{new_version}] - {today}\n\n{unreleased_body}\n"
    old_block = unreleased_match.group(0)
    new_block = f"{new_unreleased}\n{new_version_section}"
    content = content.replace(old_block, new_block)

    # Update Unreleased comparison link
    content = re.sub(
        r"(\[Unreleased\]: https://github\.com/BrierAinz/Yggdrasil/compare/v)\d+\.\d+\.\d+(\.\.\.HEAD)",
        rf"\g<1>{new_version}\g<2>",
        content,
    )

    # Insert new version link before the first numbered-version link
    # Pattern matches any [X.Y.Z]: ... compare/vA.B.C...vX.Y.Z
    link_pattern = r"(\[\d+\.\d+\.\d+\]: https://github\.com/BrierAinz/Yggdrasil/compare/v)\d+\.\d+\.\d+(\.\.\.v)\d+\.\d+\.\d+"
    first_link_match = re.search(link_pattern, content)
    if first_link_match:
        first_link = first_link_match.group(0)
        current_in_link = first_link_match.group(0).split("...v")[-1]
        new_link_line = f"[{new_version}]: https://github.com/BrierAinz/Yggdrasil/compare/v{current_in_link}...v{new_version}\n{first_link}"
        content = content.replace(first_link, new_link_line)
    else:
        content = (
            content.rstrip()
            + f"\n\n[{new_version}]: https://github.com/BrierAinz/Yggdrasil/compare/v2.1.0...v{new_version}\n"
        )

    with open(changelog_path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    print(f"Updated CHANGELOG.md -> [{new_version}]")


def bump_file(path: Path, patterns: list, new_version: str) -> None:
    if not path.exists():
        print(f"WARNING: {path} not found")
        return

    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()
    original = content

    for pattern, replacement_template in patterns:
        replacement = replacement_template.format(new_version=new_version)
        content = re.sub(pattern, replacement, content)

    if content != original:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print(f"Updated {path.relative_to(REPO_ROOT)}")
    else:
        print(f"No changes in {path.relative_to(REPO_ROOT)}")


def extract_version_notes(new_version: str) -> str:
    """Extract release notes for the given version from CHANGELOG."""
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    with open(changelog_path, "r", encoding="utf-8", newline="") as f:
        content = f.read()
    pattern = rf"## \[{re.escape(new_version)}\] - \d{{4}}-\d{{2}}-\d{{2}}\n\n(.*?)\n(?=## \[)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return f"Release v{new_version}"


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("patch", "minor", "major"):
        print("Usage: bump-version.py [patch|minor|major]")
        return 1

    bump_type = sys.argv[1]
    current = get_current_version()
    major, minor, patch = map(int, current.split("."))

    if bump_type == "patch":
        patch += 1
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:
        major += 1
        minor = 0
        patch = 0

    new_version = f"{major}.{minor}.{patch}"
    print(f"Bumping {current} -> {new_version}\n")

    bump_changelog(new_version)

    version_files = get_file_patterns(current)
    for rel_path, patterns in version_files.items():
        bump_file(REPO_ROOT / rel_path, patterns, new_version)

    # Write release notes for CI
    notes = extract_version_notes(new_version)
    notes_path = REPO_ROOT / "RELEASE_NOTES.md"
    notes_path.write_text(notes, encoding="utf-8")
    print(f"\nWrote release notes to {notes_path.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
