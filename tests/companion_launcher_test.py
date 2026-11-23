from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest import TestCase, main
from unittest.mock import MagicMock, patch
import importlib.util


SPEC = importlib.util.spec_from_file_location(
    "start_companion", Path(__file__).resolve().parents[1] / "extras" / "start_companion.py"
)
launch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launch)


class CompanionLauncherTests(TestCase):
    def test_the_web_and_companion_ports_share_the_browser_origin(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").touch()
            interpreter = root / ".venv" / "bin" / "python"
            interpreter.parent.mkdir(parents=True)
            interpreter.touch()
            server = MagicMock()
            process = MagicMock()
            process.__enter__.return_value.wait.return_value = 7
            opened = Event()
            with (
                patch.object(launch.sys.stdout, "isatty", return_value=True),
                patch.object(launch, "ThreadingHTTPServer", return_value=server) as bind,
                patch.object(launch.subprocess, "Popen", return_value=process) as spawn,
                patch.object(launch.webbrowser, "open", side_effect=lambda _url: opened.set()) as browser,
            ):
                result = launch.main(["--bone-root", directory, "--web-port", "8040",
                                      "--companion-port", "8766"])
                self.assertTrue(opened.wait(1))

            self.assertEqual(result, 7)
            self.assertEqual(bind.call_args.args[0], ("127.0.0.1", 8040))
            spawn.assert_called_once_with(
                [str(interpreter), "main.py", "--companion", "--origin", "http://localhost:8040",
                 "--port", "8766"],
                cwd=root,
            )
            server.shutdown.assert_called_once()
            server.__exit__.assert_called_once()
            browser.assert_called_once_with("http://localhost:8040/index.html")


if __name__ == "__main__":
    main()
