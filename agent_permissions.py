#!/usr/bin/env python3
"""
Sistema de Permisos Explicitos para Lilith CLI
"""

import json
import logging
import sys
import time
from pathlib import Path


# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("agent_permissions.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class PermissionSystem:
    """Sistema de permisos para el agente Lilith CLI"""

    def __init__(self):
        self.permissions = self.load_permissions()
        self.user_consent = {}
        self.verification_code = None
        self.verified = False

    def load_permissions(self):
        """Carga los permisos del agente"""
        permissions_path = Path("agent_permissions.json")

        if permissions_path.exists():
            with open(permissions_path, encoding="utf-8") as f:
                return json.load(f)

        return self.default_permissions()

    def default_permissions(self):
        """Permisos por defecto para el agente"""
        return {
            "Lilith CLI": {
                "read_files": {
                    "allowed": False,
                    "description": "Acceso a archivos locales para lectura",
                    "scope": "Limited to Yggdrasil project files",
                    "level": "medium",
                    "category": "File System",
                },
                "write_files": {
                    "allowed": False,
                    "description": "Acceso a archivos locales para escritura",
                    "scope": "Limited to project files",
                    "level": "high",
                    "category": "File System",
                },
                "run_commands": {
                    "allowed": False,
                    "description": "Ejecución de comandos del sistema",
                    "scope": "Limited to project-related commands",
                    "level": "high",
                    "category": "System",
                },
                "access_web": {
                    "allowed": False,
                    "description": "Conexión a servicios web",
                    "scope": "API calls only",
                    "level": "medium",
                    "category": "Network",
                },
                "manage_content": {
                    "allowed": False,
                    "description": "Gestión de contenido en plataformas",
                    "scope": "Social media and business websites",
                    "level": "medium",
                    "category": "Web Services",
                },
                "computer_vision": {
                    "allowed": False,
                    "description": "Visión por computadora para lectura de imágenes",
                    "scope": "Text extraction and object detection",
                    "level": "medium",
                    "category": "Computer Vision",
                },
                "download_files": {
                    "allowed": False,
                    "description": "Descarga de archivos desde la web",
                    "scope": "Project-related files only",
                    "level": "medium",
                    "category": "Network",
                },
                "view_repositories": {
                    "allowed": False,
                    "description": "Visualización de repositorios de código",
                    "scope": "Yggdrasil project only",
                    "level": "low",
                    "category": "File System",
                },
            }
        }

    def generate_verification_code(self):
        """Genera un código de verificación para el usuario"""
        import random

        self.verification_code = str(random.randint(100000, 999999))
        logger.info("Código de verificación generado: %s", self.verification_code)
        return self.verification_code

    def validate_verification_code(self, user_code: str) -> bool:
        """Valida el código de verificación del usuario"""
        if user_code == self.verification_code:
            self.verified = True
            logger.info("Código de verificación validado correctamente")
            return True
        else:
            logger.warning("Código de verificación incorrecto")
            return False

    def request_consent(self, agent_name: str) -> bool:
        """Solicita consentimiento explícito del usuario para los permisos"""
        logger.info("Solicitando consentimiento para el agente %s", agent_name)

        agent_permissions = self.permissions.get(agent_name, {})

        print("\n📋 Solicitud de Permisos para Lilith CLI")
        print("=" * 50)
        print("El agente requiere los siguientes permisos para funcionar:")
        print()

        # Mostrar permisos organizados por categoría
        categories = {}
        for permission_name, permission_info in agent_permissions.items():
            category = permission_info.get("category", "General")
            if category not in categories:
                categories[category] = []
            categories[category].append(permission_name)

        for category, permissions in categories.items():
            print(f"📁 Categoría: {category}")
            for permission_name in permissions:
                info = agent_permissions[permission_name]
                status = "✅" if info["allowed"] else "❌"
                level = info.get("level", "medium").upper()

                print(f"   {status} {permission_name}")
                print(f"      Descripción: {info['description']}")
                print(f"      Alcance: {info['scope']}")
                print(f"      Nivel de riesgo: {level}")
                print()

        print("🔐 Verificación por Código")
        print("=" * 50)

        # Generar y enviar código de verificación
        self.generate_verification_code()
        print(f"Código de verificación enviado a: {self.get_user_email()}")
        print("Por favor, ingresa el código para confirmar tu consentimiento.")

        # Solicitar código al usuario
        user_input = input("Código de verificación: ").strip()

        if self.validate_verification_code(user_input):
            # Obtener consentimiento para cada permiso
            print("\n✅ Verificación completada!")
            print("\n📝 Aceptación de Permisos")
            print("=" * 50)

            all_accepted = True

            for permission_name, permission_info in agent_permissions.items():
                print(f"\n🔍 {permission_name}")
                print(f"   Descripción: {permission_info['description']}")
                print(f"   Alcance: {permission_info['scope']}")

                accept = input("Aceptar permiso? (S/N): ").strip().lower()

                if accept in {"s", "si"}:
                    permission_info["allowed"] = True
                    logger.info("Permiso %s aceptado", permission_name)
                else:
                    permission_info["allowed"] = False
                    logger.warning("Permiso %s rechazado", permission_name)
                    all_accepted = False

            # Guardar permisos
            self.save_permissions()
            logger.info("Permisos guardados: agent_permissions.json")

            print("\n🎉 Permisos configurados correctamente!")
            return all_accepted
        else:
            print("❌ Código de verificación incorrecto")
            return False

    def get_user_email(self):
        """Obtiene el correo electrónico del usuario (simulación)"""
        return "usuario@ejemplo.com"

    def save_permissions(self):
        """Guarda los permisos en archivo"""
        with open("agent_permissions.json", "w", encoding="utf-8") as f:
            json.dump(self.permissions, f, indent=2, ensure_ascii=False)

    def check_permission(self, agent_name: str, permission: str) -> bool:
        """Verifica si un permiso está autorizado para un agente"""
        agent = self.permissions.get(agent_name, {})

        if agent.get(permission, {}).get("allowed", False):
            return True

        logger.warning("Permiso %s no autorizado para %s", permission, agent_name)
        return False

    def log_permission_usage(self, agent_name: str, permission: str, context: dict):
        """Registra el uso de permisos"""
        log_entry = {
            "timestamp": time.time(),
            "agent": agent_name,
            "permission": permission,
            "context": context,
            "success": True,
        }

        log_path = Path("permission_usage.log")
        if log_path.exists():
            with open(log_path) as f:
                log_entries = json.load(f)
        else:
            log_entries = []

        log_entries.append(log_entry)

        with open(log_path, "w") as f:
            json.dump(log_entries, f, indent=2, ensure_ascii=False)

        logger.info("Uso de permiso %s registrado", permission)

    def generate_permission_report(self):
        """Genera un informe de permisos"""
        report = {
            "agent": "Lilith CLI",
            "timestamp": time.time(),
            "total_permissions": len(self.permissions["Lilith CLI"]),
            "permissions": [],
            "usage_statistics": self.get_usage_statistics(),
            "security_level": self.calculate_security_level(),
        }

        for permission_name, permission_info in self.permissions["Lilith CLI"].items():
            report["permissions"].append(
                {
                    "name": permission_name,
                    "status": "Authorized" if permission_info["allowed"] else "Denied",
                    "description": permission_info["description"],
                    "scope": permission_info["scope"],
                    "level": permission_info.get("level", "medium"),
                }
            )

        with open("permission_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("Informe de permisos generado: permission_report.json")
        return report

    def get_usage_statistics(self):
        """Obtiene estadísticas de uso de permisos"""
        log_path = Path("permission_usage.log")

        if not log_path.exists():
            return {"total_usages": 0, "permissions_used": []}

        with open(log_path) as f:
            log_entries = json.load(f)

        permissions_used = {}
        for entry in log_entries:
            permission = entry["permission"]
            if permission not in permissions_used:
                permissions_used[permission] = 0
            permissions_used[permission] += 1

        return {
            "total_usages": len(log_entries),
            "permissions_used": [
                {"name": name, "count": count} for name, count in permissions_used.items()
            ],
        }

    def calculate_security_level(self):
        """Calcula el nivel de seguridad basado en permisos"""
        high_risk_permissions = 0
        medium_risk_permissions = 0
        low_risk_permissions = 0

        for permission_info in self.permissions["Lilith CLI"].values():
            level = permission_info.get("level", "medium")

            if permission_info["allowed"]:
                if level == "high":
                    high_risk_permissions += 1
                elif level == "medium":
                    medium_risk_permissions += 1
                else:
                    low_risk_permissions += 1

        high_risk_permissions + medium_risk_permissions + low_risk_permissions

        if high_risk_permissions > 2:
            return "High Risk"
        elif high_risk_permissions > 0:
            return "Medium Risk"
        else:
            return "Low Risk"


def main():
    """Función principal para la configuración de permisos"""
    logger.info("Iniciando configuración de permisos para Lilith CLI...")

    permission_system = PermissionSystem()

    # Solicitar consentimiento al usuario
    if not permission_system.request_consent("Lilith CLI"):
        logger.error("Consentimiento no proporcionado")
        sys.exit(1)

    # Generar reporte de permisos
    report = permission_system.generate_permission_report()

    print("\n📊 Informe de Permisos")
    print("=" * 50)
    print(f"🤖 Agente: {report['agent']}")
    print(f"📦 Total de permisos: {report['total_permissions']}")
    print(f"🔒 Nivel de seguridad: {report['security_level']}")
    print(f"📈 Uso total: {report['usage_statistics']['total_usages']}")
    print()

    print("📝 Permisos Autorizados:")
    print("-" * 50)
    for permission in report["permissions"]:
        if permission["status"] == "Authorized":
            print(f"✅ {permission['name']}")
            print(f"   Descripción: {permission['description']}")
            print(f"   Alcance: {permission['scope']}")
            print(f"   Nivel de riesgo: {permission['level']}")
            print()

    if report["usage_statistics"]["permissions_used"]:
        print("📊 Estadísticas de Uso:")
        print("-" * 50)
        for usage in report["usage_statistics"]["permissions_used"]:
            print(f"📈 {usage['name']}: {usage['count']} usos")

    logger.info("Configuración de permisos completada")
    return True


if __name__ == "__main__":
    main()
