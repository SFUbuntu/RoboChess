"""Optional DGT electronic board link for RoboChess.

Requires the GPL library python-asyncdgt plus pyserial and pyee:
    pip install asyncdgt pyserial pyee
"""
import asyncio
import queue
import threading


class DgtLink:
    def __init__(self, events):
        self.events = events
        self.thread = None
        self.loop = None
        self.connection = None
        self.stop = threading.Event()

    def start(self, ports):
        self.stop_link()
        self.stop.clear()
        self.thread = threading.Thread(target=self._run, args=(ports,), daemon=True)
        self.thread.start()

    def stop_link(self):
        self.stop.set()
        loop = self.loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.thread = None
        self.loop = None
        self.connection = None

    def _run(self, ports):
        try:
            import asyncdgt
        except ImportError as err:
            self.events.put(('error', 'Falta python-asyncdgt. Instala asyncdgt, pyserial y pyee. / Missing python-asyncdgt. Install asyncdgt, pyserial and pyee. ' + str(err)))
            return
        loop = asyncio.new_event_loop()
        self.loop = loop
        asyncio.set_event_loop(loop)
        try:
            connection = asyncdgt.auto_connect(loop, ports)
        except Exception as err:
            self.events.put(('error', str(err)))
            return
        self.connection = connection

        @connection.on('connected')
        def on_connected(port):
            self.events.put(('connected', str(port)))

        @connection.on('disconnected')
        def on_disconnected():
            self.events.put(('disconnected', ''))

        @connection.on('board')
        def on_board(board):
            self.events.put(('board', board))

        try:
            loop.run_forever()
        finally:
            try:
                connection.close()
            except Exception:
                pass
            loop.close()
            self.loop = None


def default_ports():
    return ['COM%s' % n for n in range(1, 33)] + ['/dev/ttyACM*', '/dev/ttyUSB*', '/dev/tty.usbmodem*']
