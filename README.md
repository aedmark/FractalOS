# FractalOS v0.0.5: The Little OS That Could

### An AI-centric operating system built with relentless optimism and a whole lot of Python.

This project is a bold exploration into creating a unique, web-based operating system where the primary interface is a generative AI. After a successful and system-wide migration, our core logic now runs on a robust Python kernel, making the OS more powerful and extensible than ever. It's a testament to what we can achieve with a can-do attitude, a lot of heart, and a little help from our friends (even the digital ones!).

## What is this?

FractalOS is a **Hybrid Web Operating System**. It reimagines the OS experience by placing a Large Language Model (LLM) at the center of the user interaction loop.

Instead of clicking icons or memorizing complex CLI flags, you converse with the system. The AI acts as your intelligent agent, capable of understanding natural language, executing system commands, managing files, and even writing code on your behalf.

Technically, it is a single-page web application that runs entirely in your browser (or as a native desktop app), combining the reach of the web with the power of a full Python environment.

## The Hybrid Architecture

Our architecture is a deliberate fusion of two powerful environments:

1.  **The Python Kernel (Backend):**
    *   Runs inside the browser using **Pyodide** (WebAssembly).
    *   Acts as the single source of truth for the system state.
    *   Manages the virtual file system, user/group permissions, process scheduling, and complex command logic.
    *   It is sandboxed and secure.

2.  **The JavaScript Frontend (Stage Manager):**
    *   Handles the UI, DOM manipulation, and browser APIs.
    *   Manages the terminal interface, sound synthesis, and graphical applications.
    *   Communicates with the kernel via a strict `syscall` bridge.

### The `effect` Contract

The magic happens through a pattern we call the **Effect Contract**. When the Python kernel needs to do something it can't do natively (like playing a sound or opening a modal), it doesn't try to hack the DOM. Instead, it returns a JSON `effect` object.

*   **User:** "Play a C major chord."
*   **Kernel:** Returns `{"effect": "play_sound", "notes": ["C4", "E4", "G4"], "duration": "4n"}`
*   **Frontend:** Receives the effect and uses Tone.js to generate the audio.

This keeps our core logic clean, testable, and decoupled from the display layer.

---

## How to Run

FractalOS is designed to be flexible. You can run it in two modes:

### 1. Browser Mode (Quick Start)
Great for quick testing and development. No installation required other than a simple web server.

*   **Pros:** Instant start, works on any device with a modern browser.
*   **Cons:** No access to your real hard drive (uses IndexedDB), some native features disabled.

**Steps:**
1.  **Clone the repository.**
2.  **Download Pyodide:**
    *   Download the Pyodide distribution (v0.26.0 or compatible) and extract it into `resources/dep/pyodide/`.
3.  **Start a Web Server:**
    *   Run `python -m http.server` in the project root.
4.  **Open in Browser:**
    *   Navigate to `http://localhost:8000`.

### 2. Portable Mode (Recommended)
The full experience. Runs as a standalone desktop application using **Neutralinojs**.

*   **Pros:** Native file system access (saves data to `data/`), system tray support, window management.
*   **Cons:** Requires the Neutralinojs binary.

**Steps:**
1.  **Download the Neutralinojs binary** for your OS and place it in the root directory.
2.  **Run the binary.**
    *   **Linux/Mac:** `./neutralino-linux_x64` (or similar)
    *   **Windows:** `neutralino-win_x64.exe`

---

## Features

*   **🧠 AI-Powered Shell:** The `gemini` command integrates a Large Language Model directly into your terminal. Ask it to "summarize my documents," "write a Python script to calculate pi," or "tell me a story."
*   **📁 Virtual File System:** A full Unix-like file system with support for users, groups, permissions (`chmod`, `chown`), and standard operations (`ls`, `cd`, `cp`, `mv`).
*   **🎨 Graphical Apps:** Includes a text editor (`edit`), paint program (`paint`), process viewer (`top`), and more.
*   **🛡️ Security:** A robust permission model with `sudo` support and a virtual `/etc/sudoers` file.
*   **🎭 Cinematic Mode:** Toggle `cinematic` for a retro, typewriter-style aesthetic.
*   **📦 Package Management:** (Coming Soon) Install new commands and apps dynamically.

## System Reference

### Core Commands
| Command | Description |
| :--- | :--- |
| `gemini` | Chat with the system AI. |
| `edit` | Open the text editor. |
| `paint` | Open the pixel art editor. |
| `help` | List all available commands. |
| `man <cmd>` | Show the manual page for a command. |
| `ls`, `cd`, `pwd` | Standard file system navigation. |
| `cat`, `grep`, `echo` | Text processing tools. |
| `python` | (Planned) Run Python scripts directly. |

*(For a full list, run `help` inside the OS)*

---

## Contributing

We welcome contributions! Whether you're fixing a bug, adding a new command, or improving the documentation, your help is appreciated.

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to get started.

---

## The Road Ahead

We are currently working on **Milestone 1: The AI Town Manager**, focusing on giving the AI long-term memory and the ability to perform complex, multi-step tasks autonomously.

Join us on this journey!