# Contributing to FractalOS

Welcome! We're thrilled you're interested in contributing to FractalOS. This project is a labor of love, and we want to make it as easy as possible for you to join in.

Whether you're a Python pro, a JavaScript wizard, or just getting started, there's a place for you here.

## Table of Contents

1.  [Getting Started](#getting-started)
2.  [Project Structure](#project-structure)
3.  [Developing Commands (Python)](#developing-commands-python)
4.  [Developing Frontend (JavaScript)](#developing-frontend-javascript)
5.  [Testing & Verification](#testing--verification)
6.  [Style Guide](#style-guide)

---

## Getting Started

1.  **Fork the repository** on GitLab.
2.  **Clone your fork** locally.
3.  **Set up the environment** (see `README.md` for "How to Run").
4.  **Create a branch** for your feature or fix (`git checkout -b feature/my-cool-feature`).

---

## Project Structure

*   `resources/core/`: **The Python Kernel.** This is where the OS logic lives.
    *   `commands/`: Individual command modules (e.g., `ls.py`, `grep.py`).
    *   `apps/`: Backend logic for GUI apps.
    *   `kernel.py`: The main kernel loop and syscall handler.
*   `resources/scripts/`: **The JavaScript Frontend.**
    *   `main.js`: Entry point and initialization.
    *   `terminal_ui.js`: Handles user input and terminal rendering.
    *   `bridge.js`: The communication layer between JS and Python.
*   `resources/dep/`: External dependencies (Pyodide, Tone.js, etc.).

---

## Developing Commands (Python)

Commands are the lifeblood of FractalOS. They are written in Python and run inside the kernel.

### How to Add a New Command

1.  **Create the File:** Add a new Python file in `resources/core/commands/`. Name it after your command (e.g., `roll.py`).
2.  **Implement the Interface:** Your module **must** implement these three functions:

    ```python
    def run(args, flags, user_context, **kwargs):
        # Your logic here
        return {"success": True, "output": "Hello World"}

    def help(args, flags, user_context, **kwargs):
        return "Usage: roll [OPTIONS]"

    def man(args, flags, user_context, **kwargs):
        return """
    NAME
        roll - Roll some dice
    ...
    """
    ```

3.  **Return Standard Responses:**
    *   **Success:** `return {"success": True, "output": "..."}`
    *   **Error:** `return {"success": False, "error": {"message": "...", "suggestion": "..."}}`
    *   **Effect:** `return {"success": True, "effect": {"name": "play_sound", ...}}`

### The "Golden Standard"
Refer to `resources/core/commands/grep.py` or `resources/core/commands/ls.py` for examples of robust, well-structured commands.

---

## Developing Frontend (JavaScript)

The frontend handles everything the user *sees* and *hears*.

*   **UI Components:** Use `resources/scripts/ui_components.js` for reusable UI elements.
*   **Styling:** We use vanilla CSS in `resources/main.css`. Keep it clean and semantic.
*   **Effects:** If you need to add a new capability (like a new sound or visual effect), add a handler in `resources/scripts/effect_handler.js`.

---

## Testing & Verification

Since this is a hybrid OS, testing can be tricky.

### Manual Testing Checklist
Before submitting a Merge Request, please verify:

1.  **Browser Compatibility:** Does it work in Chrome/Firefox?
2.  **Mode Compatibility:** Does it work in both **Browser Mode** (Python server) and **Portable Mode** (Neutralino)?
    *   *Tip: Use `window.NL_PORT` to check if you are in Portable Mode.*
3.  **Error Handling:** What happens if the user types garbage input? Does the app crash, or show a nice error message?

---

## Style Guide

*   **Python:** PEP 8. Keep it readable.
*   **JavaScript:** Modern ES6+. Use `async/await` over callbacks where possible.
*   **Commits:** Write clear, descriptive commit messages.

Thank you for helping us build the little OS that could! 🚀