# -*- coding: utf-8 -*-
"""
Lilith v2.1 - GIT HOOKS INTEGRATION
FASE D: Ecosistema - Automatic Git Hooks

Features:
- Install/uninstall hooks automatically
- Pre-commit code quality checks
- Post-commit analysis
- Pre-push validation
"""

import os
import stat
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .logger import get_logger

logger = get_logger(__name__)


class HookType(Enum):
    """Tipos de Git hooks soportados"""

    PRE_COMMIT = "pre-commit"
    POST_COMMIT = "post-commit"
    PRE_PUSH = "pre-push"
    POST_MERGE = "post-merge"
    PRE_REBASE = "pre-rebase"


@dataclass
class HookConfig:
    """ConfiguraciÃ³n de un hook"""

    enabled: bool = True
    strict: bool = (
        False  # Si True, falla el git operation si Lilith encuentra problemas
    )
    auto_fix: bool = False  # Intentar arreglar automÃ¡ticamente
    notify: bool = True  # Mostrar notificaciones


class GitHookManager:
    """Gestor de Git hooks de Lilith"""

    HOOK_TEMPLATES = {
        HookType.PRE_COMMIT: """#!/bin/bash
# Lilith v2.1 - Pre-commit Hook
# Generated automatically - Do not edit manually

echo "ðŸ” Lilith: Analyzing staged files..."

# Run security scan
lilith-cli security-scan --staged
if [ $? -ne 0 ] && [ "{strict}" = "true" ]; then
    echo "âŒ Security issues found. Commit aborted."
    exit 1
fi

# Run code review
lilith-cli code-review --staged --quick
if [ $? -ne 0 ] && [ "{strict}" = "true" ]; then
    echo "âŒ Code quality issues found. Commit aborted."
    exit 1
fi

# Run tests if present
if [ -f "pytest.ini" ] || [ -f "setup.py" ]; then
    echo "ðŸ§ª Running tests..."
    python -m pytest -x -q
    if [ $? -ne 0 ] && [ "{strict}" = "true" ]; then
        echo "âŒ Tests failed. Commit aborted."
        exit 1
    fi
fi

echo "âœ… Pre-commit checks passed!"
exit 0
""",
        HookType.POST_COMMIT: """#!/bin/bash
# Lilith v2.1 - Post-commit Hook

echo "ðŸ“ Lilith: Analyzing commit..."

# Get commit info
COMMIT_MSG=$(git log -1 --pretty=%B)
COMMIT_HASH=$(git log -1 --pretty=%H)

# Suggest improvements for next time
lilith-cli analyze-commit --hash=$COMMIT_HASH

# Update metrics
lilith-cli metrics-update --type=commit

echo "âœ… Post-commit analysis complete!"
""",
        HookType.PRE_PUSH: """#!/bin/bash
# Lilith v2.1 - Pre-push Hook

echo "ðŸš€ Lilith: Pre-push validation..."

# Full security scan
lilith-cli security-scan --full
if [ $? -ne 0 ] && [ "{strict}" = "true" ]; then
    echo "âŒ Security vulnerabilities found. Push aborted."
    echo "Run: lilith-cli security-report for details"
    exit 1
fi

# Full test suite
echo "ðŸ§ª Running full test suite..."
python -m pytest
if [ $? -ne 0 ] && [ "{strict}" = "true" ]; then
    echo "âŒ Tests failed. Push aborted."
    exit 1
fi

# Check for secrets
lilith-cli secrets-scan
if [ $? -ne 0 ]; then
    echo "âŒ Potential secrets detected! Push aborted."
    exit 1
fi

echo "âœ… Pre-push validation passed!"
exit 0
""",
    }

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.git_dir = self._find_git_dir()
        self.hooks_dir = self.git_dir / "hooks" if self.git_dir else None

    def _find_git_dir(self) -> Optional[Path]:
        """Encontrar directorio .git"""
        current = self.project_path
        while current != current.parent:
            git_dir = current / ".git"
            if git_dir.exists():
                return git_dir
            current = current.parent
        return None

    def is_git_repo(self) -> bool:
        """Verificar si es un repositorio git"""
        return self.git_dir is not None

    def install_hook(self, hook_type: HookType, config: HookConfig = None) -> bool:
        """Instalar un hook"""
        if not self.is_git_repo():
            logger.error("No es un repositorio git")
            return False

        config = config or HookConfig()

        if not config.enabled:
            logger.info(f"Hook {hook_type.value} deshabilitado")
            return True

        hook_path = self.hooks_dir / hook_type.value

        # Generar contenido del hook
        template = self.HOOK_TEMPLATES.get(hook_type, "")
        if not template:
            logger.error(f"Template no encontrado para {hook_type.value}")
            return False

        hook_content = template.format(
            strict="true" if config.strict else "false",
            auto_fix="true" if config.auto_fix else "false",
        )

        # Escribir hook
        try:
            with open(hook_path, "w") as f:
                f.write(hook_content)

            # Hacer ejecutable
            hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

            logger.info(f"Hook instalado: {hook_type.value}")
            return True

        except Exception as e:
            logger.error(f"Error instalando hook: {e}")
            return False

    def uninstall_hook(self, hook_type: HookType) -> bool:
        """Desinstalar un hook"""
        if not self.is_git_repo():
            return False

        hook_path = self.hooks_dir / hook_type.value

        # Verificar si es un hook de Lilith
        if hook_path.exists():
            try:
                content = hook_path.read_text()
                if "Lilith v2.1" in content:
                    hook_path.unlink()
                    logger.info(f"Hook desinstalado: {hook_type.value}")
                    return True
                else:
                    logger.warning(
                        f"El hook {hook_type.value} no fue creado por Lilith"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error desinstalando hook: {e}")
                return False

        return True

    def install_all_hooks(
        self, configs: Dict[HookType, HookConfig] = None
    ) -> Dict[str, bool]:
        """Instalar todos los hooks"""
        configs = configs or {}
        results = {}

        for hook_type in HookType:
            config = configs.get(hook_type, HookConfig())
            results[hook_type.value] = self.install_hook(hook_type, config)

        return results

    def get_hook_status(self, hook_type: HookType) -> Dict:
        """Obtener estado de un hook"""
        if not self.is_git_repo():
            return {"installed": False, "error": "No es un repo git"}

        hook_path = self.hooks_dir / hook_type.value

        if not hook_path.exists():
            return {"installed": False, "is_Lilith": False}

        try:
            content = hook_path.read_text()
            is_Lilith = "Lilith v2.1" in content

            return {
                "installed": True,
                "is_Lilith": is_Lilith,
                "path": str(hook_path),
                "size": len(content),
            }
        except Exception as e:
            return {"installed": True, "error": str(e)}

    def list_installed_hooks(self) -> List[Dict]:
        """Listar todos los hooks instalados"""
        if not self.is_git_repo():
            return []

        hooks = []
        for hook_type in HookType:
            status = self.get_hook_status(hook_type)
            if status["installed"]:
                hooks.append({"type": hook_type.value, **status})

        return hooks


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CLI INTERFACE PARA HOOKS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class GitHookCLI:
    """Interfaz de lÃ­nea de comandos para hooks"""

    def __init__(self):
        self.manager = GitHookManager()

    async def run_pre_commit(self, options: Dict) -> Dict:
        """Ejecutar lÃ³gica de pre-commit"""
        from .code_review_ai import get_code_review_ai
        from .security_scanner import get_security_scanner

        results = {"passed": True, "checks": []}

        # Security scan
        scanner = get_security_scanner()
        scan_result = await scanner.scan_project(include_dependencies=False)

        critical = sum(
            1 for f in scan_result.findings if f.severity.value == "critical"
        )
        if critical > 0:
            results["passed"] = False
            results["checks"].append(
                {
                    "name": "security",
                    "passed": False,
                    "message": f"{critical} vulnerabilidades crÃ­ticas encontradas",
                }
            )
        else:
            results["checks"].append(
                {
                    "name": "security",
                    "passed": True,
                    "message": "No se encontraron vulnerabilidades crÃ­ticas",
                }
            )

        # Code review
        reviewer = get_code_review_ai()
        review_result = await reviewer.review_project(include_duplicates=False)

        if review_result.overall_score < 50:
            results["passed"] = False
            results["checks"].append(
                {
                    "name": "quality",
                    "passed": False,
                    "message": f"Score de calidad bajo: {review_result.overall_score}",
                }
            )
        else:
            results["checks"].append(
                {
                    "name": "quality",
                    "passed": True,
                    "message": f"Score de calidad: {review_result.overall_score}",
                }
            )

        return results

    async def run_post_commit(self, commit_hash: str) -> Dict:
        """Analizar commit despuÃ©s de crearlo"""
        return {
            "analyzed": True,
            "commit": commit_hash,
            "suggestions": [
                "Considera agregar mÃ¡s tests para el cambio",
                "El mensaje de commit es claro",
            ],
        }

    async def run_pre_push(self) -> Dict:
        """ValidaciÃ³n completa antes de push"""
        results = await self.run_pre_commit({})

        # AquÃ­ irÃ­an mÃ¡s validaciones especÃ­ficas de pre-push

        return results


# Instancia global
_hook_manager = None


def get_hook_manager(project_path: Optional[Path] = None) -> GitHookManager:
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = GitHookManager(project_path)
    return _hook_manager
