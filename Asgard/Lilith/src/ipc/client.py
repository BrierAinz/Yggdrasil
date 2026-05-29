import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

import pywintypes
import win32file
import win32pipe
from pydantic import ValidationError

# Import schema relative to project root or use sys.path hack if needed
# For now assuming Yggdrasil IA is in PYTHONPATH
try:
    from src.ipc.messages import (
        BaseIPCMessage,
        CommandSendMessage,
        EventChatDelta,
        EventChatFinal,
        EventData,
        EventError,
        EventStatusUpdate,
        IPCMessageType,
        QueryGetStatus,
    )
except ImportError:
    # Fallback or local definition if imports fail during dev
    logging.error("Could not import Backend schemas. Ensure PYTHONPATH is set.")
    raise

logger = logging.getLogger("IPCClient")


class IPCClient:
    PIPE_NAME = r"\\.\pipe\SEBAS_CORE_IPC"

    def __init__(self, on_message_callback: Callable[[BaseIPCMessage], None]):
        self.pipe_handle = None
        self.connected = False
        self.on_message = on_message_callback
        self.stop_event = threading.Event()
        self._thread = None
        self._buffer = ""

    def connect(self) -> bool:
        # Cierra el handle anterior si existe antes de reconectar
        if self.pipe_handle:
            try:
                win32file.CloseHandle(self.pipe_handle)
            except Exception:
                pass
            self.pipe_handle = None
        try:
            self.pipe_handle = win32file.CreateFile(
                self.PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None,
            )
            # Removemos SetNamedPipeHandleState(..., PIPE_READMODE_MESSAGE, ...)
            # porque IPCServer fue creado en PIPE_TYPE_BYTE. Error 87 occurrÃ­a aquÃ­.

            self._buffer = ""
            self.connected = True
            logger.info("Connected to SEBAS Core IPC")

            # Start listening thread
            self.stop_event.clear()
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()

            return True
        except pywintypes.error as e:
            # Sin Core (main.py) la API puede funcionar igual para Discord y endpoints HTTP
            logger.warning(
                "IPC no disponible (Core no en ejecución). API en modo standalone: %s",
                e,
            )
            self.connected = False
            return False

    def disconnect(self):
        self.stop_event.set()
        if self.pipe_handle:
            try:
                win32file.CloseHandle(self.pipe_handle)
            except:
                pass
        self.connected = False

    def send(self, msg: BaseIPCMessage):
        if not self.connected:
            logger.warning("Not connected")
            return
        try:
            data = msg.model_dump_json() + "\n"
            win32file.WriteFile(self.pipe_handle, data.encode("utf-8"))
        except pywintypes.error as e:
            logger.error(f"Write failed: {e}")
            self.connected = False

    def _listen_loop(self):
        while not self.stop_event.is_set() and self.connected:
            try:
                try:
                    _, avail, _ = win32pipe.PeekNamedPipe(self.pipe_handle, 0)
                except pywintypes.error as e:
                    if e.winerror == 109:  # Broken Pipe
                        logger.info("Server disconnected")
                        break
                    raise e

                if avail > 0:
                    res, data = win32file.ReadFile(self.pipe_handle, 64 * 1024)
                    if not data:
                        break

                    self._buffer += data.decode("utf-8")
                    parts = self._buffer.split("\n")
                    self._buffer = parts[-1]

                    for line in parts[:-1]:
                        line = line.strip()
                        if line:
                            self._process_inbound(line)
                else:
                    time.sleep(0.01)

            except pywintypes.error as e:
                logger.error(f"Read loop error: {e}")
                break
        self.connected = False
        logger.info("Disconnected from IPC")

    def _process_inbound(self, line: str):
        try:
            data = json.loads(line)
            action = data.get("action")

            # Map action to schema
            msg = None
            if action == "status_update":
                msg = EventStatusUpdate(**data)
            elif action == "chat_delta":
                msg = EventChatDelta(**data)
            elif action == "chat_final":
                msg = EventChatFinal(**data)
            elif action == "error":
                msg = EventError(**data)
            elif action == "data":
                msg = EventData(**data)
            else:
                logger.debug(f"Unknown event: {action}")
                return

            if self.on_message:
                self.on_message(msg)

        except Exception as e:
            logger.error(f"Error processing inbound msg: {e}")
