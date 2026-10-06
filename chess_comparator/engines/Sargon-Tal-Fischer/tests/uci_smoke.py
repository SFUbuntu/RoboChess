import subprocess
import sys


def send(proc, command):
    proc.stdin.write(command + "\n")
    proc.stdin.flush()


def read_until(proc, prefix):
    output = []
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError(f"engine ended before {prefix!r}: {output}")
        line = line.strip()
        output.append(line)
        if line.startswith(prefix):
            return output


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/uci_smoke.py PATH_TO_ENGINE")
    proc = subprocess.Popen(
        [sys.argv[1]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1
    )
    try:
        send(proc, "uci")
        hello = read_until(proc, "uciok")
        assert any("Hash type spin default 16 min 1 max 32" in row for row in hello)
        assert any("Max Depth type spin default 20 min 1 max 20" in row for row in hello)
        send(proc, "isready")
        assert proc.stdout.readline().strip() == "readyok"

        send(proc, "setoption name Hash value 32")
        send(proc, "setoption name Max Depth value 1")
        send(proc, "setoption name Style value Tal")
        send(proc, "position startpos")
        send(proc, "go")
        limited = read_until(proc, "bestmove")
        assert any(row.startswith("info depth 1 ") for row in limited)
        assert limited[-1].split()[1] not in ("0000", "(none)")

        send(proc, "position fen 7k/6pp/5KQ1/8/8/8/8/8 w - - 0 1")
        send(proc, "go depth 3")
        mate = read_until(proc, "bestmove")
        assert any("score mate 1" in row for row in mate), mate

        send(proc, "position fen 7k/8/8/8/8/8/1q6/KR6 w - - 0 1")
        send(proc, "go depth 3")
        capture = read_until(proc, "bestmove")
        assert capture[-1] == "bestmove b1b2", capture
        send(proc, "quit")
        proc.wait(timeout=10)
        assert proc.returncode == 0
        assert proc.stderr.read() == ""
        print("UCI handshake, Hash 32 MB, depth control, mate-in-1, and tactical capture: PASS")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


if __name__ == "__main__":
    main()
