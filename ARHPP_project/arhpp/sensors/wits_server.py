"""WITS TCP/IP Server — thread-safe."""

import socket
import socketserver
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Callable, List

from arhpp.sensors.wits_mapper import (
    parse_wits_line, to_arhpp_inputs, to_wits_out_line,
)

log = logging.getLogger(__name__)


@dataclass
class WITSReading:
    timestamp: datetime = field(default_factory=datetime.utcnow)
    raw: Dict[str, float] = field(default_factory=dict)
    arhpp_inputs: Dict[str, float] = field(default_factory=dict)


class WITSSharedState:
    def __init__(self, history_size: int = 3600):
        self._lock = threading.RLock()
        self._latest: Optional[WITSReading] = None
        self._history: List[WITSReading] = []
        self._history_size = history_size
        self._client_count = 0
        self._last_message_at: Optional[datetime] = None
        self._total_received: int = 0

    def push(self, r: WITSReading) -> None:
        with self._lock:
            self._latest = r
            self._history.append(r)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size:]
            self._last_message_at = datetime.utcnow()
            self._total_received += 1

    def latest(self) -> Optional[WITSReading]:
        with self._lock:
            return self._latest

    def history(self, n: int = 300) -> List[WITSReading]:
        with self._lock:
            return list(self._history[-n:])

    def stats(self) -> Dict:
        with self._lock:
            return {
                "client_count": self._client_count,
                "history_size": len(self._history),
                "total_received": self._total_received,
                "last_message_at": (self._last_message_at.isoformat()
                                      if self._last_message_at else None),
            }

    def client_connected(self) -> None:
        with self._lock:
            self._client_count += 1

    def client_disconnected(self) -> None:
        with self._lock:
            self._client_count = max(0, self._client_count - 1)


class _WITSHandler(socketserver.BaseRequestHandler):
    def handle(self):
        peer = self.client_address
        log.info(f"WITS client connected: {peer}")
        self.server.shared.client_connected()
        try:
            buf = b""
            while not self.server.stop_event.is_set():
                try:
                    self.request.settimeout(1.0)
                    chunk = self.request.recv(4096)
                except socket.timeout:
                    continue
                except (ConnectionResetError, OSError):
                    break
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line_bytes, buf = buf.split(b"\n", 1)
                    line = line_bytes.decode("utf-8",
                                              errors="ignore").strip()
                    if line:
                        self._process_line(line)
        finally:
            log.info(f"WITS client disconnected: {peer}")
            self.server.shared.client_disconnected()

    def _process_line(self, line: str):
        rec = parse_wits_line(line)
        if rec is None:
            return
        arhpp_inputs = to_arhpp_inputs(rec)
        reading = WITSReading(
            timestamp=datetime.utcnow(),
            raw=rec.fields,
            arhpp_inputs=arhpp_inputs)
        self.server.shared.push(reading)
        # Callbacks OUTSIDE lock
        for cb in self.server._external_callbacks:
            try:
                cb(reading)
            except Exception:
                log.exception("callback failed")


class WITSTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, host, port, shared, on_reading=None):
        super().__init__((host, port), _WITSHandler)
        self.shared = shared
        self.on_reading = on_reading
        self._external_callbacks = [on_reading] if on_reading else []
        self.stop_event = threading.Event()


class WITSReceiver:
    def __init__(self, host: str = "0.0.0.0", port: int = 14200,
                 on_reading: Optional[Callable] = None,
                 history_size: int = 3600):
        self.host = host
        self.port = port
        self.shared = WITSSharedState(history_size=history_size)
        self.server = WITSTCPServer(host, port, self.shared,
                                      on_reading=on_reading)
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._start_lock = threading.Lock()

    def start(self) -> None:
        with self._start_lock:
            if self._running:
                return
            self._running = True
            self.server.stop_event.clear()
            self._thread = threading.Thread(
                target=self.server.serve_forever,
                name="WITSReceiver", daemon=True)
            self._thread.start()
            log.info(f"WITS Receiver listening {self.host}:{self.port}")

    def stop(self) -> None:
        with self._start_lock:
            if not self._running:
                return
            self._running = False
            self.server.stop_event.set()
            self.server.shutdown()
            self.server.server_close()
            if self._thread:
                self._thread.join(timeout=3.0)
            log.info("WITS Receiver stopped")

    def latest(self):
        return self.shared.latest()

    def history(self, n: int = 300):
        return self.shared.history(n)

    def stats(self):
        return self.shared.stats()


class WITSSender:
    def __init__(self, host: str, port: int = 14200):
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        with self._lock:
            if self._sock is not None:
                return True
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5.0)
                s.connect((self.host, self.port))
                s.settimeout(None)
                self._sock = s
                log.info(f"WITS Sender connected {self.host}:{self.port}")
                return True
            except Exception as e:
                log.warning(f"WITS Sender connect failed: {e}")
                self._sock = None
                return False

    def send(self, channels: Dict[str, float]) -> bool:
        with self._lock:
            if self._sock is None:
                if not self.connect():
                    return False
            try:
                line = to_wits_out_line(channels)
                self._sock.sendall(line.encode("utf-8"))
                return True
            except Exception as e:
                log.warning(f"WITS send failed: {e}")
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
                return False

    def close(self) -> None:
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None


def _cli():
    import argparse, time
    ap = argparse.ArgumentParser(description="WITS TCP Server")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=14200)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s %(levelname)s %(message)s")
    rx = WITSReceiver(host=args.host, port=args.port)
    rx.start()
    print(f"Listening on {args.host}:{args.port}")
    try:
        while True:
            time.sleep(2)
            r = rx.latest()
            if r:
                print(f"[{r.timestamp.isoformat(timespec='seconds')}] "
                        f"{r.arhpp_inputs}")
            else:
                print(f"Waiting... stats: {rx.stats()}")
    except KeyboardInterrupt:
        pass
    finally:
        rx.stop()


if __name__ == "__main__":
    _cli()
