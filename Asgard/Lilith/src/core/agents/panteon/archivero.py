"""
ArchiveroAgent - Especialista en documentación técnica del ecosistema Lilith.
Reside en Svartalfheim (Biblioteca Técnica).
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.core.agents.base import BaseAgent
from src.core.memory.muninn_memory import MuninnMemory


class ArchiveroAgent(BaseAgent):
    """
    Archivero de Yggdrasil - Guardián de la Biblioteca Técnica en Svartalfheim.

    Especialidad: Documentación técnica del ecosistema Lilith
    - Arquitectura y diseño
    - Documentación histórica (Legacy)
    - Decisiones arquitectónicas
    - Procedimientos y playbooks

    Capacidades:
    - Consulta semántica a Knowledge Base (MuninnDB vault "docs")
    - Respuestas con citas de fuentes
    - Diferenciación entre docs actuales (00-17) y legacy
    """

    name: str = "Archivero"
    description: str = "Especialista en documentación técnica de Yggdrasil"

    def __init__(self):
        super().__init__()
        # Usar vault "docs" dedicado para documentación
        self.muninn_docs = MuninnMemory(
            base_path=Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core"),
            vault_name="docs",
        )
        self.top_k = 5  # Chunks a recuperar

    def get_system_prompt(self) -> str:
        return """Eres el Archivero de Yggdrasil, guardián de la Biblioteca Técnica en Svartalfheim.

Tu especialidad es la documentación del ecosistema Lilith:
- Arquitectura del sistema (Backend, Frontend, Agentes)
- Sistemas centrales (Memoria, Tools, Orquestador)
- Documentación histórica (Cortana → Lilith, Legacy)
- Decisiones arquitectónicas y patrones
- Procedimientos y playbooks

REGLAS:
1. Siempre cita la fuente (nombre del documento) al final de tu respuesta
2. Si no sabes algo con certeza, admítelo y sugiere dónde buscar
3. Usa ejemplos de código cuando sea relevante
4. Mantén respuestas concisas pero completas
5. Diferencia entre:
   - Docs actuales (00-17): documentación vigente
   - Legacy: documentación histórica/archivada
   - El Inicio del Todo: historia del proyecto (docs 18-21)

FORMATO DE RESPUESTA:
[Respuesta clara y directa en markdown]

---
[FUENTES]
- [Nombre del documento] (categoría: current/legacy/historical)
"""

    async def execute(self, task: str, context: str = "") -> str:
        """
        Ejecuta consulta a la Knowledge Base.

        Args:
            task: Pregunta sobre documentación
            context: Contexto adicional (opcional)

        Returns:
            Respuesta con fuentes citadas
        """
        # Construir query enriquecida
        query = task
        if context:
            query = f"{context}\n\nPregunta: {task}"

        # 1. Recuperar chunks relevantes
        results = await self._retrieve_chunks(query)

        if not results:
            return """No encontré información relevante en la Biblioteca Técnica.

Sugerencias:
- Reformula tu pregunta con términos más específicos
- Verifica que estás usando la nomenclatura correcta de Lilith
- Consulta el índice en /api/docs/index"""

        # 2. Construir contexto para LLM
        context_blocks = []
        sources = []

        for i, result in enumerate(results, 1):
            concept = result.get("concept", "N/A")
            content = result.get("content", "")
            tags = result.get("tags", [])

            # Extraer categoría de tags
            category = "unknown"
            for tag in tags:
                if tag.startswith("category:"):
                    category = tag.split(":")[1]
                    break

            # Extraer nombre de documento
            doc_name = concept.split(":")[0] if ":" in concept else concept

            context_blocks.append(
                f"""--- FRAGMENTO {i} ---
Documento: {doc_name}
Sección: {concept}
Categoría: {category}

{content[:800]}
"""
            )

            sources.append(
                {
                    "doc": doc_name,
                    "concept": concept,
                    "category": category,
                    "score": result.get("score", 0),
                }
            )

        retrieved_context = "\n\n".join(context_blocks)

        # 3. Generar respuesta con LLM (Kimi)
        from src.llm.kimi_client import KimiClient

        client = KimiClient()

        prompt = f"""Pregunta del usuario: {task}

Información recuperada de la Biblioteca Técnica:
{retrieved_context}

Instrucciones:
1. Responde la pregunta usando la información proporcionada
2. Sé conciso pero completo
3. Si hay código relevante, inclúyelo
4. Al final, lista las fuentes consultadas

Responde en español."""

        try:
            # KimiClient no tiene chat_completion(), usar generate_text()
            response = await asyncio.to_thread(
                client.generate_text,
                prompt=prompt,
                system_prompt=self.get_system_prompt(),
                max_tokens=1500,
            )
        except Exception as e:
            response = f"[Error generando respuesta: {e}]\n\nBasándome en la información recuperada:\n\n"
            # Fallback: mostrar contenido directo
            response += "\n\n".join([f"- {s['concept']}" for s in sources[:3]])

        # 4. Agregar sección de fuentes si no la incluyó el LLM
        if "📚 Fuentes:" not in response and "---" not in response[-500:]:
            response += "\n\n---\n📚 Fuentes consultadas:\n"
            for src in sources[:3]:
                cat_marker = {
                    "current": "[ACTUAL]",
                    "legacy": "[LEGACY]",
                    "historical": "[HIST]",
                }.get(src["category"], "[DOC]")
                response += f"- {cat_marker} [{src['doc']}] ({src['category']})\n"

        return response

    async def _retrieve_chunks(self, query: str) -> List[Dict]:
        """
        Recupera chunks relevantes de MuninnDB.

        Args:
            query: Consulta de búsqueda

        Returns:
            Lista de resultados
        """
        try:
            results = await self.muninn_docs.activate(
                context=query, vault="docs", max_results=self.top_k, log_why=False
            )
            return results
        except Exception as e:
            print(f"[Archivero] Error retrieving chunks: {e}")
            return []

    async def query_with_metadata(self, question: str) -> Dict:
        """
        Consulta con metadata completa para API.

        Returns:
            Dict con answer, sources, confidence
        """
        results = await self._retrieve_chunks(question)

        if not results:
            return {
                "answer": "No se encontró información relevante.",
                "sources": [],
                "confidence": 0.0,
            }

        # Calcular confianza basada en scores
        scores = [r.get("score", 0) for r in results if r.get("score")]
        confidence = sum(scores) / len(scores) if scores else 0.5

        # Generar respuesta
        answer = await self.execute(question)

        # Extraer fuentes
        sources = []
        for r in results:
            concept = r.get("concept", "")
            doc_name = concept.split(":")[0] if ":" in concept else concept
            if doc_name not in [s["doc"] for s in sources]:
                sources.append({"doc": doc_name, "score": r.get("score", 0)})

        return {
            "answer": answer,
            "sources": [s["doc"] for s in sources],
            "confidence": min(confidence, 1.0),
        }
