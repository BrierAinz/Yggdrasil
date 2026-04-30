"""
CLI nativo para hablar con Lilith vía /api/discord/chat.

Uso rápido:
  python lilith_cli.py "mensaje rápido"

Modo interactivo:
  python lilith_cli.py
  Lilith> ...

Siempre habla como owner (role="owner") y canal "dm".
Requiere que la API esté arriba en LILITH_API_URL (por defecto http://127.0.0.1:8000).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Optional

try:
    import requests  # type: ignore
except ImportError as e:  # pragma: no cover
    print(
        "Este CLI requiere el paquete 'requests'. Instálalo con:\n  pip install requests",
        file=sys.stderr,
    )
    raise


DEFAULT_API_URL = os.getenv("LILITH_API_URL", "http://127.0.0.1:8000").rstrip("/")


@dataclass
class LilithClient:
    api_url: str = DEFAULT_API_URL
    user_id: str = "cli-owner"

    def send(self, message: str, session_id: Optional[str] = None) -> str:
        """Envía un mensaje a /api/discord/chat como owner en DM. session_id opcional para agrupar historial en el futuro."""
        url = f"{self.api_url}/api/discord/chat"
        payload = {
            "text": message,
            "user_id": self.user_id,
            "role": "owner",
            "channel": "dm",
        }
        # Por ahora no mandamos history explícito; la memoria la lleva el backend.
        headers = {"Content-Type": "application/json; charset=utf-8"}
        try:
            resp = requests.post(
                url, data=json.dumps(payload), headers=headers, timeout=120
            )
        except Exception as e:  # pragma: no cover
            return f"[CLI] Error de conexión con {url}: {e}"

        if resp.status_code != 200:
            try:
                data = resp.json()
            except Exception:
                data = {}
            detail = data.get("detail") or data.get("error") or resp.text
            return f"[CLI] HTTP {resp.status_code}: {detail}"

        try:
            data = resp.json()
        except Exception:
            return resp.text

        return (data.get("response") or "").strip() or "(Sin respuesta)"


def _print_usage() -> None:
    script = os.path.basename(sys.argv[0] or "lilith_cli.py")
    print(
        f'Uso:\n  python {script} "mensaje rápido"\n  python {script}        # modo interactivo\n',
        file=sys.stderr,
    )


def main() -> None:
    client = LilithClient()

    # Modo no interactivo: mensaje en la línea de comandos
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:]).strip()
        if not text:
            _print_usage()
            sys.exit(1)
        resp = client.send(text)
        print(resp)
        return

    # Modo interactivo
    print(f"Lilith CLI — API: {client.api_url}  (Ctrl+C para salir)")
    try:
        while True:
            try:
                prompt = "Lilith> "
                text = input(prompt).strip()
            except EOFError:
                break
            if not text:
                continue
            if text.lower() in {"exit", "quit", ":q"}:
                break
            resp = client.send(text)
            print(resp)
    except KeyboardInterrupt:
        print("\nSaliendo.")


if __name__ == "__main__":  # pragma: no cover
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        # Permitir: echo "hola" | python lilith_cli.py
        raw = sys.stdin.read().strip()
        if raw:
            sys.argv.append(raw)
    main()
