#!/usr/bin/env python3
"""Run the local FractalOS browser and BoneAmanita companion together."""

import argparse
import subprocess
import sys
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


FRACTAL_ROOT = Path(__file__).resolve().parents[1]


class StaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        # Keep asset requests from scrolling the pairing code out of view.
        return


def port(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a port from 1 to 65535") from exc
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("expected a port from 1 to 65535")
    return number


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bone-root", type=Path, default=FRACTAL_ROOT.parent / "BoneAmanita",
                        help="BoneAmanita checkout (default: sibling directory)")
    parser.add_argument("--web-port", type=port, default=8000, help="FractalOS HTTP port (default: 8000)")
    parser.add_argument("--companion-port", type=port, default=8765, help="BoneAmanita HTTP port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="print the URL without opening a browser")
    args = parser.parse_args(argv)

    bone_root = args.bone_root.expanduser().resolve()
    interpreter = bone_root / ".venv" / "bin" / "python"
    if not (bone_root / "main.py").is_file() or not interpreter.is_file():
        parser.error(f"Expected main.py and .venv/bin/python in {bone_root}. Use --bone-root to select the checkout.")
    if args.web_port == args.companion_port:
        parser.error("FractalOS and BoneAmanita need different ports")
    if not sys.stdout.isatty():
        parser.error("Use a private interactive terminal for the pairing code")

    origin = f"http://localhost:{args.web_port}"
    url = f"{origin}/index.html"
    handler = partial(StaticHandler, directory=str(FRACTAL_ROOT / "resources"))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.web_port), handler)
    except OSError as exc:
        print(f"Could not start FractalOS on port {args.web_port}: {exc}. "
              "Stop the previous server or choose --web-port.", file=sys.stderr)
        return 1

    with server:
        worker = threading.Thread(target=server.serve_forever, name="FractalOS HTTP")
        worker.start()
        try:
            print(f"FractalOS: {url}", flush=True)
            print(f"Open Adventure with adventure --companion and pair on port {args.companion_port}.", flush=True)
            cmd = [str(interpreter), "main.py", "--companion", "--origin", origin, "--port", str(args.companion_port)]
            with subprocess.Popen(cmd, cwd=bone_root) as child:
                if not args.no_browser:
                    threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
                try:
                    return child.wait()
                except KeyboardInterrupt:
                    # Both processes receive Ctrl+C from the terminal. Let BoneAmanita finish saving.
                    return child.wait()
        except OSError as exc:
            print(f"Could not start BoneAmanita: {exc}", file=sys.stderr)
            return 1
        finally:
            server.shutdown()
            worker.join()


if __name__ == "__main__":
    raise SystemExit(main())
