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
from commands.forge import decode_content


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
        self.am._checkpoint_home = lambda: {'success': True, 'snapshot_id': 'test-baseline'}

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

    def run_plan(self, plan, agent=False, **options):
        async def llm(*args):
            return {'success': True, 'answer': plan}
        async def context():
            return 'Current Directory: /home/test'
        self.am._call_llm_api = llm
        self.am._get_terminal_context = context
        method = self.am.perform_agentic_search if agent else self.am.perform_autopilot
        return asyncio.run(method('test', [], 'ollama', None, options))

    def test_failed_cd_stops_writes_and_returns_failure(self):
        self.executor.results['cd missing'] = {'success': False, 'error': 'absent'}
        result = self.run_plan('1. cd missing\n2. forge tools.txt "trowel"\n3. story save "done"')
        self.assertFalse(result['success'])
        self.assertEqual([c[0] for c in self.executor.calls], ['cd missing'])

    def test_later_invalid_command_prevents_all_execution(self):
        for agent in [False, True]:
            result = self.run_plan('1. mkdir changed\n2. forbidden command', agent=agent)
            self.assertFalse(result['success'])
        self.assertEqual(self.executor.calls, [])

    def test_compounds_and_substitutions_are_rejected(self):
        for command in ['ls; rm -rf x', 'ls | cat', 'echo $(rm x)', 'echo "$HOME"', 'ls && pwd']:
            self.assertIsNotNone(self.am.validate_plan([command]), command)
        self.assertIsNone(self.am.validate_plan(['python -c "x=1; print(x)"']))

    def test_agent_failed_command_never_synthesizes_success(self):
        self.executor.results['cat missing'] = {'success': False, 'error': 'absent'}
        result = self.run_plan('1. cat missing\n2. ls', agent=True)
        self.assertFalse(result['success'])
        self.assertEqual([c[0] for c in self.executor.calls], ['cat missing'])

    def test_voltage_prices_operations_not_payload(self):
        for command in ['rm -r garden', 'rm -rf garden', 'rm -fr garden', 'rm --recursive garden']:
            self.assertEqual(BoneDriver.audit_plan_voltage([command]), 20)
        self.assertEqual(BoneDriver.audit_plan_voltage(['forge tools.txt "trowel"']), 5)
        self.assertEqual(BoneDriver.audit_plan_voltage(['echo "rm -rf story save forge python"']), 0.1)
        self.assertEqual(BoneDriver.audit_plan_voltage(['rm -r garden', 'story save "done"']), 20.1)

    def test_voltage_brake_and_force(self):
        result = self.run_plan('1. rm -fr garden')
        self.assertFalse(result['success'])
        self.assertEqual(self.executor.calls, [])
        result = self.run_plan('1. rm -fr garden', force_override=True)
        self.assertTrue(result['success'])
        self.assertEqual(self.executor.calls[0][0], 'rm -fr garden')

    def test_checkpoint_failure_stops_even_forced_plan(self):
        self.am._checkpoint_home = lambda: {'success': False, 'error': 'denied'}
        result = self.run_plan('1. rm -r garden', force_override=True)
        self.assertFalse(result['success'])
        self.assertIn('Checkpoint failed', result['error'])
        self.assertEqual(self.executor.calls, [])

    def test_force_does_not_override_validation(self):
        result = self.run_plan('1. python --steps 0 -c "pass"', force_override=True)
        self.assertFalse(result['success'])
        self.assertEqual(self.executor.calls, [])

    def test_forge_nested_python_escape_survives(self):
        import shlex
        command = r'''forge nested.py 'print("first\\nsecond")\nprint("done")' '''
        source = decode_content(shlex.split(command)[2])
        compile(source, 'nested.py', 'exec')
        self.assertEqual(source, 'print("first\\nsecond")\nprint("done")')

    def test_forge_preserves_unicode_and_unknown_escapes(self):
        self.assertEqual(decode_content(r'café\t\q'), r'café\t\q')
        self.assertEqual(decode_content(r'one\ntwo'), 'one\ntwo')

    def test_blank_lines_do_not_drop_earlier_steps(self):
        self.assertEqual(self.am.extract_plan('1. cd garden\n\n2. forge tools.txt "trowel"'),
                         ['cd garden', 'forge tools.txt "trowel"'])

    def test_invalid_final_list_is_not_replaced_by_earlier_plan(self):
        plan = self.am.extract_plan('1. ls\nFinal commands:\n1. forbidden x')
        self.assertEqual(plan, ['forbidden x'])
        self.assertIsNotNone(self.am.validate_plan(plan))


if __name__ == '__main__':
    unittest.main()
