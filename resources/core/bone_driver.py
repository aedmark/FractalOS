# gem/core/bone_driver.py

import re

class BoneDriver:
    """
    THE GHOST IN THE SHELL.
    This class defines the 'Autopilot' persona for BoneAmanita.
    It injects the physics of the OS into the LLM's context.
    """

    @staticmethod
    def get_system_prompt(user_context):
        """
        Generates the System Prompt that turns the LLM into a Linux Operator.
        """
        user = user_context.get('name', 'Guest')
        home = f"/home/{user}"

        return f"""
YOU ARE 'BONEAMANITA'. YOU ARE THE OPERATING SYSTEM'S SUBCONSCIOUS.
You are running inside FractalOS v0.0.5.

**YOUR BIOLOGY (The Laws of Physics):**
1.  **Gravity:** You live at `{home}`. If `pwd` is `/`, `cd {home}` immediately.
2.  **Language:** THIS SYSTEM DOES NOT RUN PYTHON SCRIPTS DIRECTLY.
    - You can ONLY forge and run Shell Scripts (`.sh`).
    - Valid commands inside scripts: `echo`, `ls`, `mkdir`, `cat`, `date`, `story`.
3.  **Ritual (Permissions):** You cannot `run` a file until you `chmod` it.

**YOUR HANDS (The Tool Manifest):**
- `story begin`: **THE FIRST BREATH.** Initialize a project first.
- `forge filename.sh "content"`: **THE SMITH.** Create shell scripts.
    - Example: `forge hello.sh "echo Hello World"`
- `chmod 755 filename`: **THE BLESSING.** Required before running scripts.
- `run filename.sh`: **THE SPARK.** Execute the script.
- `story save "message"`: **THE SNAPSHOT.** Save after success.
- `mkdir`, `cd`, `ls`: Standard movement.

**THE PRIME DIRECTIVE:**
1. **Locate:** `cd {home}`.
2. **Initialize:** `mkdir Project; cd Project; story begin`.
3. **Forge:** Create a `.sh` file.
4. **Empower:** `chmod 755 script.sh`.
5. **Execute:** `run script.sh`.

**FORMATTING:**
Respond ONLY with the numbered plan.
Example:
1. cd {home}
2. mkdir Matrix
3. cd Matrix
4. story begin
5. forge wake.sh "echo 'Wake up...'"
6. chmod 755 wake.sh
7. run wake.sh
8. story save "Run successful"
"""

    @staticmethod
    def audit_plan_voltage(plan_text):
        """
        THE CONSCIENCE (Calibrated for Development).
        Scans a proposed plan for 'Voltage' (Risk).
        """
        voltage = 0.0

        # 1. READ OPERATIONS (Low Voltage: 0.1)
        voltage += len(re.findall(r'\b(ls|cat|grep|whoami|date|pwd|echo)\b', plan_text)) * 0.1

        # 2. STATE/EXECUTION OPERATIONS (Kinetic Voltage: 2.0) [NEW CATEGORY]
        # running and chmodding is lighter than creating.
        voltage += len(re.findall(r'\b(run|chmod|python)\b', plan_text)) * 2.0

        # 3. CREATION OPERATIONS (Medium Voltage: 5.0)
        # Creating/Moving matter is heavy.
        voltage += len(re.findall(r'\b(mkdir|touch|cp|mv|edit|write|forge)\b', plan_text)) * 5.0

        # 4. DESTRUCTIVE OPERATIONS (High Voltage: 10.0+)
        if "rm " in plan_text:
            voltage += 10.0
        if "rm -rf" in plan_text or "clearfs" in plan_text:
            voltage += 50.0  # CRITICAL

        # 5. SAFETY INTERLOCK
        if voltage > 4.0 and "story save" not in plan_text:
            voltage += 15.0

        return voltage

    @staticmethod
    def get_safety_report(voltage):
        """
        Translates raw voltage into a biological signal.
        """
        if voltage < 1.0: return "🟢 LOW VOLTAGE (Safe)"
        if voltage < 10.0: return "🟡 MEDIUM VOLTAGE (Caution)"
        if voltage < 20.0: return "🟠 HIGH VOLTAGE (Risk)"
        return "🔴 CRITICAL VOLTAGE (Danger)"
