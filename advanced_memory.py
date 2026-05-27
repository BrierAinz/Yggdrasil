#!/usr/bin/env python3
"""
AdvancedMemory - Sistema de memoria avanzada para Yggdrasil
Autor: BrierAinz
Fecha: 2026-05-26
Descripción: Memoria con embeddings y búsqueda semántica
"""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from lilith_memory.store import MemoryStore


class AdvancedMemoryStore(MemoryStore):
    """Clase para una memoria avanzada con embeddings y búsqueda semántica"""

    def __init__(self, db_path: str = None):
        """
        Inicializar la memoria avanzada
        
        Args:
            db_path: Ruta de la base de datos SQLite
        """
        if db_path is None:
            db_path = "/mnt/d/Proyectos/Yggdrasil/chat_memory.db"

        super().__init__(Path(db_path))

        # Inicializar embeddings (si están disponibles)
        self._init_embedding_support()

    def _init_embedding_support(self):
        """Inicializar soporte para embeddings"""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            self.has_embeddings = True
            print("✅ Soporte de embeddings activado")
        except ImportError:
            self.embedding_model = None
            self.has_embeddings = False
            print("⚠️  Soporte de embeddings no disponible (sentence_transformers no instalado)")

    def add(self, content: str, metadata: dict | None = None) -> int:
        """
        Agregar contenido a la memoria con embeddings
        
        Args:
            content: Contenido a almacenar
            metadata: Metadatos adicionales
            
        Returns:
            ID de la entrada creada
        """
        if metadata is None:
            metadata = {}

        # Generar embedding si el modelo está disponible
        embedding = None
        if self.has_embeddings:
            try:
                embedding = self.embedding_model.encode(content)
            except Exception as e:
                print(f"❌ Error al generar embedding: {e}")

        return super().add(content, embedding, metadata)

    def search_semantic(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Buscar en la memoria de forma semántica
        
        Args:
            query: Consulta para buscar
            limit: Número máximo de resultados
            
        Returns:
            Lista de resultados con similitud
        """
        if not self.has_embeddings:
            print("⚠️  Búsqueda semántica no disponible")
            return self.search(query, limit=limit)

        try:
            # Generar embedding de la consulta
            query_embedding = self.embedding_model.encode(query)

            # Obtener todas las entradas con embeddings
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM memories WHERE embedding IS NOT NULL")
                rows = cursor.fetchall()

            # Calcular similitud
            results = []
            for row in rows:
                # Decodificar embedding desde SQLite
                import pickle
                try:
                    entry_embedding = pickle.loads(row["embedding"])

                    # Calcular similitud coseno
                    similarity = self._cosine_similarity(query_embedding, entry_embedding)

                    results.append({
                        "id": row["id"],
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "timestamp": row["timestamp"],
                        "similarity": similarity
                    })
                except Exception as e:
                    print(f"❌ Error al decodificar embedding: {e}")

            # Ordenar por similitud (descendente)
            results.sort(key=lambda x: x["similarity"], reverse=True)

            # Limitar resultados
            return results[:limit]

        except Exception as e:
            print(f"❌ Error en búsqueda semántica: {e}")
            return self.search(query, limit=limit)

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calcular similitud coseno entre dos vectores
        
        Args:
            vec1: Primer vector
            vec2: Segundo vector
            
        Returns:
            Similitud coseno (0-1)
        """
        import numpy as np

        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def get_context_relevant_to_query(self, query: str, max_entries: int = 3) -> str:
        """
        Obtener contexto relevante para una consulta
        
        Args:
            query: Consulta para la que se necesita contexto
            max_entries: Número máximo de entradas relevantes
            
        Returns:
            Texto con el contexto
        """
        results = self.search_semantic(query, limit=max_entries)

        if len(results) == 0:
            return "No hay contexto relevante disponible"

        # Formatear resultados
        context = []
        for i, result in enumerate(results, 1):
            # Limpiar contenido para contexto
            clean_content = self._clean_for_context(result["content"])

            context.append(f"{i}. {clean_content}")

        return "\n".join(context)

    def _clean_for_context(self, content: str) -> str:
        """
        Limpiar contenido para incluir en contexto
        
        Args:
            content: Contenido a limpiar
            
        Returns:
            Contenido limpio
        """
        # Eliminar prefijos como "Usuario: " o "Lilith: "
        content = re.sub(r"^(Usuario|lilith):?\s?", "", content, flags=re.IGNORECASE)

        # Eliminar caracteres especiales
        content = content.strip()

        # Limitar longitud
        if len(content) > 100:
            content = content[:100] + "..."

        return content

    def analyze_conversation_patterns(self, limit: int = 50) -> dict[str, Any]:
        """
        Analizar patrones de conversación
        
        Args:
            limit: Número de conversaciones a analizar
            
        Returns:
            Dict con patrones analizados
        """
        recent_entries = self.recent(limit=limit)

        analysis = {
            "total_entries": len(recent_entries),
            "user_entries": 0,
            "assistant_entries": 0,
            "avg_length": 0,
            "topics": [],
            "frequent_words": {}
        }

        if len(recent_entries) == 0:
            return analysis

        total_length = 0
        all_words = []

        for entry in recent_entries:
            content = entry.get("content", "").lower()
            total_length += len(content)

            # Contar tipos de entradas
            if content.startswith("usuario:"):
                analysis["user_entries"] += 1
            elif content.startswith("lilith:"):
                analysis["assistant_entries"] += 1

            # Extraer palabras clave
            words = self._extract_keywords(content)
            all_words.extend(words)

            # Detectar temas
            topics = self._extract_topics(content)
            analysis["topics"].extend(topics)

        # Calcular promedio de longitud
        analysis["avg_length"] = total_length / len(recent_entries)

        # Contar palabras frecuentes
        from collections import Counter
        word_counts = Counter(all_words)
        analysis["frequent_words"] = dict(word_counts.most_common(10))

        # Eliminar duplicados de temas
        analysis["topics"] = list(dict.fromkeys(analysis["topics"]))

        return analysis

    def _extract_topics(self, content: str) -> list[str]:
        """
        Extraer temas de un contenido
        
        Args:
            content: Contenido a analizar
            
        Returns:
            Lista de temas
        """
        topics = []

        # Palabras clave que indican temas
        topic_indicators = [
            ("yggdrasil", ["yggdrasil"]),
            ("lilith", ["lilith"]),
            ("cli", ["cli", "command line", "terminal"]),
            ("memory", ["memoria", "memory"]),
            ("skills", ["skills", "habilidades", "funciones"]),
            ("improvement", ["mejora", "improvement", "optimización"]),
            ("conversación", ["conversación", "chat"])
        ]

        for topic_name, indicators in topic_indicators:
            if any(indicator in content for indicator in indicators):
                topics.append(topic_name)

        return topics

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

        stop_words = ["el", "la", "los", "las", "de", "del", "a", "ante", "con",
                     "para", "por", "sin", "so", "sobre", "tras", "cuando",
                     "donde", "como", "que", "qui", "quien", "quienes"]

        keywords = []
        for word in words:
            if len(word) > 3 and word not in stop_words:
                if not word.isdigit():
                    keywords.append(word)

        return keywords

    def generate_conversation_summary(self, limit: int = 30) -> str:
        """
        Generar un resumen de la conversación
        
        Args:
            limit: Número de entradas a incluir en el resumen
            
        Returns:
            Resumen de la conversación
        """
        recent_entries = self.recent(limit=limit)

        if len(recent_entries) == 0:
            return "No hay conversaciones para resumir"

        # Generar resumen
        first_entry = recent_entries[-1]["content"]
        last_entry = recent_entries[0]["content"]

        summary = f"Conversación de {len(recent_entries)} entradas:\n"
        summary += f"1. Primero: {first_entry}\n"
        summary += f"2. Último: {last_entry}"

        return summary

    def export_memory(self, output_path: str = None, format: str = "json") -> str:
        """
        Exportar la memoria
        
        Args:
            output_path: Ruta de salida
            format: Formato de exportación (json, csv, markdown)
            
        Returns:
            Ruta del archivo exportado
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"memory_export_{timestamp}.{format}"

        entries = self.recent(limit=1000)

        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, default=str)
        elif format == "csv":
            import csv
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "content", "metadata", "timestamp"])
                writer.writeheader()
                for entry in entries:
                    writer.writerow(entry)
        elif format == "markdown":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("# Historial de Conversación\n\n")
                for entry in reversed(entries):
                    timestamp = datetime.fromtimestamp(entry["timestamp"]).strftime("%d/%m/%Y %H:%M:%S")
                    f.write(f"## {timestamp}\n\n")
                    f.write(f"{entry['content']}\n\n---\n\n")

        return output_path

    def import_memory(self, file_path: str) -> int:
        """
        Importar memoria desde un archivo
        
        Args:
            file_path: Ruta del archivo de importación
            
        Returns:
            Número de entradas importadas
        """
        count = 0

        try:
            if file_path.endswith(".json"):
                with open(file_path, encoding="utf-8") as f:
                    entries = json.load(f)

                    for entry in entries:
                        metadata = entry.get("metadata", {})
                        # Convertir cadena de fecha a timestamp
                        if isinstance(metadata.get("timestamp"), str):
                            try:
                                dt = datetime.fromisoformat(metadata["timestamp"])
                                metadata["timestamp"] = dt.timestamp()
                            except:
                                pass

                        self.add(entry["content"], metadata)
                        count += 1

            elif file_path.endswith(".csv"):
                import csv
                with open(file_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        metadata = json.loads(row.get("metadata", "{}"))
                        self.add(row["content"], metadata)
                        count += 1

        except Exception as e:
            print(f"❌ Error al importar memoria: {e}")

        return count


def main():
    """Función principal para probar la memoria avanzada"""
    print("🧠 AdvancedMemory - Yggdrasil")
    print("=" * 40)

    memory = AdvancedMemoryStore()

    while True:
        print("\nOpciones disponibles:")
        print("1. Analizar patrones de conversación")
        print("2. Generar resumen de la conversación")
        print("3. Buscar semánticamente")
        print("4. Exportar memoria")
        print("5. Importar memoria")
        print("6. Salir")

        choice = input("\nSelecciona una opción: ").strip()

        if choice == "1":
            limit = int(input("Número de conversaciones a analizar (50): ") or "50")
            analysis = memory.analyze_conversation_patterns(limit=limit)

            print("\n📊 Análisis de Patrones:")
            print(f"Total entradas: {analysis['total_entries']}")
            print(f"Entradas de usuario: {analysis['user_entries']}")
            print(f"Entradas de asistente: {analysis['assistant_entries']}")
            print(f"Longitud promedio: {analysis['avg_length']:.1f} caracteres")

            if analysis["topics"]:
                print(f"Temas detectados: {', '.join(analysis['topics'])}")

            if analysis["frequent_words"]:
                print("Palabras frecuentes:")
                for word, count in analysis["frequent_words"].items():
                    print(f"   • {word}: {count}")

        elif choice == "2":
            limit = int(input("Número de entradas para resumen (30): ") or "30")
            summary = memory.generate_conversation_summary(limit=limit)
            print(f"\n📝 Resumen:\n{summary}")

        elif choice == "3":
            query = input("Consulta para búsqueda semántica: ").strip()
            results = memory.search_semantic(query, limit=5)

            print("\n🔍 Resultados:")
            for i, result in enumerate(results, 1):
                similarity = result["similarity"] * 100
                print(f"{i}. [{similarity:.1f}%] {result['content']}")

        elif choice == "4":
            format = input("Formato de exportación (json, csv, markdown): ").strip() or "json"
            file_path = memory.export_memory(format=format)
            print(f"\n✅ Memoria exportada: {file_path}")

        elif choice == "5":
            file_path = input("Ruta del archivo a importar: ").strip()
            imported = memory.import_memory(file_path)
            print(f"\n✅ Entradas importadas: {imported}")

        elif choice == "6":
            print("\n👋 Saliendo de AdvancedMemory")
            break

        else:
            print("\n❌ Opción inválida. Por favor, selecciona un número entre 1 y 6.")


if __name__ == "__main__":
    main()
