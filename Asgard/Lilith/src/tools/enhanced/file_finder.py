"""
Lilith FileFinder Tool v2.0
Finds files by pattern, extension, or content
"""

import os
from pathlib import Path
from typing import List


class FileFinder:
    """Find files by various criteria"""

    def find_by_pattern(
        self, pattern: str, root: str = ".", max_results: int = 100
    ) -> List[str]:
        """Find files matching glob pattern"""
        root_path = Path(root)
        matches = []

        for path in root_path.rglob(pattern):
            if path.is_file():
                matches.append(str(path))
                if len(matches) >= max_results:
                    break

        return matches

    def find_by_content(
        self, text: str, root: str = ".", max_results: int = 50
    ) -> List[str]:
        """Find files containing text"""
        root_path = Path(root)
        matches = []

        for path in root_path.rglob("*"):
            if path.is_file() and path.stat().st_size < 1_000_000:  # Skip large files
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    if text.lower() in content.lower():
                        matches.append(str(path))
                        if len(matches) >= max_results:
                            break
                except Exception:
                    continue

        return matches

    def find_by_extension(
        self, extension: str, root: str = ".", max_results: int = 100
    ) -> List[str]:
        """Find files by extension"""
        return self.find_by_pattern(f"*.{extension.lstrip('.')}", root, max_results)

    def execute(self, command: str) -> str:
        """Execute file finding command"""
        parts = command.split()
        if len(parts) < 2:
            return "[ERROR] Usage: find <pattern|content|ext> <value> [root]"

        try:
            if parts[0] == "pattern":
                pattern = parts[1]
                root = parts[2] if len(parts) > 2 else "."
                files = self.find_by_pattern(pattern, root)
            elif parts[0] == "content":
                text = parts[1]
                root = parts[2] if len(parts) > 2 else "."
                files = self.find_by_content(text, root)
            elif parts[0] == "ext":
                ext = parts[1]
                root = parts[2] if len(parts) > 2 else "."
                files = self.find_by_extension(ext, root)
            else:
                return (
                    f"[ERROR] Unknown mode: {parts[0]}. Use: pattern, content, or ext"
                )

            if not files:
                return "No files found."

            lines = [f"Found {len(files)} files:"]
            lines.extend(files[:20])  # First 20 files
            if len(files) > 20:
                lines.append(f"... and {len(files) - 20} more files")

            return "\n".join(lines)
        except Exception as e:
            return f"[ERROR] FileFinder failed: {e}"


if __name__ == "__main__":
    import sys

    finder = FileFinder()

    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        print(finder.execute(cmd))
    else:
        print("FileFinder tool ready")
        # Quick test
        py_files = finder.find_by_extension("py", ".", max_results=5)
        print(f"Test: Found {len(py_files)} Python files")
