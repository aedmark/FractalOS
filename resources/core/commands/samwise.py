import asyncio
import json

def define_flags():
    """Declares the flags that the samwise command accepts."""
    return {
        'flags': [
            {'name': 'chat', 'short': 'c', 'long': 'chat', 'takes_value': False},
            {'name': 'autopilot', 'short': 'a', 'long': 'autopilot', 'takes_value': False, 'description': 'Engage BoneAmanita Autopilot Mode.'},
            {'name': 'force', 'short': 'f', 'long': 'force', 'takes_value': False, 'description': 'Override safety interlocks for High Voltage actions.'},
            {'name': 'provider', 'short': 'p', 'long': 'provider', 'takes_value': True},
            {'name': 'model', 'short': 'm', 'long': 'model', 'takes_value': True},
            {'name': 'chat-internal', 'long': 'chat-internal', 'takes_value': False, 'hidden': True},
            {'name': 'resume-agent', 'long': 'resume-agent', 'takes_value': True, 'hidden': True},
            {'name': 'dry-run', 'long': 'dry-run', 'takes_value': False},
        ],
        'metadata': {}
    }

async def run(args, flags, user_context, stdin_data=None, api_key=None, ai_manager=None, **kwargs):
    """
    Engages in a context-aware conversation OR activates Autopilot.
    """
    if not ai_manager:
        return {
            "success": False,
            "error": {
                "message": "samwise: AI Manager is not available.",
                "suggestion": "This is an internal system error. Please try again later."
            }
        }

    provider = flags.get('provider')
    model = flags.get('model')
    is_dry_run = flags.get('dry-run', False)
    is_autopilot = flags.get('autopilot', False)
    force_override = flags.get('force', False)

    if flags.get('chat', False):
        return {
            "effect": "launch_app",
            "app_name": "SamwiseChat",
            "options": {
                "provider": provider,
                "model": model
            }
        }

    if flags.get('chat-internal'):
        # Samwise Chat sends {"prompt", "history", "provider", "model"} as JSON on stdin, never on the
        # command line, so the shell cannot expand anything the user typed (P2-20).
        try:
            payload = json.loads(stdin_data) if stdin_data else None
        except (TypeError, ValueError):
            payload = None
        if not isinstance(payload, dict) or not isinstance(payload.get("prompt"), str) or not payload["prompt"].strip():
            return {"success": False, "error": {
                "message": "samwise: --chat-internal expects a JSON message on stdin.",
                "suggestion": "This flag belongs to Samwise Chat. Open it with 'samwise -c'."}}
        user_prompt = payload["prompt"]
        history = payload.get("history") or []
        provider = payload.get("provider") or provider
        model = payload.get("model") or model
        result = await ai_manager.continue_chat_conversation(
            user_prompt,
            history,
            provider,
            model,
            api_key
        )
        if result["success"]:
            return result.get("answer")
        else:
            return {"success": False, "error": result["error"]}

    if flags.get('resume-agent'):
        try:
            state = json.loads(flags.get('resume-agent'))
        except json.JSONDecodeError as e:
            return {"success": False, "error": {"message": "samwise: failed to decode resume state", "suggestion": str(e)}}
        
        result = await ai_manager.resume_agentic_search(state, provider, model, {"apiKey": api_key})
        if result.get("effect"):
            return result
        if result.get("success"):
            return {
                "effect": "display_prose",
                "header": "Samwise",
                "content": result.get("data")
            }
        else:
            return {
                "success": False,
                "error": {
                    "message": "samwise: The AI agent failed to complete the request.",
                    "suggestion": f"Reason: {result.get('error', 'Unknown error')}"
                }
            }

    if not args:
        return {
            "success": False,
            "error": {
                "message": "samwise: insufficient arguments.",
                "suggestion": "Try 'samwise \"<prompt>\"' or 'samwise --autopilot \"<task>\"'."
            }
        }

    user_prompt = " ".join(args)

    if is_dry_run:
        return await _dry_run(ai_manager, user_prompt, provider, model, api_key, is_autopilot, force_override)

    if is_autopilot:
        result = await ai_manager.perform_autopilot(
            user_prompt, 
            [], 
            provider, 
            model, 
            {
                "apiKey": api_key, 
                "force_override": force_override
            }
        )
        
        if result["success"]:
            return {
                "effect": "display_prose",
                "header": "🍄 BoneAmanita Autopilot Report",
                "content": result.get("data")
            }
        else:
            return {
                "success": False,
                "error": {
                    "message": "Autopilot Disengaged." if "DISENGAGED" in str(result.get("error")) else "Autopilot stopped.",
                    "suggestion": result.get("error")
                }
            }

    result = await ai_manager.perform_agentic_search(user_prompt, [], provider, model, {"apiKey": api_key})

    if result.get("effect"):
        return result
    if result.get("success"):
        return {
            "effect": "display_prose",
            "header": "Samwise",
            "content": result.get("data")
        }
    else:
        return {
            "success": False,
            "error": {
                "message": "samwise: The AI agent failed to complete the request.",
                "suggestion": f"Reason: {result.get('error', 'Unknown error')}"
            }
        }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    samwise - The AI Interface for FractalOS.

SYNOPSIS
    samwise [OPTIONS] "<prompt>"

DESCRIPTION
    The samwise command is the bridge to the AI Kernel. It has two primary modes:
    1. **Agent Mode (Default):** A helpful assistant that answers questions.
    2. **Autopilot Mode (--autopilot):** A kinetic driver (BoneAmanita) that EXECUTES tasks.

OPTIONS
    -c, --chat
        Open an interactive, graphical chat session.

    -a, --autopilot
        Engage BoneAmanita Autopilot. The AI will DIRECTLY execute commands to
        fulfill your request. Use with caution.
        
    -f, --force
        Override Safety Interlocks. Allows the Autopilot to perform High Voltage
        actions (like mass deletion) without braking.

    -p, --provider <name>
        Specify the AI provider (e.g., 'gemini', 'ollama').

    -m, --model <name>
        Specify the exact model name.

    --dry-run
        Show the plan and what would happen, without running any of it: which steps
        would ask first, or (with --autopilot) the voltage and whether it would
        disengage. Beats --force. Only pwd and ls run, so the model can see where you are.

CONFIGURATION
    /etc/ai.conf is JSON. "provider" and "model" set the defaults that -p and -m
    override. "timeout_seconds" is how long to wait for one reply before giving
    up (default 120). A big model loading from a cold start can need more.

EXAMPLES
    samwise "how do I list files?"
    samwise --autopilot "create a folder named 'Void' and put a readme in it"
    samwise --autopilot --force "delete the 'Void' folder"
"""

def help(args, flags, user_context, **kwargs):
    return 'Usage: samwise [-c | --autopilot] [OPTIONS] "<prompt>"'


def _plan_block(commands, notes=None):
    notes = notes or {}
    lines = [f"{i}. {c}{notes.get(c, '')}" for i, c in enumerate(commands, 1)]
    return "```\n" + "\n".join(lines) + "\n```"


async def _dry_run(ai_manager, user_prompt, provider, model, api_key, is_autopilot, force_override):
    """Ask for a plan and say what would happen. Nothing in the plan runs (P2-16).

    Only `pwd` and `ls -la` run, to show the model where the shell is.
    """
    options = {"apiKey": api_key}
    if is_autopilot:
        planned = await ai_manager.plan_autopilot(user_prompt, provider, model, options)
    else:
        planned = await ai_manager.plan_agentic_search(user_prompt, [], provider, model, options)
    if not planned.get("success"):
        return {"success": False, "error": {
            "message": "samwise: the dry run could not get a plan.",
            "suggestion": f"Reason: {planned.get('error', 'Unknown error')}"}}

    header = "Samwise Dry Run" + (" (Autopilot)" if is_autopilot else "")
    parts = ["**Nothing was executed.** This is what would happen."]
    if planned.get("warning"):
        parts.append(planned["warning"])
    commands = planned["commands"]

    if not commands:
        parts.append("No commands. The model would answer directly:")
        parts.append(planned["plan_text"])
    elif planned["refusal"]:
        parts.append(_plan_block(commands))
        parts.append(f"**Would halt before any step runs:** {planned['refusal']}.")
    elif is_autopilot:
        voltage = planned["voltage"]
        parts.append(_plan_block(commands))
        parts.append(f"**Voltage:** {voltage} ({planned['safety_status']})")
        if voltage >= 20.0 and not force_override:
            parts.append("**Would disengage.** Nothing would run. Add `--force` to run it after a home checkpoint.")
        else:
            steps = "save a home checkpoint, then run every step" if planned["needs_checkpoint"] else "run every step"
            forced = " (`--force` overrides the voltage brake)" if voltage >= 20.0 else ""
            parts.append(f"**Would {steps}**{forced}, stopping at the first failure.")
    else:
        confirm = set(planned["confirm"])
        parts.append(_plan_block(commands, {c: "    <- asks you first" for c in confirm}))
        if confirm:
            parts.append(f"**Would ask before {len(confirm)} step{'' if len(confirm) == 1 else 's'}**, then summarize the output.")
        else:
            parts.append("**Would run every step without asking**, then summarize the output.")

    return {"effect": "display_prose", "header": header, "content": "\n\n".join(parts)}

