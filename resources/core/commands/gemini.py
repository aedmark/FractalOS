# gem/core/commands/gemini.py

import asyncio
import json

def define_flags():
    """Declares the flags that the gemini command accepts."""
    return {
        'flags': [
            {'name': 'chat', 'short': 'c', 'long': 'chat', 'takes_value': False},
            {'name': 'autopilot', 'short': 'a', 'long': 'autopilot', 'takes_value': False, 'description': 'Engage BoneAmanita Autopilot Mode.'},
            {'name': 'force', 'short': 'f', 'long': 'force', 'takes_value': False, 'description': 'Override safety interlocks for High Voltage actions.'},
            {'name': 'provider', 'short': 'p', 'long': 'provider', 'takes_value': True},
            {'name': 'model', 'short': 'm', 'long': 'model', 'takes_value': True},
            {'name': 'chat-internal', 'long': 'chat-internal', 'takes_value': True, 'hidden': True},
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
                "message": "gemini: AI Manager is not available.",
                "suggestion": "This is an internal system error. Please try again later."
            }
        }

    provider = flags.get('provider')
    model = flags.get('model')
    is_dry_run = flags.get('dry-run', False)
    is_autopilot = flags.get('autopilot', False)
    force_override = flags.get('force', False)

    # --- MODE 1: GRAPHICAL CHAT ---
    if flags.get('chat', False):
        return {
            "effect": "launch_app",
            "app_name": "GeminiChat",
            "options": {
                "provider": provider,
                "model": model
            }
        }

    # --- MODE 2: INTERNAL CHAT (Used by App) ---
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

    if not args:
        return {
            "success": False,
            "error": {
                "message": "gemini: insufficient arguments.",
                "suggestion": "Try 'gemini \"<prompt>\"' or 'gemini --autopilot \"<task>\"'."
            }
        }

    user_prompt = " ".join(args)

    # --- MODE 3: BONEAMANITA AUTOPILOT ---
    if is_autopilot:
        # Route to the BoneDriver logic
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
            # Autopilot returns a pre-formatted report string in 'data'
            return {
                "effect": "display_prose",
                "header": "🍄 BoneAmanita Autopilot Report",
                "content": result.get("data")
            }
        else:
            # If Autopilot braked (High Voltage), we return the error
            return {
                "success": False,
                "error": {
                    "message": "Autopilot Disengaged.",
                    "suggestion": result.get("error")
                }
            }

    # --- MODE 4: STANDARD AGENTIC SEARCH (Dry Run) ---
    if is_dry_run:
        plan_result = await ai_manager.perform_agentic_search(user_prompt, [], provider, model, {"apiKey": api_key})
        if plan_result["success"]:
            if isinstance(plan_result.get("data"), str):
                return {
                    "effect": "display_prose",
                    "header": "Gemini Dry-Run Plan",
                    "content": plan_result.get("data")
                }
            return f"Dry run invoked: '{user_prompt}'"
        else:
            return plan_result

    # --- MODE 5: STANDARD AGENTIC SEARCH (Execute) ---
    result = await ai_manager.perform_agentic_search(user_prompt, [], provider, model, {"apiKey": api_key})

    if result["success"]:
        return {
            "effect": "display_prose",
            "header": "Gemini Response",
            "content": result.get("data")
        }
    else:
        return {
            "success": False,
            "error": {
                "message": "gemini: The AI agent failed to complete the request.",
                "suggestion": f"Reason: {result.get('error', 'Unknown error')}"
            }
        }

def man(args, flags, user_context, **kwargs):
    return """
NAME
    gemini - The AI Interface for FractalOS.

SYNOPSIS
    gemini [OPTIONS] "<prompt>"

DESCRIPTION
    The gemini command is the bridge to the AI Kernel. It has two primary modes:
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
    gemini "how do I list files?"
    gemini --autopilot "create a folder named 'Void' and put a readme in it"
    gemini --autopilot --force "delete the 'Void' folder"
"""

def help(args, flags, user_context, **kwargs):
    return 'Usage: gemini [-c | --autopilot] [OPTIONS] "<prompt>"'