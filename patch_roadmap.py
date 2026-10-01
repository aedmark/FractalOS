import sys

with open('docs/ROADMAP.md', 'r') as f:
    content = f.read()

phase_6 = """
## Phase 6: The Bare-Metal Appliance (Fractal Pi)

Bring FractalOS full circle by deploying it as the primary interface of physical hardware (ARM64 / Raspberry Pi).

- [ ] P6-01 **Kiosk Architecture**: Design the boot sequence. (Minimal Debian/Buildroot -> X11/Wayland -> Chromium Kiosk or Neutralinojs).
- [ ] P6-02 **Build Script (`build_distro.sh`)**: A script to automate the provisioning of a base image (e.g., Raspberry Pi OS Lite), installing dependencies, and configuring auto-login and auto-start.
- [ ] P6-03 **Hardware Integration**: Expose Python modules to allow FractalOS to interact with GPIO pins or local hardware interfaces (bridging Neutralino's native API or a local WebSocket backend).
- [ ] P6-04 **Peer Discovery on Boot**: Ensure the OS automatically starts the signaling server or connects to the local mesh network upon boot.
"""

content += phase_6

with open('docs/ROADMAP.md', 'w') as f:
    f.write(content)
