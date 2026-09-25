"""A stand-in for Ollama, for exercising the agent's wire path without a model.

    python3 tests/fake_ollama.py            # listens on http://127.0.0.1:11434
    python3 tests/fake_ollama.py --port 11434 --log tests/out/fake-ollama-requests.jsonl

Speaks just enough of Ollama's HTTP API for `ai_manager._call_llm_api`: GET /api/tags,
POST /api/generate (non-streaming), and the CORS preflight the browser sends first
(real Ollama allows http://localhost:* and http://127.0.0.1:* origins by default; so
does this). It answers each prompt with a canned, persona-shaped plan chosen by
keywords in the user's request, so `node tests/agent.js` can run against it and
prove the harness and the OS's Ollama plumbing before a real model is plugged in.

It is not a model. A run against it says nothing about how an LLM behaves; it
says the request reached port 11434 in the right shape and the answer came back
through the right fields. Every request is appended to the log as one JSON line.
"""
import argparse
import json
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "fake:latest"


def _home(prompt):
    m = re.search(r"You live at `([^`]+)`", prompt)
    return m.group(1) if m else "/home/Guest"


def _autopilot_plan(request, home):
    r = request.lower()
    if "seeds" in r:
        return (f"1. cd {home}\n2. mkdir garden\n3. cd garden\n4. story begin\n"
                f'5. forge seeds.txt "basil\\nmint\\nthyme"\n6. story save "seeds planted"')
    if "tools.txt" in r:
        return f'1. cd garden\n2. forge tools.txt "trowel"\n3. story save "tools listed"'
    if "sum.py" in r:
        return (f'1. cd {home}\n2. forge sum.py "print(sum(range(1, 11)))"\n'
                f'3. python sum.py\n4. story save "summed"')
    if "delete" in r or "remove" in r:
        return f'1. cd {home}\n2. rm -rf garden\n3. story save "garden cleared"'
    if "forever" in r:
        return '1. python --steps 0 -c "while True: pass"'
    return "I sense no kinetic action in that request."


def _planner_plan(request):
    r = request.lower()
    if "rename" in r:
        return "1. mv garden/tools.txt garden/kit.txt"
    if "home directory" in r or "files" in r:
        return "1. pwd\n2. ls -la"
    if "capital of france" in r:
        return "Paris."
    return "1. ls"


def answer_for(prompt):
    """(stage, answer) for one Ollama prompt as ai_manager builds it."""
    if "USER REQUEST:" in prompt:
        request = prompt.rsplit("USER REQUEST:", 1)[1].strip()
        return "autopilot", _autopilot_plan(request, _home(prompt))
    if "Original user question:" in prompt:
        context = prompt.split("Context from file system:", 1)[-1].strip()
        return "synthesizer", "Here is what the commands showed:\n" + context[:400]
    if "User Prompt:" in prompt:
        m = re.search(r'User Prompt: "(.*?)"', prompt, re.DOTALL)
        return "planner", _planner_plan(m.group(1) if m else prompt)
    return "chat", "Hello from the stand-in. I am not a model."


class Handler(BaseHTTPRequestHandler):
    log_path = None

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/tags":
            return self._send(200, {"models": [{"name": MODEL, "model": MODEL}]})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/generate":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        prompt = body.get("prompt", "")
        stage, answer = answer_for(prompt)
        if Handler.log_path:
            with open(Handler.log_path, "a") as f:
                f.write(json.dumps({"time": time.time(), "model": body.get("model"), "stream": body.get("stream"),
                                    "stage": stage, "prompt_chars": len(prompt), "prompt": prompt,
                                    "response": answer}) + "\n")
        print(f"[fake-ollama] {stage:11} model={body.get('model')} prompt={len(prompt)} chars", flush=True)
        self._send(200, {"model": body.get("model", MODEL), "response": answer, "done": True,
                         "done_reason": "stop", "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})

    def log_message(self, *args):
        pass


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--port", type=int, default=11434)
    p.add_argument("--log", default=None, help="append one JSON line per request here")
    a = p.parse_args(argv)
    Handler.log_path = a.log
    if a.log:
        open(a.log, "w").close()
    server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"[fake-ollama] listening on http://127.0.0.1:{a.port} (model {MODEL})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
