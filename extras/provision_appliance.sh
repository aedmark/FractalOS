#!/usr/bin/env bash
# provision_appliance.sh - Turns a minimal Debian/Ubuntu/Raspberry Pi OS Lite install into a FractalOS Appliance.
# Supports x86_64, aarch64 (ARM64), and armhf.

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "=== FractalOS Appliance Provisioning Script ==="

# 1. Detect Architecture
ARCH=$(uname -m)
case "$ARCH" in
    x86_64)
        NEUTRALINO_BIN="neutralino-linux_x64"
        ;;
    aarch64|arm64)
        NEUTRALINO_BIN="neutralino-linux_arm64"
        ;;
    armv7l|armhf)
        NEUTRALINO_BIN="neutralino-linux_armhf"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac
echo "Architecture detected: $ARCH. Will use binary: $NEUTRALINO_BIN"

# 2. Install Dependencies
echo "Installing minimal X11 environment and WebKit dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    xserver-xorg xserver-xorg-video-fbdev x11-xserver-utils xinit openbox \
    libwebkit2gtk-4.0-37 libgtk-3-0 curl unzip git

# 3. Create a dedicated user (if it doesn't exist)
if ! id -u fractal >/dev/null 2>&1; then
    echo "Creating 'fractal' user..."
    useradd -m -s /bin/bash -G video,audio,render fractal
else
    echo "User 'fractal' already exists."
fi

# 4. Fetch the FractalOS repository
FRACTAL_DIR="/home/fractal/FractalOS"
if [ ! -d "$FRACTAL_DIR" ]; then
    echo "Cloning FractalOS repository..."
    sudo -u fractal git clone https://github.com/aedmark/FractalOS.git "$FRACTAL_DIR"
else
    echo "FractalOS repo already exists. Pulling latest..."
    sudo -u fractal bash -c "cd $FRACTAL_DIR && git pull"
fi

# 5. Download and set up Neutralino
echo "Downloading Neutralinojs 6.2.0..."
sudo -u fractal bash -c "cd $FRACTAL_DIR && curl -L -o neutralinojs.zip https://github.com/neutralinojs/neutralinojs/releases/download/v6.2.0/neutralinojs-v6.2.0.zip"
sudo -u fractal bash -c "cd $FRACTAL_DIR && unzip -o neutralinojs.zip $NEUTRALINO_BIN && chmod +x $NEUTRALINO_BIN && rm neutralinojs.zip"

# Ensure Neutralino configuration points to the correct binary name in the OS
# (It defaults to searching for 'fractalos', we'll just run the binary directly)

# 6. Create Openbox Kiosk Configuration
echo "Configuring Openbox..."
mkdir -p /home/fractal/.config/openbox
cat << 'OB_EOF' > /home/fractal/.config/openbox/autostart
# Disable screen blanking
xset s off
xset s noblank
xset -dpms

# Launch FractalOS in full screen
cd /home/fractal/FractalOS
./'$NEUTRALINO_BIN' --window-enable-inspector=false --window-full-screen=true &
OB_EOF
# Replace the literal with the actual variable
sed -i "s/'\$NEUTRALINO_BIN'/$NEUTRALINO_BIN/g" /home/fractal/.config/openbox/autostart
chown -R fractal:fractal /home/fractal/.config

# 7. Create .xinitrc
cat << 'XINIT_EOF' > /home/fractal/.xinitrc
#!/bin/bash
exec openbox-session
XINIT_EOF
chown fractal:fractal /home/fractal/.xinitrc
chmod +x /home/fractal/.xinitrc

# 8. Setup Systemd Service for Autologin and X11 Start
echo "Creating systemd service for automatic GUI boot..."
cat << 'SYS_EOF' > /etc/systemd/system/fractalos-kiosk.service
[Unit]
Description=FractalOS Kiosk Mode
After=systemd-user-sessions.service network-online.target plymouth-quit-wait.service
Wants=network-online.target

[Service]
User=fractal
Group=fractal
PAMName=login
Environment=DISPLAY=:0
TTYPath=/dev/tty7
ExecStart=/usr/bin/startx -- /usr/bin/X :0 -nolisten tcp vt7
Restart=always
RestartSec=5
StandardInput=tty

[Install]
WantedBy=graphical.target
SYS_EOF

systemctl daemon-reload
systemctl enable fractalos-kiosk.service

echo ""
echo "=== Provisioning Complete! ==="
echo "You can test the kiosk now by running: sudo systemctl start fractalos-kiosk.service"
echo "On the next reboot, FractalOS will automatically launch in full screen!"
