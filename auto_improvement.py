#!/usr/bin/env python3
"""
AutoImprovement - Sistema de automejora inteligente para Yggdrasil
Autor: BrierAinz
Fecha: 2026-05-26
Descripción: Analiza conversaciones para identificar oportunidades de mejora
"""

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from lilith_memory.store import MemoryStore


class AutoImprovement:
    """Clase para la automejora inteligente de Yggdrasil"""

    def __init__(self, project_dir: str | None = None):
        """
        Inicializar el AutoImprovement

        Args:
            project_dir: Directorio raíz del proyecto
        """
        if project_dir is None:
            project_dir = "/mnt/d/Proyectos/Yggdrasil"

        self.project_dir = Path(project_dir)
        self.memory_path = self.project_dir / "chat_memory.db"

        # Inicializar memoria
        self.memory = MemoryStore(self.memory_path)

        # Tipos de mejora que se pueden identificar
        self.improvement_patterns = {
            "bug_report": [
                r"(error|bug|problema|fallo|no funciona|no me funciona)",
                r"(no responde|no se conecta|se cae|se bloquea)",
                r"(crash|crash|se cierra abruptamente)",
            ],
            "feature_request": [
                r"(necesito|quiero|me gustaría|me encantaría)",
                r"(agregar|añadir|crear|implementar)",
                r"(¿puedes|¿podrías|¿sería posible)",
            ],
            "optimization": [
                r"(lento|lenta|poco rapido|poco eficiente)",
                r"(mejorar|optimizar|acelerar|refactorizar)",
                r"(consume demasiado|usa mucho)",
            ],
            "documentation": [
                r"(no entiendo|no sé cómo|no se explica|falta)",
                r"(documentación|manual|guía|tutorial)",
                r"(ejemplo|ejemplo de|ejemplo cómo)",
            ],
            "ux_improvement": [
                r"(difícil|complicado|incomodo|no intuitivo)",
                r"(interfaz|ux|ui|interface)",
                r"(mejorar la experiencia|hacer más fácil)",
            ],
        }

    def analyze_conversations(self, limit: int = 100) -> list[dict]:
        """
        Analizar conversaciones para identificar oportunidades de mejora

        Args:
            limit: Número máximo de conversaciones a analizar

        Returns:
            Lista de mejoras identificadas
        """
        print("🔍 Analizando conversaciones para identificar oportunidades de mejora...")

        recent = self.memory.recent(limit=limit)
        improvements = []

        for entry in recent:
            content = entry.get("content", "").lower()

            # Verificar cada patrón de mejora
            for improvement_type, patterns in self.improvement_patterns.items():
                matches = []

                for pattern in patterns:
                    if re.search(pattern, content):
                        matches.append(pattern)

                if matches:
                    improvement = {
                        "type": improvement_type,
                        "content": entry.get("content", ""),
                        "timestamp": entry.get("timestamp", 0),
                        "patterns": matches,
                        "id": entry.get("id", None),
                    }
                    improvements.append(improvement)

        print(f"✅ Identificadas {len(improvements)} oportunidades de mejora")
        return improvements

    def prioritize_improvements(self, improvements: list[dict]) -> list[dict]:
        """
        Priorizar las mejoras según su impacto

        Args:
            improvements: Lista de mejoras identificadas

        Returns:
            Lista de mejoras priorizadas
        """
        print("📊 Priorizando mejoras...")

        # Pesos por tipo de mejora
        type_weights = {
            "bug_report": 10,  # Muy alto impacto
            "feature_request": 5,  # Medio impacto
            "optimization": 7,  # Alto impacto
            "documentation": 3,  # Bajo impacto
            "ux_improvement": 6,  # Alto impacto
        }

        # Calcular prioridad para cada mejora
        for improvement in improvements:
            # Peso por tipo de mejora
            type_weight = type_weights.get(improvement["type"], 1)

            # Peso por antigüedad (más reciente = más importante)
            age_weight = (
                1 + (time.time() - improvement["timestamp"]) / 3600 / 24
            )  # Descuento por día

            # Peso por número de patrones que coinciden
            pattern_weight = len(improvement["patterns"])

            # Calcular prioridad total
            improvement["priority_score"] = type_weight * pattern_weight / age_weight

        # Ordenar por prioridad (descendente)
        prioritized = sorted(improvements, key=lambda x: x["priority_score"], reverse=True)

        # Asignar nivel de prioridad
        for i, improvement in enumerate(prioritized):
            if i == 0:
                improvement["priority"] = "ALTA"
            elif i < 3:
                improvement["priority"] = "MEDIA"
            else:
                improvement["priority"] = "BAJA"

        print(f"✅ Mejoras priorizadas: {len(prioritized)}")
        return prioritized

    def generate_improvement_report(self, improvements: list[dict]) -> dict:
        """
        Generar un informe de mejoras

        Args:
            improvements: Lista de mejoras priorizadas

        Returns:
            Diccionario con el informe
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_improvements": len(improvements),
            "by_type": {},
            "by_priority": {},
            "top_3": [],
        }

        # Contar por tipo
        for improvement in improvements:
            if improvement["type"] not in report["by_type"]:
                report["by_type"][improvement["type"]] = 0
            report["by_type"][improvement["type"]] += 1

        # Contar por prioridad
        for improvement in improvements:
            if improvement["priority"] not in report["by_priority"]:
                report["by_priority"][improvement["priority"]] = 0
            report["by_priority"][improvement["priority"]] += 1

        # Mejoras top 3
        report["top_3"] = improvements[:3]

        return report

    def save_improvement_report(self, report: dict, output_path: str | None = None) -> str:
        """
        Guardar el informe de mejoras en un archivo

        Args:
            report: Informe de mejoras
            output_path: Ruta del archivo de salida

        Returns:
            Ruta del archivo guardado
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(self.project_dir / f"autoimprovement_report_{timestamp}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"✅ Informe de mejoras guardado: {output_path}")
        return output_path

    def apply_automated_improvements(self, improvements: list[dict]) -> list[dict]:
        """
        Aplicar mejoras automáticas cuando sea posible

        Args:
            improvements: Lista de mejoras priorizadas

        Returns:
            Lista de mejoras aplicadas
        """
        print("🔄 Aplicando mejoras automáticas...")

        applied_improvements = []

        for improvement in improvements:
            try:
                if improvement["type"] == "bug_report":
                    applied = self._handle_bug_report(improvement)
                elif improvement["type"] == "feature_request":
                    applied = self._handle_feature_request(improvement)
                elif improvement["type"] == "optimization":
                    applied = self._handle_optimization(improvement)
                elif improvement["type"] == "documentation":
                    applied = self._handle_documentation(improvement)
                elif improvement["type"] == "ux_improvement":
                    applied = self._handle_ux_improvement(improvement)
                else:
                    applied = False

                if applied:
                    applied_improvements.append(improvement)
                    print(f"✅ Mejora aplicada: {improvement['type']}")
                else:
                    print(f"⚠️  Mejora no aplicable automáticamente: {improvement['type']}")

            except Exception as e:
                print(f"❌ Error al aplicar mejora: {e}")

        print(f"\n✅ Total de mejoras aplicadas automáticamente: {len(applied_improvements)}")
        return applied_improvements

    def _handle_bug_report(self, improvement: dict) -> bool:
        """
        Manejar un reporte de bug

        Args:
            improvement: Datos del bug report

        Returns:
            True si se aplicó la mejora, False en caso contrario
        """
        # Búsqueda simple de bugs comunes
        content = improvement["content"].lower()

        if any(keyword in content for keyword in ["no funciona", "no me funciona", "no responde"]):
            print("🐛 Bug report - Intentando reiniciar el servicio")

            try:
                # Intentar reiniciar el servicio
                subprocess.run(
                    ["pkill", "-f", "python3.*yggdrasil_cli.py"],
                    capture_output=True,
                )
                return True
            except Exception as e:
                print(f"❌ Error al reiniciar: {e}")

        return False

    def _handle_feature_request(self, improvement: dict) -> bool:
        """
        Manejar una solicitud de función

        Args:
            improvement: Datos de la solicitud

        Returns:
            True si se aplicó la mejora, False en caso contrario
        """
        # Verificar si la función ya existe
        content = improvement["content"].lower()

        if any(keyword in content for keyword in ["agregar", "añadir", "crear"]):
            # Buscar si el skill existe
            keywords = self._extract_keywords(content)

            for category_dir in (self.project_dir / "skills").iterdir():
                if category_dir.is_dir():
                    for skill_file in category_dir.glob("*.md"):
                        try:
                            skill_content = skill_file.read_text(encoding="utf-8")

                            if any(keyword in skill_content.lower() for keyword in keywords):
                                print(f"🎯 Solicitud de función ya existe: {skill_file.stem}")
                                return True
                        except Exception as e:
                            print(f"❌ Error al leer skill: {e}")

        return False

    def _handle_optimization(self, improvement: dict) -> bool:
        """
        Manejar una solicitud de optimización

        Args:
            improvement: Datos de la optimización

        Returns:
            True si se aplicó la mejora, False en caso contrario
        """
        # Optimizaciones básicas
        content = improvement["content"].lower()

        if any(keyword in content for keyword in ["lento", "lenta", "consume demasiado"]):
            print("⚡ Optimizando - Limpiando cache")

            try:
                # Limpiar cache de Python
                cache_dir = self.project_dir / "__pycache__"
                if cache_dir.exists():
                    subprocess.run(
                        ["rm", "-rf", str(cache_dir)],
                        capture_output=True,
                    )

                return True
            except Exception as e:
                print(f"❌ Error al limpiar cache: {e}")

        return False

    def _handle_documentation(self, improvement: dict) -> bool:
        """
        Manejar una solicitud de documentación

        Args:
            improvement: Datos de la documentación

        Returns:
            True si se aplicó la mejora, False en caso contrario
        """
        return False  # Documentación requiere intervención humana

    def _handle_ux_improvement(self, improvement: dict) -> bool:
        """
        Manejar una solicitud de mejora UX

        Args:
            improvement: Datos de la mejora UX

        Returns:
            True si se aplicó la mejora, False en caso contrario
        """
        return False  # Mejoras UX requieren intervención humana

    def _extract_keywords(self, text: str) -> list[str]:
        """
        Extraer palabras clave de un texto

        Args:
            text: Texto para extraer keywords

        Returns:
            Lista de palabras clave
        """
        text = re.sub(r"[^\w\s]", "", text.lower())
        words = text.split()

        stop_words = [
            "el",
            "la",
            "los",
            "las",
            "de",
            "del",
            "a",
            "ante",
            "con",
            "para",
            "por",
            "sin",
            "so",
            "sobre",
            "tras",
            "cuando",
            "donde",
            "como",
            "que",
            "qui",
            "quien",
            "quienes",
        ]

        keywords = []
        for word in words:
            if len(word) > 3 and word not in stop_words:
                if not word.isdigit():
                    keywords.append(word)

        return list(dict.fromkeys(keywords))

    def run_complete_analysis(self) -> dict:
        """
        Ejecutar un análisis completo de automejora

        Returns:
            Informe de la automejora
        """
        print("🔧 Iniciando análisis completo de automejora")
        print("=" * 40)

        # Analizar conversaciones
        improvements = self.analyze_conversations()

        # Priorizar mejoras
        prioritized = self.prioritize_improvements(improvements)

        # Generar informe
        report = self.generate_improvement_report(prioritized)

        # Aplicar mejoras automáticas
        applied = self.apply_automated_improvements(prioritized)

        # Actualizar el informe con las mejoras aplicadas
        report["applied_improvements"] = [
            {"id": i["id"], "type": i["type"], "priority": i["priority"]} for i in applied
        ]

        # Guardar el informe
        self.save_improvement_report(report)

        print("\n✅ Análisis de automejora completado")
        print("=" * 40)

        return report

    def print_simple_report(self, report: dict):
        """
        Imprimir un informe simple en la consola

        Args:
            report: Informe de automejora
        """
        print("📋 Informe de Automejora Yggdrasil")
        print("=" * 40)

        print(f"📅 Fecha: {report['generated_at']}")
        print(f"🔍 Mejoras identificadas: {report['total_improvements']}")
        print(f"✅ Mejoras aplicadas: {len(report.get('applied_improvements', []))}")
        print()

        print("📊 Por tipo de mejora:")
        for improvement_type, count in report.get("by_type", {}).items():
            type_name = self._get_type_name(improvement_type)
            print(f"   • {type_name}: {count}")
        print()

        print("📈 Por prioridad:")
        for priority, count in report.get("by_priority", {}).items():
            print(f"   • {priority}: {count}")
        print()

        print("🎯 Top 3 mejoras más importantes:")
        for i, improvement in enumerate(report.get("top_3", []), 1):
            type_name = self._get_type_name(improvement["type"])
            print(f"   {i}. [{improvement['priority']}] {type_name}")
            print(f"      {improvement['content'][:100]}...")
        print()

    def _get_type_name(self, improvement_type: str) -> str:
        """
        Obtener el nombre legible de un tipo de mejora

        Args:
            improvement_type: Tipo de mejora

        Returns:
            Nombre legible
        """
        type_names = {
            "bug_report": "Reporte de Bug",
            "feature_request": "Solicitud de Función",
            "optimization": "Optimizacion",
            "documentation": "Documentacion",
            "ux_improvement": "Mejora UX",
        }

        return type_names.get(improvement_type, improvement_type)


def main():
    """Función principal para probar el AutoImprovement"""
    print("🔧 AutoImprovement - Yggdrasil")
    print("=" * 40)

    auto_improvement = AutoImprovement()

    while True:
        print("\nOpciones disponibles:")
        print("1. Analizar conversaciones")
        print("2. Ejecutar análisis completo")
        print("3. Ver informe de mejora")
        print("4. Salir")

        choice = input("\nSelecciona una opción: ").strip()

        if choice == "1":
            limit = int(input("Número máximo de conversaciones a analizar (100): ") or "100")
            improvements = auto_improvement.analyze_conversations(limit=limit)

            if improvements:
                print("\nMejoras identificadas:")
                for i, improvement in enumerate(improvements, 1):
                    type_name = auto_improvement._get_type_name(improvement["type"])
                    print(f"{i}. [{type_name}] {improvement['content']}")

        elif choice == "2":
            report = auto_improvement.run_complete_analysis()
            auto_improvement.print_simple_report(report)

        elif choice == "3":
            reports_dir = auto_improvement.project_dir

            # Buscar el último informe
            reports = list(reports_dir.glob("autoimprovement_report_*.json"))

            if reports:
                latest_report = max(reports, key=lambda x: x.stat().st_mtime)

                print(f"\n📄 Leyendo informe: {latest_report.name}")
                with open(latest_report, encoding="utf-8") as f:
                    report = json.load(f)

                auto_improvement.print_simple_report(report)
            else:
                print("\n⚠️  No hay informes de automejora disponibles")

        elif choice == "4":
            print("\n👋 Saliendo del AutoImprovement")
            break

        else:
            print("\n❌ Opción inválida. Por favor, selecciona un número entre 1 y 4.")


if __name__ == "__main__":
    main()
