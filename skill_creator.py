#!/usr/bin/env python3
"""
Skill Creator - Sistema de autocreación de skills para Yggdrasil
Autor: BrierAinz
Fecha: 2026-05-26
Descripción: Analiza conversaciones y genera skills automáticamente
"""

import re
from datetime import datetime
from pathlib import Path

from lilith_memory.store import MemoryStore


class SkillCreator:
    """Clase para crear skills automáticamente a partir de conversaciones"""

    def __init__(self, project_dir: str | None = None):
        """
        Inicializar el SkillCreator

        Args:
            project_dir: Directorio raíz del proyecto
        """
        if project_dir is None:
            project_dir = "/mnt/d/Proyectos/Yggdrasil"

        self.project_dir = Path(project_dir)
        self.skills_dir = self.project_dir / "skills"
        self.memory_path = self.project_dir / "chat_memory.db"

        # Crear directorio de skills si no existe
        self.skills_dir.mkdir(exist_ok=True)

        # Inicializar memoria
        self.memory = MemoryStore(self.memory_path)

        # Patrones para identificar posibles skills
        self.skill_patterns = [
            r"cómo.*(hacer|crear|implementar|configurar|instalar)",
            r"(guía|tutorial|pasos|procedimiento) para.*",
            r"(mejorar|optimizar|refactorizar|arreglar)",
            r"(error|bug|problema|fallo).*solucionar",
            r"(ejemplo|ejemplo de|ejemplo cómo).*",
            r"(consejo|recomendación|mejor práctica).*",
        ]

    def analyze_conversations(self, limit: int = 100) -> list[dict]:
        """
        Analizar conversaciones para identificar posibles skills

        Args:
            limit: Número máximo de conversaciones a analizar

        Returns:
            Lista de candidatos a skills
        """
        print("🔍 Analizando conversaciones para identificar posibles skills...")

        recent = self.memory.recent(limit=limit)
        skill_candidates = []

        for entry in recent:
            content = entry.get("content", "").lower()

            # Verificar si el contenido coincide con patrones de skill
            matches = []
            for pattern in self.skill_patterns:
                if re.search(pattern, content):
                    matches.append(pattern)

            if matches:
                candidate = {
                    "content": entry.get("content", ""),
                    "timestamp": entry.get("timestamp", 0),
                    "patterns": matches,
                    "id": entry.get("id", None),
                }
                skill_candidates.append(candidate)

        print(f"✅ Identificados {len(skill_candidates)} candidatos a skills")
        return skill_candidates

    def extract_keywords(self, text: str) -> list[str]:
        """
        Extraer palabras clave de un texto

        Args:
            text: Texto para extraer keywords

        Returns:
            Lista de palabras clave
        """
        # Eliminar símbolos y palabras comunes
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
                # Verificar que no sea un número
                if not word.isdigit():
                    keywords.append(word)

        return list(dict.fromkeys(keywords))  # Eliminar duplicados

    def generate_skill_name(self, content: str) -> str:
        """
        Generar un nombre adecuado para un skill

        Args:
            content: Contenido de la conversación

        Returns:
            Nombre del skill
        """
        # Extraer palabras clave principales
        keywords = self.extract_keywords(content)

        if len(keywords) > 0:
            name = "_".join(keywords[:3])
            return name.lower().replace(" ", "_")
        else:
            return f"skill_{int(datetime.now().timestamp())}"

    def create_skill(self, candidate: dict, category: str = "general") -> str:
        """
        Crear un skill a partir de un candidato

        Args:
            candidate: Datos del candidato a skill
            category: Categoría del skill

        Returns:
            Ruta del archivo creado
        """
        # Generar nombre del skill
        skill_name = self.generate_skill_name(candidate["content"])
        skill_dir = self.skills_dir / category
        skill_dir.mkdir(exist_ok=True)

        skill_path = skill_dir / f"{skill_name}.md"

        # Plantilla de skill
        skill_content = f"""---
name: {skill_name}
category: {category}
description: Skill automáticamente generado desde la conversación
created_at: {datetime.now().isoformat()}
conversacion_id: {candidate["id"]}
keywords: {", ".join(self.extract_keywords(candidate["content"]))}
patterns: {", ".join(list(candidate["patterns"]))}
---

# {skill_name}

## Descripción
{self._clean_skill_content(candidate["content"])}

## Uso
Este skill fue automáticamente generado desde una conversación con Lilith.
Puede ser modificado y amplificado manualmente para mejorar su precisión.

## Ejemplos
- "{self._clean_skill_content(candidate["content"])[:100]}..."

## Patrones de Activación
{", ".join(list(candidate["patterns"]))}
"""

        # Escribir el archivo
        skill_path.write_text(skill_content, encoding="utf-8")
        print(f"✅ Skill creado: {skill_path}")

        return str(skill_path)

    def _clean_skill_content(self, content: str) -> str:
        """
        Limpiar el contenido para el skill

        Args:
            content: Contenido a limpiar

        Returns:
            Contenido limpio
        """
        # Eliminar prefijos como "Usuario: " o "Lilith: "
        content = re.sub(r"^(Usuario|lilith):?\s?", "", content, flags=re.IGNORECASE)

        # Eliminar caracteres especiales
        content = content.strip()

        return content

    def create_skills_from_conversations(
        self, category: str = "general", limit: int = 100
    ) -> list[str]:
        """
        Crear skills automáticamente a partir de conversaciones

        Args:
            category: Categoría para los skills
            limit: Número máximo de conversaciones a analizar

        Returns:
            Lista de rutas de skills creados
        """
        candidates = self.analyze_conversations(limit=limit)
        created_skills = []

        for candidate in candidates:
            try:
                skill_path = self.create_skill(candidate, category=category)
                created_skills.append(skill_path)
            except Exception as e:
                print(f"❌ Error al crear skill: {e}")

        print(f"\n✅ Total de skills creados: {len(created_skills)}")
        return created_skills

    def update_existing_skills(self, limit: int = 50) -> list[str]:
        """
        Actualizar skills existentes con información nueva

        Args:
            limit: Número máximo de conversaciones a analizar

        Returns:
            Lista de skills actualizados
        """
        print("🔄 Actualizando skills existentes...")

        candidates = self.analyze_conversations(limit=limit)
        updated_skills = []

        for candidate in candidates:
            # Buscar skills existentes que coincidan con las keywords
            keywords = self.extract_keywords(candidate["content"])

            for category_dir in self.skills_dir.iterdir():
                if category_dir.is_dir():
                    for skill_file in category_dir.glob("*.md"):
                        try:
                            content = skill_file.read_text(encoding="utf-8")

                            # Verificar si el skill contiene alguna de las keywords
                            if any(keyword in content.lower() for keyword in keywords):
                                # Agregar la nueva información al skill
                                updated_content = self._update_skill_content(content, candidate)
                                skill_file.write_text(updated_content, encoding="utf-8")
                                updated_skills.append(str(skill_file))
                                print(f"✅ Skill actualizado: {skill_file}")
                        except Exception as e:
                            print(f"❌ Error al leer skill {skill_file}: {e}")

        print(f"\n✅ Total de skills actualizados: {len(updated_skills)}")
        return updated_skills

    def _update_skill_content(self, existing_content: str, candidate: dict) -> str:
        """
        Actualizar el contenido de un skill existente

        Args:
            existing_content: Contenido existente
            candidate: Datos del candidato

        Returns:
            Contenido actualizado
        """
        # Agregar la nueva información en la sección de "Ejemplos"
        if "## Ejemplos" in existing_content:
            # Encontrar la posición de la sección de ejemplos
            examples_pos = existing_content.find("## Ejemplos")
            existing_examples = existing_content[examples_pos:].split("\n")[1:]

            # Verificar que el ejemplo no exista ya
            new_example = f'- "{self._clean_skill_content(candidate["content"])[:100]}..."'
            if new_example not in existing_examples:
                updated_content = existing_content.replace(
                    "## Ejemplos", f"## Ejemplos\n{new_example}"
                )
                return updated_content

        return existing_content

    def list_skills(self) -> list[dict]:
        """
        Listar todos los skills disponibles

        Returns:
            Lista de skills con información básica
        """
        skills = []

        for category_dir in self.skills_dir.iterdir():
            if category_dir.is_dir():
                category = category_dir.name

                for skill_file in category_dir.glob("*.md"):
                    try:
                        content = skill_file.read_text(encoding="utf-8")

                        # Extraer metadata del frontmatter
                        metadata = self._extract_frontmatter(content)

                        skills.append(
                            {
                                "name": skill_file.stem,
                                "category": category,
                                "path": str(skill_file),
                                "metadata": metadata,
                            }
                        )

                    except Exception as e:
                        print(f"❌ Error al leer skill {skill_file}: {e}")

        return skills

    def _extract_frontmatter(self, content: str) -> dict:
        """
        Extraer el frontmatter YAML de un archivo Markdown

        Args:
            content: Contenido del archivo

        Returns:
            Diccionario con la metadata
        """
        frontmatter = {}

        if content.startswith("---"):
            end_pos = content.find("---", 3)

            if end_pos != -1:
                yaml_content = content[3:end_pos].strip()

                # Extraer campos simple
                lines = yaml_content.split("\n")
                for line in lines:
                    line = line.strip()

                    if line and ": " in line:
                        key, value = line.split(": ", 1)

                        # Eliminar comillas si existen
                        value = value.strip().strip("\"'")

                        frontmatter[key] = value

        return frontmatter

    def delete_skill(self, skill_name: str) -> bool:
        """
        Eliminar un skill

        Args:
            skill_name: Nombre del skill a eliminar

        Returns:
            True si se eliminó correctamente, False en caso de error
        """
        for category_dir in self.skills_dir.iterdir():
            if category_dir.is_dir():
                skill_path = category_dir / f"{skill_name}.md"

                if skill_path.exists():
                    try:
                        skill_path.unlink()
                        print(f"✅ Skill eliminado: {skill_path}")
                        return True
                    except Exception as e:
                        print(f"❌ Error al eliminar skill: {e}")

        print(f"❌ Skill no encontrado: {skill_name}")
        return False


def main():
    """Función principal para probar el SkillCreator"""
    print("🧠 Skill Creator - Yggdrasil")
    print("=" * 40)

    creator = SkillCreator()

    while True:
        print("\nOpciones disponibles:")
        print("1. Crear skills de conversaciones")
        print("2. Actualizar skills existentes")
        print("3. Listar skills")
        print("4. Eliminar skill")
        print("5. Salir")

        choice = input("\nSelecciona una opción: ").strip()

        if choice == "1":
            category = input("Ingresa la categoría (general): ").strip() or "general"
            limit = int(input("Número máximo de conversaciones a analizar (100): ") or "100")
            creator.create_skills_from_conversations(category=category, limit=limit)

        elif choice == "2":
            limit = int(input("Número máximo de conversaciones a analizar (50): ") or "50")
            creator.update_existing_skills(limit=limit)

        elif choice == "3":
            skills = creator.list_skills()
            print(f"\nTotal de skills: {len(skills)}")

            for skill in skills:
                print(f"\n🔹 {skill['name']} ({skill['category']})")

                if "description" in skill["metadata"]:
                    print(f"   {skill['metadata']['description']}")

                if "keywords" in skill["metadata"]:
                    print(f"   Keywords: {skill['metadata']['keywords']}")

        elif choice == "4":
            skill_name = input("Ingresa el nombre del skill a eliminar: ").strip()
            creator.delete_skill(skill_name)

        elif choice == "5":
            print("\n👋 Saliendo del Skill Creator")
            break

        else:
            print("\n❌ Opción inválida. Por favor, selecciona un número entre 1 y 5.")


if __name__ == "__main__":
    main()
