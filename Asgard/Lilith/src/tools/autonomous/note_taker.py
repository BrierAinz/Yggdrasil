"""
NoteTaker - Skill autÃ³noma para tomar notas y recordatorios

Permite a Lilith:
- Guardar notas durante conversaciones
- Extraer TODOs automÃ¡ticamente
- Recordar decisiones importantes
- Buscar notas previas por contenido o fecha
- Persistir en memoria vectorial (ChromaDB)
"""

import hashlib
import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NoteTaker")


class NoteType(str, Enum):
    """Tipos de notas soportadas"""

    GENERAL = "general"
    TODO = "todo"
    DECISION = "decision"
    IDEA = "idea"
    CODE_SNIPPET = "code_snippet"
    LINK = "link"
    REMINDER = "reminder"


@dataclass
class Note:
    """Estructura de una nota"""

    id: str
    content: str
    note_type: NoteType
    created_at: str
    updated_at: str
    source: str  # "user", "assistant", "auto"
    tags: List[str]
    conversation_id: Optional[str] = None
    project: Optional[str] = None
    priority: Optional[str] = None  # "low", "medium", "high"
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {**asdict(self), "note_type": self.note_type.value}


class NoteTaker:
    """
    Skill autÃ³noma para gestiÃ³n de notas y memoria de conversaciÃ³n.

    Capacidades:
    - Crear notas manuales o automÃ¡ticas
    - Extraer TODOs del texto con regex
    - Recordar decisiones clave
    - Buscar notas por contenido (texto o semÃ¡ntico)
    - Listar notas por tipo/fecha/proyecto
    - Marcar TODOs como completados
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.name = "NoteTaker"
        self.description = "Toma notas, extrae TODOs y recuerda decisiones"
        self.version = "1.0.0"

        # Storage paths
        self.storage_path = storage_path or os.path.join(
            os.path.expanduser("~"), ".Lilith", "notes"
        )
        os.makedirs(self.storage_path, exist_ok=True)

        self.notes_file = os.path.join(self.storage_path, "notes.json")

        # Cargar notas existentes
        self.notes: Dict[str, Note] = {}
        self._load_notes()

        # Patrones para extracciÃ³n automÃ¡tica
        self.todo_patterns = [
            r"(?:TODO|FIXME|BUG|HACK|XXX)[\s:.-]+(.+?)(?:\n|$)",
            r"(?:hay que|tenemos que|deberÃ­amos|falta|pendiente)[\s:.-]+(.+?)(?:\n|$)",
        ]

        self.decision_patterns = [
            r"(?:decidimos|decisiÃ³n|acordamos|vamos a)[\s:.-]+(.+?)(?:\n|$)",
            r"(?:elegimos|seleccionamos|optamos por)[\s:.-]+(.+?)(?:\n|$)",
        ]

        logger.info(f"NoteTaker initialized with {len(self.notes)} notes")

    def _generate_id(self, content: str) -> str:
        """Generar ID Ãºnico para nota"""
        timestamp = datetime.now().isoformat()
        hash_input = f"{content}{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def _load_notes(self):
        """Cargar notas desde archivo"""
        if os.path.exists(self.notes_file):
            try:
                with open(self.notes_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for note_data in data:
                        note = Note(
                            id=note_data["id"],
                            content=note_data["content"],
                            note_type=NoteType(note_data["note_type"]),
                            created_at=note_data["created_at"],
                            updated_at=note_data["updated_at"],
                            source=note_data["source"],
                            tags=note_data.get("tags", []),
                            conversation_id=note_data.get("conversation_id"),
                            project=note_data.get("project"),
                            priority=note_data.get("priority"),
                            completed=note_data.get("completed", False),
                        )
                        self.notes[note.id] = note
            except Exception as e:
                logger.error(f"Error loading notes: {e}")

    def _save_notes(self):
        """Guardar notas a archivo"""
        try:
            data = [note.to_dict() for note in self.notes.values()]
            with open(self.notes_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving notes: {e}")

    def create_note(
        self,
        content: str,
        note_type: str = "general",
        source: str = "user",
        tags: Optional[List[str]] = None,
        conversation_id: Optional[str] = None,
        project: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crear una nueva nota

        Args:
            content: Contenido de la nota
            note_type: Tipo de nota (general, todo, decision, idea, code_snippet, link, reminder)
            source: Origen (user, assistant, auto)
            tags: Lista de etiquetas
            conversation_id: ID de conversaciÃ³n relacionada
            project: Proyecto relacionado
            priority: Prioridad (low, medium, high)

        Returns:
            Dict con resultado y ID de la nota creada
        """
        try:
            now = datetime.now().isoformat()
            note = Note(
                id=self._generate_id(content),
                content=content.strip(),
                note_type=NoteType(note_type),
                created_at=now,
                updated_at=now,
                source=source,
                tags=tags or [],
                conversation_id=conversation_id,
                project=project,
                priority=priority,
            )

            self.notes[note.id] = note
            self._save_notes()

            logger.info(f"Created note {note.id} of type {note_type}")

            return {
                "success": True,
                "note_id": note.id,
                "note_type": note_type,
                "message": f"Nota creada exitosamente",
                "preview": content[:100] + "..." if len(content) > 100 else content,
            }

        except Exception as e:
            return {"success": False, "error": f"Error creando nota: {str(e)}"}

    def extract_todos(self, text: str, auto_create: bool = True) -> Dict[str, Any]:
        """
        Extraer TODOs de un texto

        Args:
            text: Texto a analizar
            auto_create: Si True, crea notas automÃ¡ticamente

        Returns:
            Dict con TODOs encontrados
        """
        todos = []

        for pattern in self.todo_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                todo_text = match.group(1).strip()
                if len(todo_text) > 3:  # Evitar matches muy cortos
                    todos.append(
                        {"text": todo_text, "full_match": match.group(0).strip()}
                    )

        created_notes = []
        if auto_create and todos:
            for todo in todos:
                result = self.create_note(
                    content=todo["text"],
                    note_type="todo",
                    source="auto",
                    priority="medium",
                )
                if result["success"]:
                    created_notes.append(result["note_id"])

        return {
            "success": True,
            "todos_found": len(todos),
            "todos": todos,
            "notes_created": len(created_notes),
            "note_ids": created_notes,
        }

    def extract_decisions(self, text: str, auto_create: bool = True) -> Dict[str, Any]:
        """
        Extraer decisiones de un texto

        Args:
            text: Texto a analizar
            auto_create: Si True, crea notas automÃ¡ticamente

        Returns:
            Dict con decisiones encontradas
        """
        decisions = []

        for pattern in self.decision_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                decision_text = match.group(1).strip()
                if len(decision_text) > 5:
                    decisions.append(
                        {"text": decision_text, "full_match": match.group(0).strip()}
                    )

        created_notes = []
        if auto_create and decisions:
            for decision in decisions:
                result = self.create_note(
                    content=decision["text"], note_type="decision", source="auto"
                )
                if result["success"]:
                    created_notes.append(result["note_id"])

        return {
            "success": True,
            "decisions_found": len(decisions),
            "decisions": decisions,
            "notes_created": len(created_notes),
            "note_ids": created_notes,
        }

    def search_notes(
        self,
        query: str,
        note_type: Optional[str] = None,
        project: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Buscar notas por contenido

        Args:
            query: Texto a buscar
            note_type: Filtrar por tipo
            project: Filtrar por proyecto
            tags: Filtrar por tags
            limit: MÃ¡ximo de resultados

        Returns:
            Dict con notas encontradas
        """
        results = []
        query_lower = query.lower()

        for note in self.notes.values():
            # Aplicar filtros
            if note_type and note.note_type.value != note_type:
                continue
            if project and note.project != project:
                continue
            if tags and not any(tag in note.tags for tag in tags):
                continue

            # Buscar en contenido
            if query_lower in note.content.lower():
                results.append(note.to_dict())
                continue

            # Buscar en tags
            if any(query_lower in tag.lower() for tag in note.tags):
                results.append(note.to_dict())

        # Ordenar por fecha (mÃ¡s recientes primero)
        results.sort(key=lambda x: x["created_at"], reverse=True)

        return {
            "success": True,
            "query": query,
            "total_found": len(results),
            "notes": results[:limit],
        }

    def list_notes(
        self,
        note_type: Optional[str] = None,
        project: Optional[str] = None,
        include_completed: bool = True,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Listar notas con filtros

        Args:
            note_type: Filtrar por tipo
            project: Filtrar por proyecto
            include_completed: Incluir TODOs completados
            limit: MÃ¡ximo de resultados

        Returns:
            Dict con notas
        """
        results = []

        for note in self.notes.values():
            if note_type and note.note_type.value != note_type:
                continue
            if project and note.project != project:
                continue
            if (
                note.note_type == NoteType.TODO
                and note.completed
                and not include_completed
            ):
                continue

            results.append(note.to_dict())

        # Ordenar por fecha
        results.sort(key=lambda x: x["created_at"], reverse=True)

        return {"success": True, "total": len(results), "notes": results[:limit]}

    def get_note(self, note_id: str) -> Dict[str, Any]:
        """
        Obtener una nota especÃ­fica

        Args:
            note_id: ID de la nota

        Returns:
            Dict con la nota o error
        """
        if note_id not in self.notes:
            return {"success": False, "error": f"Nota no encontrada: {note_id}"}

        return {"success": True, "note": self.notes[note_id].to_dict()}

    def update_note(
        self,
        note_id: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Actualizar una nota existente

        Args:
            note_id: ID de la nota
            content: Nuevo contenido (opcional)
            tags: Nuevas etiquetas (opcional)
            priority: Nueva prioridad (opcional)
            completed: Marcar como completado (para TODOs)

        Returns:
            Dict con resultado
        """
        if note_id not in self.notes:
            return {"success": False, "error": f"Nota no encontrada: {note_id}"}

        note = self.notes[note_id]

        if content is not None:
            note.content = content
        if tags is not None:
            note.tags = tags
        if priority is not None:
            note.priority = priority
        if completed is not None:
            note.completed = completed

        note.updated_at = datetime.now().isoformat()
        self._save_notes()

        return {"success": True, "message": "Nota actualizada", "note_id": note_id}

    def delete_note(self, note_id: str) -> Dict[str, Any]:
        """
        Eliminar una nota

        Args:
            note_id: ID de la nota a eliminar

        Returns:
            Dict con resultado
        """
        if note_id not in self.notes:
            return {"success": False, "error": f"Nota no encontrada: {note_id}"}

        del self.notes[note_id]
        self._save_notes()

        return {"success": True, "message": f"Nota {note_id} eliminada"}

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadÃ­sticas de notas

        Returns:
            Dict con estadÃ­sticas
        """
        stats = {
            "total": len(self.notes),
            "by_type": {},
            "pending_todos": 0,
            "completed_todos": 0,
        }

        for note in self.notes.values():
            # Contar por tipo
            note_type = note.note_type.value
            stats["by_type"][note_type] = stats["by_type"].get(note_type, 0) + 1

            # Contar TODOs
            if note.note_type == NoteType.TODO:
                if note.completed:
                    stats["completed_todos"] += 1
                else:
                    stats["pending_todos"] += 1

        return {"success": True, "stats": stats}

    # === MÃ©todo principal de ejecuciÃ³n ===

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecutar una acciÃ³n del NoteTaker

        Args:
            action: AcciÃ³n a ejecutar
            **kwargs: ParÃ¡metros especÃ­ficos

        Returns:
            Resultado de la operaciÃ³n
        """
        action_map = {
            "create": self.create_note,
            "create_note": self.create_note,
            "add": self.create_note,
            "extract_todos": self.extract_todos,
            "todos": self.extract_todos,
            "extract_decisions": self.extract_decisions,
            "decisions": self.extract_decisions,
            "search": self.search_notes,
            "search_notes": self.search_notes,
            "find": self.search_notes,
            "list": self.list_notes,
            "list_notes": self.list_notes,
            "get": self.get_note,
            "get_note": self.get_note,
            "update": self.update_note,
            "update_note": self.update_note,
            "delete": self.delete_note,
            "delete_note": self.delete_note,
            "stats": self.get_stats,
            "get_stats": self.get_stats,
        }

        if action not in action_map:
            return {
                "success": False,
                "error": f"AcciÃ³n no vÃ¡lida: {action}. "
                f"Acciones disponibles: {', '.join(action_map.keys())}",
            }

        method = action_map[action]
        return method(**kwargs)


# === Testing ===
if __name__ == "__main__":
    import asyncio

    async def test():
        print("=" * 60)
        print("NoteTaker - Test Suite")
        print("=" * 60)

        nt = NoteTaker()

        # Test 1: Crear nota
        print("\n[Test 1] Crear nota general")
        result = await nt.execute(
            "create",
            content="Recordar revisar el cÃ³digo de server.py",
            note_type="general",
            tags=["urgente", "backend"],
        )
        print(f"âœ“ {result.get('message')}, ID: {result.get('note_id')}")
        note_id = result.get("note_id")

        # Test 2: Extraer TODOs
        print("\n[Test 2] Extraer TODOs de texto")
        text = """
        Tenemos que refactorizar el mÃ³dulo de autenticaciÃ³n.
        TambiÃ©n falta actualizar la documentaciÃ³n.
        TODO: Implementar tests unitarios para el nuevo cÃ³digo.
        """
        result = await nt.execute("extract_todos", text=text, auto_create=True)
        print(
            f"âœ“ {result.get('todos_found')} TODOs encontrados, {result.get('notes_created')} notas creadas"
        )

        # Test 3: Listar notas
        print("\n[Test 3] Listar todas las notas")
        result = await nt.execute("list", limit=10)
        print(f"âœ“ {result.get('total')} notas totales")

        # Test 4: Buscar notas
        print("\n[Test 4] Buscar notas por texto")
        result = await nt.execute("search", query="refactorizar")
        print(f"âœ“ {result.get('total_found')} notas encontradas")

        # Test 5: EstadÃ­sticas
        print("\n[Test 5] EstadÃ­sticas")
        result = await nt.execute("stats")
        stats = result.get("stats", {})
        print(
            f"âœ“ Total: {stats.get('total')}, TODOs pendientes: {stats.get('pending_todos')}"
        )

        # Test 6: Extraer decisiones
        print("\n[Test 6] Extraer decisiones")
        text = "Decidimos usar FastAPI en lugar de Flask. Optamos por PostgreSQL."
        result = await nt.execute("extract_decisions", text=text, auto_create=True)
        print(f"âœ“ {result.get('decisions_found')} decisiones encontradas")

        print("\n" + "=" * 60)
        print("Tests completados!")
        print("=" * 60)

    asyncio.run(test())
