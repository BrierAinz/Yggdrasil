import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CodeEditor")


class CodeEditor:
    """
    Specialized tool for safe and structured file modifications.
    Supports editing, writing, and inserting code with automated backups.
    """

    def __init__(self, root_path: str = ".", backup_dir: str = "backups"):
        self.root_path = Path(root_path).absolute()
        self.backup_path = self.root_path / backup_dir
        self.backup_path.mkdir(exist_ok=True)

    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a timestamped backup of the file"""
        try:
            if not file_path.exists():
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rel_path = file_path.relative_to(self.root_path)
            # Replace slashes and dots to create a safe flat filename
            safe_name = str(rel_path).replace(os.sep, "_").replace(".", "_")
            backup_file = self.backup_path / f"{safe_name}_{timestamp}.bak"

            shutil.copy2(file_path, backup_file)
            logger.info(f"Backup created: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return None

    def edit_file(
        self, file_path: str, target: str, replacement: str
    ) -> Dict[str, Any]:
        """
        Replace target text with replacement text in a file.
        """
        try:
            full_path = self.root_path / file_path
            if not full_path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            if target not in content:
                # Try with stripped versions to be more flexible
                if target.strip() in content:
                    target = target.strip()
                else:
                    return {
                        "success": False,
                        "error": "Target content not found in file exactly",
                    }

            # Count occurrences
            occurrences = content.count(target)
            if occurrences > 1:
                return {
                    "success": False,
                    "error": f"Target content is ambiguous ({occurrences} occurrences found). Please provide more context.",
                }

            # Create backup
            backup = self._create_backup(full_path)

            # Apply replacement
            new_content = content.replace(target, replacement)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "success": True,
                "message": f"Successfully edited {file_path}",
                "backup": str(backup.relative_to(self.root_path)) if backup else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(
        self, file_path: str, content: str, overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new file or overwrite an existing one.
        """
        try:
            full_path = self.root_path / file_path
            exists = full_path.exists()

            if exists and not overwrite:
                return {
                    "success": False,
                    "error": f"File already exists and overwrite is False: {file_path}",
                }

            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)

            backup = None
            if exists:
                backup = self._create_backup(full_path)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "message": f"Successfully {'overwritten' if exists else 'created'} {file_path}",
                "backup": str(backup.relative_to(self.root_path)) if backup else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def insert_at(
        self, file_path: str, line_number: int, content: str
    ) -> Dict[str, Any]:
        """
        Insert content at a specific line number (1-indexed).
        """
        try:
            full_path = self.root_path / file_path
            if not full_path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Adjust to 0-indexed
            idx = max(0, min(line_number - 1, len(lines)))

            # Create backup
            backup = self._create_backup(full_path)

            # Ensure line ends with newline if needed
            if not content.endswith("\n"):
                content += "\n"

            lines.insert(idx, content)

            with open(full_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            return {
                "success": True,
                "message": f"Inserted content at line {line_number} in {file_path}",
                "backup": str(backup.relative_to(self.root_path)) if backup else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute interface for tool registry"""
        file_path = kwargs.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path is required"}

        if action == "edit":
            return self.edit_file(
                file_path=file_path,
                target=kwargs.get("target", ""),
                replacement=kwargs.get("replacement", ""),
            )
        elif action == "write":
            return self.write_file(
                file_path=file_path,
                content=kwargs.get("content", ""),
                overwrite=kwargs.get("overwrite", False),
            )
        elif action == "insert":
            return self.insert_at(
                file_path=file_path,
                line_number=kwargs.get("line_number", 1),
                content=kwargs.get("content", ""),
            )
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


if __name__ == "__main__":
    # Test
    editor = CodeEditor(root_path="D:\\Proyectos\\Lilith\\Core")
    # editor.write_file("Tests/test_editor.txt", "Hello World\nLine 2\nLine 3\n")
    # editor.insert_at("Tests/test_editor.txt", 2, "Inserted Line\n")
    # editor.edit_file("Tests/test_editor.txt", "Hello World", "Bonjour Le Monde")
    print("CodeEditor test script ready")
