"""
swarm_manager.py - Swarm Safety & Voltage Policies for FractalOS Mesh.
Controls inter-node task execution permissions, voltage budget caps,
hardware GPIO actuation interlocks, and cryptographic provenance auditing.
"""

import json
import shlex
from filesystem import fs_manager
from audit import audit_manager

SWARM_CONFIG_PATH = "/etc/swarm.conf"

DEFAULT_SWARM_POLICY = {
    "max_remote_voltage": 10.0,
    "allow_remote_autopilot": True,
    "allow_remote_gpio": False,
    "allow_remote_force": False,
    "audit_remote_tasks": True,
}

class SwarmManager:
    """
    Manages mesh agent safety policies, voltage thresholds, and remote task dispatching.
    """

    def __init__(self, fs=None, ai=None, audit=None):
        self.fs = fs or fs_manager
        self.ai = ai
        self.audit = audit or audit_manager

    def set_ai_manager(self, ai):
        self.ai = ai

    def get_policy(self):
        """Reads and returns the current swarm safety policy from /etc/swarm.conf."""
        policy = dict(DEFAULT_SWARM_POLICY)
        node = self.fs.get_node(SWARM_CONFIG_PATH)
        if node and node.get("type") == "file":
            try:
                data = json.loads(node.get("content", "{}"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        if k in policy:
                            if isinstance(DEFAULT_SWARM_POLICY[k], bool):
                                policy[k] = bool(v)
                            elif isinstance(DEFAULT_SWARM_POLICY[k], (int, float)):
                                policy[k] = float(v)
                            else:
                                policy[k] = v
            except (json.JSONDecodeError, ValueError):
                pass
        return policy

    def set_policy_value(self, key, value, user_context=None):
        """Updates a specific policy setting in /etc/swarm.conf."""
        if key not in DEFAULT_SWARM_POLICY:
            valid_keys = ", ".join(DEFAULT_SWARM_POLICY.keys())
            return {
                "success": False,
                "error": f"Unknown policy setting: '{key}'. Valid settings: {valid_keys}"
            }

        policy = self.get_policy()
        expected_type = type(DEFAULT_SWARM_POLICY[key])

        if expected_type == bool:
            if isinstance(value, bool):
                parsed_val = value
            elif str(value).lower() in ("true", "1", "yes", "on", "enable", "enabled"):
                parsed_val = True
            elif str(value).lower() in ("false", "0", "no", "off", "disable", "disabled"):
                parsed_val = False
            else:
                return {"success": False, "error": f"Value for '{key}' must be boolean (true/false)"}
        elif expected_type in (int, float):
            try:
                parsed_val = float(value)
                if parsed_val < 0:
                    return {"success": False, "error": f"Value for '{key}' must be non-negative"}
            except (ValueError, TypeError):
                return {"success": False, "error": f"Value for '{key}' must be numeric"}
        else:
            parsed_val = str(value)

        policy[key] = parsed_val

        ctx = user_context or {"name": "root", "group": "root"}
        try:
            if not self.fs.get_node("/etc"):
                self.fs.create_directory("/etc", ctx)
            self.fs.write_file(SWARM_CONFIG_PATH, json.dumps(policy, indent=2), ctx)
            return {"success": True, "policy": policy, "updated": {key: parsed_val}}
        except Exception as e:
            return {"success": False, "error": f"Failed to save {SWARM_CONFIG_PATH}: {str(e)}"}

    def reset_policy(self, user_context=None):
        """Resets /etc/swarm.conf to default values."""
        ctx = user_context or {"name": "root", "group": "root"}
        try:
            if not self.fs.get_node("/etc"):
                self.fs.create_directory("/etc", ctx)
            self.fs.write_file(SWARM_CONFIG_PATH, json.dumps(DEFAULT_SWARM_POLICY, indent=2), ctx)
            return {"success": True, "policy": dict(DEFAULT_SWARM_POLICY)}
        except Exception as e:
            return {"success": False, "error": f"Failed to reset {SWARM_CONFIG_PATH}: {str(e)}"}

    async def handle_remote_agent_request(self, payload):
        """
        Processes an incoming mesh agent request with swarm voltage budgeting,
        GPIO safety interlocks, and provenance auditing.
        """
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        source_id = payload.get("sourceId") or payload.get("source_id") or "unknown"
        sender_user = payload.get("senderUser") or payload.get("sender_user") or "Guest"
        prompt = payload.get("prompt") or ""
        is_autopilot = bool(payload.get("isAutopilot"))
        req_max_voltage = payload.get("maxVoltage")
        is_dry_run = bool(payload.get("isDryRun"))
        is_force = bool(payload.get("isForce"))

        policy = self.get_policy()

        # Check 1: Is autopilot permitted remotely?
        if is_autopilot and not policy.get("allow_remote_autopilot", True):
            err_msg = "🛑 SWARM POLICY VIOLATION: Remote autopilot execution is disabled by target node policy."
            if policy.get("audit_remote_tasks", True):
                self.audit.log_swarm(source_id, sender_user, "SWARM_REJECTED", None, f"Prompt: {prompt} | Error: {err_msg}")
            return {"success": False, "error": err_msg}

        # Check 2: Remote force override
        effective_force = False
        if is_force:
            if policy.get("allow_remote_force", False):
                effective_force = True

        # Check 3: Determine effective voltage budget limit
        policy_max_v = float(policy.get("max_remote_voltage", 10.0))
        if req_max_voltage is not None:
            try:
                effective_limit = min(policy_max_v, float(req_max_voltage))
            except (ValueError, TypeError):
                effective_limit = policy_max_v
        else:
            effective_limit = policy_max_v

        # Prepare AI execution options
        swarm_ctx = {
            "source_id": source_id,
            "sender_user": sender_user,
            "allow_gpio": bool(policy.get("allow_remote_gpio", False)),
            "effective_limit": effective_limit
        }

        options = {
            "max_voltage_budget": effective_limit,
            "swarm_context": swarm_ctx,
            "force_override": effective_force,
            "dry_run": is_dry_run
        }

        if not self.ai:
            from executor import command_executor
            from ai_manager import AIManager
            self.ai = AIManager(self.fs, command_executor)

        config = self.ai._get_ai_config()
        provider = config.get("provider")
        model = config.get("model")

        if is_autopilot:
            result = await self.ai.perform_autopilot(prompt, [], provider, model, options)
            voltage = result.get("voltage")
            if result.get("success"):
                action_type = "SWARM_PLAN_DRY_RUN" if is_dry_run else "SWARM_AUTOPILOT"
                if policy.get("audit_remote_tasks", True):
                    self.audit.log_swarm(source_id, sender_user, action_type, voltage, f"Prompt: {prompt}")
                return {
                    "success": True,
                    "data": result.get("data", ""),
                    "voltage": voltage,
                    "safety_status": result.get("safety_status"),
                    "dry_run": is_dry_run,
                    "effective_limit": effective_limit,
                    "plan_text": result.get("plan_text"),
                    "commands": result.get("commands", [])
                }
            else:
                err_msg = result.get("error", "Autopilot execution failed.")
                if policy.get("audit_remote_tasks", True):
                    self.audit.log_swarm(source_id, sender_user, "SWARM_AUTOPILOT_FAILED", voltage, f"Prompt: {prompt} | Error: {err_msg}")
                return {
                    "success": False,
                    "error": err_msg,
                    "voltage": voltage
                }
        else:
            if is_dry_run:
                planned = await self.ai.plan_agentic_search(prompt, [], provider, model, options)
                if planned.get("success"):
                    if policy.get("audit_remote_tasks", True):
                        self.audit.log_swarm(source_id, sender_user, "SWARM_QUERY_DRY_RUN", None, f"Prompt: {prompt}")
                    return {
                        "success": True,
                        "data": f"### 🐝 SWARM PLAN (DRY RUN)\nPlan:\n{planned.get('plan_text', '')}\nCommands: {planned.get('commands', [])}",
                        "dry_run": True,
                        "plan_text": planned.get("plan_text"),
                        "commands": planned.get("commands", [])
                    }
                else:
                    return {"success": False, "error": planned.get("error", "Planning failed.")}

            result = await self.ai.perform_agentic_search(prompt, [], provider, model, options)
            if result.get("success"):
                if policy.get("audit_remote_tasks", True):
                    self.audit.log_swarm(source_id, sender_user, "SWARM_QUERY", None, f"Prompt: {prompt}")
                return {
                    "success": True,
                    "data": result.get("data", ""),
                    "effective_limit": effective_limit
                }
            else:
                err_msg = result.get("error", "Query execution failed.")
                if policy.get("audit_remote_tasks", True):
                    self.audit.log_swarm(source_id, sender_user, "SWARM_QUERY_FAILED", None, f"Prompt: {prompt} | Error: {err_msg}")
                return {"success": False, "error": err_msg}

swarm_manager = SwarmManager()
