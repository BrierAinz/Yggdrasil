#!/usr/bin/env python3
"""
CLI para consultar al Archivero desde terminal.

Uso:
    python Scripts/ask_archivero.py "¿Cómo funciona el DAG Executor?"
    python Scripts/ask_archivero.py "Explica el sistema de memoria"
    python Scripts/ask_archivero.py "Historia de Cortana a Lilith"
"""
import argparse
import asyncio
import sys

import httpx


API_URL = "http://localhost:8000/api/docs/query"


def print_banner():
    print("=" * 70)
    print("  ARCHIVERO DE SVARTALFHEIM - Biblioteca Técnica de Yggdrasil")
    print("=" * 70)
    print()


def print_response(result: dict):
    """Imprime respuesta formateada."""
    print()
    print("-" * 70)
    print("RESPUESTA:")
    print("-" * 70)
    print(result["answer"])
    print()

    if result.get("sources"):
        print("-" * 70)
        print("FUENTES CONSULTADAS:")
        print("-" * 70)
        for i, src in enumerate(result["sources"], 1):
            print(f"  {i}. {src}")
        print()

    confidence = result.get("confidence", 0) * 100
    print("-" * 70)
    print(f"Confianza: {confidence:.0f}%")
    print("=" * 70)
    print()


async def query_api(question: str) -> dict:
    """Consulta API del Archivero."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                API_URL,
                json={"question": question, "context": ""}
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "error": "No se puede conectar a Lilith API",
                "message": "Asegúrate de que el servidor esté corriendo en localhost:8000"
            }
        except httpx.HTTPStatusError as e:
            return {
                "error": f"Error HTTP {e.response.status_code}",
                "message": str(e)
            }
        except Exception as e:
            return {
                "error": "Error inesperado",
                "message": str(e)
            }


async def interactive_mode():
    """Modo interactivo de consultas."""
    print_banner()
    print("Modo interactivo. Escribe 'exit' o 'quit' para salir.\n")

    while True:
        try:
            question = input("[Archivero] Pregunta> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nSaliendo...")
            break

        if not question:
            continue

        if question.lower() in ("exit", "quit", "salir"):
            print("\nSaliendo...")
            break

        print("\nConsultando...")
        result = await query_api(question)

        if "error" in result:
            print(f"\n[ERROR] {result['error']}")
            print(f"        {result.get('message', '')}")
        else:
            print_response(result)


async def main():
    global API_URL  # Declarar global al inicio

    parser = argparse.ArgumentParser(
        description="Consulta al Archivero de Svartalfheim",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python ask_archivero.py "¿Cómo funciona el DAG Executor?"
  python ask_archivero.py "Explica MuninnDB"
  python ask_archivero.py -i                    # Modo interactivo
        """
    )
    parser.add_argument(
        "question",
        nargs="?",
        help="Pregunta sobre documentación de Lilith"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Modo interactivo"
    )
    parser.add_argument(
        "--api-url",
        default=API_URL,
        help="URL de la API (default: http://localhost:8000/api/docs/query)"
    )

    args = parser.parse_args()

    # Actualizar URL global
    API_URL = args.api_url

    if args.interactive or not args.question:
        await interactive_mode()
    else:
        print_banner()
        print(f"Pregunta: {args.question}\n")
        print("Consultando a Svartalfheim...")

        result = await query_api(args.question)

        if "error" in result:
            print(f"\n[ERROR] {result['error']}")
            print(f"        {result.get('message', '')}")
            sys.exit(1)
        else:
            print_response(result)


if __name__ == "__main__":
    asyncio.run(main())
