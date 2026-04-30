import fnmatch
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("GrepTool")


class GrepTool:
    """
    Advanced searching tool for project-wide pattern matching.
    Supports regex, globbing, and context extraction.
    """

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).absolute()

    def grep(
        self,
        pattern: str,
        glob_pattern: str = "*",
        is_regex: bool = False,
        context_lines: int = 2,
    ) -> Dict[str, Any]:
        """
        Search for a pattern in files matching glob_pattern.
        """
        results = []
        try:
            # Compile regex if needed
            if is_regex:
                regex = re.compile(pattern, re.IGNORECASE)
            else:
                regex = re.compile(re.escape(pattern), re.IGNORECASE)

            # Find files
            files = list(self.root_path.rglob(glob_pattern))

            for file_path in files:
                if not file_path.is_file():
                    continue
                # Skip common binary/hidden dirs
                if (
                    any(part.startswith(".") for part in file_path.parts)
                    or "node_modules" in file_path.parts
                    or "__pycache__" in file_path.parts
                ):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines):
                        if regex.search(line):
                            # Extract context
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)

                            results.append(
                                {
                                    "file": str(file_path.relative_to(self.root_path)),
                                    "line_number": i + 1,
                                    "content": line.strip(),
                                    "context": [
                                        l.strip("\n") for l in lines[start:end]
                                    ],
                                    "context_start_line": start + 1,
                                }
                            )

                            if len(results) >= 50:  # Safety cap
                                return {
                                    "success": True,
                                    "results": results,
                                    "note": "Limit of 50 results reached",
                                }
                except Exception as e:
                    logger.debug(f"Could not read {file_path}: {e}")
                    continue

            return {"success": True, "results": results}

        except Exception as e:
            logger.error(f"Grep failed: {e}")
            return {"success": False, "error": str(e)}

    def list_files(self, glob_pattern: str = "**/*") -> Dict[str, Any]:
        """
        List files matching a glob pattern.
        """
        try:
            matches = []
            for path in self.root_path.glob(glob_pattern):
                if path.is_file():
                    matches.append(str(path.relative_to(self.root_path)))
                if len(matches) >= 100:
                    break
            return {"success": True, "files": matches}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute interface for tool registry"""
        if action == "grep":
            return self.grep(
                pattern=kwargs.get("pattern", ""),
                glob_pattern=kwargs.get("glob_pattern", "*"),
                is_regex=kwargs.get("is_regex", False),
                context_lines=kwargs.get("context_lines", 2),
            )
        elif action == "list_files":
            return self.list_files(glob_pattern=kwargs.get("glob_pattern", "**/*"))
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


if __name__ == "__main__":
    # Test
    grep = GrepTool(root_path="D:\\Proyectos\\Lilith\\Core")
    res = grep.grep("ConversationalIntentDetector", glob_pattern="Backend/**/*.py")
    print(f"Found {len(res.get('results', []))} matches")
    if res["results"]:
        print(
            f"First match: {res['results'][0]['file']}:{res['results'][0]['line_number']}"
        )
