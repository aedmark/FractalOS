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
            {'name': 'chat-internal', 'long': 'chat-internal', 'takes_value': True, 'hidden': True},
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
        user_prompt = flags.get('chat-internal')
        history = json.loads(stdin_data) if stdin_data else []
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

    if is_dry_run:
        plan_result = await ai_manager.perform_agentic_search(user_prompt, [], provider, model, {"apiKey": api_key})
        if plan_result.get("effect"):
            return plan_result
        if plan_result.get("success"):
            if isinstance(plan_result.get("data"), str):
                return {
                    "effect": "display_prose",
                    "header": "Samwise Dry-Run Plan",
                    "content": plan_result.get("data")
                }
            return f"Dry run invoked: '{user_prompt}'"
        else:
            return plan_result

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
        Display the command plan without executing it.

EXAMPLES
    samwise "how do I list files?"
    samwise --autopilot "create a folder named 'Void' and put a readme in it"
    samwise --autopilot --force "delete the 'Void' folder"
"""

def help(args, flags, user_context, **kwargs):
    return 'Usage: samwise [-c | --autopilot] [OPTIONS] "<prompt>"'