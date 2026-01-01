# CHANGELOG.md

## [Unreleased] - BoneAmanita Integration

### 🚀 New Features (The Kinetic Engine)
- **BoneAmanita Autopilot:** Integrated a state-aware, kinetic AI driver accessible via `gemini --autopilot`.
    - **The Switch:** Added `--autopilot` (`-a`) and `--force` (`-f`) flags to the `gemini` command.
    - **The Brain:** Created `bone_driver.py` to handle system prompting, physics injection, and safety auditing.
    - **The Conscience:** implemented "Voltage" metrics to assess the risk of AI plans (e.g., `rm` is High Voltage, `ls` is Low Voltage).
    - **The Loop:** `ai_manager.py` now supports "Stateless Memory Injection," allowing the AI to remember `cd` changes across execution steps.

- **New Command: `forge`**
    - A specialized file-writing tool (`resources/core/commands/forge.py`) designed for AI use.
    - Supports atomic writes and newline expansion (`\n`) to replace the clumsy `echo` redirection for code generation.

### ⚡ System Improvements
- **Expanded Whitelist:** Updated `ai_manager.py` to allow the AI to use `forge`, `run`, `chmod`, and `python`.
- **Manifest Update:** Updated `resources/bridge.js` to include `bone_driver` in the Python Kernel boot sequence.
- **Safety Calibration:** Tuned the "Voltage" costs to distinguish between "Creation" (High Cost) and "Execution" (Medium Cost), enabling smoother developer workflows.

### 🐛 Bug Fixes
- **Ghost Limb Fix:** Resolved `ModuleNotFoundError` for `bone_driver` by correctly registering it in the Kernel Manifest.
- **Amnesia Fix:** Patched `ai_manager.py` to inject `simulated_current_path` into the execution context, preventing the Autopilot from defaulting to `/` (Root) during multi-step plans.
- **Cache Exorcism:** Purged stale `gemini.py` definitions from the browser/Python cache.

---

## [0.0.5] - 2024-XX-XX
### Added
- Initial release of FractalOS (Hybrid Web/Python Architecture).
- Core Kernel (`kernel.py`, `filesystem.py`, `executor.py`).
- AI Manager with basic "Agentic Search" (Librarian Mode).
- Basic Tools: `ls`, `cat`, `grep`, `story`, `edit`.
