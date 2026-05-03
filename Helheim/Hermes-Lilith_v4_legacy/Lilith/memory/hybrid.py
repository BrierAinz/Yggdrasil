"""
Hybrid Memory System
====================
Sistema de memoria híbrido que combina:
1. **Memoria Local** - Archivos JSON/Markdown en disco (episódica, procedural)
2. **Memoria Conversacional** - Integración con Mem0/Zep (semántica)
3. **Memoria de Errores** - Registro de errores y soluciones aprendidas
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class LocalMemory:
    """
    Memoria local usando archivos en disco.
    Incluye:
    - Episodic: Conversaciones pasadas
    - Procedural: Reglas y procedimientos aprendidos
    - Errors: Errores y soluciones
    """

    def __init__(self, base_path: str = "D:/Proyectos/Midgard/Lilith/Memory"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

        self.episodes_file = self.base / "episodes.json"
        self.procedural_file = self.base / "procedural.json"
        self.errors_file = self.base / "errors.json"
        self.facts_file = self.base / "facts.json"

        self._init_files()

    def _init_files(self):
        """Inicializa archivos si no existen."""
        for f in [
            self.episodes_file,
            self.procedural_file,
            self.errors_file,
            self.facts_file,
        ]:
            if not f.exists():
                f.write_text("[]", encoding="utf-8")

    def _read_json(self, filepath: Path) -> List:
        """Lee JSON del archivo."""
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except:
            return []

    def _write_json(self, filepath: Path, data: List):
        """Escribe JSON al archivo."""
        filepath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ─────────────────────────────────────────────────────────────
    # EPISODIC MEMORY (Conversaciones pasadas)
    # ─────────────────────────────────────────────────────────────
    def add_episode(self, user_input: str, response: str, tools_used: List[str] = None):
        """Agrega un episodio de conversación."""
        episodes = self._read_json(self.episodes_file)

        episode = {
            "id": len(episodes) + 1,
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "response": response[:500],  # Limitar tamaño
            "tools_used": tools_used or [],
            "success": True,
        }

        episodes.append(episode)

        # Mantener solo últimos 100 episodios
        if len(episodes) > 100:
            episodes = episodes[-100:]

        self._write_json(self.episodes_file, episodes)
        return episode["id"]

    def get_recent_episodes(self, count: int = 10) -> List[Dict]:
        """Obtiene episodios recientes."""
        episodes = self._read_json(self.episodes_file)
        return episodes[-count:]

    def search_episodes(self, query: str) -> List[Dict]:
        """Busca en episodios."""
        episodes = self._read_json(self.episodes_file)
        query_lower = query.lower()
        return [
            e
            for e in episodes
            if query_lower in e["user_input"].lower()
            or query_lower in e["response"].lower()
        ]

    # ─────────────────────────────────────────────────────────────
    # PROCEDURAL MEMORY (Reglas y procedimientos)
    # ─────────────────────────────────────────────────────────────
    def add_procedure(self, name: str, steps: List[str], description: str = ""):
        """Agrega un procedimiento aprendido."""
        procedures = self._read_json(self.procedural_file)

        procedure = {
            "id": len(procedures) + 1,
            "name": name,
            "description": description,
            "steps": steps,
            "created": datetime.now().isoformat(),
            "times_used": 0,
            "success_rate": 1.0,
        }

        procedures.append(procedure)
        self._write_json(self.procedural_file, procedures)
        return procedure["id"]

    def get_procedure(self, name: str) -> Optional[Dict]:
        """Obtiene un procedimiento por nombre."""
        procedures = self._read_json(self.procedural_file)
        for p in procedures:
            if p["name"].lower() == name.lower():
                return p
        return None

    def list_procedures(self) -> List[Dict]:
        """Lista todos los procedimientos."""
        return self._read_json(self.procedural_file)

    # ─────────────────────────────────────────────────────────────
    # ERROR MEMORY (Errores y soluciones)
    # ─────────────────────────────────────────────────────────────
    def add_error(
        self, error_type: str, error_message: str, solution: str, command: str = ""
    ):
        """Registra un error y su solución."""
        errors = self._read_json(self.errors_file)

        error = {
            "id": len(errors) + 1,
            "type": error_type,
            "message": error_message,
            "solution": solution,
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "times_seen": 1,
        }

        # Verificar si ya existe
        for existing in errors:
            if existing["message"] == error_message:
                existing["times_seen"] += 1
                self._write_json(self.errors_file, errors)
                return existing["id"]

        errors.append(error)
        self._write_json(self.errors_file, errors)
        return error["id"]

    def get_error_solution(self, error_message: str) -> Optional[str]:
        """Busca solución para un error."""
        errors = self._read_json(self.errors_file)
        for e in errors:
            if e["message"] in error_message or error_message in e["message"]:
                return e.get("solution")
        return None

    def list_errors(self) -> List[Dict]:
        """Lista errores registrados."""
        return self._read_json(self.errors_file)

    # ─────────────────────────────────────────────────────────────
    # FACTS (Hechos sobre el usuario y el sistema)
    # ─────────────────────────────────────────────────────────────
    def add_fact(self, category: str, key: str, value: Any, confidence: float = 1.0):
        """Agrega un hecho aprendido."""
        facts = self._read_json(self.facts_file)

        # Verificar si ya existe
        for f in facts:
            if f["category"] == category and f["key"] == key:
                f["value"] = value
                f["confidence"] = confidence
                f["updated"] = datetime.now().isoformat()
                self._write_json(self.facts_file, facts)
                return f["id"]

        fact = {
            "id": len(facts) + 1,
            "category": category,  # "user", "system", "preferences"
            "key": key,
            "value": value,
            "confidence": confidence,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }

        facts.append(fact)
        self._write_json(self.facts_file, facts)
        return fact["id"]

    def get_fact(self, category: str = None, key: str = None) -> List[Dict]:
        """Obtiene hechos por categoría o clave."""
        facts = self._read_json(self.facts_file)
        if category:
            facts = [f for f in facts if f["category"] == category]
        if key:
            facts = [f for f in facts if f["key"] == key]
        return facts

    def get_user_preferences(self) -> Dict[str, Any]:
        """Obtiene todas las preferencias del usuario."""
        facts = self._read_json(self.facts_file)
        return {f["key"]: f["value"] for f in facts if f["category"] == "user"}


class SemanticMemory:
    """
    Memoria semántica usando embedding vectors.
    Para integración futura con Mem0, Zep, o vector DB local.

    Por ahora usa búsqueda por palabras clave con puntuación.
    """

    def __init__(self, base_path: str = "D:/Proyectos/Midgard/Lilith/Memory"):
        self.base = Path(base_path)
        self.vectors_file = self.base / "vectors.json"

        if not self.vectors_file.exists():
            self.vectors_file.write_text("[]", encoding="utf-8")

    def add_memory(self, content: str, metadata: Dict = None):
        """
        Agrega un recuerdo semántico.
        En producción, esto usaría embeddings reales de Mem0/Zep.
        """
        memories = self._read_json()

        memory = {
            "id": len(memories) + 1,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "keywords": self._extract_keywords(content),
        }

        memories.append(memory)
        self._write_json(memories)
        return memory["id"]

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Busca recuerdos relevantes."""
        memories = self._read_json()
        query_words = set(query.lower().split())

        scored = []
        for m in memories:
            score = len(query_words & set(m.get("keywords", [])))
            if score > 0:
                scored.append((score, m))

        scored.sort(reverse=True)
        return [m for _, m in scored[:limit]]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extrae palabras clave del texto."""
        # Palabras comunes a ignorar
        stop_words = {
            "el",
            "la",
            "los",
            "las",
            "un",
            "una",
            "de",
            "en",
            "que",
            "es",
            "y",
            "a",
            "para",
            "por",
        }
        words = text.lower().split()
        return [w for w in words if len(w) > 3 and w not in stop_words]

    def _read_json(self) -> List:
        try:
            return json.loads(self.vectors_file.read_text(encoding="utf-8"))
        except:
            return []

    def _write_json(self, data: List):
        self.vectors_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


class HybridMemory:
    """
    Sistema de memoria híbrido que combina:
    - LocalMemory: Almacenamiento en archivos JSON
    - SemanticMemory: Búsqueda semántica por keywords

    Diseñado para integrarse con:
    - Mem0 (memoria conversacional AI)
    - Zep (memoria a largo plazo)
    - Qdrant/Chroma (vector DB local)
    """

    def __init__(self):
        self.local = LocalMemory()
        self.semantic = SemanticMemory()

    def remember_context(self, user_input: str, response: str, tools_used: List = None):
        """Guarda una interacción completa."""
        # Guardar en memoria episódica
        episode_id = self.local.add_episode(user_input, response, tools_used)

        # Guardar en memoria semántica para búsqueda futura
        self.semantic.add_memory(
            content=f"Usuario preguntó: {user_input}. LILITH respondió: {response}",
            metadata={
                "type": "conversation",
                "episode_id": episode_id,
                "tools_used": tools_used,
            },
        )

        return episode_id

    def learn_from_error(self, error: str, solution: str, context: str = ""):
        """Aprende de un error."""
        self.local.add_error(
            error_type="execution_error",
            error_message=error,
            solution=solution,
            command=context,
        )

        # También guardar en semántica
        self.semantic.add_memory(
            content=f"Error solucionado: {error}. Solución: {solution}. Contexto: {context}",
            metadata={"type": "error_solution"},
        )

    def learn_preference(self, key: str, value: Any, category: str = "user"):
        """Aprende preferencia del usuario."""
        self.local.add_fact(category, key, value)

        # Guardar en semántica
        self.semantic.add_memory(
            content=f"Preferencia del usuario: {key} = {value}",
            metadata={"type": "preference", "category": category},
        )

    def get_context_for_prompt(self, current_task: str = "") -> str:
        """
        Genera contexto para agregar al prompt del modelo.
        Combina:
        - Hechos sobre el usuario
        - Procedimientos relevantes
        - Episodios recientes
        - Errores conocidos
        """
        context_parts = []

        # 1. Preferencias del usuario
        prefs = self.local.get_user_preferences()
        if prefs:
            context_parts.append("PREFERENCIAS DEL USUARIO:")
            for k, v in prefs.items():
                context_parts.append(f"  - {k}: {v}")

        # 2. Procedimientos relevantes
        if current_task:
            procedure = self.local.get_procedure(current_task)
            if procedure:
                context_parts.append(f"\nPROCEDIMIENTO PARA '{procedure['name']}':")
                for i, step in enumerate(procedure["steps"], 1):
                    context_parts.append(f"  {i}. {step}")

        # 3. Episodios recientes
        episodes = self.local.get_recent_episodes(3)
        if episodes:
            context_parts.append("\nCONVERSACIONES PREVIAS:")
            for ep in episodes:
                context_parts.append(f"  - Usuario: {ep['user_input'][:50]}...")

        # 4. Errores conocidos relacionados
        if current_task:
            errors = self.local.list_errors()
            related = [
                e
                for e in errors[-5:]
                if current_task.lower() in e.get("message", "").lower()
            ]
            if related:
                context_parts.append("\nERRORES CONOCIDOS:")
                for e in related:
                    context_parts.append(
                        f"  - {e['message'][:50]}... -> {e.get('solution', 'N/A')[:50]}..."
                    )

        return "\n".join(context_parts) if context_parts else ""

    def get_full_history(self) -> List[Dict]:
        """Obtiene historial completo de conversaciones."""
        return self.local.get_recent_episodes(50)

    def get_stats(self) -> Dict:
        """Obtiene estadísticas de la memoria."""
        return {
            "episodes": len(self.local._read_json(self.local.episodes_file)),
            "procedures": len(self.local._read_json(self.local.procedural_file)),
            "errors": len(self.local._read_json(self.local.errors_file)),
            "facts": len(self.local._read_json(self.local.facts_file)),
            "semantic_memories": len(self.semantic._read_json()),
        }


# Instancia global
_hybrid_memory: Optional[HybridMemory] = None


def get_hybrid_memory() -> HybridMemory:
    """Obtiene la instancia global de memoria híbrida."""
    global _hybrid_memory
    if _hybrid_memory is None:
        _hybrid_memory = HybridMemory()
    return _hybrid_memory
