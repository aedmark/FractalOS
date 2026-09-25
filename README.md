# FractalOS v0.1: We Put Python in Your Python So You Can Write While You Code

### An AI-centric, virtual operating system built with relentless optimism and a whole lot of Python.

This project is a bold exploration into creating a unique, web-based operating system where the primary interface is a large language model.

FractalOS is self-described as a **Narrative Operating System**. It re-imagines the OS experience by placing a Large Language Model (LLM) at the center of the user interaction loop.

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
2.  **Pyodide runtime:**
    *   The trimmed Pyodide runtime (v314.0.7, Python 3.14) is already vendored in `resources/dep/pyodide/`. Only the core files plus the `cryptography` wheel and its dependencies are kept; nothing to download.
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

*   **AI-Powered Shell:** Certain commands and programs integrate a Large Language Model directly into your terminal.
*   **Virtual File System:** A full Unix-like file system with support for users, groups, permissions (`chmod`, `chown`), and standard operations (`ls`, `cd`, `cp`, `mv`).
*   **Graphical Apps:** Includes a text editor (`edit`), paint program (`paint`), process viewer (`top`), and more.
*   **Security:** A robust permission model with `sudo` support and a virtual `/etc/sudoers` file.
*   **Cinematic Mode:** Toggle `cinematic` for a retro, typewriter-style aesthetic.
*   **Real Python:** `python script.py`, `python -c "..."`, or pipe code in. Same interpreter as the kernel, with `open()` and `input()` wired to the virtual file system and the pipe, and a step budget so a runaway loop can't freeze the page.
*   **Package Management:** (Coming Soon) Install new commands and apps dynamically.

---

## Contributing

We welcome contributions! Whether you're fixing a bug, adding a new command, or improving the documentation, your help is appreciated.

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to get started.

Working on the code with an AI session? Start with [CLAUDE.md](CLAUDE.md), then [docs/HANDOFF.md](docs/HANDOFF.md)
for where things stand, [ROADMAP.md](ROADMAP.md) for the plan, [docs/DECISIONS.md](docs/DECISIONS.md) for why
things are the way they are, and [docs/TESTING.md](docs/TESTING.md) for how to check your work.

---

## System Reference[](#system-reference)

### Available Commands[](#available-commands)

| Command<br><br>Click to sort ascending | Description<br><br>Click to sort ascending                    |
| -------------------------------------- | ------------------------------------------------------------- |
| **adventure**                          | Starts an interactive text adventure game.                    |
| **agenda**                             | Schedules commands to run at specified times.                 |
| **alias**                              | Define or display command aliases.                            |
| **awk**                                | Pattern scanning and processing language.                     |
| **backup**                             | Creates a secure backup of the system state.                  |
| **base64**                             | Base64 encode or decode data.                                 |
| **basic**                              | The Samwise BASIC Integrated Development Environment.         |
| **bc**                                 | An arbitrary precision calculator language.                   |
| **beep**                               | Play a short system sound.                                    |
| **bg**                                 | Resume a job in the background.                               |
| **binder**                             | Create and manage collections of files.                       |
| **bulletin**                           | Manages the system-wide bulletin board.                       |
| **cast**                               | Performs a magical spell within the OS.                       |
| **cat**                                | Concatenate and print files.                                  |
| **cd**                                 | Change the current directory.                                 |
| **character**                          | A tool suite for managing tabletop RPG characters.            |
| **check_fail**                         | A testing utility to check if a command fails.                |
| **chgrp**                              | Change group ownership of files.                              |
| **chidi**                              | AI-powered document and code analyst.                         |
| **chmod**                              | Change file mode bits (permissions).                          |
| **chown**                              | Change file owner.                                            |
| **cinematic**                          | Toggles the cinematic typewriter effect for terminal output.  |
| **cksum**                              | Checksum and count the bytes in a file.                       |
| **clear**                              | Clear the terminal screen.                                    |
| **clearfs**                            | Clears all files from the user's home directory.              |
| **comm**                               | Compare two sorted files line by line.                        |
| **committee**                          | Creates a collaborative project space.                        |
| **cp**                                 | Copy files and directories.                                   |
| **csplit**                             | Split a file into sections.                                   |
| **cut**                                | Remove sections from each line of files.                      |
| **date**                               | Print the system date and time.                               |
| **delay**                              | Pause script execution for a specified time.                  |
| **df**                                 | Report file system disk space usage.                          |
| **diff**                               | Compare files line by line.                                   |
| **du**                                 | Estimate file space usage.                                    |
| **echo**                               | Display a line of text.                                       |
| **edit**                               | A powerful text and code editor.                              |
| **export**                             | Download a file from SamwiseOS to your local machine.         |
| **expr**                               | Evaluate expressions.                                         |
| **fg**                                 | Resume a job in the foreground.                               |
| **find**                               | Search for files in a directory hierarchy.                    |
| **forge**                              | AI-powered scaffolding and boilerplate generation.            |
| **fsck**                               | Check and repair a file system.                               |
| **gemini**                             | Engage in a conversation with an AI model.                    |
| **grep**                               | Print lines that match patterns.                              |
| **groupadd**                           | Create a new group.                                           |
| **groupdel**                           | Delete a group.                                               |
| **groups**                             | Print the groups a user is in.                                |
| **head**                               | Output the first part of files.                               |
| **help**                               | Display information about available commands.                 |
| **history**                            | Display command history.                                      |
| **jobs**                               | Display status of jobs in the current session.                |
| **kill**                               | Send a signal to a process or job.                            |
| **less**                               | Opposite of more; a file perusal filter.                      |
| **listusers**                          | Lists all registered users on the system.                     |
| **ln**                                 | Make links between files.                                     |
| **log**                                | A personal, timestamped journal and log application.          |
| **login**                              | Begin a session on the system.                                |
| **logout**                             | Terminate a login session.                                    |
| **ls**                                 | List directory contents.                                      |
| **man**                                | Format and display the on-line manual pages.                  |
| **mkdir**                              | Make directories.                                             |
| **more**                               | File perusal filter for CRT viewing.                          |
| **mv**                                 | Move or rename files.                                         |
| **nc**                                 | Netcat utility for network communication.                     |
| **netstat**                            | Shows network status and connections.                         |
| **nl**                                 | Number lines of files.                                        |
| **ocrypt**                             | Securely encrypt and decrypt files.                           |
| **paint**                              | Opens the character-based art editor.                         |
| **passwd**                             | Change user password.                                         |
| **patch**                              | Apply a diff file to an original.                             |
| **planner**                            | Manages shared project to-do lists.                           |
| **play**                               | Plays a musical note or chord.                                |
| **post_message**                       | Sends a message to a background job.                          |
| **printf**                             | Format and print data.                                        |
| **printscreen**                        | Captures the screen content as an image or text.              |
| **ps**                                 | Report a snapshot of the current processes.                   |
| **pwd**                                | Print name of current/working directory.                      |
| **read_messages**                      | Reads all messages from a job's message queue.                |
| **reboot**                             | Reboot the system.                                            |
| **remix**                              | Synthesizes a new article from two source documents using AI. |
| **removeuser**                         | Remove a user from the system.                                |
| **rename**                             | Rename a file.                                                |
| **reset**                              | Reset the filesystem to its initial state.                    |
| **restore**                            | Restores the system state from a backup file.                 |
| **ritual**                             | Perform a multi-step, atmospheric ritual.                     |
| **rm**                                 | Remove files or directories.                                  |
| **rmdir**                              | Remove empty directories.                                     |
| **roll**                               | A utility for rolling polyhedral dice.                        |
| **run**                                | Execute commands from a file.                                 |
| **score**                              | Displays user productivity scores.                            |
| **sed**                                | Stream editor for filtering and transforming text.            |
| **set**                                | Set or display shell variables.                               |
| **shuf**                               | Generate random permutations.                                 |
| **sort**                               | Sort lines of text files.                                     |
| **storyboard**                         | Analyzes and creates a narrative summary of files.            |
| **su**                                 | Substitute user identity.                                     |
| **sudo**                               | Execute a command as another user.                            |
| **sync**                               | Synchronize data on disk with memory.                         |
| **tail**                               | Output the last part of files.                                |
| **theme**                              | Manages the visual and auditory theme of the OS.              |
| **top**                                | Displays a real-time view of running processes.               |
| **touch**                              | Change file timestamps.                                       |
| **tr**                                 | Translate, squeeze, and/or delete characters.                 |
| **tree**                               | List contents of directories in a tree-like format.           |
| **unalias**                            | Remove alias definitions.                                     |
| **uniq**                               | Report or omit repeated lines.                                |
| **unset**                              | Unset shell variables.                                        |
| **unzip**                              | List, test and extract compressed files in a ZIP archive.     |
| **upload**                             | Upload files from your local machine to SamwiseOS.            |
| **uptime**                             | Tell how long the system has been running.                    |
| **useradd**                            | Create a new user.                                            |
| **usermod**                            | Modify a user account.                                        |
| **visudo**                             | Edit the sudoers file safely.                                 |
| **wc**                                 | Print newline, word, and byte counts for each file.           |
| **who**                                | Show who is logged on.                                        |
| **whoami**                             | Print effective user ID.                                      |
| **xargs**                              | Build and execute command lines from standard input.          |
| **xor**                                | Perform XOR encryption/decryption.                            |
| **zip**                                | Package and compress (archive) files.                         |

### Graphical Applications[](#graphical-applications)

|Command<br><br>Click to sort ascending|Application Name<br><br>Click to sort ascending|Description<br><br>Click to sort ascending|
|---|---|---|
|**edit**|SamwiseOS Editor|A full-featured text and code editor with Markdown/HTML preview.|
|**paint**|SamwiseOS Paint|A character-based art and ASCII editor.|
|**chidi**|Chidi Analyst|An AI-powered tool to summarize, study, and ask questions about your documents.|
|**gemini**|Gemini Chat|An interactive, graphical chat session with the system's AI.|
|**top**|Process Viewer|A real-time display of all running background jobs.|
|**log**|Captain's Log|A personal, timestamped journal application.|
|**basic**|Samwise BASIC|An integrated development environment for the BASIC programming language.|
|**adventure**|Text Adventure|A classic interactive fiction game engine.|
