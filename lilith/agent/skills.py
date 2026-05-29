"""Lilith Agent — Skill management."""

import re
from pathlib import Path


class SkillManager:
    """Manage reusable skills (procedures Lilith learns)."""

    def __init__(self, skills_dir: Path = Path(".lilith/skills")):
        self.dir = Path(skills_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[dict]:
        return [{"name": f.stem, **self._parse(f)} for f in sorted(self.dir.glob("*.md"))]

    def get(self, name: str) -> str | None:
        f = self.dir / f"{name}.md"
        return f.read_text() if f.exists() else None

    def save(self, name: str, content: str, description: str = "", trigger: str = ""):
        header = f'---\ndescription: "{description}"\ntrigger: "{trigger}"\n---\n\n'
        (self.dir / f"{name}.md").write_text(header + content)

    def delete(self, name: str) -> bool:
        f = self.dir / f"{name}.md"
        if f.exists():
            f.unlink()
            return True
        return False

    def _parse(self, path: Path) -> dict:
        text = path.read_text()[:500]
        desc = re.search(r'description:\s*"([^"]*)"', text)
        trig = re.search(r'trigger:\s*"([^"]*)"', text)
        return {
            "description": desc.group(1) if desc else "",
            "trigger": trig.group(1) if trig else "",
        }
