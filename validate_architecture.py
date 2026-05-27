#!/usr/bin/env python3
"""
Valida la Arquitectura de Yggdrasil post-Transformación
"""

import json
import logging
import sys
from pathlib import Path

import requests


# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ArchitectureValidator:
    """Valida la arquitectura de Yggdrasil"""

    def __init__(self):
        self.manifest = self.load_manifest()
        self.config = self.load_config()
        self.validation_results = {
            "modules": [],
            "services": [],
            "agents": [],
            "permissions": [],
            "communication": [],
            "security": []
        }

    def load_manifest(self):
        """Carga el manifesto de la arquitectura"""
        manifest_path = Path("yggdrasil_manifest.json")

        if manifest_path.exists():
            with open(manifest_path, encoding='utf-8') as f:
                return json.load(f)

        raise FileNotFoundError("Manifesto de arquitectura no encontrado")

    def load_config(self):
        """Carga la configuración del sistema"""
        config_path = Path(".env")

        if config_path.exists():
            config = {}

            with open(config_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()

            return config

        raise FileNotFoundError("Archivo de configuración .env no encontrado")

    def validate_modules(self):
        """Valida la disponibilidad y compatibilidad de los módulos"""
        logger.info("Validando módulos...")

        for module in self.manifest["modules"]:
            module_result = {
                "name": module["name"],
                "version": module["version"],
                "status": "OK" if self.validate_module(module) else "ERROR",
                "errors": []
            }

            if not self.validate_module(module):
                module_result["errors"].append(f"Module {module['name']} not found or incompatible")

            self.validation_results["modules"].append(module_result)

        logger.info(f"{sum(1 for m in self.validation_results['modules'] if m['status'] == 'OK')} modules validated successfully")

    def validate_module(self, module: dict) -> bool:
        """Valida un módulo individual"""
        module_path = Path(module["path"])

        if not module_path.exists():
            logger.error(f"Module path {module['path']} not found")
            return False

        # Validar presencia de pyproject.toml
        pyproject_path = module_path / "pyproject.toml"
        if not pyproject_path.exists():
            logger.warning(f"pyproject.toml not found for module {module['name']}")

        # Validar estructura básica
        src_path = module_path / module["name"].replace("-", "_")
        if not src_path.exists() or not src_path.is_dir():
            logger.warning(f"Source directory not found for module {module['name']}")

        return True

    def validate_services(self):
        """Valida la disponibilidad de los servicios"""
        logger.info("Validando servicios...")

        for service in self.manifest["services"]:
            service_result = {
                "name": service["name"],
                "port": service["port"],
                "status": "OK" if self.validate_service(service) else "ERROR",
                "errors": []
            }

            if not self.validate_service(service):
                service_result["errors"].append(f"Service {service['name']} not reachable")

            self.validation_results["services"].append(service_result)

        logger.info(f"{sum(1 for s in self.validation_results['services'] if s['status'] == 'OK')} services validated successfully")

    def validate_service(self, service: dict) -> bool:
        """Valida un servicio individual"""
        try:
            response = requests.get(f"http://localhost:{service['port']}/health", timeout=5)
            return response.status_code == 200
        except:
            logger.warning(f"Service {service['name']} on port {service['port']} not reachable")
            return False

    def validate_agents(self):
        """Valida la integración de agentes"""
        logger.info("Validando agentes...")

        for agent in self.manifest["agents"]:
            agent_result = {
                "name": agent["name"],
                "version": agent["version"],
                "status": "OK" if self.validate_agent(agent) else "ERROR",
                "errors": []
            }

            if not self.validate_agent(agent):
                agent_result["errors"].append(f"Agent {agent['name']} not reachable")

            self.validation_results["agents"].append(agent_result)

        logger.info(f"{sum(1 for a in self.validation_results['agents'] if a['status'] == 'OK')} agents validated successfully")

    def validate_agent(self, agent: dict) -> bool:
        """Valida un agente individual"""
        agent_path = Path(agent["path"])

        if not agent_path.exists():
            logger.error(f"Agent path {agent['path']} not found")
            return False

        if not agent_path.is_file() or not agent_path.suffix == '.py':
            logger.error(f"Agent {agent['name']} is not a valid Python file")
            return False

        return True

    def validate_permissions(self):
        """Valida la configuración de permisos"""
        logger.info("Validando permisos...")

        permissions_result = {
            "status": "OK" if self.validate_permission_system() else "ERROR",
            "errors": [],
            "total_permissions": self.count_permissions()
        }

        if not self.validate_permission_system():
            permissions_result["errors"].append("Permission system configuration error")

        self.validation_results["permissions"].append(permissions_result)

    def validate_permission_system(self) -> bool:
        """Valida el sistema de permisos"""
        permissions_path = Path("agent_permissions.json")

        if not permissions_path.exists():
            logger.error("Permission configuration file not found")
            return False

        with open(permissions_path, encoding='utf-8') as f:
            permissions = json.load(f)

        if "Lilith CLI" not in permissions:
            logger.error("Lilith CLI permissions not configured")
            return False

        return True

    def count_permissions(self) -> int:
        """Cuenta el número de permisos configurados"""
        permissions_path = Path("agent_permissions.json")

        if not permissions_path.exists():
            return 0

        with open(permissions_path, encoding='utf-8') as f:
            permissions = json.load(f)

        return len(permissions.get("Lilith CLI", {}))

    def validate_communication(self):
        """Valida los canales de comunicación"""
        logger.info("Validando canales de comunicación...")

        communication_result = {
            "channels": len(self.manifest["communication_channels"]),
            "optimizations": self.validate_data_transmission(),
            "errors": []
        }

        if not self.validate_data_transmission():
            communication_result["errors"].append("Data transmission optimizations not configured")

        self.validation_results["communication"].append(communication_result)

    def validate_data_transmission(self) -> bool:
        """Valida la optimización de transmisión de datos"""
        return self.manifest["data_transmission"]["compression"]["enabled"] and \
               self.manifest["data_transmission"]["caching"]["enabled"] and \
               self.manifest["data_transmission"]["batching"]["enabled"]

    def validate_security(self):
        """Valida la seguridad de la arquitectura"""
        logger.info("Validando seguridad...")

        try:
            security_result = {
                "security_level": self.get_security_level(),
                "risk_permissions": self.get_risk_permissions(),
                "blocked_commands": self.get_blocked_commands(),
                "errors": []
            }

            self.validation_results["security"].append(security_result)

        except Exception as e:
            logger.error(f"Error en validación de seguridad: {e!s}")
            security_result = {
                "security_level": "Unknown",
                "risk_permissions": [],
                "blocked_commands": [],
                "errors": [str(e)]
            }

            self.validation_results["security"].append(security_result)

    def get_security_level(self) -> str:
        """Obtiene el nivel de seguridad"""
        permissions_path = Path("agent_permissions.json")

        if not permissions_path.exists():
            return "High Risk"

        with open(permissions_path, encoding='utf-8') as f:
            permissions = json.load(f)

        high_risk = sum(1 for p in permissions.get("Lilith CLI", {}).values()
                       if p.get("level", "medium") == "high" and p.get("allowed", False))

        if high_risk > 2:
            return "High Risk"
        elif high_risk > 0:
            return "Medium Risk"
        else:
            return "Low Risk"

    def get_risk_permissions(self) -> list[str]:
        """Obtiene permisos de alto riesgo autorizados"""
        permissions_path = Path("agent_permissions.json")

        if not permissions_path.exists():
            return []

        with open(permissions_path, encoding='utf-8') as f:
            permissions = json.load(f)

        return [name for name, info in permissions.get("Lilith CLI", {}).items()
               if info.get("level", "medium") == "high" and info.get("allowed", False)]

    def get_blocked_commands(self) -> list[str]:
        """Obtiene los comandos bloqueados desde .env"""
        blocked_commands = self.config.get("BLOCKED_COMMANDS", "")
        return [cmd.strip() for cmd in blocked_commands.split(',') if cmd.strip()]

    def generate_validation_report(self):
        """Genera un informe de validación completo"""
        report = {
            "architecture": "Yggdrasil v3.0.0",
            "timestamp": self.manifest["timestamp"],
            "validation_time": logger.handlers[0].level,
            "summary": {
                "total_modules": len(self.manifest["modules"]),
                "valid_modules": sum(1 for m in self.validation_results["modules"] if m["status"] == "OK"),
                "total_services": len(self.manifest["services"]),
                "valid_services": sum(1 for s in self.validation_results["services"] if s["status"] == "OK"),
                "total_agents": len(self.manifest["agents"]),
                "valid_agents": sum(1 for a in self.validation_results["agents"] if a["status"] == "OK"),
                "total_permissions": self.count_permissions()
            },
            "results": self.validation_results
        }

        with open("architecture_validation_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("Informe de validación generado: architecture_validation_report.json")
        return report

    def print_validation_summary(self):
        """Imprime un resumen de la validación"""
        report = self.generate_validation_report()

        print("\n📊 Resumen de Validación de Yggdrasil")
        print("=" * 50)

        summary = report["summary"]
        print(f"🔧 Módulos: {summary['valid_modules']}/{summary['total_modules']} válidos")
        print(f"🚀 Servicios: {summary['valid_services']}/{summary['total_services']} accesibles")
        print(f"🤖 Agentes: {summary['valid_agents']}/{summary['total_agents']} disponibles")
        print(f"🔒 Permisos: {summary['total_permissions']} configurados")
        print()

        security = report["results"]["security"][0]
        print(f"🔐 Nivel de seguridad: {security['security_level']}")

        if security["risk_permissions"]:
            print(f"⚠️  Permisos de alto riesgo: {len(security['risk_permissions'])}")
            for perm in security["risk_permissions"]:
                print(f"   - {perm}")

        if security["blocked_commands"]:
            print(f"🚫 Comandos bloqueados: {len(security['blocked_commands'])}")
            for cmd in security["blocked_commands"]:
                print(f"   - {cmd}")

        print()

        if self.is_architecture_healthy():
            print("🎉 Arquitectura de Yggdrasil es válida y operativa!")
        else:
            print("❌ Arquitectura con problemas - revisar reporte detallado")

        print()
        print("📋 Archivos generados:")
        print("   - architecture_validation_report.json (detallado)")
        print("   - validation.log (registro completo)")

    def is_architecture_healthy(self) -> bool:
        """Verifica si la arquitectura es saludable"""
        # Todos los módulos validos, al menos 1 agente válido, sistema de permisos operativo
        valid_modules = sum(1 for m in self.validation_results["modules"] if m["status"] == "OK")
        valid_agents = sum(1 for a in self.validation_results["agents"] if a["status"] == "OK")
        permission_system = len(self.validation_results["permissions"]) > 0 and self.validation_results["permissions"][0]["status"] == "OK"

        return valid_modules == len(self.validation_results["modules"]) and \
               valid_agents > 0 and \
               permission_system

def main():
    """Función principal para la validación"""
    logger.info("Iniciando validación de la arquitectura de Yggdrasil...")

    try:
        validator = ArchitectureValidator()

        # Realizar todas las validaciones
        validator.validate_modules()
        validator.validate_services()
        validator.validate_agents()
        validator.validate_permissions()
        validator.validate_communication()
        validator.validate_security()

        # Imprimir resumen
        validator.print_validation_summary()

        return validator.is_architecture_healthy()

    except Exception as e:
        logger.error(f"Error en la validación: {e!s}")
        print(f"❌ Error: {e!s}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
