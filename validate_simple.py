#!/usr/bin/env python3
"""
Validación Simplificada de la Arquitectura de Yggdrasil
"""

import json
import logging
import sys
from pathlib import Path


# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("validation_simple.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class SimpleArchitectureValidator:
    """Validador simplificado de la arquitectura de Yggdrasil"""

    def __init__(self):
        self.manifest = self.load_manifest()

    def load_manifest(self):
        """Carga el manifesto de la arquitectura"""
        manifest_path = Path("yggdrasil_manifest.json")

        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                return json.load(f)

        raise FileNotFoundError("Manifesto de arquitectura no encontrado")

    def validate_modules(self):
        """Valida la disponibilidad de los módulos"""
        logger.info("Validando módulos...")

        valid_modules = []
        invalid_modules = []

        for module in self.manifest["modules"]:
            module_path = Path(module["path"])

            if module_path.exists():
                valid_modules.append(module)
                logger.info(f"✅ Módulo {module['name']} (v{module['version']}) - OK")
            else:
                invalid_modules.append(module)
                logger.error(f"❌ Módulo {module['name']} - Ruta no encontrada: {module['path']}")

        return valid_modules, invalid_modules

    def validate_agents(self):
        """Valida la disponibilidad de agentes"""
        logger.info("Validando agentes...")

        valid_agents = []
        invalid_agents = []

        for agent in self.manifest["agents"]:
            agent_path = Path(agent["path"])

            if agent_path.exists() and agent_path.is_file():
                valid_agents.append(agent)
                logger.info(f"✅ Agente {agent['name']} (v{agent['version']}) - OK")
            else:
                invalid_agents.append(agent)
                logger.error(f"❌ Agente {agent['name']} - Ruta no encontrada: {agent['path']}")

        return valid_agents, invalid_agents

    def validate_permissions(self):
        """Valida la configuración de permisos"""
        logger.info("Validando permisos...")

        permissions_path = Path("agent_permissions.json")

        if permissions_path.exists():
            with open(permissions_path, encoding="utf-8") as f:
                permissions = json.load(f)

            if "Lilith CLI" in permissions:
                logger.info(
                    f"✅ Permisos para Lilith CLI - {len(permissions['Lilith CLI'])} configurados"
                )
                return True
            else:
                logger.error("❌ Permisos para Lilith CLI no configurados")
                return False
        else:
            logger.error("❌ Archivo de permisos no encontrado")
            return False

    def validate_configuration(self):
        """Valida la configuración del sistema"""
        logger.info("Validando configuración...")

        config_path = Path(".env")

        if config_path.exists():
            logger.info("✅ Archivo de configuración - OK")
            return True
        else:
            logger.error("❌ Archivo de configuración .env no encontrado")
            return False

    def generate_summary(self):
        """Genera un resumen de la validación"""
        print("\n📊 Resumen de Validación de Yggdrasil")
        print("=" * 50)

        # Validar módulos
        valid_modules, invalid_modules = self.validate_modules()
        print(f"🔧 Módulos: {len(valid_modules)}/{len(self.manifest['modules'])} válidos")

        if invalid_modules:
            print("\n❌ Módulos inválidos:")
            for module in invalid_modules:
                print(f"   - {module['name']} (v{module['version']})")

        # Validar agentes
        valid_agents, invalid_agents = self.validate_agents()
        print(f"\n🤖 Agentes: {len(valid_agents)}/{len(self.manifest['agents'])} válidos")

        if invalid_agents:
            print("\n❌ Agentes inválidos:")
            for agent in invalid_agents:
                print(f"   - {agent['name']} (v{agent['version']})")

        # Validar permisos
        permissions_valid = self.validate_permissions()
        print(f"\n🔒 Permisos: {'OK' if permissions_valid else 'ERROR'}")

        # Validar configuración
        config_valid = self.validate_configuration()
        print(f"⚙️  Configuración: {'OK' if config_valid else 'ERROR'}")

        # Estado general
        overall_status = (
            "OK"
            if len(invalid_modules) == 0
            and len(invalid_agents) == 0
            and permissions_valid
            and config_valid
            else "ERROR"
        )

        print(f"\n📋 Estado general: {overall_status}")

        if overall_status == "OK":
            print("\n🎉 Arquitectura de Yggdrasil es válida y operativa!")
            print(
                "Nota: Los servicios (API Gateway, Model Orchestrator, Memory Service) se deben iniciar manualmente."
            )
        else:
            print("\n❌ Arquitectura con problemas - revisar errores")

        return overall_status == "OK"


def main():
    """Función principal"""
    logger.info("Iniciando validación simplificada de la arquitectura de Yggdrasil...")

    try:
        validator = SimpleArchitectureValidator()
        success = validator.generate_summary()
        return success

    except Exception as e:
        logger.exception(f"Error en la validación: {e!s}")
        print(f"❌ Error: {e!s}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
