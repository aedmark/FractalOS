"""Deterministic agent regressions; no browser, provider or user files needed.

Run: python3 tests/agent_unit.py
Browser integration remains covered by tests/smoke.js and tests/agent.js.
"""
import asyncio
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'resources/core'))
http = types.ModuleType('pyodide.http')
pyodide = types.ModuleType('pyodide')
pyodide.http = http
audit = types.ModuleType('audit')
audit.audit_manager = types.SimpleNamespace(log=lambda *args: None)
with patch.dict(sys.modules, {'pyodide': pyodide, 'pyodide.http': http, 'audit': audit}):
    from ai_manager import AIManager
from bone_driver import BoneDriver


class FakeFS:
    current_path = '/home/test'

    def get_node(self, path):
        return None


class FakeExecutor:
    def __init__(self):
        self.fs_manager = FakeFS()
        self.user_context = {'name': 'test', 'group': 'test'}
        self.calls = []
        self.results = {}

    async def execute(self, command, context):
        self.calls.append((command, json.loads(context)))
        return json.dumps(self.results.get(command, {'success': True, 'output': 'ok'}))


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.executor = FakeExecutor()
        self.am = AIManager(self.executor.fs_manager, self.executor)

    def test_manifest_matches_tools(self):
        manifest = self.am.PLANNER_SYSTEM_PROMPT.split('--- TOOL MANIFEST ---')[1].split('--- END MANIFEST ---')[0]
        self.assertEqual(set(manifest.strip().split(', ')), set(self.am.COMMAND_WHITELIST))

    def test_persona_does_not_invent_project(self):
        prompt = BoneDriver.get_system_prompt({'name': 'test'})
        self.assertNotIn('mkdir Project', prompt)
        self.assertNotIn('mkdir Matrix', prompt)
        self.assertIn('any text file directly', prompt)

    def test_final_command_list_wins_over_explanation(self):
        text = '1. **pwd**: Explain location\n2. **ls**: Explain files\n\nFinal commands:\n1. `pwd`\n2. `ls`'
        self.assertEqual(self.am.extract_plan(text), ['pwd', 'ls'])

    def test_unknown_command_not_dropped(self):
        self.assertEqual(self.am.extract_plan('1. ls\n2. forbidden x\n3. pwd'), ['ls', 'forbidden x', 'pwd'])

    def test_fenced_and_bullet_plans(self):
        self.assertEqual(self.am.extract_plan('```sh\nls\npwd\n```'), ['ls', 'pwd'])
        self.assertEqual(self.am.extract_plan('- `ls`\n- `pwd`'), ['ls', 'pwd'])

    def test_backticks_inside_content_preserved(self):
        command = 'forge note.txt "Use `ls` to list files"'
        self.assertEqual(self.am.extract_plan('1. ' + command), [command])

    def test_plain_answer_is_not_plan(self):
        self.assertEqual(self.am.extract_plan('Paris is the capital of France.'), [])


if __name__ == '__main__':
    unittest.main()
