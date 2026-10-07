# FractalOS 1.0: The Living Terminal & Distributed Mesh

### A browser-based, Unix-flavoured virtual operating system with a Python kernel under WebAssembly, distributed P2P mesh swarms, and an LLM living in your shell.

FractalOS is an open-source, narrative operating system where the primary interface is a large language model paired with a Unix-like environment.

Instead of rigid static interfaces, you converse with the system or drive it through familiar command-line paradigms. The built-in AI agent (`samwise`, powered by local Ollama or the Gemini API) understands natural language, executes shell pipelines, manages files, inspects hardware, delegates tasks across peer nodes, and writes code on your behalf under safety voltage policies.

FractalOS runs entirely client-side in your browser, as a standalone native desktop application via Neutralinojs, or as a dedicated bare-metal kiosk appliance on Raspberry Pi hardware.

---

## The Hybrid Architecture

FractalOS is built on a deliberate fusion of two decoupled environments:

1. **The Python Kernel (Backend):**
   * Runs inside the browser using **Pyodide** (WebAssembly / CPython 3.14).
   * Acts as the single source of truth for all system state.
   * Manages the virtual file system (VFS), user/group permissions, process scheduling, package auditing, and command logic.
   * Sandboxed, secure, and fully testable without a browser.

2. **The JavaScript Frontend (Stage Manager):**
   * Handles the UI, DOM manipulation, and browser APIs.
   * Manages the terminal interface, multiplexed split panes, floating/docked window manager, Tone.js sound synthesis, and graphical applications.
   * Communicates with the kernel via a strict `syscall` bridge.

3. **The Distributed P2P Mesh:**
   * Peer discovery and real-time communication via WebRTC data channels, BroadcastChannel, and optional WebSocket signaling.
   * Multi-node shell attachment, remote file copying (`mesh-cp`), distributed multi-agent task swarms, and multiplayer gaming.

### The Effect Contract

When the Python kernel needs to perform an action outside its WebAssembly sandbox (playing audio, opening a modal window, splitting a pane, copying to host clipboard), it returns a structured JSON `effect` object.

* **User:** `play C4 E4 G4`
* **Kernel:** Returns `{"effect": "play_sound", "notes": ["C4", "E4", "G4"], "duration": "4n"}`
* **Frontend:** Receives the effect via `effect_handler.js` and synthesizes the audio with Tone.js.

This decoupling keeps core system logic clean, auditable, and isolated from presentation.

---

## How to Run

FractalOS is designed to run anywhere modern web standards or native runtimes exist:

### 1. Browser Mode (Quick Start)
Instant start on any device with a modern browser. No build steps or npm installations required.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/aedmark/FractalOS.git
   cd FractalOS
   ```
2. **Start a local web server:**
   ```bash
   python3 -m http.server 8000 --directory resources
   ```
3. **Open in your browser:**
   Navigate to [http://localhost:8000](http://localhost:8000).

> **Note:** The trimmed Pyodide runtime (v314.0.7, Python 3.14.2) and core cryptography dependencies are pre-vendored in `resources/dep/pyodide/`. Everything loads locally without external CDN fetches.

### 2. Portable Desktop Mode (Recommended)
Run FractalOS as a standalone native desktop application with local file system persistence (`data/`) using **Neutralinojs**.

1. Download the [Neutralinojs](https://neutralino.js.org/) binary for your operating system and place it in the project root.
2. Launch the binary:
   * **Linux/macOS:** `./neutralino-linux_x64` (or `neutralino-mac_x64`)
   * **Windows:** `neutralino-win_x64.exe`

### 3. Bare-Metal Appliance Mode (Fractal Pi)
Deploy FractalOS as a dedicated boot-to-shell appliance on Raspberry Pi or ARM64 single-board computers.

1. Review `extras/build_distro.sh` to configure auto-login, kiosk display server, and hardware GPIO mappings.
2. Flash the base appliance image onto an SD card or eMMC storage.
3. Boot directly into the FractalOS living shell with active hardware pin sensing and auto-mesh discovery.

---

## Key Features in 1.0

* **The Living Shell & Kinetic AI (`samwise`):**
  * **Autopilot & Persona:** Full kinetic automation (`samwise --autopilot`) powered by the BoneAmanita driver.
  * **Voltage Safety:** Automatic risk analysis calculating execution voltage (e.g. destructive commands trigger confirmation or require `--force`).
  * **Inner Validation Retry Loop:** If an LLM generates invalid flags or syntax, the kernel explains the error back to the model for self-correction.
  * **Scar Tissue:** Ephemeral execution failure context injected into system prompts to prevent repetitive mistakes.
  * **Atomic File Generation (`forge`):** Dedicated tool for the model to scaffold and write files cleanly without shell escaping issues.
  * **Dry-Run Planning:** Preview complete agent execution plans, voltage scores, and prompts with `samwise --dry-run`.

* **Distributed P2P Mesh & Swarms:**
  * **Mesh Discovery & Status:** Real-time peer discovery and telemetry (`peers`, `netstat --mesh`).
  * **Remote Shells & Collaboration:** Attach directly to peer terminals across nodes (`attach`, `detach`, `wall`, `talk`).
  * **Zero-Cloud File Transfer (`mesh-cp`):** Secure peer-to-peer file transfer over WebRTC data channels.
  * **Multi-Agent Swarm Delegation:** Dispatch tasks from one node's agent to peer agents across the mesh and synthesize outcomes.
  * **Multiplayer TUI Gaming:** Built-in network games like Connect 4 (`c4`) and the NetGame hub (`netgame`).

* **Terminal Multiplexing & Window Manager:**
  * **Split Panes:** Divide the terminal into horizontal and vertical split panes (`split-h`, `split-v`, `panes`, `close_pane`).
  * **Window Manager (`wm` / `window`):** Float, dock, tile, minimize, or maximize graphical apps beside your terminal panes.
  * **System Status & Notifications:** Persistent status monitor and notification system (`status`, `notify`).
  * **Host Clipboard Bridge:** Seamless clipboard sync (`clip`, `pbcopy`, `pbpaste`) and file drag-and-drop straight into the virtual file system.

* **Physical IoT & Sensor Automation (`gpio`):**
  * Read and write GPIO pins, listen to hardware button interrupts, stream sensor data, and configure agent automation rules.

* **Package Ecosystem & Sandboxing (`pkg`):**
  * Package manager supporting dependency resolution, manifest validation, cryptographic hash checks (`pkg verify`), permission audits (`pkg audit`), and custom repository publishing (`pkg publish`).
  * Pre-packaged community utilities including `fortune`, `cowsay`, `cal`, and `banner`.

* **Real In-OS Python (`python`):**
  * Execute Python scripts, inline expressions (`python -c "..."`), or pipelines in CPython 3.14. Wired to the virtual file system, permissions, standard streams, and a step budget to prevent runaway loops.

* **Unix Virtual File System & Story Versioning:**
  * Hierarchical file system with full POSIX permissions (`chmod`, `chown`, `chgrp`), users, groups, `/etc/sudoers`, `/etc/passwd`, and symlinks.
  * **Story Versioning (`story`):** Snapshot-based file version control native to the VFS.
  * **Audit Trails:** Complete system audit logging (`/var/log/audit.log`).

---

## Graphical Applications

| Command | Application Name | Description |
| --- | --- | --- |
| **edit** | FractalOS Editor | Text and code editor with Markdown and HTML live preview. |
| **paint** | FractalOS Paint | Character-based ASCII art studio with export capabilities. |
| **chidi** | Chidi Analyst | AI-powered document analyzer, summarizer, and research assistant. |
| **samwise -c** | Samwise Chat | Dedicated conversational AI chat interface. |
| **top** | Process Viewer | Real-time monitoring of running background jobs and system resources. |
| **log** | Captain's Log | Timestamped personal journal and note-taking application. |
| **basic** | Fractal BASIC | Integrated development environment for the BASIC programming language. |
| **adventure** | Text Adventure | Classic interactive fiction engine and game creator. |
| **peers** | Mesh Peer Discovery | Visual dashboard of discovered mesh nodes, latency, and capabilities. |
| **netgame** | NetGame Hub | Networked multiplayer gaming lobby across the P2P mesh. |
| **wm** | Window Manager | Controls floating, tiled, and docked application windows. |

---

## System Command Reference

FractalOS includes 150+ built-in commands and utilities:

| Command | Description |
| --- | --- |
| **adventure** | Interactive text adventure game engine and story player. |
| **agenda** | Schedule commands to run at specified times or intervals. |
| **alias** | Define or display command aliases. |
| **attach** | Attach to a shared terminal session across FractalOS mesh nodes. |
| **awk** | Pattern scanning and processing language. |
| **backup** | Creates a secure backup of the current FractalOS system state. |
| **base64** | Base64 encode or decode data and print to standard output. |
| **basic** | The Fractal Basic Integrated Development Environment. |
| **bc** | An arbitrary precision calculator language. |
| **beep** | Play a short system sound. |
| **bg** | Resume a job in the background. |
| **binder** | A tool for creating and managing collections of files. |
| **bulletin** | Manages the system-wide bulletin board. |
| **c4** | Terminal multiplayer Connect 4 game over local or mesh network. |
| **cast** | Performs a magical spell within the OS. |
| **cat** | Concatenate files and print on the standard output. |
| **cd** | Change the current directory. |
| **character** | A tool suite for managing tabletop RPG characters. |
| **check_fail** | Checks command failure or empty output (for testing). |
| **chgrp** | Change group ownership. |
| **chidi** | Opens the Chidi AI-powered document and code analyst. |
| **chmod** | Change file mode bits. |
| **chown** | Change file owner. |
| **cinematic** | Toggles the cinematic typewriter effect for terminal output. |
| **cksum** | Checksum and count the bytes in a file. |
| **clear** | Clear the terminal screen. |
| **clearfs** | Clears all files from the current user's home directory. |
| **clip** | Clipboard bridge between host OS and FractalOS shell. |
| **close_pane** | Close an active terminal split pane. |
| **comm** | Compare two sorted files line by line. |
| **committee** | Creates and manages a collaborative project space. |
| **cp** | Copy files and directories. |
| **csplit** | Split a file into sections determined by context lines. |
| **cut** | Remove sections from each line of files. |
| **date** | Print the system date and time. |
| **delay** | Pause script or command execution for a specified time. |
| **detach** | Detach from an active remote FractalOS terminal session. |
| **df** | Report file system disk space usage. |
| **diff** | Compare files line by line. |
| **du** | Estimate file space usage. |
| **echo** | Display a line of text. |
| **edit** | A powerful, context-aware text and code editor. |
| **export** | Download a file from FractalOS to your local machine. |
| **expr** | Evaluate expressions. |
| **fg** | Resume a job in the foreground. |
| **find** | Search for files in a directory hierarchy. |
| **focus** | Switch focus between terminal split panes. |
| **forge** | AI-assisted code generator and atomic file writer. |
| **fsck** | Check and repair a file system. |
| **gpio** | Control physical/simulated GPIO pins, sensor streaming, and alerts. |
| **grep** | Print lines that match patterns. |
| **groupadd** | Create a new group. |
| **groupdel** | Delete a group. |
| **groups** | Print the groups a user is in. |
| **head** | Output the first part of files. |
| **help** | Display information about available commands. |
| **history** | Display command history. |
| **jobs** | Display status of jobs in the current session. |
| **kill** | Send a signal to a process or job. |
| **less** | Opposite of more; a file perusal filter. |
| **listusers** | Lists all registered users on the system. |
| **ln** | Make links between files. |
| **log** | A personal, timestamped journal and log application. |
| **login** | Begin a session on the system. |
| **logout** | Terminate a login session. |
| **ls** | List directory contents. |
| **man** | Format and display the on-line manual pages. |
| **mesh_agent** | Delegate tasks and queries to peer AI agents across the FractalOS mesh network. |
| **mesh_cp** | Copy files peer-to-peer across connected FractalOS nodes. |
| **mkdir** | Make directories. |
| **more** | File perusal filter for CRT viewing. |
| **mount** | Mount host directories into the VFS (portable mode only). |
| **mv** | Move or rename files and directories. |
| **nc** | Netcat utility for network communication. |
| **netgame** | Multiplayer networked gaming hub across the mesh. |
| **netstat** | Shows network status, connections, and mesh presence. |
| **nl** | Number lines of files. |
| **notify** | Send desktop/system notifications and alerts. |
| **ocrypt** | Securely encrypt and decrypt files. |
| **paint** | Opens the character-based art editor. |
| **panes** | List and manage active terminal split panes. |
| **passwd** | Change user password. |
| **patch** | Apply a diff file to an original. |
| **pbcopy** | Copy standard input or arguments to the system clipboard. |
| **pbpaste** | Print clipboard content to standard output. |
| **peers** | Inspect discovered mesh nodes, latency, and capabilities. |
| **pkg** | Package manager and publisher with dependency resolution and audit. |
| **planner** | Manages shared and personal project to-do lists. |
| **play** | Plays a musical note or chord. |
| **post_message** | Sends a message to a background job. |
| **printf** | Format and print data. |
| **printscreen** | Captures the screen content as an image or text. |
| **ps** | Report a snapshot of the current processes. |
| **pwd** | Print name of current/working directory. |
| **python** | Run real Python scripts, one-liners, or piped code in CPython 3.14. |
| **read_messages** | Reads all messages from a job's message queue. |
| **reboot** | Reboot the system. |
| **remix** | Synthesizes a new article from two source documents using AI. |
| **removeuser** | Remove a user from the system. |
| **rename** | Rename a file. |
| **reset** | Reset the filesystem to its initial state. |
| **restore** | Restores the FractalOS system state from a backup file. |
| **ritual** | Perform a multi-step, atmospheric ritual. |
| **rm** | Remove files or directories. |
| **rmdir** | Remove empty directories. |
| **roll** | A utility for rolling polyhedral dice. |
| **run** | Execute commands from a file in the current shell. |
| **samwise** | AI agent shell (Gemini / Ollama), Autopilot, and dry-run planner. |
| **score** | Displays user productivity scores. |
| **scp** | Secure copy over FractalOS mesh network (alias to mesh-cp). |
| **sed** | Stream editor for filtering and transforming text. |
| **set** | Set or display shell variables. |
| **shuf** | Generate random permutations. |
| **sort** | Sort lines of text files. |
| **split** | Split terminal into multiple panes and manage multiplexer layout. |
| **split_h** | Split the terminal horizontally into two panes. |
| **split_v** | Split the terminal vertically into two panes. |
| **status** | View system status, tray monitors, and notification states. |
| **story** | A narrative-driven version control system. |
| **storyboard** | Analyzes and creates a narrative summary of files. |
| **su** | Substitute user identity. |
| **sudo** | Execute a command as another user. |
| **swarm** | Manage mesh swarm safety policies, peer agent delegations, and audit logs. |
| **sync** | Synchronize data on disk with memory. |
| **tail** | Output the last part of files. |
| **talk** | Interactive two-way chat with another node on the mesh. |
| **theme** | Manages the visual and auditory theme of the OS. |
| **top** | Display a real-time view of running processes. |
| **touch** | Change file timestamps. |
| **tr** | Translate, squeeze, and/or delete characters. |
| **tree** | List contents of directories in a tree-like format. |
| **true** | Do nothing, successfully. |
| **ttt** | Tic-Tac-Toe terminal game. |
| **unalias** | Remove alias definitions. |
| **uniq** | Report or omit repeated lines. |
| **unset** | Unset shell variables. |
| **unzip** | List, test and extract compressed files in a ZIP archive. |
| **upload** | Upload files from your local machine to FractalOS. |
| **uptime** | Tell how long the system has been running. |
| **useradd** | Create a new user account. |
| **usermod** | Modify a user account. |
| **visudo** | Edit the sudoers file safely. |
| **wall** | Broadcast a message to all terminals across the mesh network. |
| **wc** | Print newline, word, and byte counts for each file. |
| **who** | Show who is logged on. |
| **whoami** | Print effective user ID. |
| **window** | Manage graphical application windows (alias for wm). |
| **wm** | Window manager for floating, docked, and tiled app viewports. |
| **xargs** | Build and execute command lines from standard input. |
| **xor** | Perform XOR encryption/decryption. |
| **zip** | Package and compress (archive) files. |


---

## Testing & Verification

FractalOS features a comprehensive verification suite spanning fast unit tests, headless browser smoke tests, in-OS diagnostic test suites, and autonomous agent graders:

```bash
# Instant structure & manifest validation (Node.js, no browser required)
node tests/structure.js

# Headless browser smoke test
node tests/smoke.js http://127.0.0.1:8000/index.html

# Full in-OS diagnostic suite (runs extras/diag.sh inside Pyodide)
node tests/diag.js http://127.0.0.1:8000/index.html

# Autonomous AI agent harness (tests Ollama / Gemini against live filesystem)
AGENT_MODEL=llama3.1:8b node tests/agent.js http://127.0.0.1:8000/index.html

# Fast offline agent unit tests
python3 tests/agent_unit.py
node tests/agent_grading.js
```

See [docs/TESTING.md](docs/TESTING.md) for full testing workflows and configuration recipes.

---

## Contributing

We welcome contributions from developers, designers, and terminal enthusiasts!

Please review [CONTRIBUTING.md](CONTRIBUTING.md) for architectural guidelines, coding conventions, and pull request procedures.

Working on FractalOS with an AI agent? Review [AGENTS.md](AGENTS.md), [docs/HANDOFF.md](docs/HANDOFF.md), [docs/ROADMAP.md](docs/ROADMAP.md), and [docs/DECISIONS.md](docs/DECISIONS.md) to understand current state and project memory.

---

## License

FractalOS is open-source software licensed under the MIT License.
