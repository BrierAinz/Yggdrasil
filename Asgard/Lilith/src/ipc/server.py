import json
import logging
import queue
import sys
import threading
import time
from typing import Optional

import pywintypes
import win32event
import win32file
import win32pipe
from pydantic import ValidationError

from .ipc_messages import (
    BaseIPCMessage,
    CommandDecisionResult,
    CommandGeneric,
    CommandSendMessage,
    CommandUpdateConfig,
    EventChatDelta,
    EventChatFinal,
    EventError,
    EventStatusUpdate,
    QueryGetConfig,
    QueryGetStats,
    QueryGetStatus,
)

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("IPCServer")


class IPCServer:
    PIPE_NAME = r"\\.\pipe\SEBAS_CORE_IPC"

    def __init__(self, msg_queue: queue.Queue):
        self.msg_queue = msg_queue
        self.stop_event = threading.Event()
        self.pipe_handle = None
        self.connected = False
        self._thread = None
        self._buffer = ""
        # Outbound send queue â€” send() enqueues, _write_loop drains
        self._send_queue: queue.Queue = queue.Queue()
        self._writer_thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(target=self._server_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.stop_event.set()
        if self.pipe_handle:
            try:
                win32file.CloseHandle(self.pipe_handle)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def _server_loop(self):
        logger.info("Starting IPC Server loop...")
        while not self.stop_event.is_set():
            try:
                self.pipe_handle = win32pipe.CreateNamedPipe(
                    self.PIPE_NAME,
                    win32pipe.PIPE_ACCESS_DUPLEX | win32file.FILE_FLAG_OVERLAPPED,
                    win32pipe.PIPE_TYPE_BYTE
                    | win32pipe.PIPE_READMODE_BYTE
                    | win32pipe.PIPE_WAIT,
                    1,
                    1048576,
                    1048576,  # 1 MB buffers (in/out)
                    0,
                    None,
                )

                logger.info(f"Listening on {self.PIPE_NAME}")

                # Overlapped ConnectNamedPipe
                overlap_connect = pywintypes.OVERLAPPED()
                overlap_connect.hEvent = win32event.CreateEvent(None, True, False, None)
                try:
                    rc = win32pipe.ConnectNamedPipe(self.pipe_handle, overlap_connect)
                except pywintypes.error as e:
                    if e.winerror == 535:  # ERROR_PIPE_CONNECTED â€” already connected
                        pass
                    elif e.winerror == 232:  # Pipe closing
                        win32file.CloseHandle(overlap_connect.hEvent)
                        break
                    else:
                        # For overlapped, 997 (ERROR_IO_PENDING) is normal
                        if e.winerror != 997:
                            win32file.CloseHandle(overlap_connect.hEvent)
                            raise
                else:
                    if rc == 997:  # ERROR_IO_PENDING
                        pass

                # Wait for connection or stop
                while not self.stop_event.is_set():
                    ret = win32event.WaitForSingleObject(overlap_connect.hEvent, 200)
                    if ret == win32event.WAIT_OBJECT_0:
                        break
                win32file.CloseHandle(overlap_connect.hEvent)

                if self.stop_event.is_set():
                    break

                logger.info("Client connected")
                self.connected = True
                self._buffer = ""  # reset for new session
                self._drain_send_queue()  # discard stale outbound msgs

                # Start dedicated writer thread
                self._writer_thread = threading.Thread(
                    target=self._write_loop,
                    daemon=True,
                )
                self._writer_thread.start()

                self._handle_client()

            except pywintypes.error as e:
                logger.error(f"Pipe error in server loop: {e}")
                time.sleep(1)
            finally:
                self.connected = False
                self._drain_send_queue()
                if self.pipe_handle:
                    try:
                        win32file.CloseHandle(self.pipe_handle)
                    except Exception:
                        pass
                self.pipe_handle = None

    # ------------------------------------------------------------------
    # Read path  (runs in _server_loop thread, uses overlapped I/O)
    # ------------------------------------------------------------------

    def _handle_client(self):
        """Read loop using overlapped ReadFile.

        With FILE_FLAG_OVERLAPPED, ReadFile and WriteFile use separate
        OVERLAPPED structures and don't contend â€” true concurrent duplex.
        """
        overlap = pywintypes.OVERLAPPED()
        overlap.hEvent = win32event.CreateEvent(None, True, False, None)

        try:
            while not self.stop_event.is_set():
                try:
                    buf = win32file.AllocateReadBuffer(64 * 1024)
                    rc, _ = win32file.ReadFile(self.pipe_handle, buf, overlap)

                    if rc == 997:  # ERROR_IO_PENDING
                        # Wait for completion or stop (poll every 100ms)
                        while not self.stop_event.is_set():
                            ret = win32event.WaitForSingleObject(overlap.hEvent, 100)
                            if ret == win32event.WAIT_OBJECT_0:
                                break
                        if self.stop_event.is_set():
                            break

                    n = win32file.GetOverlappedResult(self.pipe_handle, overlap, False)
                    data = bytes(buf[:n])
                    if not data:
                        continue

                    self._buffer += data.decode("utf-8")
                    parts = self._buffer.split("\n")
                    self._buffer = parts[-1]
                    for line in parts[:-1]:
                        line = line.strip()
                        if line:
                            self._process_raw_message(line)

                except pywintypes.error as e:
                    if e.winerror == 109:  # Broken pipe
                        logger.info("Client disconnected (Broken Pipe)")
                    elif e.winerror == 995:  # Operation aborted (handle closed)
                        logger.info("Read aborted (server stopping)")
                    else:
                        logger.error(f"Read error: {e}")
                    break
        finally:
            win32file.CloseHandle(overlap.hEvent)

    def _process_raw_message(self, line: str):
        try:
            data = json.loads(line)
            action = data.get("action")

            validated_msg = None
            if action == "send_message":
                validated_msg = CommandSendMessage(**data)
            elif action == "get_status":
                validated_msg = QueryGetStatus(**data)
            elif action == "get_config":
                validated_msg = QueryGetConfig(**data)
            elif action == "update_config":
                validated_msg = CommandUpdateConfig(**data)
            elif action == "decision_result":
                validated_msg = CommandDecisionResult(**data)
            elif action == "get_stats":
                validated_msg = QueryGetStats(**data)
            elif action in (
                "session_history",
                "load_session",
                "new_session",
                "get_token_stats",
                "get_pantheon_status",
                "auto_pause",
                "auto_resume",
            ):
                # Session management / status / auto_mode - pass through as generic commands
                validated_msg = CommandGeneric(**data)
            else:
                logger.warning(f"Unknown message action: {action}")
                return

            self.msg_queue.put(validated_msg)

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Invalid message: {e} - Line: {line}")

    # ------------------------------------------------------------------
    # Write path  (runs in dedicated _writer_thread, uses overlapped I/O)
    # ------------------------------------------------------------------

    def _write_loop(self):
        """Dedicated thread that drains _send_queue and writes to the pipe.

        Uses overlapped WriteFile so writes don't block reads.
        """
        overlap = pywintypes.OVERLAPPED()
        overlap.hEvent = win32event.CreateEvent(None, True, False, None)

        try:
            while not self.stop_event.is_set() and self.connected:
                try:
                    msg = self._send_queue.get(timeout=0.05)
                except queue.Empty:
                    continue

                try:
                    data = (msg.model_dump_json() + "\n").encode("utf-8")
                    rc, _ = win32file.WriteFile(self.pipe_handle, data, overlap)

                    if rc == 997:  # ERROR_IO_PENDING
                        # Wait for write completion
                        while not self.stop_event.is_set():
                            ret = win32event.WaitForSingleObject(overlap.hEvent, 100)
                            if ret == win32event.WAIT_OBJECT_0:
                                break
                        if self.stop_event.is_set():
                            break

                    win32file.GetOverlappedResult(self.pipe_handle, overlap, False)

                except pywintypes.error as e:
                    if e.winerror == 109:  # Broken pipe â€” client is gone
                        logger.info("Write failed: client disconnected")
                        self.connected = False
                        break
                    if e.winerror == 995:  # Operation aborted
                        break
                    # Transient error â€” log but do NOT kill connected flag
                    logger.warning(f"Transient write error (retryable): {e}")
        finally:
            win32file.CloseHandle(overlap.hEvent)

    def send(self, msg: BaseIPCMessage):
        """Non-blocking enqueue. The _write_loop thread handles delivery."""
        if not self.connected:
            return
        self._send_queue.put(msg)

    def _drain_send_queue(self):
        """Discard all pending outbound messages (used between sessions)."""
        while True:
            try:
                self._send_queue.get_nowait()
            except queue.Empty:
                break
