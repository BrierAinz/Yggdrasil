"""
Lilith — Bot de Telegram (canal principal de Ainz).
Polling + inline keyboards para confirmaciones + comandos rápidos.
Sin dependencias externas de Telegram SDK — solo requests.
"""
import logging
import os
import signal
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

# v4.2: Hardening imports
try:
    from retry_manager import RetryConfig, retry_with_backoff
    from telegram_heartbeat import get_heartbeat_monitor, initialize_heartbeat
    from telegram_signal_handlers import (
        get_shutdown_manager,
        initialize_shutdown_manager,
    )
    from telegram_structured_logging import (
        log_api_call,
        log_message_received,
        log_message_sent,
        setup_telegram_logging,
    )

    _hardening_available = True
except Exception:
    _hardening_available = False

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

# v4.2: Structured logging si está disponible
if _hardening_available:
    try:
        base_dir = Path(__file__).parent.parent
        data_dir = base_dir / "Core" / "Data"
        log_dir = data_dir / "logs"
        logger = setup_telegram_logging(
            log_dir=log_dir, level=logging.INFO, json_format=False, console_output=True
        )
    except Exception:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        logger = logging.getLogger("lilith.telegram")
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("lilith.telegram")

_running = True


def _handle_signal(signum, frame):
    global _running
    logger.info("Señal %s recibida — cerrando bot Telegram.", signum)
    _running = False


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


# ─── Telegram API helpers ─────────────────────────────────────────────────────


def _api(token: str, method: str, **kwargs) -> Dict[str, Any]:
    """Llamada genérica a la API de Telegram."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        r = requests.post(url, json=kwargs, timeout=15)
        return r.json()
    except Exception as e:
        logger.warning("[TG] %s falló: %s", method, e)
        return {}


def _send_message(
    token: str,
    chat_id: int,
    text: str,
    parse_mode: str = "Markdown",
    chunk_size: int = 4000,
    show_progress: bool = True,
) -> None:
    """
    Enviar mensaje de texto (chunked si >4096 chars).
    F.18: Streaming de outputs largos con indicador de progreso.
    """
    if not text:
        return

    # F.18: Chunking con paginación
    if len(text) <= chunk_size:
        _api(token, "sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode)
        return

    # Dividir en chunks respetando líneas cuando sea posible
    chunks = []
    lines = text.split("\n")
    current_chunk = ""

    for line in lines:
        # Si la línea sola excede el tamaño, cortarla
        if len(line) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            # Cortar línea larga en partes
            for i in range(0, len(line), chunk_size):
                chunks.append(line[i : i + chunk_size])
            continue

        # Verificar si agregar esta línea excede el tamaño
        if len(current_chunk) + len(line) + 1 > chunk_size:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk = current_chunk + "\n" + line if current_chunk else line

    if current_chunk:
        chunks.append(current_chunk)

    # F.18: Enviar con indicador de progreso
    total = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        if show_progress and total > 1:
            if i == 1:
                prefix = f"📄 Resultado (1/{total})\n\n"
            elif i == total:
                prefix = f"✅ ({i}/{total}) — Fin\n\n"
            else:
                prefix = f"📄 ({i}/{total})\n\n"
            chunk = prefix + chunk

        _api(token, "sendMessage", chat_id=chat_id, text=chunk, parse_mode=parse_mode)

        # Delay entre chunks para no saturar la API
        if i < total:
            time.sleep(0.2)


def _send_with_confirm_keyboard(
    token: str, chat_id: int, text: str, confirm_token: str, is_pc: bool = False
) -> None:
    """Enviar mensaje con botones inline [✅ Confirmar] [❌ Cancelar].

    Args:
        is_pc: Si es True, usa callbacks pc_confirm/pc_cancel para operaciones PC
    """
    if is_pc:
        # PC operations - endpoints específicos con rate limiting
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Ejecutar",
                        "callback_data": f"pc_confirm:{confirm_token}",
                    }
                ],
                [{"text": "❌ Cancelar", "callback_data": f"pc_cancel:{confirm_token}"}],
            ]
        }
    else:
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Confirmar",
                        "callback_data": f"confirm:{confirm_token}",
                    },
                    {"text": "❌ Cancelar", "callback_data": f"cancel:{confirm_token}"},
                ]
            ]
        }
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "reply_markup": keyboard,
                "parse_mode": "Markdown",
            },
            timeout=15,
        )
    except Exception as e:
        logger.warning("[TG] sendMessage+keyboard falló: %s", e)


def _answer_callback(token: str, callback_query_id: str, text: str = "") -> None:
    """Responder al callback query (quita el spinner del botón)."""
    _api(token, "answerCallbackQuery", callback_query_id=callback_query_id, text=text)


def _edit_message(
    token: str, chat_id: int, message_id: int, text: str, chunk_size: int = 4000
) -> None:
    """
    Editar mensaje existente (para quitar botones después de confirmar).
    F.18: Soporta textos largos editando el mensaje original y enviando continuaciones.
    """
    url = f"https://api.telegram.org/bot{token}/editMessageText"

    # Si el texto es corto, editar directamente
    if len(text) <= chunk_size:
        try:
            requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
        except Exception as e:
            logger.warning("[TG] editMessageText falló: %s", e)
        return

    # F.18: Para textos largos, truncar el mensaje editado y enviar el resto
    preview = text[: chunk_size - 100] + "\n\n... (continúa en siguiente mensaje)"
    try:
        requests.post(
            url,
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": preview,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
    except Exception as e:
        logger.warning("[TG] editMessageText falló: %s", e)

    # Enviar el resto como mensajes nuevos
    remaining = text[len(preview) - 50 :]  # -50 para solapamiento
    _send_message(
        token, chat_id, remaining, parse_mode="Markdown", chunk_size=chunk_size
    )


def _send_typing(token: str, chat_id: int) -> None:
    _api(token, "sendChatAction", chat_id=chat_id, action="typing")


def _keep_typing(token: str, chat_id: int, stop_event: threading.Event) -> None:
    """Envía 'typing' cada 4s mientras el backend procesa (Telegram lo muestra ~5s)."""
    while not stop_event.wait(4.0):
        _send_typing(token, chat_id)


def _get_updates(
    token: str, offset: Optional[int] = None, timeout: int = 30
) -> Dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params: Dict[str, Any] = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=timeout + 5)
        return r.json()
    except Exception as e:
        logger.warning("[TG] getUpdates falló: %s", e)
        return {}


# ─── Backend calls ────────────────────────────────────────────────────────────


def _call_backend_chat(
    api_url: str, token_header: str, text: str, chat_id: int
) -> Dict[str, Any]:
    """Llama al backend de chat con retry si está disponible."""

    def _do_call():
        r = requests.post(
            f"{api_url}/api/telegram/chat",
            headers={"X-Lilith-Token": token_header},
            json={"text": text, "chat_id": str(chat_id), "user_id": str(chat_id)},
            timeout=120,
        )
        return r.json()

    if _hardening_available:
        try:
            return retry_with_backoff(
                _do_call,
                config=RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0),
            )
        except Exception as e:
            logger.exception("[TG] Backend chat error (after retries): %s", e)
            return {"ok": False, "reply": "Error interno al procesar tu mensaje."}
    else:
        try:
            return _do_call()
        except Exception as e:
            logger.exception("[TG] Backend chat error: %s", e)
            return {"ok": False, "reply": "Error interno al procesar tu mensaje."}


def _call_backend_confirm(
    api_url: str, token_header: str, confirm_token: str, approved: bool
) -> Dict[str, Any]:
    """Llama al backend de confirmación con retry si está disponible."""

    def _do_call():
        r = requests.post(
            f"{api_url}/api/telegram/confirm",
            headers={"X-Lilith-Token": token_header},
            json={"token": confirm_token, "approved": approved},
            timeout=120,
        )
        return r.json()

    if _hardening_available:
        try:
            return retry_with_backoff(
                _do_call,
                config=RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0),
            )
        except Exception as e:
            logger.exception("[TG] Backend confirm error (after retries): %s", e)
            return {"ok": False, "result": f"Error al confirmar: {e}"}
    else:
        try:
            return _do_call()
        except Exception as e:
            logger.exception("[TG] Backend confirm error: %s", e)
            return {"ok": False, "result": f"Error al confirmar: {e}"}


def _call_backend_pc_confirm(
    api_url: str, token_header: str, confirm_token: str, approved: bool
) -> Dict[str, Any]:
    """Llama al endpoint de confirmación específico para PC operations con retry."""

    def _do_call():
        r = requests.post(
            f"{api_url}/api/telegram/pc/confirm",
            headers={"X-Lilith-Token": token_header},
            json={"token": confirm_token, "approved": approved},
            timeout=180,  # PC ops pueden tomar más tiempo
        )
        return r.json()

    if _hardening_available:
        try:
            return retry_with_backoff(
                _do_call,
                config=RetryConfig(max_retries=3, base_delay=2.0, max_delay=15.0),
            )
        except Exception as e:
            logger.exception("[TG] Backend PC confirm error (after retries): %s", e)
            return {"ok": False, "result": f"Error al confirmar operación PC: {e}"}
    else:
        try:
            return _do_call()
        except Exception as e:
            logger.exception("[TG] Backend PC confirm error: %s", e)
            return {"ok": False, "result": f"Error al confirmar operación PC: {e}"}


# ─── Health Check Integration ─────────────────────────────────────────────────


def _get_health_status_report() -> str:
    """
    Genera un reporte de estado del sistema usando HealthMonitor.
    Retorna un mensaje formateado para Telegram.
    """
    try:
        import asyncio
        import sys
        from pathlib import Path

        # Agregar Core al path para importar
        core_path = Path(__file__).parent.parent / "Core" / "Backend"
        if str(core_path) not in sys.path:
            sys.path.insert(0, str(core_path))

        from src.core.health_monitor import HealthMonitor, HealthStatus

        # Ejecutar health check
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        health = loop.run_until_complete(HealthMonitor.check_all())

        # Formatear reporte
        emoji_map = {
            HealthStatus.HEALTHY: "🟢",
            HealthStatus.DEGRADED: "🟡",
            HealthStatus.UNHEALTHY: "🔴",
            HealthStatus.UNKNOWN: "⚪",
        }

        status_emoji = emoji_map.get(health.overall_status, "⚪")
        lines = [
            f"{status_emoji} *Estado del Sistema* — Lilith v{health.metadata.get('lilith_version', '4.2.4')}",
            "",
            "📊 *Subsistemas:*",
        ]

        for check in health.checks:
            emoji = emoji_map.get(check.status, "⚪")
            lines.append(f"{emoji} {check.name}: {check.message}")

        lines.append("")
        lines.append(
            f"⏱️ Tiempo total: {sum(c.response_time_ms for c in health.checks):.0f}ms"
        )
        lines.append(f"🕐 {health.timestamp.strftime('%H:%M:%S')}")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("[TG] Error generando health report: %s", e)
        return f"⚠️ *Estado del Sistema*\n\nError al obtener estado: {str(e)[:200]}"


# ─── Comandos rápidos → texto natural ────────────────────────────────────────


def _command_to_text(cmd: str, args: str) -> Optional[str]:
    """Traduce /comando args → texto natural para el backend."""
    cmd = cmd.lower()
    if cmd in ("start", "help", "ayuda"):
        return "dame el status del sistema y dime brevemente qué puedes hacer"
    if cmd == "status":
        return "__HEALTH_STATUS__"  # Marcador especial para health check directo
    if cmd == "ls":
        path = args.strip() or "."
        return f"lista los archivos en {path}"
    if cmd == "cat":
        if not args.strip():
            return None
        return f"muéstrame el contenido de {args.strip()}"
    if cmd == "exec":
        if not args.strip():
            return None
        return f"ejecuta {args.strip()}"
    if cmd == "eva":
        if not args.strip():
            return None
        return f"pregúntale a Eva: {args.strip()}"
    if cmd == "adan":
        if not args.strip():
            return None
        return f"pregúntale a Adán: {args.strip()}"
    if cmd == "odin":
        if not args.strip():
            return None
        return f"pregúntale a Odín: {args.strip()}"
    if cmd == "investiga":
        if not args.strip():
            return None
        return f"investiga: {args.strip()}"
    if cmd == "auto":
        if not args.strip():
            return None
        return f"modo automático: {args.strip()}"
    if cmd == "lock":
        return "bloquea el PC Agent"
    if cmd == "unlock":
        return "desbloquea el PC Agent"
    if cmd == "modo":
        if not args.strip():
            return None
        return f"cambia al modo {args.strip()}"
    if cmd == "memoria":
        return "qué recuerdas de mí"
    # Desconocido — pasar como texto literal
    full = f"/{cmd} {args}".strip()
    return full


# ─── Handlers ─────────────────────────────────────────────────────────────────


def handle_message(
    token: str,
    api_url: str,
    internal_token: str,
    owner_chat_id: Optional[int],
    msg: dict,
) -> None:
    """Procesa un mensaje de texto/comando."""
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return
    if owner_chat_id is not None and int(chat_id) != owner_chat_id:
        logger.debug("[TG] Mensaje de chat_id=%s ignorado (no es owner).", chat_id)
        return

    text = (msg.get("text") or "").strip()
    if not text:
        return

    # Parsear comandos
    natural_text = text
    if text.startswith("/"):
        parts = text.split(None, 1)
        cmd_raw = parts[0].lstrip("/")
        # Manejar /comando@botname
        cmd = cmd_raw.split("@")[0]
        args = parts[1] if len(parts) > 1 else ""
        resolved = _command_to_text(cmd, args)
        if resolved is None:
            _send_message(token, int(chat_id), f"⚠️ Uso: `/{cmd} <argumento>`")
            return
        natural_text = resolved

    # v4.2.4: Health status directo (sin pasar por backend)
    if natural_text == "__HEALTH_STATUS__":
        logger.info("[TG] Generando health status report para chat_id=%s", chat_id)
        health_report = _get_health_status_report()
        _send_message(token, int(chat_id), health_report, parse_mode="Markdown")
        return

    logger.info("[TG] chat_id=%s: %s", chat_id, natural_text[:80])
    _send_typing(token, int(chat_id))

    # v4.2: Structured logging de mensaje recibido
    if _hardening_available:
        try:
            log_message_received(chat_id=int(chat_id), text=natural_text[:200])
        except Exception:
            pass

    # Typing loop: mantiene el indicador activo durante llamadas largas al backend
    _stop_typing = threading.Event()
    _typing_thread = threading.Thread(
        target=_keep_typing, args=(token, int(chat_id), _stop_typing), daemon=True
    )
    _typing_thread.start()
    try:
        data = _call_backend_chat(api_url, internal_token, natural_text, int(chat_id))
    finally:
        _stop_typing.set()

    if data.get("ignore"):
        return

    reply = data.get("reply") or data.get("error") or "Sin respuesta."

    if data.get("requires_confirmation") and data.get("confirmation_token"):
        confirm_token = data["confirmation_token"]
        # Detectar si es operación PC para usar los botones correctos
        is_pc = data.get("confirmation_type") == "pc" or data.get("pc_batch")
        _send_with_confirm_keyboard(
            token, int(chat_id), reply, confirm_token, is_pc=is_pc
        )
    else:
        _send_message(token, int(chat_id), reply)

    # v4.2: Structured logging de mensaje enviado
    if _hardening_available:
        try:
            log_message_sent(chat_id=int(chat_id), text=reply[:200] if reply else "")
        except Exception:
            pass


def handle_callback_query(
    token: str,
    api_url: str,
    internal_token: str,
    owner_chat_id: Optional[int],
    cbq: dict,
) -> None:
    """Procesa botones inline (confirmar/cancelar)."""
    cbq_id = cbq.get("id", "")
    from_user = cbq.get("from") or {}
    chat = (cbq.get("message") or {}).get("chat") or {}
    chat_id = chat.get("id")
    message_id = (cbq.get("message") or {}).get("message_id")

    if owner_chat_id is not None and chat_id and int(chat_id) != owner_chat_id:
        _answer_callback(token, cbq_id, "No autorizado.")
        return

    callback_data = cbq.get("data") or ""
    if ":" not in callback_data:
        _answer_callback(token, cbq_id)
        return

    action, confirm_token = callback_data.split(":", 1)

    if action == "confirm":
        _answer_callback(token, cbq_id, "Ejecutando...")
        data = _call_backend_confirm(
            api_url, internal_token, confirm_token, approved=True
        )
        result_text = data.get("result") or "✅ Ejecutado."
        if chat_id and message_id:
            _edit_message(
                token, int(chat_id), int(message_id), f"✅ Confirmado.\n\n{result_text}"
            )

    elif action == "cancel":
        _answer_callback(token, cbq_id, "Cancelado.")
        data = _call_backend_confirm(
            api_url, internal_token, confirm_token, approved=False
        )
        if chat_id and message_id:
            _edit_message(
                token, int(chat_id), int(message_id), "❌ Operación cancelada."
            )

    elif action == "pc_confirm":
        # PC operations - usar endpoint específico con rate limiting
        _answer_callback(token, cbq_id, "⏳ Ejecutando operaciones en PC...")
        data = _call_backend_pc_confirm(
            api_url, internal_token, confirm_token, approved=True
        )
        result_text = data.get("result") or data.get("error") or "✅ Completado."
        success = data.get("ok", False)
        prefix = "✅" if success else "⚠️"
        if chat_id and message_id:
            _edit_message(
                token,
                int(chat_id),
                int(message_id),
                f"{prefix} Operación PC confirmada.\n\n{result_text}",
            )

    elif action == "pc_cancel":
        _answer_callback(token, cbq_id, "❌ Cancelado.")
        _call_backend_pc_confirm(api_url, internal_token, confirm_token, approved=False)
        if chat_id and message_id:
            _edit_message(
                token, int(chat_id), int(message_id), "❌ Operación PC cancelada."
            )

    else:
        _answer_callback(token, cbq_id)


# ─── Main polling loop ────────────────────────────────────────────────────────


def main() -> None:
    TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN en el entorno.")

    TELEGRAM_OWNER_CHAT_ID_STR = _env("TELEGRAM_OWNER_CHAT_ID")
    owner_chat_id = (
        int(TELEGRAM_OWNER_CHAT_ID_STR) if TELEGRAM_OWNER_CHAT_ID_STR else None
    )

    LILITH_API_URL = _env("LILITH_API_URL", "http://127.0.0.1:8000")
    LILITH_INTERNAL_TOKEN = _env("LILITH_INTERNAL_TOKEN")
    if not LILITH_INTERNAL_TOKEN:
        raise SystemExit("Falta LILITH_INTERNAL_TOKEN en el entorno.")

    # v4.2: Inicializar sistemas de hardening si están disponibles
    if _hardening_available:
        try:
            base_dir = Path(__file__).parent.parent
            data_dir = base_dir / "Core" / "Data"
            data_dir.mkdir(parents=True, exist_ok=True)

            # Signal handlers
            initialize_shutdown_manager(state_file=data_dir / "telegram_state.json")
            shutdown_manager = get_shutdown_manager()
            shutdown_manager.register_cleanup(
                lambda: logger.info("Telegram bot shutting down...")
            )

            # Heartbeat
            initialize_heartbeat(
                heartbeat_file=data_dir / "telegram_heartbeat.txt", interval_seconds=60
            )

            logger.info(
                "[TG] Hardening systems initialized (signal handlers + heartbeat)"
            )
        except Exception as e:
            logger.warning("[TG] Failed to initialize hardening systems: %s", e)

    logger.info("[TG] Lilith Telegram bot iniciado. owner_chat_id=%s", owner_chat_id)
    offset: Optional[int] = None
    backoff = 1.0

    while _running:
        try:
            updates = _get_updates(TELEGRAM_BOT_TOKEN, offset=offset, timeout=30)
            backoff = 1.0

            if not updates.get("ok"):
                logger.warning("[TG] getUpdates no OK: %s", updates)
                time.sleep(backoff)
                continue

            for upd in updates.get("result") or []:
                offset = int(upd.get("update_id", 0)) + 1

                # Callback queries (botones inline)
                if "callback_query" in upd:
                    try:
                        handle_callback_query(
                            TELEGRAM_BOT_TOKEN,
                            LILITH_API_URL,
                            LILITH_INTERNAL_TOKEN,
                            owner_chat_id,
                            upd["callback_query"],
                        )
                    except Exception as e:
                        logger.exception("[TG] Error en callback_query: %s", e)
                    continue

                # Mensajes de texto
                msg = upd.get("message") or upd.get("edited_message") or {}
                if not msg:
                    continue
                try:
                    handle_message(
                        TELEGRAM_BOT_TOKEN,
                        LILITH_API_URL,
                        LILITH_INTERNAL_TOKEN,
                        owner_chat_id,
                        msg,
                    )
                except Exception as e:
                    logger.exception("[TG] Error en handle_message: %s", e)

        except KeyboardInterrupt:
            logger.info("[TG] KeyboardInterrupt — cerrando.")
            break
        except Exception as e:
            logger.exception("[TG] Error en polling loop: %s", e)
            time.sleep(min(backoff, 30.0))
            backoff = min(backoff * 2, 30.0)

    logger.info("[TG] Bot Telegram detenido.")


if __name__ == "__main__":
    main()
