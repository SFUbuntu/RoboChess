"""Modern Python 3.10+ bridge for a DGT e-board.

Uses the locally vendored, Python-3.12-compatible asyncdgt protocol driver.
The event queue is consumed by RoboChess's Tk main thread.
"""
from __future__ import annotations

import asyncio
import threading


class DgtLink:
    def __init__(self, events, stable_ms=180):
        self.events = events
        self.stable_ms = max(80, int(stable_ms))
        self.thread = None
        self.loop = None
        self.connection = None
        self._stop_requested = threading.Event()

    def start(self, ports):
        self.stop_link()
        self._stop_requested.clear()
        self.thread = threading.Thread(
            target=self._run, args=(tuple(ports),), name="RoboChess-DGT", daemon=True
        )
        self.thread.start()

    def stop_link(self):
        self._stop_requested.set()
        loop = self.loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        thread = self.thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5)
        self.thread = None
        self.loop = None
        self.connection = None

    def _run(self, ports):
        loop = asyncio.new_event_loop()
        connection = None
        self.loop = loop
        asyncio.set_event_loop(loop)
        try:
            import asyncdgt

            connection = asyncdgt.auto_connect(loop, list(ports))
            self.connection = connection
            pending_board = {"fen": None, "handle": None}

            @connection.on("connected")
            def on_connected(port):
                self.events.put(("connected", str(port)))

            @connection.on("disconnected")
            def on_disconnected():
                self.events.put(("disconnected", ""))

            def publish_stable_board():
                fen = pending_board["fen"]
                pending_board["handle"] = None
                if fen:
                    self.events.put(("board", fen))

            def queue_stable_board(fen):
                pending_board["fen"] = fen
                handle = pending_board["handle"]
                if handle:
                    handle.cancel()
                pending_board["handle"] = loop.call_later(
                    self.stable_ms / 1000.0, publish_stable_board
                )

            @connection.on("board")
            def on_board(board):
                try:
                    fen = board.board_fen()
                except Exception as err:
                    self.events.put(("error", "No se pudo leer el tablero DGT: " + str(err)))
                    return
                # DGT field updates may report the board while a piece is in
                # transit. Only pass a position to Tk after it settles briefly.
                loop.call_soon_threadsafe(queue_stable_board, fen)

            loop.run_forever()
        except Exception as err:
            self.events.put(("error", f"DGT: {type(err).__name__}: {err}"))
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception as err:
                    self.events.put(("error", f"DGT disconnect: {err}"))
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending and not loop.is_closed():
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            if not loop.is_closed():
                loop.close()
            asyncio.set_event_loop(None)
            self.loop = None
            self.connection = None


def default_ports():
    """Globs accepted by asyncdgt; serial port enumeration handles COM names."""
    return ["COM*", "/dev/ttyACM*", "/dev/ttyUSB*", "/dev/cu.*", "/dev/tty.*"]
